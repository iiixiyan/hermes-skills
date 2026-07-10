---
name: github-repo-management
description: "Clone/create/fork repos; manage remotes, releases. Also covers cross-platform mirroring (GitHub → Gitee)."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Repositories, Git, Releases, Secrets, Configuration]
    related_skills: [github-auth, github-pr-workflow, github-issues, gitee-repo-management]
---

# GitHub Repository Management

Create, clone, fork, configure, and manage GitHub repositories. Each section shows `gh` first, then the `git` + `curl` fallback.

## Prerequisites

- Authenticated with GitHub (see `github-auth` skill)

### Setup

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
fi

# Get your GitHub username (needed for several operations)
if [ "$AUTH" = "gh" ]; then
  GH_USER=$(gh api user --jq '.login')
else
  GH_USER=$(curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user | python3 -c "import sys,json; print(json.load(sys.stdin)['login'])")
fi
```

If you're inside a repo already:

```bash
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
```

---

## 1. Cloning Repositories

Cloning is pure `git` — works identically either way:

```bash
# Clone via HTTPS (works with credential helper or token-embedded URL)
git clone https://github.com/owner/repo-name.git

# Clone into a specific directory
git clone https://github.com/owner/repo-name.git ./my-local-dir

# Shallow clone (faster for large repos)
git clone --depth 1 https://github.com/owner/repo-name.git

# Clone a specific branch
git clone --branch develop https://github.com/owner/repo-name.git

# Clone via SSH (if SSH is configured)
git clone git@github.com:owner/repo-name.git
```

**With gh (shorthand):**

```bash
gh repo clone owner/repo-name
gh repo clone owner/repo-name -- --depth 1
```

## 2. Creating Repositories

**With gh:**

```bash
# Create a public repo and clone it
gh repo create my-new-project --public --clone

# Private, with description and license
gh repo create my-new-project --private --description "A useful tool" --license MIT --clone

# Under an organization
gh repo create my-org/my-new-project --public --clone

# From existing local directory
cd /path/to/existing/project
gh repo create my-project --source . --public --push
```

**With git + curl:**

```bash
# Create the remote repo via API
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user/repos \
  -d '{
    "name": "my-new-project",
    "description": "A useful tool",
    "private": false,
    "auto_init": true,
    "license_template": "mit"
  }'

# Clone it
git clone https://github.com/$GH_USER/my-new-project.git
cd my-new-project

# -- OR -- push an existing local directory to the new repo
cd /path/to/existing/project
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/$GH_USER/my-new-project.git
git push -u origin main
```

To create under an organization:

```bash
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/orgs/my-org/repos \
  -d '{"name": "my-new-project", "private": false}'
```

### ⚠️ Pitfall: `git push` over HTTPS times out (GitHub API fallback)

When `git push` over HTTPS times out repeatedly — even with `http.postBuffer` tuning — but `curl` to `api.github.com` works fine, use the **GitHub Contents API** to push individual files directly. This is a reliable fallback when git's HTTP transport stalls.

**Symptoms:** `git push origin main` times out (30s/60s/120s) with empty output, stalling at `Trying 20.205.243.166:443...` — but `curl https://api.github.com` responds normally.

**Fix — push via Contents API (Python):**

```python
import json, base64, urllib.request

TOKEN="<your_gh...NER, REPO = "owner", "repo"

def get_sha(path):
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}")
        req.add_header("Authorization", f"Bearer {TOKEN}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode()).get("sha")
    except: return None

def push_file(path, content, msg):
    sha = get_sha(path)
    data = {"message": msg, "content": base64.b64encode(content.encode()).decode()}
    if sha: data["sha"] = sha
    req = urllib.request.Request(f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}",
                                 data=json.dumps(data).encode(), method="PUT")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

push_file("index.html", html_content, "Update page")
push_file("data.json", json_content, "Update data")
```

**Shell version (single file):**
```bash
BASE64=$(base64 -w0 file.json)
SHA=$(curl -s -H "Authorization: Bearer *** \
  "https://api.github.com/repos/$OWNER/$REPO/contents/file.json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('sha',''))")
curl -s -X PUT -H "Authorization: Bearer *** \"$SHA\" ] && echo ,\\\"sha\\\":\\\"$SHA\\\"\" }" \
  "https://api.github.com/repos/$OWNER/$REPO/contents/file.json" \
  -d "{\"message\":\"Update file\",\"content\":\"$BASE64\"}"
```

**Limitations:** Individual files only (≤ 1 MB each). For many files, fix the HTTPS transport or switch to SSH.

