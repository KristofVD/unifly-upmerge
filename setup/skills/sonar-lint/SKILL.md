---
name: sonar-lint
description: Check SonarQube Cloud quality gates and new issues for any repo in the unifly-jenkins-github organization (unifly-services, unifly-portal, unifly-tiles, unifly-geoserver, proj-*). Use for "sonar lint" checks on a PR or branch, before/after pushing a merge, or when a Sonar quality gate failed and the issues must be listed and fixed.
allowed-tools: Bash(python3 *sonar_check.py*), Bash(curl *)
---

# Sonar lint check (sonarcloud.io, org `unifly-jenkins-github`)

One script answers "is Sonar happy, and if not, what exactly do I fix":

```bash
python3 ~/.claude/skills/sonar-lint/sonar_check.py --repo <repo> --pr <number>
python3 ~/.claude/skills/sonar-lint/sonar_check.py --repo <repo> --branch <branch>
python3 ~/.claude/skills/sonar-lint/sonar_check.py --project <sonarKey> --pr <number>
```

Output is JSON: `gate`, `failing_conditions[]` (metric/actual/threshold),
`new_issues.issues[]` (rule, severity, file, line, message), `hotspots_to_review`,
and `uncovered_new_code[]` when a coverage condition fails, plus a `dashboard` link.

Exit codes: `0` gate OK, `1` gate ERROR, `4` no analysis yet (the Jenkins
`Sonar PR` stage has not run yet), `2` unknown repo.

## Repo → Sonar project key

| Repo | Sonar key |
|---|---|
| unifly-services | `unifly-all-services` (not `aero.unifly:unifly-all-services`, that one is stale) |
| unifly-portal | `unifly-portal` |
| unifly-tiles | `unifly-tiles` |
| unifly-geoserver | `unifly-geoserver` |
| proj-demo, unifly-testing and the other proj-* repos | same as repo name |

`unifly-keycloak`, `unifly-socketcluster`, `unifly-automation`, `unifly.data` and
`app-automation` have no Sonar project; report "no Sonar" and move on.
Full list: `curl -s -u "$(cat ~/.claude/skills/sonar-lint/token):" "https://sonarcloud.io/api/components/search_projects?organization=unifly-jenkins-github&ps=100"`.

## How Sonar runs here

- Jenkins runs the analysis: stage `Sonar PR` on PR builds (`sonar.pullrequest.key`),
  stage `Sonar` on branch builds. Nothing is analysed locally.
- **Jenkins does not wait for the quality gate**: a green Jenkins build can still
  have a red Sonar gate. Always run this check after the build finishes.
- The gate on new code: no new critical/major issues, new code smells under the
  threshold, coverage on new code >= 80%.

## Lint flow

1. **Before pushing a merge branch** (prediction): run `--branch <source>` and
   `--branch <target>`. Issues already open on the source branch will show up as
   new issues on the upmerge PR. Note them; they are not caused by the merge.
2. **After the PR build** (the real gate): run `--pr <number>`. Exit 4 means the
   analysis is not there yet; wait for the Jenkins build to finish and retry.
3. **Fixing**: for each issue open `file:line` in the local checkout (the line is
   from the analysed commit; re-check if the branch moved). Rule details:
   `curl -s -u "$(cat ~/.claude/skills/sonar-lint/token):" "https://sonarcloud.io/api/rules/show?key=<rule>&organization=unifly-jenkins-github" | python3 -c 'import sys,json;r=json.load(sys.stdin)["rule"];print(r["name"]);print(r.get("mdDesc","")[:1500])'`
4. On an upmerge PR, only fix issues the merge itself introduced (conflict
   resolutions) unless asked; inherited issues belong to their original branch.

## Token

`~/.claude/skills/sonar-lint/token` (mode 600), sent as basic-auth user with an
empty password. Unauthenticated calls return empty results instead of erroring.
To replace: `printf '%s' '<TOKEN>' > ~/.claude/skills/sonar-lint/token && chmod 600 ~/.claude/skills/sonar-lint/token`
(new tokens: https://sonarcloud.io/account/security).

## Arguments
$ARGUMENTS - repo name plus PR number or branch
