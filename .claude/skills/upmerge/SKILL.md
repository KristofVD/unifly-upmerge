---
name: upmerge
description: Run the upmerge across the Unifly repos - check the setup, scan which version branches need merging forward, ask the developer which merges to do, merge + compile + unit test each in parallel agents, verify, sonar-lint, push to the fork, open the PRs, then watch the Jenkins PR builds until green, fix what breaks and commit the report to this repo. Use when the developer says upmerge or asks what needs merging.
---

# Upmerge

Root: this repo, the session's working directory. The repos, the GitHub org and the
branch chain are configuration in `config/upmerge.toml`: edit them there, never in the code
or in these instructions.

Agents (in `.claude/agents/`): `upmerge-merger`, `upmerge-resolver`, `upmerge-verifier`, `upmerge-ci-watcher`.
Skills used: `sonar-lint`, `jenkins`, `confluence` (Jira: hard tier, Merge Monday ticket), `jira-like-me` (sub-ticket text).

Set once at the start (after step 0):
- `ROOT` = `pwd` (the repo root). Pass it to every agent as `root`.
- `FORK` = `fork_user` from the preflight: the developer's GitHub user that owns the forks.
- `SONAR_CHECK` = `paths.sonar_check` from the preflight: the sonar-lint script.
- `ORG` = `github_org` from the configuration:
  `python3 -c "import tomllib; print(tomllib.load(open('config/upmerge.toml', 'rb'))['github_org'])"`.
- `DATE` = today as `DDMMYYYY` (branch names), `DAY` = `YYYY-MM-DD` (report dir `reports/<DAY>/`).
- Branch name: `merge<DATE>_<src><to><tgt>`, versions without `v` and dots: v4.8→v5.0 = `merge09102026_48to50`.

$ARGUMENTS may narrow the run to some repos (repo names from the configuration).

## 0. Preflight: is the setup complete?

```bash
python3 tools/preflight.py --json [--repos <the repos of this run>]
```

It checks Python, the configuration, the git identity, `gh` and SSH, a fork of every repo, JDK 25,
the node tools, the `jenkins`, `sonar-lint` and `confluence` skills, and tests the Jenkins, SonarQube
Cloud and Atlassian logins read-only. Each entry of `checks` is `ok`, `warn` or `fail`, with a
`detail` and a `fix`; it also returns `fork_user` and `paths`.

- Nothing `fail` → mention each `warn` in one line and go on.
- Something `fail` → do not start. Show the failing lines with their fix and ask the developer
  with AskUserQuestion what to do, one question per kind of problem:
  - a missing fork → "fork it now" (run its `fix`: it creates the fork under their account) /
    "leave this repo out of this run" / "stop".
  - anything else (credentials, a skill, JDK, `gh`, SSH, git identity) → give them the `fix` to run
    themselves (e.g. with `! <command>`, or by editing the file) and ask "done, check again" / "stop".
    Never ask for a token or password in the chat, and never write one into a file yourself.

  Run the preflight again after each fix, until nothing fails or the developer stops.

## 1. Scan: is there anything to merge?

```bash
mkdir -p reports/<DAY>
python3 upmerge_scan.py --json [repos...] > reports/<DAY>/scan.json
```

Build the list of pending pairs from `scan.json`. Apply the **waterfall**: per repo
only the lowest pending pair can be done now; higher pairs are *deferred* until
the lower PR has been merged upstream. Also drop a pair when an upmerge PR for it
is already open: `gh pr list -R <ORG>/<repo> --base <target> --state open --json number,title,headRefName`
(titles like `Merge <source> to <target>`); show it as "PR already open #n" instead.

A repo that lacks a branch of the chain (`missing_branches` in scan.json): report it, never force the merge.

Nothing pending → say so in one line per repo and stop.

## 2. Ask the developer

Predict the difficulty per conflicting pair from the scan's file list:
`python3 tools/conflict_difficulty.py --files <conflict files...>` (path-based guess; the real score comes after the merge).

Print a compact table: repo | merge | commits | clean / N conflict files (name them) | predicted tier | build type | deferred/open-PR notes.
Then always print the full overview, two sections: **clean** and **conflicting**.
Per pending pair (doable and deferred): repo | merge | branch name | every commit
(sha + subject) | CI (Jenkins job / Sonar project / none) | for conflicting ones
the conflict files. Mark deferred pairs and which PR they wait on. The developer may do
some merges manually from this overview. Repeat it in the step 5 report.
Then use **AskUserQuestion** (multiSelect) with one option per doable merge,
conflicted ones flagged, so the developer picks which merges to do now. More than 4
doable merges → first question "all / only clean / only conflicted / let me pick",
then narrow. Nothing selected → stop.

