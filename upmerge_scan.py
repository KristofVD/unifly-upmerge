#!/usr/bin/env python3
"""Improved upmerge scanner for the version-branch upmerges.

Replaces the read-side of repo_check.py + branch_check.py. For every repo it
walks the BRANCH_CHAIN and, for each consecutive (source -> target) pair where
source has commits not yet in target, reports:

  * the number of pending commits (and their subjects),
  * the *actual* conflicting files (via a real trial merge in a throwaway
    worktree -- far more reliable than scanning legacy `git merge-tree` output),
  * the repo build type (gradle-java / node / hybrid / other) and which quality
    gates exist (spotless / integrationTest / npm scripts).

Improvements over the old scripts:
  * Output is grouped per-repo and printed atomically -- no more interleaving of
    buffered parent headers with flushed child diff lines.
  * Clones are cached under .cache/<repo> and refreshed with `git fetch` instead
    of being re-cloned from scratch on every run.
  * `--json` emits a machine-readable report consumed by the upmerge skill.
  * Repos and the branch chain come from the configuration, config/upmerge.toml.

Usage:
    python3 upmerge_scan.py                      # scan all repos, human table
    python3 upmerge_scan.py unifly-tiles         # scan one (or more) by name
    python3 upmerge_scan.py --json unifly-tiles  # machine-readable JSON
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass, field, asdict
from typing import List, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(SCRIPT_DIR, '.cache')
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'config', 'upmerge.toml')

with open(CONFIG_PATH, 'rb') as config_file:
    CONFIG = tomllib.load(config_file)

BRANCH_CHAIN = CONFIG['branch_chain']

REPOS = [f"git@github.com:{CONFIG['github_org']}/{r['name']}.git" for r in CONFIG['repos']]

CI_META = {
    r['name']: {'jenkins_job': r.get('jenkins_job'), 'sonar_project': r.get('sonar_project')}
    for r in CONFIG['repos']
}


@dataclass
class PendingMerge:
    source: str
    target: str
    commit_count: int
    clean: bool
    conflict_files: List[str] = field(default_factory=list)
    commits: List[str] = field(default_factory=list)  # "<sha> <subject>"


@dataclass
class BuildInfo:
    type: str = 'unknown'            # gradle-java | node | hybrid | other
    has_gradle: bool = False
    has_node: bool = False
    has_spotless: bool = False
    has_integration_test: bool = False
    npm_scripts: List[str] = field(default_factory=list)


@dataclass
class RepoReport:
    name: str
    url: str
    browser_url: str
    error: Optional[str] = None
    missing_branches: List[str] = field(default_factory=list)
    build: BuildInfo = field(default_factory=BuildInfo)
    pending: List[PendingMerge] = field(default_factory=list)
    jenkins_job: Optional[str] = None
    sonar_project: Optional[str] = None


def repo_name(repo_url: str) -> str:
    return repo_url.split('/')[-1].removesuffix('.git')


def browser_url(repo_url: str) -> str:
    path = repo_url.split(':', 1)[1] if ':' in repo_url else repo_url
    return f"https://github.com/{path.removesuffix('.git')}"


def git(args: List[str], cwd: str = None, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=check)


def out(args: List[str], cwd: str = None) -> str:
    return git(args, cwd=cwd).stdout.strip()


def ensure_clone(repo_url: str, cache_path: str) -> bool:
    """Clone into the cache or fetch if it already exists. Returns success."""
    if os.path.isdir(os.path.join(cache_path, '.git')):
        r = git(['fetch', '--prune', 'origin'], cwd=cache_path)
        return r.returncode == 0
    os.makedirs(CACHE_DIR, exist_ok=True)
    r = git(['clone', '--quiet', repo_url, cache_path])
    return r.returncode == 0


def remote_branches(cache_path: str) -> set:
    refs = out(['for-each-ref', '--format=%(refname:short)', 'refs/remotes/origin'], cwd=cache_path)
    return {ln[len('origin/'):] for ln in refs.splitlines() if ln.startswith('origin/')}


def conflict_files(cache_path: str, source: str, target: str) -> List[str]:
    """Real trial merge in a throwaway worktree -> list of conflicting paths."""
    wt = tempfile.mkdtemp(prefix='upmerge-wt-')
    shutil.rmtree(wt, ignore_errors=True)  # git worktree add wants a fresh path
    try:
        add = git(['worktree', 'add', '--detach', wt, f'origin/{target}'], cwd=cache_path)
        if add.returncode != 0:
            return []  # treat as clean-unknown; caller still has commit info
        git(['merge', '--no-commit', '--no-ff', f'origin/{source}'], cwd=wt)
        files = out(['diff', '--name-only', '--diff-filter=U'], cwd=wt)
        git(['merge', '--abort'], cwd=wt)
        return [f for f in files.splitlines() if f]
    finally:
        git(['worktree', 'remove', '--force', wt], cwd=cache_path)
        git(['worktree', 'prune'], cwd=cache_path)
        shutil.rmtree(wt, ignore_errors=True)


def show_file(cache_path: str, ref: str, path: str) -> Optional[str]:
    r = git(['show', f'{ref}:{path}'], cwd=cache_path)
    return r.stdout if r.returncode == 0 else None


def detect_build(cache_path: str, ref: str) -> BuildInfo:
    info = BuildInfo()
    root = out(['ls-tree', '--name-only', ref], cwd=cache_path).splitlines()
    rootset = set(root)
    info.has_gradle = bool({'build.gradle', 'settings.gradle', 'gradlew'} & rootset)
    info.has_node = 'package.json' in rootset

    if info.has_gradle and info.has_node:
        info.type = 'hybrid'
    elif info.has_gradle:
        info.type = 'gradle-java'
    elif info.has_node:
        info.type = 'node'
    else:
        info.type = 'other'

    if info.has_gradle:
        # git grep on a ref needs no checkout.
        g = git(['grep', '-l', '-i', 'spotless', ref, '--', '*.gradle', 'buildSrc/'], cwd=cache_path)
        info.has_spotless = g.returncode == 0 and bool(g.stdout.strip())
        g = git(['grep', '-l', '-E', 'integrationTest|testIntegration', ref, '--', '*.gradle'], cwd=cache_path)
        info.has_integration_test = g.returncode == 0 and bool(g.stdout.strip())

    if info.has_node:
        pkg = show_file(cache_path, ref, 'package.json')
        if pkg:
            try:
                info.npm_scripts = sorted((json.loads(pkg).get('scripts') or {}).keys())
            except json.JSONDecodeError:
                pass
    return info


def scan_repo(repo_url: str, chain: List[str]) -> RepoReport:
    name = repo_name(repo_url)
    meta = CI_META.get(name, {})
    rep = RepoReport(name=name, url=repo_url, browser_url=browser_url(repo_url),
                     jenkins_job=meta.get('jenkins_job'), sonar_project=meta.get('sonar_project'))
    cache_path = os.path.join(CACHE_DIR, name)

    if not ensure_clone(repo_url, cache_path):
        rep.error = 'clone/fetch failed'
        return rep

    existing = remote_branches(cache_path)
    rep.missing_branches = [b for b in chain if b not in existing]

    # Build info from the highest existing chain branch (falls back down the chain).
    for ref in reversed(chain):
        if ref in existing:
            rep.build = detect_build(cache_path, f'origin/{ref}')
            break

    for i in range(len(chain) - 1):
        source, target = chain[i], chain[i + 1]
        if source not in existing or target not in existing:
            continue
        log = out(['log', '--oneline', f'origin/{target}..origin/{source}'], cwd=cache_path)
        commits = [c for c in log.splitlines() if c]
        if not commits:
            continue
        cfiles = conflict_files(cache_path, source, target)
        rep.pending.append(PendingMerge(
            source=source, target=target, commit_count=len(commits),
            clean=not cfiles, conflict_files=cfiles, commits=commits,
        ))
    return rep


def print_report(rep: RepoReport) -> None:
    """Atomic per-repo block -- built as one string so output never interleaves."""
    lines = [f"\n=== {rep.name} ===", f"  {rep.browser_url}"]
    if rep.error:
        lines.append(f"  ERROR: {rep.error}")
        print('\n'.join(lines), flush=True)
        return
    b = rep.build
    gates = []
    if b.has_spotless:
        gates.append('spotless')
    if b.has_integration_test:
        gates.append('integrationTest')
    if b.npm_scripts:
        gates.append('npm:' + ','.join(b.npm_scripts[:6]))
    lines.append(f"  build: {b.type}" + (f"  [{'; '.join(gates)}]" if gates else ""))
    lines.append(f"  ci: jenkins={rep.jenkins_job or '-'}  sonar={rep.sonar_project or '-'}")
    if rep.missing_branches:
        lines.append(f"  missing branches: {', '.join(rep.missing_branches)}")
    if not rep.pending:
        lines.append("  up to date ✓")
    for p in rep.pending:
        status = "clean" if p.clean else f"CONFLICTS ({len(p.conflict_files)} files)"
        lines.append(f"  * {p.source} → {p.target}  ({p.commit_count} commits)  [{status}]")
        for f in p.conflict_files:
            lines.append(f"      ✖ {f}")
    print('\n'.join(lines), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description='Scan repos for pending upmerges')
    ap.add_argument('repos', nargs='*', help='repo name filters (default: all)')
    ap.add_argument('--json', action='store_true', help='emit machine-readable JSON')
    args = ap.parse_args()

    selected = REPOS
    if args.repos:
        wanted = set(args.repos)
        selected = [r for r in REPOS if repo_name(r) in wanted]
        unknown = wanted - {repo_name(r) for r in REPOS}
        if unknown:
            print(f"Unknown repo(s): {', '.join(sorted(unknown))}", file=sys.stderr)
        if not selected:
            sys.exit(2)

    reports = []
    for repo in selected:
        if not args.json:
            print(f"Scanning {repo_name(repo)} ...", file=sys.stderr, flush=True)
        reports.append(scan_repo(repo, BRANCH_CHAIN))

    if args.json:
        print(json.dumps({'chain': BRANCH_CHAIN, 'repos': [asdict(r) for r in reports]}, indent=2))
    else:
        for rep in reports:
            print_report(rep)
        actionable = sum(len(r.pending) for r in reports)
        print(f"\n{actionable} pending merge(s) across {len(reports)} repo(s).")


if __name__ == '__main__':
    main()
