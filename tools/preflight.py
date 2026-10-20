#!/usr/bin/env python3
import argparse
import base64
import json
import netrc
import os
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import jenkins_wait

CONFIG_PATH = os.path.join(ROOT, 'config', 'upmerge.toml')
JDK = os.path.expanduser('~/.jdks/jdk-25')
SONAR_API = 'https://sonarcloud.io/api'
ATLASSIAN_HOST = 'unifly.atlassian.net'
SKILLS = {'jenkins': True, 'sonar-lint': True, 'confluence': False}

checks = []
paths = {}


def add(check, status, detail='', fix=''):
    checks.append({'check': check, 'status': status, 'detail': detail, 'fix': fix})


def run(cmd, cwd=ROOT, timeout=30):
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return subprocess.CompletedProcess(cmd, 127, '', f'{cmd[0]}: not found')
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, '', f'{cmd[0]}: timed out after {timeout}s')


def last_line(result):
    lines = (result.stderr or result.stdout).strip().splitlines()
    return lines[-1] if lines else f'exit {result.returncode}'


def http_json(url, header):
    req = urllib.request.Request(url, headers={'Authorization': header, 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        return 0, str(e)


def basic(login, password):
    return 'Basic ' + base64.b64encode(f'{login}:{password}'.encode()).decode()


def check_python():
    version = '.'.join(map(str, sys.version_info[:3]))
    if sys.version_info >= (3, 11):
        add('python', 'ok', version)
        return True
    add('python', 'fail', f'{version}, the scanner needs 3.11 or newer for tomllib', 'install Python 3.11 or newer')
    return False


def check_config():
    import tomllib
    try:
        with open(CONFIG_PATH, 'rb') as fh:
            config = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as e:
        add('configuration', 'fail', f'config/upmerge.toml: {e}', 'fix config/upmerge.toml')
        return None
    missing = [k for k in ('github_org', 'branch_chain', 'repos') if not config.get(k)]
    if missing:
        add('configuration', 'fail', f'config/upmerge.toml lacks {", ".join(missing)}', 'fix config/upmerge.toml')
        return None
    add('configuration', 'ok', f"{len(config['repos'])} repos, chain {' → '.join(config['branch_chain'])}")
    return config


def check_git_identity():
    name = run(['git', 'config', 'user.name']).stdout.strip()
    email = run(['git', 'config', 'user.email']).stdout.strip()
    if name and email:
        add('git identity', 'ok', 'user.name and user.email are set')
    else:
        add('git identity', 'fail', 'user.name or user.email is not set; merge commits need them',
            'git config --global user.name "<your name>" && git config --global user.email "<your e-mail>"')


def check_gh():
    status = run(['gh', 'auth', 'status'])
    if status.returncode != 0:
        add('gh login', 'fail', last_line(status), 'gh auth login')
        return None
    login = run(['gh', 'api', 'user', '--jq', '.login']).stdout.strip()
    if not login:
        add('gh login', 'fail', 'gh is logged in but `gh api user` gave no login', 'gh auth refresh')
        return None
    add('gh login', 'ok', f'logged in as {login}')
    return login


def check_ssh():
    r = run(['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'git@github.com'], timeout=20)
    text = (r.stderr + r.stdout).strip()
    if 'successfully authenticated' in text:
        add('ssh to github', 'ok', text.split('!')[0] + '!')
    else:
        add('ssh to github', 'fail', text.splitlines()[-1] if text else f'exit {r.returncode}',
            'ssh-keygen -t ed25519 && gh ssh-key add ~/.ssh/id_ed25519.pub')


def check_forks(config, user, only):
    org = config['github_org']
    for repo in (r['name'] for r in config['repos']):
        if only and repo not in only:
            continue
        cmd = ['gh', 'api', f'repos/{user}/{repo}', '--jq', '[.fork, (.parent.full_name // "")] | @tsv']
        r = run(cmd)
        if r.returncode != 0 and 'HTTP 404' not in r.stderr:
            r = run(cmd)
        if r.returncode != 0:
            if 'HTTP 404' in r.stderr:
                add(f'fork {repo}', 'fail', f'{user}/{repo} does not exist', f'gh repo fork {org}/{repo} --clone=false')
            else:
                add(f'fork {repo}', 'fail', f'could not check {user}/{repo}: {last_line(r)}', 'run the preflight again')
            continue
        is_fork, parent = (r.stdout.strip().split('\t') + [''])[:2]
        if is_fork == 'true' and parent == f'{org}/{repo}':
            add(f'fork {repo}', 'ok', f'{user}/{repo}')
        else:
            add(f'fork {repo}', 'fail', f'{user}/{repo} exists but is not a fork of {org}/{repo}',
                f'rename or remove {user}/{repo}, then gh repo fork {org}/{repo} --clone=false')


def check_jdk():
    r = run([os.path.join(JDK, 'bin', 'java'), '-version'])
    text = (r.stderr + r.stdout).strip()
    if r.returncode == 0 and 'version "25' in text:
        add('jdk 25', 'ok', text.splitlines()[0])
    else:
        add('jdk 25', 'fail', f'no JDK 25 in {JDK}' if r.returncode else text.splitlines()[0],
            'install JDK 25 into ~/.jdks/jdk-25 (or link it there)')


def check_node():
    found = {tool: run([tool, '--version']) for tool in ('node', 'npm', 'corepack')}
    missing = [tool for tool, r in found.items() if r.returncode != 0]
    if missing:
        add('node tools', 'warn', f'missing: {", ".join(missing)}; needed for the node and hybrid repos',
            'install Node.js (it brings npm and corepack)')
    else:
        add('node tools', 'ok', ', '.join(f'{t} {r.stdout.strip()}' for t, r in found.items()))


def find_skill(name):
    for d in jenkins_wait.skills_dirs():
        candidate = os.path.join(d, name)
        if os.path.isfile(os.path.join(candidate, 'SKILL.md')):
            return candidate
    return None


def check_skills():
    found = {}
    target = jenkins_wait.skills_dirs()[0]
    for name, required in SKILLS.items():
        path = find_skill(name)
        found[name] = path
        if path:
            paths[f'{name}_skill'] = path
            add(f'skill {name}', 'ok', path)
        else:
            add(f'skill {name}', 'fail' if required else 'warn',
                'not installed' + ('' if required else '; hard merges are then resolved from git only'),
                f'cp -r setup/skills/{name} {target}/')
    return found


def credential_file(check, path, required, example):
    severity = 'fail' if required else 'warn'
    if not os.path.isfile(example):
        skill = os.path.basename(os.path.dirname(path))
        example = os.path.join('setup', 'skills', skill, os.path.basename(example))
    if not os.path.isfile(path):
        add(check, severity, f'{path} is missing', f'cp {example} {path} && chmod 600 {path}, then fill it in')
        return None
    text = open(path, encoding='utf-8', errors='replace').read()
    if '<your' in text:
        add(check, severity, f'{path} still holds the <...> placeholders', f'fill in {path}')
        return None
    if os.stat(path).st_mode & 0o077:
        add(f'{check} mode', 'warn', f'{path} is readable by others', f'chmod 600 {path}')
    return text


def netrc_login(path, host):
    try:
        entry = netrc.netrc(path).authenticators(host)
    except (netrc.NetrcParseError, OSError) as e:
        return None, str(e)
    if not entry:
        return None, f'no "machine {host}" line'
    return entry, ''


def check_jenkins(skill):
    path = jenkins_wait.netrc_path() or os.path.join(skill or jenkins_wait.skills_dirs()[0] + '/jenkins', '.netrc')
    if not credential_file('jenkins credentials', path, True, os.path.join(os.path.dirname(path), '.netrc.example')):
        return
    entry, error = netrc_login(path, jenkins_wait.HOST)
    if not entry:
        add('jenkins credentials', 'fail', f'{path}: {error}', f'see setup/skills/jenkins/.netrc.example')
        return
    paths['jenkins_netrc'] = path
    status, body = http_json(f'https://{jenkins_wait.HOST}/whoAmI/api/json', basic(entry[0], entry[2]))
    if status == 200 and isinstance(body, dict) and not body.get('anonymous', True):
        add('jenkins credentials', 'ok', f'{jenkins_wait.HOST} accepts the token')
    else:
        add('jenkins credentials', 'fail', f'{jenkins_wait.HOST} rejected the login (HTTP {status})',
            'create a new API token in Jenkins (your user, Security) and put it in the .netrc')


def check_sonar(skill):
    if not skill:
        return
    path = os.path.join(skill, 'token')
    script = os.path.join(skill, 'sonar_check.py')
    if os.path.isfile(script):
        paths['sonar_check'] = script
    else:
        add('sonar-lint script', 'fail', f'{script} is missing', f'cp setup/skills/sonar-lint/sonar_check.py {skill}/')
    text = credential_file('sonar credentials', path, True, os.path.join(skill, 'token.example'))
    if not text:
        return
    status, body = http_json(f'{SONAR_API}/users/current', basic(text.strip(), ''))
    if status == 200 and isinstance(body, dict) and body.get('isLoggedIn'):
        add('sonar credentials', 'ok', 'sonarcloud.io accepts the token')
    else:
        add('sonar credentials', 'fail', f'sonarcloud.io rejected the token (HTTP {status})',
            'create a new token at https://sonarcloud.io/account/security and put it in the token file')


def check_confluence(skill):
    if not skill:
        return
    path = os.path.join(skill, '.netrc')
    if not credential_file('atlassian credentials', path, False, os.path.join(skill, '.netrc.example')):
        return
    entry, error = netrc_login(path, ATLASSIAN_HOST)
    if not entry:
        add('atlassian credentials', 'warn', f'{path}: {error}', 'see setup/skills/confluence/.netrc.example')
        return
    paths['confluence_netrc'] = path
    status, _ = http_json(f'https://{ATLASSIAN_HOST}/rest/api/3/myself', basic(entry[0], entry[2]))
    if status == 200:
        add('atlassian credentials', 'ok', f'{ATLASSIAN_HOST} accepts the token')
    else:
        add('atlassian credentials', 'warn', f'{ATLASSIAN_HOST} rejected the login (HTTP {status})',
            'create a new API token at https://id.atlassian.com/manage-profile/security/api-tokens')


def print_table():
    marks = {'ok': 'OK  ', 'warn': 'WARN', 'fail': 'FAIL'}
    width = max(len(c['check']) for c in checks)
    for c in checks:
        print(f"{marks[c['status']]}  {c['check']:<{width}}  {c['detail']}")
        if c['status'] != 'ok' and c['fix']:
            print(f"{'':<{width + 8}}fix: {c['fix']}")


def main() -> int:
    ap = argparse.ArgumentParser(description='Check that everything the upmerge needs is set up on this machine.')
    ap.add_argument('--json', action='store_true', help='machine-readable output for the upmerge skill')
    ap.add_argument('--repos', nargs='*', help='only check the forks of these repos')
    args = ap.parse_args()

    user = None
    if check_python():
        config = check_config()
        check_git_identity()
        user = check_gh()
        check_ssh()
        if config and user:
            check_forks(config, user, set(args.repos or []))
        check_jdk()
        check_node()
        skills = check_skills()
        check_jenkins(skills['jenkins'])
        check_sonar(skills['sonar-lint'])
        check_confluence(skills['confluence'])

    ok = not any(c['status'] == 'fail' for c in checks)
    if args.json:
        print(json.dumps({'ok': ok, 'fork_user': user, 'paths': paths, 'checks': checks}, indent=1))
    else:
        print_table()
        print('\nAll set.' if ok else '\nFix the FAIL lines, then run this again.')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
