#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

from conflict_difficulty import category

MARKER = r'^(<<<<<<<|>>>>>>>|\|\|\|\|\|\|\|)( |$)'
CAP = 200
SLASH = {'.java', '.kt', '.groovy', '.gradle', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.scss', '.less', '.go', '.c', '.cpp', '.h', '.cs', '.swift', '.vue'}
STAR = SLASH | {'.css'}
HASH = {'.py', '.sh', '.bash', '.yml', '.yaml', '.properties', '.toml', '.cfg', '.conf', '.ini', '.rb', '.tf', '.j2', '.env'}
ANGLE = {'.xml', '.html', '.htm', '.md', '.bpmn', '.svg', '.vue', '.xsd', '.wsdl'}
DASH = {'.sql'}


def git(wd, *args):
    return subprocess.run(['git', '-C', wd, *args], capture_output=True, text=True)


def out(wd, *args):
    return git(wd, *args).stdout.strip()


def is_comment(path, text):
    line = text.strip()
    name = os.path.basename(path)
    ext = os.path.splitext(name)[1].lower()
    if name in ('Jenkinsfile',) or ext in SLASH:
        if line.startswith('//') or line.startswith('/*'):
            return True
    if ext in STAR and line.startswith('*'):
        return True
    if (ext in HASH or name in ('Dockerfile', 'Makefile', '.gitignore')) and line.startswith('#'):
        return True
    if ext in ANGLE and line.startswith('<!--'):
        return True
    return ext in DASH and line.startswith('--')


def norm(text):
    return re.sub(r'\s+', '', text)


def find_merge(wd, target):
    merges = out(wd, 'rev-list', '--merges', '--first-parent', '--reverse', f'origin/{target}..HEAD').splitlines()
    return merges[0] if merges else None


def check_parents(wd, merge, source, target):
    parents = out(wd, 'rev-list', '--parents', '-n1', merge).split()[1:]
    expected = [out(wd, 'rev-parse', f'origin/{target}'), out(wd, 'rev-parse', f'origin/{source}')]
    return {'ok': parents == expected, 'parents': parents, 'expected': expected}


def check_carried(wd, source):
    ok = git(wd, 'merge-base', '--is-ancestor', f'origin/{source}', 'HEAD').returncode == 0
    missing = [] if ok else out(wd, 'log', '--oneline', f'HEAD..origin/{source}').splitlines()
    return {'ok': ok, 'missing_commits': missing[:CAP], 'missing_total': len(missing)}


def check_markers(wd):
    r = git(wd, 'grep', '-n', '-I', '-E', MARKER, 'HEAD')
    return r.stdout.splitlines()[:CAP] if r.returncode == 0 else []


def new_lines(wd, merge):
    lines, path = [], None
    for raw in git(wd, 'show', '--format=', '--cc', merge).stdout.splitlines():
        if raw.startswith('diff --cc '):
            path = raw[len('diff --cc '):]
        elif path and raw.startswith('++') and not raw.startswith('+++'):
            text = raw[2:]
            if text.strip():
                lines.append({'file': path, 'text': text, 'comment': is_comment(path, text)})
    return lines


def added_by(wd, base, side):
    added, path = {}, None
    for raw in git(wd, 'diff', '-U0', '-M', '--no-color', base, side).stdout.splitlines():
        if raw.startswith('diff --git '):
            path = None
        elif raw.startswith('+++ '):
            path = None if raw == '+++ /dev/null' else raw[len('+++ b/'):]
        elif path and raw.startswith('+'):
            added.setdefault(path, []).append(raw[1:])
    return added


def possibly_dropped(wd, base, side):
    found, counts = [], {}
    for path, lines in added_by(wd, base, side).items():
        if category(path) == 'lockfile':
            continue
        shown = git(wd, 'show', f'HEAD:{path}')
        if shown.returncode != 0:
            counts[path] = len(lines)
            found.append({'file': path, 'text': f'<file is gone at HEAD; {len(lines)} lines added on this side>'})
            continue
        present = {norm(line) for line in shown.stdout.splitlines()}
        missing = [line for line in lines if len(norm(line)) >= 4 and norm(line) not in present]
        if missing:
            counts[path] = len(missing)
            found.extend({'file': path, 'text': line} for line in missing)
    return found, counts


def versions(wd, target):
    result = []
    for path, pattern in (('gradle.properties', r'^version\s*=\s*(\S+)'), ('package.json', r'^\s*"version"\s*:\s*"([^"]+)"')):
        at_head = git(wd, 'show', f'HEAD:{path}')
        at_target = git(wd, 'show', f'origin/{target}:{path}')
        if at_head.returncode or at_target.returncode:
            continue
        head_match = re.search(pattern, at_head.stdout, re.M)
        target_match = re.search(pattern, at_target.stdout, re.M)
        if head_match and target_match:
            result.append({'file': path, 'target': target_match.group(1), 'head': head_match.group(1),
                           'ok': head_match.group(1) == target_match.group(1)})
    return result


def extra_commits(wd, merge):
    commits = out(wd, 'log', '--format=%h %s', f'{merge}..HEAD').splitlines()
    comments, path = [], None
    for raw in git(wd, 'diff', '-U0', '--no-color', merge, 'HEAD').stdout.splitlines():
        if raw.startswith('+++ '):
            path = None if raw == '+++ /dev/null' else raw[len('+++ b/'):]
        elif path and raw.startswith('+') and is_comment(path, raw[1:]):
            comments.append({'file': path, 'text': raw[1:]})
    return commits, comments


def main() -> int:
    ap = argparse.ArgumentParser(description='Read-only mechanical checks of one upmerge branch: parents, carried commits, markers, new lines, possibly dropped changes, versions.')
    ap.add_argument('--workdir', required=True)
    ap.add_argument('--source', required=True)
    ap.add_argument('--target', required=True)
    ap.add_argument('--merge-commit', help='default: the first merge on the branch after origin/<target>')
    args = ap.parse_args()

    wd = os.path.abspath(args.workdir)
    merge = args.merge_commit or find_merge(wd, args.target)
    if not merge:
        print(json.dumps({'error': f'no merge commit between origin/{args.target} and HEAD'}))
        return 2
    base = out(wd, 'merge-base', f'origin/{args.target}', f'origin/{args.source}')

    parents = check_parents(wd, merge, args.source, args.target)
    carried = check_carried(wd, args.source)
    markers = check_markers(wd)
    lines = new_lines(wd, merge)
    source_dropped, source_counts = possibly_dropped(wd, base, f'origin/{args.source}')
    target_dropped, target_counts = possibly_dropped(wd, base, f'origin/{args.target}')
    version = versions(wd, args.target)
    commits, fix_comments = extra_commits(wd, merge)
    added_comments = [{'file': line['file'], 'text': line['text']} for line in lines if line['comment']] + fix_comments

    hard = []
    if not parents['ok']:
        hard.append('the merge commit does not have origin/<target> and origin/<source> as its two parents')
    if not carried['ok']:
        hard.append(f"{carried['missing_total']} commits of origin/{args.source} are not in HEAD")
    if markers:
        hard.append(f'{len(markers)} conflict marker lines at HEAD')
    if added_comments:
        hard.append(f'{len(added_comments)} added comment lines that are in neither parent')
    if any(not v['ok'] for v in version):
        hard.append('a version differs from the target branch')

    print(json.dumps({
        'merge_commit': merge, 'head': out(wd, 'rev-parse', 'HEAD'), 'merge_base': base,
        'parents': parents, 'source_carried': carried, 'markers': markers,
        'new_lines': [line for line in lines if not line['comment']][:CAP], 'new_lines_total': len(lines),
        'added_comments': added_comments[:CAP],
        'possibly_dropped': {
            'source': source_dropped[:CAP], 'source_total': len(source_dropped), 'source_by_file': source_counts,
            'target': target_dropped[:CAP], 'target_total': len(target_dropped), 'target_by_file': target_counts,
        },
        'versions': version, 'extra_commits': commits, 'hard_failures': hard,
    }, indent=1))
    return 1 if hard else 0


if __name__ == '__main__':
    sys.exit(main())
