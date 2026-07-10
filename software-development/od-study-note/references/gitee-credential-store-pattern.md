# Gitee HTTPS Push with Git Credential Store

## Problem

Gitee Personal Access Tokens may contain special characters (`$`, `!`, `#`, `&`, etc.) that break inline URL substitution in Bash:

```bash
# ❌ FAILS when token has $, !, # etc.
git remote add origin "https://oauth2:$GITEE_TOKEN@gitee.com/user/repo.git"
```
Bash interprets `$`, `!` etc. in double quotes, causing quoting errors or wrong expansion.

## Solution: Git Credential Store (Robust)

Works with ANY token content, including special characters:

```bash
cd /path/to/local/repo
git init
git remote add origin "https://gitee.com/$GITEE_USER/repo-name.git"

# Store Gitee credentials in a temp file
git config credential.helper 'store --file /tmp/gitee-creds'
printf 'https://oauth2:%s@gitee.com\n' "$GITEE_TOKEN" > /tmp/gitee-creds

# Push (credential helper reads from /tmp/gitee-creds)
git push -u origin main

# Clean up
rm -f /tmp/gitee-creds
git config --unset credential.helper
```

**Why this works:** `printf` processes the token as a shell variable (safe from quoting issues), and git's credential store reads it cleanly. The `oauth2:` prefix is Gitee's expected credential format for OAuth2 tokens.

## Complete Push-from-Scratch Workflow

```bash
#!/bin/bash
source ~/.hermes/.env
GITEE_USER="iiixiyan"
REPO_NAME="my-new-repo"

# 1. Create repo on Gitee
curl -s -X POST 'https://gitee.com/api/v5/user/repos' \
  -H 'Content-Type: application/json;charset=UTF-8' \
  -d "{
    \"access_token\": \"$GITEE_TOKEN\",
    \"name\": \"$REPO_NAME\",
    \"description\": \"Description\"
  }" > /dev/null

# 2. Local git setup
mkdir -p /tmp/$REPO_NAME
cp /path/to/document.md /tmp/$REPO_NAME/README.md
cd /tmp/$REPO_NAME
git init
git config user.name "$GITEE_USER"
git config user.email "$GITEE_USER@users.noreply.gitee.com"
git add README.md
git commit -m "Initial commit"

# 3. Push with credential store
git remote add origin "https://gitee.com/$GITEE_USER/$REPO_NAME.git"
git config credential.helper 'store --file /tmp/gitee-creds'
printf 'https://oauth2:%s@gitee.com\n' "$GITEE_TOKEN" > /tmp/gitee-creds
git push -u origin main
rm -f /tmp/gitee-creds

# 4. Make public (only works after push — Gitee blocks public on empty repos)
curl -s -X PATCH "https://gitee.com/api/v5/repos/$GITEE_USER/$REPO_NAME" \
  -H 'Content-Type: application/json;charset=UTF-8' \
  -d "{
    \"access_token\": \"$GITEE_TOKEN\",
    \"name\": \"$REPO_NAME\",
    \"private\": false
  }"

echo "✅ https://gitee.com/$GITEE_USER/$REPO_NAME"
```

## Gitee Quirks & Pitfalls Summary

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Empty repo can't be public** | `"空仓库不支持设置为公开仓库"` | Push code first, THEN set `private: false` |
| **PATCH requires name field** | `"name is missing"` | Include `"name": "repo-name"` in the PATCH body |
| **Token special chars break URL** | Bash quoting errors with `$` `!` etc. | Use credential store method (above) |
| **`oauth2:` prefix in credentials** | Auth fails with bare token | Use `printf 'https://oauth2:%s@gitee.com\n' "$TOKEN"` |
| **Gitee API base** | Wrong endpoint | Use `https://gitee.com/api/v5/` (not `api.github.com`) |
| **Auth header format** | 401 errors | Use `Authorization: token TOKEN` (same as GitHub, no `Bearer`) |
| **Visibility after creation** | Repo stays private despite `"private": false` | Must push code first, then PATCH to set public |

## Quick API Reference

| Action | Command |
|--------|---------|
| Get user info | `curl -s -H "Authorization: token $T" https://gitee.com/api/v5/user` |
| Create repo | `POST https://gitee.com/api/v5/user/repos` with `{"name":"..."}` |
| List repos | `GET https://gitee.com/api/v5/users/$USER/repos` |
| Update repo | `PATCH https://gitee.com/api/v5/repos/$USER/$REPO` (must include `"name"`) |
| Delete repo | `DELETE https://gitee.com/api/v5/repos/$USER/$REPO` |
| HTTPS clone | `git clone https://gitee.com/$USER/$REPO.git` |
