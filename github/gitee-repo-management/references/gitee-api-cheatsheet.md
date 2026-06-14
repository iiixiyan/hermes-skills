# Gitee REST API v5 Cheatsheet

Base URL: `https://gitee.com/api/v5`

Auth: `Authorization: token $GITEE_TOKEN` (header) OR `access_token=$GITEE_TOKEN` (body param)

## User

| Action | Method | Endpoint |
|--------|--------|----------|
| Get current user | GET | `/user` |
| Get a user | GET | `/users/{username}` |

## Repositories

| Action | Method | Endpoint | Notes |
|--------|--------|----------|-------|
| List user repos | GET | `/users/{username}/repos?type=all&sort=updated` | Paginated (default 20, max 100) |
| Create repo | POST | `/user/repos` | Body: `{"name":"...", "private":false}` |
| Get repo | GET | `/repos/{owner}/{repo}` | |
| Update repo | PATCH | `/repos/{owner}/{repo}` | **Must include `"name"` field** |
| Delete repo | DELETE | `/repos/{owner}/{repo}` | |

### Create Repo Body

```json
{
  "access_token": "your_token_here",  // or use Authorization header instead
  "name": "repo-name",
  "description": "Description of the repo",
  "homepage": "",
  "has_issues": true,
  "has_wiki": false,
  "auto_init": false,
  "private": false
}
```

### Update Repo Body (PATCH)

```json
{
  "access_token": "your_token_here",
  "name": "repo-name",           // REQUIRED even when only changing visibility
  "private": false
}
```

## Common curl Patterns

```bash
# Auth with header (preferred)
curl -s -H "Authorization: token $GITEE_TOKEN" https://gitee.com/api/v5/user

# Auth with body param
curl -s -X POST https://gitee.com/api/v5/user/repos \
  -d "access_token=$GITEE_TOKEN&name=my-repo"

# JSON body (requires Content-Type header)
curl -s -X POST https://gitee.com/api/v5/user/repos \
  -H 'Content-Type: application/json;charset=UTF-8' \
  -d '{"access_token":"...", "name":"my-repo", "private":false}'

# Parse JSON with python3
curl -s ... | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['html_url'])"
```

## Key Differences from GitHub API

| Aspect | GitHub | Gitee |
|--------|--------|-------|
| Base URL | `api.github.com` | `gitee.com/api/v5` |
| Auth header | `Authorization: token TOKEN` | Same format |
| Body auth | N/A (header only) | Also supports `access_token` in body |
| Repo visibility | `PATCH` without `name` works | **Requires `name` in PATCH body** |
| Empty repos | Can be public immediately | **Cannot** be public — push first |
| Max per_page | 100 | 100 |
| Public repo creation | `"private": false` works on empty | May be ignored on empty; fix after push |