**Before resorting to API, try:**
```bash
git config http.postBuffer 524288000
git config http.lowSpeedLimit 1000
git config http.lowSpeedTime 60
git remote set-url origin git@github.com:owner/repo.git  # SSH fallback
```

### ⚠️ Pitfall: Embedded `.git` directories in source directories

When pushing an existing directory that contains **nested git repositories** (e.g. syncing `~/.hermes/skills/` where individual skill dirs were created by `skill_manage` and may have their own `.git/`), `git add -A` will silently register them as **git submodules (gitlinks, mode 160000)** instead of tracking their contents. The outer repo will contain only a pointer, not the actual files.

**Fix before `git add`:**

```bash
find /path/to/source -name ".git" -type d | while read d; do
  rm -rf "$d"
  echo "Removed embedded .git: $d"
done
git add -A
```

Verify no submodule entries snuck in:
```bash
git ls-files --stage | grep ^160000  # Should return nothing
```

### From a Template

**With gh:**

```bash
gh repo create my-new-app --template owner/template-repo --public --clone
```

**With curl:**

```bash
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/owner/template-repo/generate \
  -d '{"owner": "'"$GH_USER"'", "name": "my-new-app", "private": false}'
```

## 3. Forking Repositories

**With gh:**

```bash
gh repo fork owner/repo-name --clone
```

**With git + curl:**

```bash
# Create the fork via API
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/owner/repo-name/forks

# Wait a moment for GitHub to create it, then clone
sleep 3
git clone https://github.com/$GH_USER/repo-name.git
cd repo-name

# Add the original repo as "upstream" remote
git remote add upstream https://github.com/owner/repo-name.git
```

### Keeping a Fork in Sync

```bash
# Pure git — works everywhere
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

**With gh (shortcut):**

```bash
gh repo sync $GH_USER/repo-name
```

## 4. Repository Information

**With gh:**

```bash
gh repo view owner/repo-name
gh repo list --limit 20
gh search repos "machine learning" --language python --sort stars
```

**With curl:**

```bash
# View repo details
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO \
  | python3 -c "
