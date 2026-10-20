#!/usr/bin/env python3
import argparse
import base64
import functools
import json
import netrc
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import List, Optional

HOST = 'ci.unifly.tech'
BASE = f'https://{HOST}/job/Unifly%20nv'


def skills_dirs() -> List[str]:
    config_dir = os.environ.get('CLAUDE_CONFIG_DIR')
    dirs = [os.path.join(config_dir, 'skills')] if config_dir else []
    return dirs + [os.path.expanduser('~/.claude/skills')]


def netrc_path() -> Optional[str]:
    candidates = (os.path.join(d, 'jenkins', '.netrc') for d in skills_dirs())
    return next((p for p in candidates if os.path.isfile(p)), None)


@functools.lru_cache(maxsize=None)
def auth_header() -> str:
    login, _, password = netrc.netrc(netrc_path()).authenticators(HOST)
    return 'Basic ' + base64.b64encode(f'{login}:{password}'.encode()).decode()


def get(url: str):
    req = urllib.request.Request(url, headers={'Authorization': auth_header()})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def job_url(job: str, branch: str) -> str:
    return f"{BASE}/job/{urllib.parse.quote(job)}/job/{urllib.parse.quote(branch, safe='')}"


def snapshot(job: str, branch: str):
    base = job_url(job, branch)
    build = get(f'{base}/lastBuild/api/json?tree=number,result,building,timestamp,duration,url')
    return base, build


def failure_details(build_url: str) -> dict:
    details = {}
    stages = get(f'{build_url}wfapi/describe') or {}
    details['failed_stages'] = [
        {'name': s['name'], 'durationMillis': s.get('durationMillis')}
        for s in stages.get('stages', []) if s.get('status') in ('FAILED', 'UNSTABLE')
    ]
    report = get(f'{build_url}testReport/api/json?tree=failCount,passCount,skipCount')
    if report:
        details['tests'] = report
    return details


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--job', required=True)
    ap.add_argument('--branch', required=True)
    ap.add_argument('--after', type=int, default=0)
    ap.add_argument('--max-wait', type=int, default=540)
    ap.add_argument('--interval', type=int, default=60)
    args = ap.parse_args()

    if not netrc_path():
        print(json.dumps({'state': 'NO_CREDENTIALS', 'looked_in': [os.path.join(d, 'jenkins') for d in skills_dirs()],
                          'hint': 'create the jenkins .netrc, see Setup in the README'}))
        sys.exit(2)

    deadline = time.time() + args.max_wait
    while True:
        base, build = snapshot(args.job, args.branch)
        stale = build is None or build['number'] <= args.after
        if not stale and not build['building']:
            ok = build['result'] == 'SUCCESS'
            out = {'state': build['result'], 'build': build['number'], 'url': build['url'],
                   'durationMin': round((build.get('duration') or 0) / 60000, 1)}
            if not ok:
                out.update(failure_details(build['url']))
            print(json.dumps(out, indent=2))
            sys.exit(0 if ok else 1)
        if time.time() + args.interval > deadline:
            if stale:
                print(json.dumps({'state': 'NOT_FOUND', 'job': base, 'after': args.after,
                                  'hint': 'PR job not indexed yet or no new build; run again'}))
                sys.exit(4)
            print(json.dumps({'state': 'BUILDING', 'build': build['number'], 'url': build['url'],
                              'runningMin': round((time.time() * 1000 - build['timestamp']) / 60000, 1)}))
            sys.exit(3)
        time.sleep(args.interval)


if __name__ == '__main__':
    main()
