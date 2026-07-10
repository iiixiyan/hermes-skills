#!/usr/bin/env python3
"""
Push a local directory to a GitHub repo via API (Git Trees).

Use when 'git push' over HTTPS times out but api.github.com is reachable.
Batches files into trees of 100, creates a single commit, updates ref.

Usage:
  export GITHUB_TOKEN=ghp_...
  python3 github-push-via-trees-api.py /path/to/dir owner repo [--message "commit msg"]

Dependencies: none (stdlib only: os, json, base64, urllib, subprocess)
"""
import os, sys, json, base64, urllib.request, subprocess, time
from concurrent.futures import ThreadPoolExecutor, as_completed

OWNER = REPO = None
MSG = "Sync via Trees API"

def api(method, path, data=None):
    token = os.environ.get("GITHUB_TOKEN", "")
    url = f"https://api.github.com{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method, unverifiable=True)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("Content-Type", "application/json")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 502 and attempt < 2:
                time.sleep(3)
                continue
            print(f"  HTTP {e.code}: {e.read().decode()[:200]}")
            return None
        except Exception as e:
            if attempt < 2:
                time.sleep(3)
                continue
            print(f"  Error: {e}")
            return None

def push_directory(base_dir):
    """Push all files in base_dir to OWNER/REPO on GitHub via Trees API."""
    if not os.path.isdir(base_dir):
        print(f"❌ Not a directory: {base_dir}")
        return False

    # Collect files
    skip_dirs = {'.git', '.hub', '__pycache__', '.curator_backups', '.git'}
    skip_files = {'.DS_Store', 'Thumbs.db'}
    files = []
    for root, dirs, filenames in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in filenames:
            if f in skip_files or f.endswith('.pyc'):
                continue
            fpath = os.path.join(root, f)
            rel = os.path.relpath(fpath, base_dir)
            with open(fpath, 'rb') as fh:
                content = fh.read()
            try:
                text = content.decode('utf-8')
                files.append((rel, text, "utf-8"))
            except UnicodeDecodeError:
                files.append((rel, base64.b64encode(content).decode(), "base64"))

    print(f"共 {len(files)} 个文件")

    # Step 1: Create blobs in parallel
    blobs = [None] * len(files)
    def create_blob(i, rel, content, encoding):
        data = {"content": content}
        if encoding == "base64":
            data["encoding"] = "base64"
        result = api("POST", f"/repos/{OWNER}/{REPO}/git/blobs", data)
        if result and result.get("sha"):
            return (i, rel, result["sha"])
        return (i, rel, None)

    print("创建 blobs (20并发)")
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(create_blob, i, rel, c, enc)
                   for i, (rel, c, enc) in enumerate(files)]
        done = 0
        for f in as_completed(futures):
            i, rel, sha = f.result()
            if sha:
                blobs[i] = {"path": rel, "mode": "100644", "type": "blob", "sha": sha}
            done += 1
            if done % 100 == 0:
                print(f"  {done}/{len(files)}")

    failed = [i for i, b in enumerate(blobs) if b is None]
    if failed:
        print(f"❌ {len(failed)} blobs failed")
        return False
    print(f"✅ {len(blobs)} blobs")

    # Step 2: Create tree in chunks of 100 (GitHub API limit)
    CHUNK = 100
    tree_sha = None
    total_chunks = (len(blobs) - 1) // CHUNK + 1
    for i in range(0, len(blobs), CHUNK):
        chunk = blobs[i:i+CHUNK]
        payload = {"tree": chunk}
        if tree_sha:
            payload["base_tree"] = tree_sha
        result = api("POST", f"/repos/{OWNER}/{REPO}/git/trees", payload)
        if not result or not result.get("sha"):
            print(f"  chunk {i//CHUNK+1}/{total_chunks} failed")
            return False
        tree_sha = result["sha"]
        print(f"  tree chunk {i//CHUNK+1}/{total_chunks}: {tree_sha[:8]}")

    print(f"✅ Tree: {tree_sha}")

    # Step 3: Create commit
    commit = api("POST", f"/repos/{OWNER}/{REPO}/git/commits",
                 {"message": MSG, "tree": tree_sha, "parents": []})
    if not commit or not commit.get("sha"):
        print("❌ Commit failed")
        return False
    print(f"✅ Commit: {commit['sha'][:12]}")

    # Step 4: Update ref
    ref = api("PATCH", f"/repos/{OWNER}/{REPO}/git/refs/heads/main",
              {"sha": commit["sha"], "force": True})
    if not ref:
        ref = api("POST", f"/repos/{OWNER}/{REPO}/git/refs",
                  {"ref": "refs/heads/main", "sha": commit["sha"]})
    if ref and ref.get("ref"):
        print(f"✅ Pushed to {ref['ref']}")
        return True
    print("❌ Ref update failed")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 github-push-via-trees-api.py <dir> <owner> <repo> [--message 'msg']")
        sys.exit(1)
    base = sys.argv[1]
    OWNER = sys.argv[2]
    REPO = sys.argv[3]
    if "--message" in sys.argv:
        idx = sys.argv.index("--message")
        MSG = sys.argv[idx + 1]

    # Also support env vars
    OWNER = os.environ.get("GH_OWNER", OWNER)
    REPO = os.environ.get("GH_REPO", REPO)

    if not os.environ.get("GITHUB_TOKEN"):
        # Try to get token from ~/.hermes/.env
        env_file = os.path.expanduser("~/.hermes/.env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.startswith("GITHUB_TOKEN="):
                        os.environ["GITHUB_TOKEN"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break

    if not os.environ.get("GITHUB_TOKEN"):
        print("❌ GITHUB_TOKEN not set")
        sys.exit(1)

    success = push_directory(base)
    sys.exit(0 if success else 1)
