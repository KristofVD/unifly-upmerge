#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from pathlib import PurePosixPath

TIERS = {
    'clean': {'model': None, 'effort': None, 'verifier_model': 'sonnet', 'verifier_effort': 'medium', 'tickets': False},
    'mechanical': {'model': 'sonnet', 'effort': 'medium', 'verifier_model': 'sonnet', 'verifier_effort': 'medium', 'tickets': False},
    'moderate': {'model': 'opus', 'effort': 'high', 'verifier_model': 'opus', 'verifier_effort': 'high', 'tickets': False},
    'hard': {'model': 'opus', 'effort': 'max', 'verifier_model': 'opus', 'verifier_effort': 'max', 'tickets': True},
}

LOCKFILES = {'yarn.lock', 'package-lock.json', 'pnpm-lock.yaml', 'gradle.lockfile', 'npm-shrinkwrap.json'}
MANIFESTS = {'package.json', 'build.gradle', 'build.gradle.kts', 'settings.gradle', 'settings.gradle.kts',
             'gradle.properties', 'pom.xml', 'libs.versions.toml'}
DOC_SUFFIXES = {'.md', '.adoc', '.txt', '.rst'}
CONFIG_SUFFIXES = {'.yml', '.yaml', '.json', '.xml', '.properties', '.toml', '.ini', '.conf', '.j2', '.cfg'}
IMPORT_LINE = re.compile(r'^\s*(import\s|export\s+\*\s+from\s|export\s+\{[^}]*\}\s+from\s|from\s+\S+\s+import\s|#include\s|using\s+[\w.]+;|package\s)')

CONFLICT_STATUS = {'UU', 'AA', 'DD', 'AU', 'UA', 'DU', 'UD'}


def category(path: str) -> str:
    p = PurePosixPath(path)
    name, suffix, parts = p.name, p.suffix.lower(), set(p.parts)
    if name in LOCKFILES:
        return 'lockfile'
    if ({'locales', 'i18n', 'translations', 'messages'} & parts) and suffix in {'.json', '.properties', '.yml', '.yaml', '.po'}:
        return 'locale'
    if re.match(r'messages(_\w+)?\.properties$', name):
        return 'locale'
    if name in MANIFESTS:
        return 'manifest'
    if suffix in DOC_SUFFIXES or name == 'antora.yml' or 'docs' in parts and suffix in CONFIG_SUFFIXES:
        return 'docs'
    if suffix in CONFIG_SUFFIXES:
        return 'config'
    if {'test', 'tests', 'testIntegration', '__tests__'} & parts or re.search(r'\.(test|spec)\.[jt]sx?$', name) or re.search(r'Test\w*\.(java|kt)$', name):
        return 'test-code'
    return 'code'


def git(wd: str, *args: str) -> str:
    return subprocess.run(['git', '-C', wd, *args], capture_output=True, text=True, check=True).stdout


def unmerged(wd: str) -> dict:
    out = {}
    for line in git(wd, 'status', '--porcelain=v1', '-z').split('\0'):
        if len(line) > 3 and line[:2] in CONFLICT_STATUS:
            out[line[3:]] = line[:2]
    return out


def parse_hunks(text: str) -> list:
    hunks, state, ours, theirs = [], None, [], []
    for raw in text.splitlines():
        line = raw.rstrip('\r')
        if line.startswith('<<<<<<<'):
            state, ours, theirs = 'ours', [], []
        elif state and line.startswith('|||||||'):
            state = 'base'
        elif state and line.startswith('======='):
            state = 'theirs'
        elif state and line.startswith('>>>>>>>'):
            hunks.append((ours, theirs))
            state = None
        elif state == 'ours':
            ours.append(line)
        elif state == 'theirs':
            theirs.append(line)
    return hunks


def import_only(hunk) -> bool:
    lines = [l for l in hunk[0] + hunk[1] if l.strip()]
    return bool(lines) and all(IMPORT_LINE.match(l) for l in lines)


def score_file(cat: str, status: str, hunks) -> tuple:
    real = [h for h in hunks if not import_only(h)]
    biggest = max((max(len(o), len(t)) for o, t in real), default=0)
    if status in {'DU', 'UD'}:
        if cat in {'code', 'test-code'}:
            return (6 if cat == 'code' else 5), 'modify/delete: a change on one side has to be ported or dropped'
        return 2, 'modify/delete on a non-code file'
    if status in {'AA', 'AU', 'UA'} and cat in {'code', 'test-code'}:
        return 5, 'added on both sides'
    if cat == 'lockfile':
        return 1, 'regenerate'
    if cat == 'docs':
        return 1, 'docs'
    if cat == 'locale':
        return 2, f'{len(hunks)} locale hunks'
    if cat == 'manifest':
        return 2, f'{len(hunks)} manifest hunks'
    if hunks and not real:
        return 1, f'{len(hunks)} import-only hunks'
    if cat == 'config':
        return (4 if len(real) > 3 or biggest > 20 else 3), f'{len(real)} config hunks, largest {biggest} lines'
    base = 4 if cat == 'code' else 3
    if biggest > 20:
        base += 1
    if len(real) > 3:
        base += 1
    if biggest > 60:
        base += 1
    return min(base, 9), f'{len(real)} code hunks, largest {biggest} lines'


def tier_for(score: int) -> str:
    if score <= 2:
        return 'mechanical'
    if score <= 5:
        return 'moderate'
    return 'hard'


def assess(files: list) -> dict:
    top = max((f['score'] for f in files), default=0)
    code_files = sum(1 for f in files if f['category'] in {'code', 'test-code'} and f['score'] >= 3)
    score = min(top + (1 if code_files >= 5 else 0), 10)
    if not files:
        return {'score': 0, 'tier': 'clean', **TIERS['clean'], 'files': []}
    tier = tier_for(score)
    return {'score': score, 'tier': tier, **TIERS[tier], 'code_files_with_real_hunks': code_files, 'files': files}


def from_workdir(wd: str) -> dict:
    files = []
    for path, status in sorted(unmerged(wd).items()):
        cat = category(path)
        hunks = []
        if status not in {'DU', 'UD', 'DD'}:
            try:
                with open(f'{wd}/{path}', encoding='utf-8', errors='replace') as fh:
                    hunks = parse_hunks(fh.read())
            except FileNotFoundError:
                pass
        score, why = score_file(cat, status, hunks)
        files.append({'file': path, 'status': status, 'category': cat, 'hunks': len(hunks), 'score': score, 'why': why})
    return assess(files)


def from_paths(paths: list) -> dict:
    files = []
    for path in paths:
        cat = category(path)
        score = {'lockfile': 1, 'docs': 1, 'locale': 2, 'manifest': 2, 'config': 3, 'test-code': 3, 'code': 4}[cat]
        files.append({'file': path, 'status': '?', 'category': cat, 'hunks': None, 'score': score, 'why': 'predicted from path only'})
    result = assess(files)
    result['predicted'] = True
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description='Score how hard the conflicts of an upmerge are and pick the resolver model/effort.')
    ap.add_argument('--workdir', help='clone with a merge in progress (real hunks)')
    ap.add_argument('--files', nargs='*', help='conflict file paths only, e.g. from scan.json (prediction)')
    args = ap.parse_args()
    if args.workdir:
        result = from_workdir(args.workdir)
    elif args.files is not None:
        result = from_paths(args.files)
    else:
        ap.error('give --workdir or --files')
    json.dump(result, sys.stdout, indent=1)
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
