#!/usr/bin/env python3
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from upmerge_scan import detect_build

JDK = os.path.expanduser('~/.jdks/jdk-25')
MARKER = r'^(<<<<<<<|>>>>>>>|\|\|\|\|\|\|\|)( |$)'
PLACEHOLDER = re.compile(r'no test specified|^\s*exit 1\s*$')
DOCKER_HINTS = ('Could not find a valid Docker environment', 'DockerClientProviderStrategy', 'docker.sock')
NODE_SCRIPTS = ('lint', 'typecheck', 'test:unit|test')

gates = []


def gate(name, command, result, detail=''):
    gates.append({'gate': name, 'command': command, 'result': result, 'detail': detail})
    return result


def sh(cmd, cwd, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)


def tail(result, n=30):
    lines = (result.stdout + result.stderr).strip().splitlines()
    return '\n'.join(lines[-n:])


def wanted(name, only):
    return not only or name in only


def check_merge_state(wd, branch):
    if os.path.exists(os.path.join(wd, '.git', 'MERGE_HEAD')):
        return gate('merge-state', 'test ! -e .git/MERGE_HEAD', 'fail', 'a merge is still in progress')
    current = sh(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], wd).stdout.strip()
    if branch and current != branch:
        return gate('merge-state', 'git rev-parse --abbrev-ref HEAD', 'fail', f'on {current}, expected {branch}')
    return gate('merge-state', 'git rev-parse --abbrev-ref HEAD', 'pass', f'on {current}, merge committed')


def check_markers(wd):
    cmd = ['git', 'grep', '-n', '-I', '-E', MARKER]
    r = sh(cmd, wd)
    if r.returncode == 1:
        return gate('markers', ' '.join(cmd), 'pass', 'no conflict markers in tracked files')
    return gate('markers', ' '.join(cmd), 'fail', '\n'.join(r.stdout.splitlines()[:20]))


def check_carried(wd, source):
    cmd = ['git', 'merge-base', '--is-ancestor', f'origin/{source}', 'HEAD']
    if sh(cmd, wd).returncode == 0:
        return gate('carried', ' '.join(cmd), 'pass', f'every commit of origin/{source} is in HEAD')
    missing = sh(['git', 'log', '--oneline', f'HEAD..origin/{source}'], wd).stdout.splitlines()
    return gate('carried', ' '.join(cmd), 'fail', f'{len(missing)} commits missing:\n' + '\n'.join(missing[:20]))


def junit_failures(wd, since):
    failures = []
    for path in glob.glob(os.path.join(wd, '**', 'build', 'test-results', '**', '*.xml'), recursive=True):
        if os.path.getmtime(path) < since:
            continue
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            continue
        for case in tree.iter('testcase'):
            problem = case.find('failure')
            if problem is None:
                problem = case.find('error')
            if problem is None:
                continue
            text = (problem.get('message') or '') + '\n' + (problem.text or '')
            failures.append({
                'class': case.get('classname'), 'name': case.get('name'),
                'message': (problem.get('message') or text).strip().splitlines()[0][:200] if text.strip() else '',
                'needs_docker': any(hint in text for hint in DOCKER_HINTS),
            })
    return failures


def jvm_sources(wd):
    files = sh(['git', 'ls-files', '*.java', '*.kt', '*.groovy'], wd).stdout.splitlines()
    return any(not f.startswith(('buildSrc/', 'gradle/')) for f in files)


def gradle_gates(wd, info, java_home, only):
    env = dict(os.environ, JAVA_HOME=java_home)
    base = ['./gradlew', '--no-daemon', f'-Dorg.gradle.java.home={java_home}']
    gradlew = os.path.join(wd, 'gradlew')
    was_dirty = bool(sh(['git', 'status', '--porcelain', '--', 'gradlew'], wd).stdout.strip())
    with open(gradlew, 'rb') as fh:
        content = fh.read()
    with open(gradlew, 'wb') as fh:
        fh.write(content.replace(b'\r\n', b'\n'))
    os.chmod(gradlew, 0o755)
    result = {'formatting_changed': [], 'failing_tests': []}
    try:
        if info.has_spotless and wanted('spotless', only):
            r = sh(base + ['spotlessApply'], wd, env)
            changed = [line[3:] for line in sh(['git', 'status', '--porcelain'], wd).stdout.splitlines()
                       if not line.startswith('??') and line[3:] != 'gradlew']
            result['formatting_changed'] = changed
            detail = ('changed: ' + ', '.join(changed)) if changed else 'no formatting changes'
            gate('spotless', './gradlew spotlessApply', 'pass' if r.returncode == 0 else 'fail',
                 detail if r.returncode == 0 else tail(r))
        tasks = ['compileJava', 'compileTestJava'] + (['compileTestIntegrationJava'] if info.has_integration_test else [])
        compiled = True
        if wanted('compile', only):
            r = sh(base + tasks, wd, env)
            compiled = gate('compile', './gradlew ' + ' '.join(tasks), 'pass' if r.returncode == 0 else 'fail',
                            'BUILD SUCCESSFUL' if r.returncode == 0 else tail(r)) == 'pass'
        if wanted('test', only):
            if not compiled:
                gate('test', './gradlew test --continue', 'skipped', 'compile failed')
            else:
                start = time.time()
                r = sh(base + ['test', '--continue'], wd, env)
                failures = junit_failures(wd, start)
                real = [f for f in failures if not f['needs_docker']]
                docker = len(failures) - len(real)
                result['failing_tests'] = real
                if r.returncode == 0:
                    gate('test', './gradlew test --continue', 'pass', 'all unit tests passed')
                elif failures and not real:
                    gate('test', './gradlew test --continue', 'skipped',
                         f'only tests that need Docker failed ({docker}); they run in Jenkins')
                else:
                    listed = '\n'.join(f"{f['class']}.{f['name']}: {f['message']}" for f in real[:20])
                    gate('test', './gradlew test --continue', 'fail',
                         (listed or tail(r)) + (f'\n(+{docker} that need Docker)' if docker else ''))
        if info.has_integration_test and wanted('integrationTest', only):
            gate('integrationTest', './gradlew integrationTest', 'skipped', 'no Docker locally; Jenkins runs it on the PR')
    finally:
        if not was_dirty:
            sh(['git', 'checkout', '--', 'gradlew'], wd)
    return result


