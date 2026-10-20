import sys
from xml.sax.saxutils import escape

W, H = 1120, 1888
SHIFT = 232
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
INK, QUIET = '#1f2328', '#57606a'
EDGE = '#6e7781'
KIND = {
    'dev': ('#e3eefc', '#2f74d0'),
    'main': ('#ffffff', '#8a8f98'),
    'agent': ('#fbe6da', '#d9622b'),
    'tool': ('#e2f4e8', '#2e9d57'),
    'config': ('#f1ebfd', '#8250df'),
}
LANES = {
    'dev': (24, 200),
    'main': (236, 224),
    'agent': (472, 384),
    'tool': (868, 228),
}
BOX = {
    'dev': (36, 176),
    'main': (248, 200),
    'agent': (572, 248),
    'tool': (880, 204),
    'config': (36, 176),
}

out = []


def text(x, y, words, size=13, weight=400, fill=INK, anchor='middle'):
    out.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(words)}</text>')


def box(kind, top, name, *lines):
    x, w = BOX[kind]
    fill, stroke = KIND[kind]
    h = 40 + 16 * len(lines)
    out.append(f'<rect x="{x}" y="{top}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    cx = x + w / 2
    text(cx, top + 24, name, size=15, weight=600)
    for i, line in enumerate(lines):
        text(cx, top + 42 + 16 * i, line, fill=INK if kind == 'dev' else QUIET)


def path(d, arrow=True):
    marker = ' marker-end="url(#arrow)"' if arrow else ''
    out.append(f'<path d="{d}" fill="none" stroke="{EDGE}" stroke-width="1.5"{marker}/>')


def uses(d):
    out.append(f'<path d="{d}" fill="none" stroke="#2e9d57" stroke-width="1.5" stroke-dasharray="6 4"/>')


def reads(d):
    out.append(f'<path d="{d}" fill="none" stroke="#8250df" stroke-width="1.5" stroke-dasharray="6 4" marker-end="url(#arrow-config)"/>')


def label(x, y, words, anchor='start'):
    text(x, y, words, size=12.5, fill=QUIET, anchor=anchor)


out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}" role="img" aria-label="Upmerge overview">')
out.append('<title>Upmerge: a developer starts it, agents merge and fix, deterministic tools check</title>')
out.append(f'<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{EDGE}"/></marker><marker id="arrow-config" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#8250df"/></marker></defs>')
out.append(f'<rect width="{W}" height="{H}" rx="12" fill="#ffffff"/>')
text(24, 40, 'Upmerge: a developer starts it, agents merge and fix, deterministic tools check', size=19, weight=700, anchor='start')
text(24, 62, 'Time runs top to bottom. Dashed green: the deterministic tool a step uses. Purple: configuration the developer maintains.', size=13.5, fill=QUIET, anchor='start')