## 2b. Merge Monday ticket

```bash
python3 tools/jira_ticket.py merge --day <DAY> --targets <target of every pending pair, deferred ones too>
```
Finds today's `Merge Monday DD/MM/YYYY: <first> up until <last>` Task in Jira (project, labels and the
releases page come from `[jira]` in the configuration) or creates it, assigned to the developer, with the
existing `vX.Y.0` fix versions of the targets. It returns `key`, `url` and `created`. Say the key in one
line. Sub-tickets of step 6 go under it.

## 3. Merge, resolve, compile, unit test (parallel)

Only conflict solving gets a stronger model or more effort. The mechanical work
(fetch, merge, build, tests) runs on `upmerge-merger`, whose model and effort
are fixed in its frontmatter (sonnet, medium).

Per selected pair, as a background pipeline. Start all pairs at once and don't wait for one pair before moving another on:

1. **Prepare.** Launch **`upmerge-merger`** with `mode: prepare`, all pairs in one message,
   `run_in_background: true`. Prompt = `root` and the pair's data from scan.json: repo, `url`, source,
   target, branch, workdir `<ROOT>/.cache/work/<repo>`, build info, conflict files, commit list.
   - Clean merge → it validates in the same run and returns the dossier. Go to the verifier.
   - Conflicts → it returns `merge_status: conflicted` with `difficulty`, the output of
     `tools/conflict_difficulty.py` on the real hunks.
2. **Resolve.** Launch **`upmerge-resolver`** (background) with the `model` and `effort`
   from `difficulty` passed as the Agent tool's `model` and `effort` parameters:

   | tier | score | what it usually is | resolver | verifier |
   |---|---|---|---|---|
   | clean | 0 | no conflicts | (none) | sonnet / medium |
   | mechanical | 1-2 | locales, lockfiles, docs, manifests, import-only hunks | sonnet / medium | sonnet / medium |
   | moderate | 3-5 | a few small code/config hunks, modify/delete of a test | opus / high | opus / high |
   | hard | 6-10 | modify/delete of production code, big or many overlapping code hunks | opus / max, plus Jira/Confluence tickets | opus / max |

   The mapping lives in `TIERS` in `tools/conflict_difficulty.py`, so edit it there. Prompt = `root`, repo,
   source, target, branch, workdir, the full `difficulty` object and the commit list.
   Say in one line which tier/model/effort each merge got. When `difficulty.tickets` is true (hard tier)
   the resolver also reads the Jira tickets behind the commits with the `confluence` skill, read-only;
   it returns the keys it used in `tickets`.
