---
name: confluence
description: Query Atlassian Jira and Confluence APIs. Use for searching issues, tickets, wiki pages, documentation, and project data at unifly.atlassian.net.
allowed-tools: Bash(curl *)
---

# Atlassian API Access (Jira & Confluence)

## Authentication
Credentials live in `~/.claude/skills/confluence/.netrc` (your Atlassian e-mail + API token,
mode 600). Pass it to every curl call:
```
curl -s --netrc-file ~/.claude/skills/confluence/.netrc ...
```
The file holds one line:
```
machine unifly.atlassian.net login <your Atlassian e-mail> password <your Atlassian API token>
```
Create the token at https://id.atlassian.com/manage-profile/security/api-tokens.

## Confluence API

### Search pages by text
```bash
curl -s --netrc-file ~/.claude/skills/confluence/.netrc \
  "https://unifly.atlassian.net/wiki/rest/api/search?cql=text~%22SEARCH_TERM%22"
```

### Search in specific space
```bash
curl -s --netrc-file ~/.claude/skills/confluence/.netrc \
  "https://unifly.atlassian.net/wiki/rest/api/search?cql=space=DEVOPS%20AND%20text~%22SEARCH_TERM%22"
```

### Get page content by ID
```bash
curl -s --netrc-file ~/.claude/skills/confluence/.netrc \
  "https://unifly.atlassian.net/wiki/rest/api/content/PAGE_ID?expand=body.storage" | jq -r '.body.storage.value' | sed 's/<[^>]*>//g'
```

### List spaces
```bash
curl -s --netrc-file ~/.claude/skills/confluence/.netrc \
  "https://unifly.atlassian.net/wiki/rest/api/space"
```

## Jira API

### Search issues (JQL)
```bash
curl -s --netrc-file ~/.claude/skills/confluence/.netrc \
  "https://unifly.atlassian.net/rest/api/3/search?jql=project=PROJECT_KEY"
```

### Get issue by key
```bash
curl -s --netrc-file ~/.claude/skills/confluence/.netrc \
  "https://unifly.atlassian.net/rest/api/3/issue/ISSUE_KEY"
```

### Get my assigned issues
```bash
curl -s --netrc-file ~/.claude/skills/confluence/.netrc \
  "https://unifly.atlassian.net/rest/api/3/search?jql=assignee=currentUser()"
```

## Common Confluence Spaces
- `DEVOPS` - DevOps documentation
- `DEV` - Engineering
- `IMS` - Integrated Management System
- `COM` - Communities

## Tips
- URL encode search terms: spaces become `%20`, quotes become `%22`
- Use `jq` to parse JSON responses
- Pipe through `sed 's/<[^>]*>//g'` to strip HTML tags from Confluence content

## Arguments
$ARGUMENTS - Pass search terms, issue keys, or page IDs