heads = {
    'dev': ('Unifly developer', 'starts, decides, merges'),
    'main': ('Upmerge skill', 'main session, orchestrates'),
    'agent': ('Agents', 'run in the background'),
    'tool': ('Deterministic tools', 'same input, same result'),
}
for kind, (x, w) in LANES.items():
    fill, stroke = KIND[kind]
    out.append(f'<rect x="{x}" y="132" width="{w}" height="{H - 24 - 132}" rx="8" fill="#f6f8fa"/>')
    out.append(f'<rect x="{x}" y="76" width="{w}" height="48" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    title, sub = heads[kind]
    text(x + w / 2, 97, title, size=15, weight=700)
    text(x + w / 2, 115, sub, size=12.5, fill=QUIET)

box('dev', 148, 'Starts the upmerge', 'types /upmerge in', 'Claude Code, by hand', 'nightly run: planned')
box('main', 148, 'Preflight check', 'is the setup complete?', 'stops on anything missing')
box('tool', 148, 'preflight.py', 'gh, SSH, forks, JDK 25', 'skills, logins tested')
box('dev', 264, 'Fixes the setup', 'asked by the skill:', 'forks, tokens, skills')
box('config', 364, 'Configuration', 'config/upmerge.toml', 'repos, branches, CI')
box('main', 364, 'Scan the repos', 'reads the configuration', 'pending pairs + conflicts')
box('tool', 364, 'upmerge_scan.py', 'git fetch, trial merge', 'gh pr list: open PRs')
path('M212 184H248')
path('M288 220V300H212')
path('M212 280H264V220')
path('M400 220V364')
reads('M212 400H248')
uses('M448 184H880')
uses('M448 400H880')
path(f'M348 436V{284 + SHIFT}H212')
label(296, 262, 'missing')
label(238, 274, 'recheck', anchor='middle')
label(408, 300, 'all OK')

out.append(f'<g transform="translate(0 {SHIFT})">')
out.append('<rect x="484" y="340" width="360" height="420" rx="8" fill="none" stroke="#d0d7de" stroke-width="1.5" stroke-dasharray="4 3"/>')
text(496, 360, 'Per merge, all merges in parallel', size=12.5, weight=600, fill=QUIET, anchor='start')
out.append('<rect x="484" y="1080" width="360" height="320" rx="8" fill="none" stroke="#d0d7de" stroke-width="1.5" stroke-dasharray="4 3"/>')
text(496, 1100, 'One upmerge-ci-watcher agent per PR', size=12.5, weight=600, fill=QUIET, anchor='start')

uses('M820 408H880')
uses('M820 508H880')
uses('M820 608H880')
uses('M820 708H880')
uses('M448 824H880')
uses('M448 1032H880')
uses('M820 1128H880')
uses('M820 1348H880')
uses('M448 1480H880')

path('M124 320V408H572')
path('M696 444V472')
path('M696 544V572')
path('M696 644V672')
path('M572 620H560V520H572')
path('M696 744V772H348V788')
path('M348 860V872')
path('M236 920H212')
path('M348 968V996')
path('M124 964V1032H248')
path('M348 1068V1128H572')
path('M696 1168V1196')
path('M572 1240H560V1156H572')
path('M820 1156H832V1328H820')
path('M696 1384V1424H348V1444')
path('M348 1516V1580H212')

label(704, 462, 'conflicts')
label(552, 574, 'retry once', anchor='end')
label(224, 910, 'no', anchor='middle')
label(356, 986, 'yes')
label(132, 998, 'push anyway')
label(704, 1188, 'red')
label(552, 1202, 'fix pushed', anchor='end')
label(828, 1303, 'green', anchor='end')
label(704, 1416, 'gate OK')

box('dev', 248, 'Picks the merges', 'from the clean and', 'conflicting overview')
box('agent', 372, 'upmerge-merger · prepare', 'branch from target, merge source', 'clean merge skips the resolver')
box('tool', 372, 'conflict_difficulty.py', 'scores conflicts 0 to 10', 'tier → model and effort')
box('agent', 472, 'upmerge-resolver', 'solves the conflicts, commits', 'model and effort from the tier')
box('tool', 472, 'Jira · Confluence', 'hard tier only, read-only', 'confluence skill')
box('agent', 572, 'upmerge-merger · validate', 'runs validate.py, then fixes', 'what the merge broke')
box('tool', 572, 'validate.py', 'markers, Spotless, compile,', 'tests, yarn/npm install')
box('agent', 672, 'upmerge-verifier', 'read-only: judges every line', 'that verify_merge.py flags')
box('tool', 672, 'verify_merge.py', 'parents, markers, new lines', 'possibly dropped lines')
box('main', 788, 'Report the results', 'status, verdict, findings', 'in reports/<date>/')
box('tool', 788, 'SonarQube Cloud', 'baseline: source + target', 'info only, never blocks', 'sonar-lint skill')
out.append('<polygon points="236,920 348,872 460,920 348,968" fill="#ffffff" stroke="#8a8f98" stroke-width="2"/>')
text(348, 915, 'merger READY-TO-PUSH', size=12.5, weight=600)
text(348, 933, 'and verifier CONFIRM?', size=12.5, weight=600)
box('dev', 876, 'Decides the push', 'reads the findings,', 'pushes anyway, fixes', 'by hand, or skips')
box('main', 996, 'Push, open the PR', "to the developer's fork", 'PR against the target')
box('tool', 996, 'GitHub', 'git push to the fork', 'gh pr create')
box('agent', 1112, 'Wait for the PR build', 're-polls while it builds')
box('tool', 1112, 'Jenkins build server', 'builds the PR, runs the', 'integration tests', 'polled: jenkins_wait.py', 'logs: jenkins skill')
box('agent', 1196, 'Red build: diagnose', 'merge defect: fix, push', 'pre-existing, infra: report', 'stops after 3 fix pushes')
box('agent', 1312, 'Check the Sonar PR gate', 'fix what the merge added', 'a fix restarts the wait')
box('tool', 1312, 'SonarQube Cloud', 'PR quality gate', 'not checked by Jenkins', 'sonar-lint skill')
box('main', 1444, 'Commit the report', 'upmerge-report.md into', 'reports/ of this repo')
box('tool', 1444, 'git · this repo', 'commit + push to main', 'reports/<date>/')
box('dev', 1544, 'Merges the PR', 'after the report;', 'agents never merge')

out.append('</g>')
out.append('</svg>')
with open(sys.argv[1], 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(out) + '\n')
