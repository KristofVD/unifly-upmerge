---
name: jenkins
description: Query the Unifly Jenkins CI server at ci.unifly.tech. Use for checking build status, diagnosing failed builds, reading console logs, pipeline stages, and test reports.
allowed-tools: Bash(curl *)
---

# Jenkins CI Access (ci.unifly.tech)

## Authentication
Credentials live in `~/.claude/skills/jenkins/.netrc` (your Jenkins user + API token).
Pass it to every curl call:
```
curl -s --netrc-file ~/.claude/skills/jenkins/.netrc ...
```
Anonymous access is denied (403). If the file is missing, ask the user to
recreate it: `printf 'machine ci.unifly.tech\nlogin <your Jenkins user>\npassword <API_TOKEN>\n' > ~/.claude/skills/jenkins/.netrc && chmod 600 ~/.claude/skills/jenkins/.netrc`

## Job structure
Everything lives under one GitHub organization folder, `Unifly nv`. Each repo is a
multibranch pipeline; each branch or PR is a job under it:

```
https://ci.unifly.tech/job/Unifly%20nv/job/<repo>/job/<branch>/<buildNumber>/
```

- Repo examples: `unifly-services`, `unifly-portal`, ...
- Branch jobs: `v5.0`, `v4.8`, ticket branches; PRs are named `PR-<number>`
- URL-encode: spaces → `%20`, slashes in branch names → `%2F`
- Build shortcuts instead of a number: `lastBuild`, `lastCompletedBuild`, `lastFailedBuild`, `lastSuccessfulBuild`

## Important: the `tree` parameter
Always limit responses with `tree=` (full JSON can be huge). URL-encode the
brackets as `%5B` / `%5D` — shell-escaped literal brackets break on nested queries:
```
api/json?tree=jobs%5Bname,color,lastBuild%5Bnumber,result,timestamp%5D%5D
```

## Recipes

### List all repos
```bash
curl -s --netrc-file ~/.claude/skills/jenkins/.netrc \
  "https://ci.unifly.tech/job/Unifly%20nv/api/json?tree=jobs%5Bname,color%5D"
```

### List branches/PRs of a repo with last build status
```bash
curl -s --netrc-file ~/.claude/skills/jenkins/.netrc \
  "https://ci.unifly.tech/job/Unifly%20nv/job/unifly-services/api/json?tree=jobs%5Bname,color,lastBuild%5Bnumber,result,timestamp%5D%5D"
```
Sort by `lastBuild.timestamp` (epoch millis) to find recent activity. `color`:
`blue`=success, `red`=failed, `notbuilt`, suffix `_anime`=currently building.

### Build status
```bash
curl -s --netrc-file ~/.claude/skills/jenkins/.netrc \
  "https://ci.unifly.tech/job/Unifly%20nv/job/unifly-services/job/v5.0/lastBuild/api/json?tree=number,result,building,timestamp,duration"
```
`result`: `SUCCESS` | `FAILURE` | `UNSTABLE` | `ABORTED` | `null` while building.

### Which stage failed (check this BEFORE reading the console log)
```bash
curl -s --netrc-file ~/.claude/skills/jenkins/.netrc \
  "https://ci.unifly.tech/job/Unifly%20nv/job/unifly-services/job/v5.0/8/wfapi/describe"
```
Returns `stages[]` with `name`, `status` (`SUCCESS`/`FAILED`/`NOT_EXECUTED`), `durationMillis`.
Note: a stage failing with 0s duration usually means it was skipped because of an
earlier real failure — look for the first FAILED stage with nonzero duration.

### Console log
Logs can be many MB — never fetch without limiting output:
```bash
curl -s --netrc-file ~/.claude/skills/jenkins/.netrc \
  "https://ci.unifly.tech/job/Unifly%20nv/job/unifly-services/job/v5.0/8/consoleText" | tail -200
# or grep for errors:
... /consoleText" | grep -iE "error|failed|exception" | head -50
```

### Test report (404 if no test results were recorded)
```bash
curl -s --netrc-file ~/.claude/skills/jenkins/.netrc \
  "https://ci.unifly.tech/job/Unifly%20nv/job/unifly-services/job/v5.0/8/testReport/api/json?tree=failCount,passCount,skipCount"
# failed test details:
...?tree=suites%5Bcases%5BclassName,name,status,errorDetails%5D%5D
```

### Build queue
```bash
curl -s --netrc-file ~/.claude/skills/jenkins/.netrc \
  "https://ci.unifly.tech/queue/api/json?tree=items%5Btask%5Bname%5D,why,inQueueSince%5D"
```

## Diagnosing a failed build — recommended order
1. `wfapi/describe` → find the first genuinely FAILED stage
2. `consoleText | tail -200` (or grep) → find the actual error
3. `testReport` if the failure is in a test stage → list failing tests

## Tips
- Timestamps are epoch milliseconds
- `jq` or `python3 -m json.tool` for parsing; `tail`/`grep` console logs
- Write-operations (triggering builds) need a Jenkins-Crumb header — read-only queries don't

## Arguments
$ARGUMENTS - repo name, branch, PR number, or build URL to investigate
