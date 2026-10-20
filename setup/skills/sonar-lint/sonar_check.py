#!/usr/bin/env python3
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = 'https://sonarcloud.io/api'
ORG = 'unifly-jenkins-github'
SKILL_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_TO_PROJECT = {
    'unifly-services': 'unifly-all-services',
    'unifly-portal': 'unifly-portal',
    'unifly-tiles': 'unifly-tiles',
    'unifly-geoserver': 'unifly-geoserver',
    'proj-demo': 'proj-demo',
    'unifly-testing': 'unifly-testing',
}


def token() -> str:
    with open(os.path.join(SKILL_DIR, 'token')) as f:
        return f.read().strip()


AUTH = 'Basic ' + base64.b64encode(f'{token()}:'.encode()).decode()


def get(path: str, **params):
    url = f'{API}/{path}?{urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})}'
    req = urllib.request.Request(url, headers={'Authorization': AUTH})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def scope(args) -> dict:
    return {'pullRequest': args.pr} if args.pr else {'branch': args.branch}


def gate(project: str, sc: dict) -> dict:
    status = get('qualitygates/project_status', projectKey=project, **sc)
    if not status:
        return {'status': 'NO_ANALYSIS', 'failing': []}
    ps = status['projectStatus']
    failing = [
        {'metric': c['metricKey'], 'actual': c.get('actualValue'), 'threshold': c.get('errorThreshold')}
        for c in ps.get('conditions', []) if c.get('status') == 'ERROR'
    ]
    return {'status': ps['status'], 'failing': failing}


def new_issues(project: str, sc: dict, limit: int) -> dict:
    res = get('issues/search', componentKeys=project, organization=ORG, issueStatuses='OPEN,CONFIRMED',
              sinceLeakPeriod='true' if 'branch' in sc else None, ps=min(limit, 500), **sc) or {}
    issues = [
        {'rule': i['rule'], 'severity': i.get('severity'), 'type': i.get('type'),
         'file': i['component'].split(':', 1)[-1], 'line': i.get('line'), 'message': i['message']}
        for i in res.get('issues', [])
    ]
    return {'total': res.get('total', 0), 'issues': issues}


def hotspots(project: str, sc: dict) -> int:
    res = get('hotspots/search', projectKey=project, status='TO_REVIEW', ps=1, **sc) or {}
    return res.get('paging', {}).get('total', 0)


def coverage(project: str, sc: dict) -> list:
    res = get('measures/component_tree', component=project, metricKeys='new_coverage,new_uncovered_lines',
              qualifiers='FIL', s='metric', metricSort='new_uncovered_lines', asc='false',
              metricSortFilter='withMeasuresOnly', ps=15, **sc) or {}
    rows = []
    for c in res.get('components', []):
        m = {x['metric']: (x.get('period') or {}).get('value', x.get('value')) for x in c.get('measures', [])}
        if m.get('new_uncovered_lines') not in (None, '0'):
            rows.append({'file': c['path'], 'new_coverage': m.get('new_coverage'),
                         'new_uncovered_lines': m.get('new_uncovered_lines')})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', help='git repo name, mapped to a Sonar project key')
    ap.add_argument('--project', help='Sonar project key (overrides --repo)')
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument('--pr', help='GitHub PR number')
    target.add_argument('--branch', help='branch name')
    ap.add_argument('--limit', type=int, default=100)
    ap.add_argument('--list-projects', action='store_true')
    args = ap.parse_args()

    project = args.project or REPO_TO_PROJECT.get(args.repo or '')
    if not project:
        print(json.dumps({'error': f'no Sonar project for repo {args.repo!r}', 'known': REPO_TO_PROJECT}))
        sys.exit(2)

    sc = scope(args)
    g = gate(project, sc)
    out = {'project': project, **sc, 'gate': g['status'], 'failing_conditions': g['failing'],
           'dashboard': f"https://sonarcloud.io/dashboard?id={project}&" + urllib.parse.urlencode(sc)}
    if g['status'] != 'NO_ANALYSIS':
        out['new_issues'] = new_issues(project, sc, args.limit)
        out['hotspots_to_review'] = hotspots(project, sc)
        if any(c['metric'].endswith('coverage') for c in g['failing']):
            out['uncovered_new_code'] = coverage(project, sc)
    print(json.dumps(out, indent=2))
    sys.exit({'OK': 0, 'NO_ANALYSIS': 4}.get(g['status'], 1))


if __name__ == '__main__':
    main()