3. **Validate.** When the resolver returns `resolved`, launch **`upmerge-merger`** with
   `mode: validate` and the resolver's result. It runs the gates with `tools/validate.py` and
   returns the dossier.
   - The resolver returns `blocked` → skip validate and take its result to step 6 as BLOCKED.
   - Validate reports a compile or unit-test `fail` caused by the merge → send the failure to
     a new `upmerge-resolver` at the same tier ("fix this merge defect, commit it as
     `Fixed tests after upmerge`"), then run validate again. Do this once; after that it is NEEDS-REVIEW.

As each dossier comes back, launch an **`upmerge-verifier`** for it (background) with `root` and
the dossier, passing `difficulty.verifier_model` and `difficulty.verifier_effort` as the Agent tool's
`model` and `effort` (clean merges: sonnet / medium). Don't wait for all mergers to finish first.
The verifier runs `tools/verify_merge.py` first and then judges every candidate it lists.

## 4. Sonar lint (prediction)

For repos with a `sonar_project` in scan.json, run
`python3 <SONAR_CHECK> --project <key> --branch <source>`
and the same for `<target>`. Record gate + open issue count per side; these
inherited issues will reappear on the PR and are not the merge's fault.

## 5. Report

Write `reports/<DAY>/upmerge-report.md` (+ `.json` with the raw dossiers/verdicts):
the Merge Monday ticket key + link at the top,
summary table (repo | merge | status | tier (model/effort) | complexity | verdict | sonar baseline | Jira sub-ticket),
then per merge: conflict files with resolution + confident flag, Jira keys the resolver used (key + its
`settled` line, never ticket text), validation gates,
extra fix commits, verifier verdict and findings, the Jira sub-ticket with the conflict it hands over, deferred section.
Show the developer the summary table.

The report is published in step 8 and this repo is public, so write it publishable from the start:
- No people: no names, GitHub handles or e-mail addresses. In commit subjects like
  `Merge pull request #n from <owner>/<branch>`, write a personal owner as `<fork>`.
  The developer is "the developer".
- No credentials, tokens, local paths (`/home/...`, `~/...`) or console dumps; quote only the failing line.
- Only `upmerge-report.md` is published; `scan.json` and `upmerge-report.json` stay local.

## 6. Push and open PRs

Per merge:
- `READY-TO-PUSH` **and** verifier `CONFIRM` → push and open the PR without asking.
- anything else (`NEEDS-REVIEW`, `BLOCKED`, `REJECT`, failed gate) → show the
  findings and ask with AskUserQuestion: push anyway / I'll fix it in `<workdir>` first /
  Jira sub-ticket (hand it over) / skip.

Jira sub-ticket: for a merge that is too tricky to finish today.
1. Load the `jira-like-me` skill (when the developer has it) and write a very short description of the conflict we can't solve:
   which file, which commits/tickets clash and the open decision, plus what is already known (e.g. the
   compile fix). No scaffold, hyphen bullets without a space. Save it to `reports/<DAY>/jira-<repo>.txt`.
2. Ask who takes it over (free text, or leave unassigned).
3. Run:
   ```bash
   python3 tools/jira_ticket.py sub --parent <merge ticket key> --day <DAY> --repo <repo> \
     --source <source> --target <target> --description-file reports/<DAY>/jira-<repo>.txt [--assignee "<name>"]
   ```
   It creates `<Repo>: Merge Monday DD/MM/YYYY: <src> up until <tgt>` as a Sub-task with the target's fix
   version. When that sub-ticket already exists (made by hand) it only fills in the description.
4. Don't push that merge. Put the sub-ticket key in the report.

Push + PR:
```bash
cd .cache/work/<repo>
git remote add fork git@github.com:<FORK>/<repo>.git 2>/dev/null || git remote set-url fork git@github.com:<FORK>/<repo>.git
git push -u fork <branch>
body=.github/pull_request_template.md; [ -f "$body" ] || body=/dev/null
gh pr create -R <ORG>/<repo> --base <target> --head <FORK>:<branch> \
  --title "Merge <source> to <target>" --body-file "$body"
```
Never force-push. No co-author trailer, no "Generated with Claude Code" footer,
in commits or PR bodies. Never merge or approve the PR: the developer does the final merge.

## 7. Watch CI until green

For each PR whose repo has a `jenkins_job`, launch an **`upmerge-ci-watcher`**
(background) with `root`, repo, jenkins_job, sonar_project, `sonar_check` = `SONAR_CHECK`, PR number + URL, branch,
source, target, workdir. Each one loops on the Jenkins PR build, fixes merge
defects (compile, unit and integration tests), pushes the fixes, and checks the
Sonar gate.

Repos without a `jenkins_job` in the configuration:
check `gh pr checks <n> -R <ORG>/<repo>` once and report.

Tell the developer the PR links right away; the watchers keep going in the background.
When each watcher returns, append its result to the report and give a short
status line. Anything in `needs_developer` gets surfaced verbatim.

## 8. Commit the report

When every watcher has returned (or the developer ends the run), add the final report
to this repo. First check it, this must print nothing; fix the report if it does:
```bash
grep -nEi "<FORK>|/home/|token|password|secret|[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}" reports/<DAY>/upmerge-report.md
```
Then:
```bash
git add -f reports/<DAY>/upmerge-report.md
git commit -m "Add upmerge report <DAY>"
git push origin main
```
`reports/` is in `.gitignore`, hence `-f`: only this one file goes in, never `scan.json` or
`upmerge-report.json`. A rejected push → `git pull --rebase origin main`, then push again;
never force-push. Give the developer the GitHub link to the report. The run ends here.

## Notes

- Integration tests never run locally (no Docker in WSL); Jenkins runs them on the PR.
- Clones under `.cache/` and `.cache/work/` are persistent caches: never delete them.
- unifly-services: Spotless with `ratchetFrom`, JDK 25 (`~/.jdks/jdk-25`), unit tests take a while.
- unifly-tiles: hybrid, no Spotless, placeholder `npm test`; the real check is `npm ci`.
- `legacy/` (local only, not in git) holds the old Workflow script and the detect-only scripts, for reference only.
- Never commit `.claude/settings.local.json` or `.cache/`, and from `reports/` only the
  `upmerge-report.md` of step 8: the rest holds local permissions, clones and raw run data.
