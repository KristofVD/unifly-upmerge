#!/usr/bin/env python3
import argparse
import base64
import functools
import json
import netrc
import os
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from typing import List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, 'config', 'upmerge.toml')


@functools.lru_cache(maxsize=None)
def jira_config() -> dict:
    with open(CONFIG, 'rb') as f:
        return tomllib.load(f)['jira']


def host() -> str:
    return urllib.parse.urlparse(jira_config()['base_url']).hostname


def skills_dirs() -> List[str]:
    config_dir = os.environ.get('CLAUDE_CONFIG_DIR')
    dirs = [os.path.join(config_dir, 'skills')] if config_dir else []
    return dirs + [os.path.expanduser('~/.claude/skills')]


def netrc_path() -> Optional[str]:
    candidates = (os.path.join(d, 'confluence', '.netrc') for d in skills_dirs())
    return next((p for p in candidates if os.path.isfile(p)), None)


@functools.lru_cache(maxsize=None)
def auth_header() -> str:
    login, _, password = netrc.netrc(netrc_path()).authenticators(host())
    return 'Basic ' + base64.b64encode(f'{login}:{password}'.encode()).decode()


def call(method: str, path: str, body: Optional[dict] = None):
    url = jira_config()['base_url'].rstrip('/') + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {'Authorization': auth_header(), 'Accept': 'application/json', 'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        sys.exit(f'{method} {path} failed: {e.code} {e.read().decode(errors="replace")}')


def browse(key: str) -> str:
    return f"{jira_config()['base_url'].rstrip('/')}/browse/{key}"


def adf(lines: List[str]) -> dict:
    paragraphs = [{'type': 'paragraph', 'content': [{'type': 'text', 'text': line}]} if line.strip()
                  else {'type': 'paragraph', 'content': []} for line in lines]
    return {'type': 'doc', 'version': 1, 'content': paragraphs}


def short(version: str) -> str:
    return version.lstrip('v')


def ticket_date(day: str) -> str:
    yyyy, mm, dd = day.split('-')
    return f'{dd}/{mm}/{yyyy}'


def repo_label(repo: str) -> str:
    return '-'.join(part[:1].upper() + part[1:] for part in repo.split('-'))


def existing_versions() -> set:
    versions = call('GET', f"/rest/api/3/project/{jira_config()['project']}/versions")
    return {v['name'] for v in versions}


def fix_versions(targets: List[str]) -> List[dict]:
    known = existing_versions()
    names = sorted({f'{t}.0' for t in targets}, key=lambda n: [int(p) for p in short(n).split('.')])
    return [{'name': n} for n in names if n in known]


def search(jql: str) -> List[dict]:
    query = urllib.parse.urlencode({'jql': jql, 'fields': 'summary,status,parent', 'maxResults': 20})
    return call('GET', f'/rest/api/3/search/jql?{query}').get('issues', [])


def myself() -> str:
    return call('GET', '/rest/api/3/myself')['accountId']


def find_user(query: str) -> str:
    users = call('GET', '/rest/api/3/user/search?' + urllib.parse.urlencode({'query': query}))
    active = [u for u in users if u.get('active') and u.get('accountType') == 'atlassian']
    if len(active) != 1:
        sys.exit(f'assignee "{query}" matches {len(active)} users: '
                 + ', '.join(u.get('displayName', '?') for u in active))
    return active[0]['accountId']


def result(key: str, summary: str, created: bool) -> None:
    print(json.dumps({'key': key, 'url': browse(key), 'summary': summary, 'created': created}, indent=1))


def merge_ticket(args) -> None:
    cfg = jira_config()
    with open(CONFIG, 'rb') as f:
        chain = tomllib.load(f)['branch_chain']
    date = ticket_date(args.day)
    summary = f'Merge Monday {date}: {short(chain[0])} up until {short(chain[-1])}'
    found = search(f'project = {cfg["project"]} AND issuetype = Task AND summary ~ "\\"Merge Monday {date}\\""')
    if found:
        result(found[0]['key'], found[0]['fields']['summary'], False)
        return
    fields = {
        'project': {'key': cfg['project']},
        'issuetype': {'name': 'Task'},
        'summary': summary,
        'description': adf([' → '.join(chain), f"see {cfg['releases_page']}"]),
        'assignee': {'accountId': myself()},
        'labels': cfg.get('labels', []),
        'fixVersions': fix_versions(args.targets),
    }
    result(call('POST', '/rest/api/3/issue', {'fields': fields})['key'], summary, True)


def sub_ticket(args) -> None:
    cfg = jira_config()
    date = ticket_date(args.day)
    summary = f'{repo_label(args.repo)}: Merge Monday {date}: {short(args.source)} up until {short(args.target)}'
    found = [i for i in search(f'parent = {args.parent}')
             if i['fields']['summary'].lower().startswith(repo_label(args.repo).lower() + ':')
             and f'{short(args.source)} up until {short(args.target)}' in i['fields']['summary']]
    with open(args.description_file, encoding='utf-8') as f:
        description = adf(f.read().rstrip('\n').split('\n'))
    if found:
        call('PUT', f"/rest/api/3/issue/{found[0]['key']}", {'fields': {'description': description}})
        result(found[0]['key'], found[0]['fields']['summary'], False)
        return
    fields = {
        'project': {'key': cfg['project']},
        'parent': {'key': args.parent},
        'issuetype': {'name': 'Sub-task'},
        'summary': summary,
        'description': description,
        'fixVersions': fix_versions([args.target]),
    }
    if args.assignee:
        fields['assignee'] = {'accountId': find_user(args.assignee)}
    result(call('POST', '/rest/api/3/issue', {'fields': fields})['key'], summary, True)


def main() -> int:
    ap = argparse.ArgumentParser(description='Create the Merge Monday Jira ticket and its sub-tickets.')
    sub = ap.add_subparsers(dest='command', required=True)
    m = sub.add_parser('merge', help='find or create the Merge Monday ticket of the day')
    m.add_argument('--day', required=True, help='YYYY-MM-DD')
    m.add_argument('--targets', nargs='+', required=True, help='target branches of the pending merges, e.g. v4.8 v5.0')
    m.set_defaults(func=merge_ticket)
    s = sub.add_parser('sub', help='create (or update the description of) the sub-ticket for one merge')
    s.add_argument('--parent', required=True)
    s.add_argument('--day', required=True, help='YYYY-MM-DD')
    s.add_argument('--repo', required=True)
    s.add_argument('--source', required=True)
    s.add_argument('--target', required=True)
    s.add_argument('--description-file', required=True)
    s.add_argument('--assignee', help='name or e-mail of the colleague who takes the merge over')
    s.set_defaults(func=sub_ticket)
    args = ap.parse_args()
    args.func(args)
    return 0


if __name__ == '__main__':
    sys.exit(main())