import sys, json
r = json.load(sys.stdin)
print(f\"Name: {r['full_name']}\")
print(f\"Description: {r['description']}\")
print(f\"Stars: {r['stargazers_count']}  Forks: {r['forks_count']}\")
print(f\"Default branch: {r['default_branch']}\")
print(f\"Language: {r['language']}\")"

# List your repos
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/user/repos?per_page=20&sort=updated" \
  | python3 -c "
import sys, json
for r in json.load(sys.stdin):
    vis = 'private' if r['private'] else 'public'
    print(f\"  {r['full_name']:40}  {vis:8}  {r.get('language', ''):10}  ★{r['stargazers_count']}\")"

# Search repos
curl -s \
  "https://api.github.com/search/repositories?q=machine+learning+language:python&sort=stars&per_page=10" \
  | python3 -c "
import sys, json
for r in json.load(sys.stdin)['items']:
    print(f\"  {r['full_name']:40}  ★{r['stargazers_count']:6}  {r['description'][:60] if r['description'] else ''}\")"
```

## 5. Repository Settings

**With gh:**

```bash
gh repo edit --description "Updated description" --visibility public
gh repo edit --enable-wiki=false --enable-issues=true
gh repo edit --default-branch main
gh repo edit --add-topic "machine-learning,python"
gh repo edit --enable-auto-merge
```

**With curl:**

```bash
curl -s -X PATCH \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO \
  -d '{
    "description": "Updated description",
    "has_wiki": false,
    "has_issues": true,
    "allow_auto_merge": true
  }'

# Update topics
curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.mercy-preview+json" \
  https://api.github.com/repos/$OWNER/$REPO/topics \
  -d '{"names": ["machine-learning", "python", "automation"]}'
```

## 6. Branch Protection

```bash
# View current protection
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/branches/main/protection

# Set up branch protection
curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/branches/main/protection \
  -d '{
    "required_status_checks": {
      "strict": true,
      "contexts": ["ci/test", "ci/lint"]
    },
    "enforce_admins": false,
    "required_pull_request_reviews": {
      "required_approving_review_count": 1
    },
    "restrictions": null
  }'
```

## 7. Secrets Management (GitHub Actions)

**With gh:**

```bash
gh secret set API_KEY --body "your-secret-value"
gh secret set SSH_KEY < ~/.ssh/id_rsa
gh secret list
gh secret delete API_KEY
```

**With curl:**

Secrets require encryption with the repo's public key — more involved via API:

```bash
# Get the repo's public key for encrypting secrets
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/actions/secrets/public-key

# Encrypt and set (requires Python with PyNaCl)
python3 -c "
from base64 import b64encode
from nacl import encoding, public
import json, sys

# Get the public key
key_id = '<key_id_from_above>'
public_key = '<base64_key_from_above>'

# Encrypt
sealed = public.SealedBox(
    public.PublicKey(public_key.encode('utf-8'), encoding.Base64Encoder)
).encrypt('your-secret-value'.encode('utf-8'))
print(json.dumps({
    'encrypted_value': b64encode(sealed).decode('utf-8'),
    'key_id': key_id
}))"

# Then PUT the encrypted secret
curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/actions/secrets/API_KEY \
  -d '<output from python script above>'

# List secrets (names only, values hidden)
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/actions/secrets \
  | python3 -c "
import sys, json
for s in json.load(sys.stdin)['secrets']:
    print(f\"  {s['name']:30}  updated: {s['updated_at']}\")"
```

Note: For secrets, `gh secret set` is dramatically simpler. If setting secrets is needed and `gh` isn't available, recommend installing it for just that operation.

## 8. Releases

**With gh:**

```bash
gh release create v1.0.0 --title "v1.0.0" --generate-notes
gh release create v2.0.0-rc1 --draft --prerelease --generate-notes
gh release create v1.0.0 ./dist/binary --title "v1.0.0" --notes "Release notes"
gh release list
gh release download v1.0.0 --dir ./downloads
```

**With curl:**

```bash
# Create a release
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/releases \
  -d '{
    "tag_name": "v1.0.0",
    "name": "v1.0.0",
    "body": "## Changelog\n- Feature A\n- Bug fix B",
    "draft": false,
    "prerelease": false,
    "generate_release_notes": true
  }'

# List releases
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/releases \
  | python3 -c "
import sys, json
for r in json.load(sys.stdin):
    tag = r.get('tag_name', 'no tag')
    print(f\"  {tag:15}  {r['name']:30}  {'draft' if r['draft'] else 'published'}\")"

# Upload a release asset (binary file)
RELEASE_ID=<id_from_create_response>
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/octet-stream" \
  "https://uploads.github.com/repos/$OWNER/$REPO/releases/$RELEASE_ID/assets?name=binary-amd64" \
  --data-binary @./dist/binary-amd64
```

## 9. GitHub Actions Workflows

**With gh:**

```bash
gh workflow list
gh run list --limit 10
gh run view <RUN_ID>
gh run view <RUN_ID> --log-failed
gh run rerun <RUN_ID>
gh run rerun <RUN_ID> --failed
gh workflow run ci.yml --ref main
gh workflow run deploy.yml -f environment=staging
```

**With curl:**

```bash
# List workflows
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/actions/workflows \
  | python3 -c "
import sys, json
for w in json.load(sys.stdin)['workflows']:
    print(f\"  {w['id']:10}  {w['name']:30}  {w['state']}\")"

# List recent runs
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/actions/runs?per_page=10" \
  | python3 -c "
import sys, json
for r in json.load(sys.stdin)['workflow_runs']:
    print(f\"  Run {r['id']}  {r['name']:30}  {r['conclusion'] or r['status']}\")"

# Download failed run logs
RUN_ID=<run_id>
curl -s -L \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID/logs \
  -o /tmp/ci-logs.zip
cd /tmp && unzip -o ci-logs.zip -d ci-logs

# Re-run a failed workflow
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID/rerun

# Re-run only failed jobs
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID/rerun-failed-jobs

# Trigger a workflow manually (workflow_dispatch)
WORKFLOW_ID=<workflow_id_or_filename>
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/actions/workflows/$WORKFLOW_ID/dispatches \
  -d '{"ref": "main", "inputs": {"environment": "staging"}}'
```

## 10. Gists

**With gh:**

```bash
gh gist create script.py --public --desc "Useful script"
gh gist list
```

**With curl:**

```bash
# Create a gist
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/gists \
  -d '{
    "description": "Useful script",
    "public": true,
    "files": {
      "script.py": {"content": "print(\"hello\")"}
    }
  }'

# List your gists
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/gists \
  | python3 -c "
import sys, json
for g in json.load(sys.stdin):
    files = ', '.join(g['files'].keys())
    print(f\"  {g['id']}  {g['description'] or '(no desc)':40}  {files}\")"
```

## Quick Reference Table

| Action | gh | git + curl |
|--------|-----|-----------|
| Clone | `gh repo clone o/r` | `git clone https://github.com/o/r.git` |
| Create repo | `gh repo create name --public` | `curl POST /user/repos` |
| Fork | `gh repo fork o/r --clone` | `curl POST /repos/o/r/forks` + `git clone` |
| Repo info | `gh repo view o/r` | `curl GET /repos/o/r` |
| Edit settings | `gh repo edit --...` | `curl PATCH /repos/o/r` |
| Create release | `gh release create v1.0` | `curl POST /repos/o/r/releases` |
| List workflows | `gh workflow list` | `curl GET /repos/o/r/actions/workflows` |
| Rerun CI | `gh run rerun ID` | `curl POST /repos/o/r/actions/runs/ID/rerun` |
| Set secret | `gh secret set KEY` | `curl PUT /repos/o/r/actions/secrets/KEY` (+ encryption) |
| Push file (API) | — | `curl PUT /repos/o/r/contents/path` (§Pitfalls) |
| Browse data UI | — | `references/data-browser-page-pattern.md` (incl. coding Q-bank 3-tab variant) |

## Related Skill References

- `github-auth` — authentication setup (tokens, SSH, gh CLI login)\n- `github-pr-workflow` — PR lifecycle (branch, commit, open, CI, merge)\n- `gitee-repo-management` — Gitee-specific mirroring and workflows\n- `references/data-browser-page-pattern.md` — building searchable/filterable single-page data viewers from static JSON (good for published datasets on GitHub Pages)\n- `references/react-data-viewer-pattern.md` — React/TS/Vite/antd approach for rich data viewers with routing, localStorage state, and GitHub Actions CI/CD

## 11. Cross-Platform Mirroring (GitHub → Gitee)

## 12. Multi-Remote Sync (Generic: Platform A → GitHub)

Clone from any git platform (GitCode, Gitee, GitLab, Bitbucket, self-hosted) → process → push to a new GitHub repo.

### Workflow

```bash
# 1. Clone from source platform
# Format: https://oauth2:TOKEN@gitcode.com/owner/repo.git
git clone https://oauth2:$SOURCE_TOKEN@gitcode.com/owner/repo.git /tmp/workdir
cd /tmp/workdir

# 2. (Optional) Process data — transform, merge, generate files
python3 process.py

# 3. Create GitHub repo (if not exists)
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user/repos \
  -d '{"name": "'"$REPO_NAME"'", "private": false}'

# 4. Init new git and push to GitHub
cd /tmp/workdir/pages  # or wherever the output files are
git init
git add -A
git commit -m "Sync from source"
git remote add origin https://oauth2:$GITHUB_TOKEN@github.com/$OWNER/$REPO_NAME.git
git branch -M main
git push -u origin main

# 5. Enable GitHub Pages
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO_NAME/pages" \
  -d '{"source": {"branch": "main", "path": "/"}}'
```

### Full Python Automation (self-contained)

When git push over HTTPS times out but the GitHub API works, use the Contents API instead:

```python
import json, base64, urllib.request, subprocess, os, re

# Get tokens
with open(os.path.expanduser('~/.git-credentials')) as f:
    creds = f.read()
gh_token = re.search(r'https://oauth2:([^@]+)@github\.com', creds).group(1)
source_token = re.search(r'https://oauth2:([^@]+)@gitcode\.com', creds).group(1)

# Clone from source
WORK = "/tmp/workdir"
if os.path.exists(WORK): subprocess.run(['rm', '-rf', WORK])
subprocess.run(['git', 'clone',
    f'https://oauth2:{source_token}@gitcode.com/owner/repo.git',
    f'{WORK}/source'], timeout=30)

# Process data (e.g. merge JSON, generate HTML)
# ... your transformation here ...

# Create GitHub repo
req = urllib.request.Request(
    f"https://api.github.com/user/repos",
    data=json.dumps({"name": REPO_NAME, "private": False}).encode(),
    method="POST")
req.add_header("Authorization", f"Bearer {gh_token}")
req.add_header("Content-Type", "application/json")
urllib.request.urlopen(req, timeout=15)

# Push files via Contents API
def push_file(path, content, msg):
    sha = None
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{OWNER}/{REPO_NAME}/contents/{path}")
        req.add_header("Authorization", f"Bearer {gh_token}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            sha = json.loads(resp.read().decode()).get("sha")
    except: pass
    data = {"message": msg, "content": base64.b64encode(content.encode()).decode()}
    if sha: data["sha"] = sha
    req = urllib.request.Request(
        f"https://api.github.com/repos/{OWNER}/{REPO_NAME}/contents/{path}",
        data=json.dumps(data).encode(), method="PUT")
    req.add_header("Authorization", f"Bearer {gh_token}")
    req.add_header("Content-Type", "application/json")
    urllib.request.urlopen(req, timeout=30)
    print(f"  {path}: pushed")

push_file("index.html", html_content, "Add page")
push_file("data.json", json_content, "Add data")

# Enable Pages
req = urllib.request.Request(
    f"https://api.github.com/repos/{OWNER}/{REPO_NAME}/pages",
    data=json.dumps({"source": {"branch": "master", "path": "/"}}).encode(),
    method="POST")
req.add_header("Authorization", f"Bearer {gh_token}")
req.add_header("Content-Type", "application/json")
urllib.request.urlopen(req, timeout=15)
```

### Pitfalls

- **Git clone from Chinese platforms may need tokens in URL format** `https://oauth2:TOKEN@domain.com/owner/repo.git` (not `Bearer` header, not `Authorization: token`).
- **Empty repos cannot enable Pages.** Push at least one commit first.
- **When `git push` stalls,** fall back to Contents API (individual files, ≤ 1 MB each).
- **Clean up `/tmp`** after sync if sensitive data was cloned there.
- **Git push over HTTPS fails** with `Invalid username or token` — this means the token is not accepted in the standard `https://TOKEN@github.com` format. The working format for token auth is `https://oauth2:${GH_TOKEN}@github.com/user/repo.git`. Use:
  ```bash
  git remote set-url origin "https://oauth2:${GH_TOKEN}@github.com/<user>/<repo>.git"
  git push origin master
  ```
  Environment variables `GH_TOKEN` and `GITHUB_TOKEN` may both be present — if one fails, try the other. The `oauth2:` prefix is specifically needed for GitHub's HTTPS auth when using a personal access token (both classic and fine-grained).

### Use Cases

| Source | Token Source | Clone URL Pattern |
|--------|-------------|-------------------|
| GitCode | `~/.git-credentials` (gitcode.com) | `https://oauth2:${TOKEN}@gitcode.com/owner/repo.git` |
| Gitee | `~/.git-credentials` (gitee.com) | `https://oauth2:${TOKEN}@gitee.com/owner/repo.git` |
| GitLab | personal access token | `https://oauth2:${TOKEN}@gitlab.com/owner/repo.git` |
| GitHub (fork→own) | `~/.git-credentials` | `https://oauth2:${TOKEN}@github.com/owner/repo.git` |

When copying a GitHub repo to Gitee (Chinese git platform), account for these differences:

### Prerequisites
- Gitee Personal Access Token (stored in `~/.hermes/.env` or passed via `GITEE_TOKEN`)
- Gitee username (e.g. `year_old`)

### Workflow

```bash
# 1. Clone from GitHub (no auth needed for public repos)
git clone https://github.com/owner/repo-name.git /tmp/repo-name
cd /tmp/repo-name

# 2. Check the default branch name
git branch --show-current   # 'main' or 'master'

# 3. Create the Gitee repo via API (starts private)
curl -s -X POST "https://gitee.com/api/v5/user/repos" \
  -H "Authorization: token $GITEE_TOKEN" \
  -d '{"name":"repo-name","description":"Mirrored from GitHub"}'

# 4. Add Gitee remote — TOKEN:USERNAME format required, not just TOKEN
git remote add gitee "https://$GITEE_USER:$GITEE_TOKEN@gitee.com/$GITEE_USER/repo-name.git"

# 5. Push to Gitee
git push -u gitee main

# 6. Set public (only works after push — Gitee blocks public on empty repos)
curl -s -X PATCH "https://gitee.com/api/v5/repos/$GITEE_USER/repo-name" \
  -H "Authorization: token $GITEE_TOKEN" \
  -d '{"name":"repo-name","private":false}'
```

### Pitfalls
- **Empty repos cannot be made public.** Push at least one commit before setting `"private": false`.
- Token special chars in shell. When the token contains $, !, #, inline URL substitution fails. Use the git credential store method: printf 'https://oauth2:%s@gitee.com\n' "$GITEE_TOKEN" > /tmp/creds && git config credential.helper 'store --file /tmp/creds' && rm -f /tmp/creds.
- **Gitee API auth header** is `Authorization: token TOKEN` (same format as GitHub, no `Bearer` prefix).
- **Gitee PATCH requires "name" field.** Gitee's PATCH /repos/{owner}/{repo} returns `"name is missing"` if the `name` field isn't included, even when you're only changing visibility.
- **Empty repo cannot be public.** Gitee returns `"空仓库不支持设置为公开仓库"` when trying to set an empty repo to public. Push code first, then toggle visibility.
- Gitee API base is https://gitee.com/api/v5, not api.github.com.

> 💡 See the gitee-repo-management skill for detailed Gitee-specific workflows: creating repos from scratch, visibility management, push with credential store, and Gitee API cheatsheet.