def package_manager(wd, pkg):
    field = pkg.get('packageManager') or ''
    if field.startswith('yarn@') or os.path.exists(os.path.join(wd, 'yarn.lock')):
        if field.startswith('yarn@'):
            berry = int(field[5:].split('.')[0]) >= 2
        else:
            berry = os.path.exists(os.path.join(wd, '.yarnrc.yml'))
        return 'yarn-berry' if berry else 'yarn'
    if field.startswith('pnpm@') or os.path.exists(os.path.join(wd, 'pnpm-lock.yaml')):
        return 'pnpm'
    return 'npm'


def node_gates(wd, only):
    with open(os.path.join(wd, 'package.json'), encoding='utf-8') as fh:
        pkg = json.load(fh)
    pm = package_manager(wd, pkg)
    install, runner = {
        'yarn-berry': (['corepack', 'yarn', 'install', '--immutable'], ['corepack', 'yarn']),
        'yarn': (['yarn', 'install', '--frozen-lockfile'], ['yarn']),
        'pnpm': (['corepack', 'pnpm', 'install', '--frozen-lockfile'], ['corepack', 'pnpm']),
        'npm': (['npm', 'ci'], ['npm', 'run']),
    }[pm]
    installed = True
    if wanted('install', only):
        r = sh(install, wd)
        installed = gate('install', ' '.join(install), 'pass' if r.returncode == 0 else 'fail',
                         'lockfile and package.json agree' if r.returncode == 0 else tail(r)) == 'pass'
    scripts = pkg.get('scripts') or {}
    for choice in NODE_SCRIPTS:
        name = next((n for n in choice.split('|') if n in scripts), choice.split('|')[-1])
        if not wanted(name, only):
            continue
        command = ' '.join(runner + [name])
        if name not in scripts or PLACEHOLDER.search(scripts[name]):
            gate(name, command, 'skipped', f'no real "{name}" script in package.json')
        elif not installed:
            gate(name, command, 'skipped', 'install failed')
        else:
            r = sh(runner + [name], wd)
            gate(name, command, 'pass' if r.returncode == 0 else 'fail', 'passed' if r.returncode == 0 else tail(r))
    return pm


def main() -> int:
    ap = argparse.ArgumentParser(description='Run the local gates of one upmerge: markers, carried commits, Spotless, compile, unit tests, lockfile install.')
    ap.add_argument('--workdir', required=True)
    ap.add_argument('--source', required=True)
    ap.add_argument('--target', required=True)
    ap.add_argument('--branch', help='the merge branch HEAD must be on')
    ap.add_argument('--only', nargs='*', help='run only these gates, e.g. compile test')
    ap.add_argument('--java-home', default=JDK)
    args = ap.parse_args()

    wd = os.path.abspath(args.workdir)
    only = set(args.only or [])
    info = detect_build(wd, 'HEAD')
    out = {'workdir': wd, 'head': sh(['git', 'rev-parse', 'HEAD'], wd).stdout.strip(), 'build': asdict(info),
           'formatting_changed': [], 'failing_tests': []}

    if wanted('merge-state', only):
        check_merge_state(wd, args.branch)
    if wanted('markers', only):
        check_markers(wd)
    if wanted('carried', only):
        check_carried(wd, args.source)
    if info.has_gradle and jvm_sources(wd):
        out.update(gradle_gates(wd, info, args.java_home, only))
    elif info.has_gradle and wanted('compile', only):
        gate('compile', 'git ls-files *.java *.kt *.groovy', 'skipped', 'no JVM sources: Gradle only versions and publishes this repo')
    if info.has_node:
        out['build']['package_manager'] = node_gates(wd, only)

    out['gates'] = gates
    out['overall'] = 'fail' if any(g['result'] == 'fail' for g in gates) else 'pass'
    print(json.dumps(out, indent=1))
    return 1 if out['overall'] == 'fail' else 0


if __name__ == '__main__':
    sys.exit(main())
