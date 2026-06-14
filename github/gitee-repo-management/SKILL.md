---
name: gitee-repo-management
description: "Create, clone, configure Gitee repositories via API + git. Covers repo creation, visibility management, HTTPS push with token auth, and Gitee API quirks."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Gitee, Repositories, Git, API]
    related_skills: [github-repo-management, github-auth]
---

# Gitee Repository Management

Create, push to, and manage repositories on [Gitee](https://gitee.com) (the main Chinese Git hosting platform). Uses the Gitee REST API v5 for repo management and `git` with HTTPS token auth for pushes.

## Prerequisites

- Gitee Personal Access Token stored in `~/.hermes/.env` as `GITEE_TOKEN`
- Gitee username (e.g. `iiixiyan` — the login name)

### Load the Token

```bash
# From .env
source ~/.hermes/.env
# Now $GITEE_TOKEN is available

# Or if sourcing .env is inconvenient:
GITEE_TOKEN=$(grep "^GITEE_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
```

---

## 1. Check or Set Gitee Identity

```bash
GITEE_USER=$(curl -s -H "Authorization: token $GITEE_TOKEN" \
  https://gitee.com/api/v5/user | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['login'])")
echo "Gitee user: $GITEE_USER"
```

---

## 2. Create a New Repository

**Create via API:**

```bash
curl -s -X POST 'https://gitee.com/api/v5/user/repos' \
  -H 'Content-Type: application/json;charset=UTF-8' \
  -d "{
    \"access_token\": \"$GITEE_TOKEN\",
    \"name\": \"repo-name\",
    \"description\": \"Short description of the repo\",
    \"has_issues\": true,
    \"has_wiki\": false,
    \"auto_init\": false,
    \"private\": false
  }" | python3 -m json.tool
```

**Key points about the API call:**
- Use `"access_token"` in the JSON body (not `"Authorization"` header) — or use the `Authorization: token $TOKEN` header **without** `access_token` in the body (do one or the other, not both)
- `"auto_init": false` means the repo is created **empty** — no README, no .gitignore
- `"private": false` may be **ignored** for empty repos (see Pitfalls below)
- Response includes `"html_url"` with the clone URL

### 2a. Fix Visibility After Push

Gitee **will not** make an empty repo public. You must push code first, then toggle visibility:

```bash
# After pushing code (see Section 3), set repo to public
curl -s -X PATCH "https://gitee.com/api/v5/repos/$GITEE_USER/repo-name" \
  -H 'Content-Type: application/json;charset=UTF-8' \
  -d "{
    \"access_token\": \"$GITEE_TOKEN\",
    \"name\": \"repo-name\",
    \"private\": false
  }" | python3 -c "import json,sys; d=json.load(sys.stdin); print('公开' if not d.get('private') else '私有')"
```

> ⚠️ The `"name"` field is **required** in the PATCH body even when only changing visibility. Gitee returns `"name is missing"` without it.

---

## 3. Push to Gitee (HTTPS with Token Auth)

### Method A: Token in Remote URL (Simple but Fragile)

```bash
git remote add origin "https://$GITEE_USER:$GITEE_TOKEN@gitee.com/$GITEE_USER/repo-name.git"
git push -u origin main
```

**⚠️ Pitfall:** If the token contains special characters (`$`, `!`, `#`, etc.) this fails with quoting errors. Switch to Method B.

### Method B: Git Credential Store (Robust — Preferred)

Works when the token has special characters that break inline URL substitution:

```bash
cd /path/to/local/repo
git init
git remote add origin "https://gitee.com/$GITEE_USER/repo-name.git"

# Store Gitee credentials in a temp file
git config credential.helper 'store --file /tmp/gitee-creds'
printf 'https://oauth2:%s@gitee.com\n' "$GITEE_TOKEN" > /tmp/gitee-creds

# Push
git push -u origin main

# Clean up
rm -f /tmp/gitee-creds
git config --unset credential.helper
```

**Why this works:** `printf` processes the token as a shell variable (safe from quoting issues), and git's credential store reads it cleanly. The `oauth2:` prefix is Gitee's expected credential format for OAuth2 tokens.

---

## 4. Push Existing Content (From Scratch Workflow)

Complete script for creating a repo from an existing document:

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

# 4. Make public
curl -s -X PATCH "https://gitee.com/api/v5/repos/$GITEE_USER/$REPO_NAME" \
  -H 'Content-Type: application/json;charset=UTF-8' \
  -d "{
    \"access_token\": \"$GITEE_TOKEN\",
    \"name\": \"$REPO_NAME\",
    \"private\": false
  }"

echo "✅ https://gitee.com/$GITEE_USER/$REPO_NAME"
```

---

## 5. List User Repos

```bash
source ~/.hermes/.env
GITEE_USER=$(curl -s -H "Authorization: token $GITEE_TOKEN" \
  https://gitee.com/api/v5/user | python3 -c "import sys,json; print(json.load(sys.stdin)['login'])")

curl -s -H "Authorization: token $GITEE_TOKEN" \
  "https://gitee.com/api/v5/users/$GITEE_USER/repos?type=all&per_page=50&sort=updated" \
  | python3 -c "
import json, sys
for r in json.load(sys.stdin):
    vis = '公开' if not r.get('private') else '私有'
    print(f\"  {r['name']:35s}  {vis:4s}  {r.get('description', '') or '(无描述)'}\")
"
```

---

## 6. Delete a Repository

```bash
source ~/.hermes/.env
curl -s -X DELETE "https://gitee.com/api/v5/repos/$GITEE_USER/repo-name" \
  -d "access_token=$GITEE_TOKEN"
```

---

## Pitfalls & Quirks

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Empty repo can't be public** | `"空仓库不支持设置为公开仓库"` | Push code first, THEN set `private: false` |
| **PATCH requires name field** | `"name is missing"` | Include `"name": "repo-name"` in the PATCH body |
| **Token special chars break URL** | Bash quoting errors with `$` `!` etc. | Use credential store method (Method B) |
| **`oauth2:` prefix in credentials** | Auth fails with bare token | Use `printf 'https://oauth2:%s@gitee.com\n' "$TOKEN"` |
| **Gitee API base** | Wrong endpoint | Use `https://gitee.com/api/v5/` (not `api.github.com`) |
| **Auth header format** | 401 errors | Use `Authorization: token TOKEN` (same as GitHub, no `Bearer`) |

---

## Quick Reference

| Action | Command |
|--------|---------|
| Get user info | `curl -s -H "Authorization: token $T" https://gitee.com/api/v5/user` |
| Create repo | `POST https://gitee.com/api/v5/user/repos` with `{"name":"..."}` |
| List repos | `GET https://gitee.com/api/v5/users/$USER/repos` |
| Update repo | `PATCH https://gitee.com/api/v5/repos/$USER/$REPO` |
| Delete repo | `DELETE https://gitee.com/api/v5/repos/$USER/$REPO` |
| HTTPS clone | `git clone https://gitee.com/$USER/$REPO.git` |
| HTTPS push with token | Credential store (Method B) preferred |
