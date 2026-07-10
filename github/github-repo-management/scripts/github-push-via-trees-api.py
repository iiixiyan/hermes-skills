#!/usr/bin/env python3
"""Push entire directory to GitHub via Git Trees API.
Fallback when 'git push' over HTTPS times out but GitHub API works.
Usage: python3 github-push-via-trees-api.py 
"""
import os, json, base64, urllib.request, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURE THESE ---
OWNER = "iiixiyan"
REPO = "hermes-skills"
LOCAL_DIR = "/root/.hermes/skills"
# -----------------------

def get_token():
    r = subprocess.run(['bash', '-c', 'source /root/.hermes/.env 2>/dev/null; echo "$GITHUB_TOKEN"'],
                       capture_output=True, text=True)
    return r.stdout.strip()

TOKEN = get_token()
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github.v3+json",
           "Content-Type": "application/json"}

def api(method, path, data=None, timeout=60):
    url = f"https://api.github.com{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method, headers=HEADERS, unverifiable=True)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
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

def main():
    exclude_dirs = {'.git', '.hub', '.curator_backups', '__pycache__'}
    exclude_files = {'.usage.json', '.usage.json.lock', '.bundled_manifest', '.curator_state'}

    files_list = []
    for root, dirs, filenames in os.walk(LOCAL_DIR):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in filenames:
            fpath = os.path.join(root, f)
            rel = os.path.relpath(fpath, LOCAL_DIR)
            if rel in exclude_files or rel.endswith('.pyc'):
                continue
            with open(fpath, 'rb') as fh:
                content = fh.read()
            try:
                text = content.decode('utf-8')
                files_list.append((rel, text, "utf-8"))
            except UnicodeDecodeError:
                files_list.append((rel, base64.b64encode(content).decode(), "base64"))

    print(f"共 {len(files_list)} 个文件")

    # Create blobs in parallel
    blobs = [None] * len(files_list)
    def create_blob(i, rel, content, encoding):
        data = {"content": content}
        if encoding == "base64":
            data["encoding"] = "base64"
        result = api("POST", f"/repos/{OWNER}/{REPO}/git/blobs", data)
        return (i, rel, result["sha"] if result and result.get("sha") else None)

    print("创建 blobs (并行20线程)...")
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(create_blob, i, rel, content, enc)
                   for i, (rel, content, enc) in enumerate(files_list)]
        done = 0
        for f in as_completed(futures):
            i, rel, sha = f.result()
            if sha:
                blobs[i] = {"path": rel, "mode": "100644", "type": "blob", "sha": sha}
            done += 1
            if done % 100 == 0:
                print(f"  进度: {done}/{len(files_list)}")

    failed = [i for i, b in enumerate(blobs) if b is None]
    if failed:
        print(f"❌ {len(failed)} blobs 失败")
        sys.exit(1)

    # Build tree in chunks of 100
    CHUNK = 100
    tree_sha = None
    for chunk_start in range(0, len(blobs), CHUNK):
        chunk = blobs[chunk_start:chunk_start+CHUNK]
        print(f"  构建 tree chunk {chunk_start//CHUNK + 1}/{(len(blobs)-1)//CHUNK + 1}...")
        payload = {"tree": chunk}
        if tree_sha:
            payload["base_tree"] = tree_sha
        result = api("POST", f"/repos/{OWNER}/{REPO}/git/trees", payload, timeout=120)
        if not result or not result.get("sha"):
            print("  tree chunk 失败")
            sys.exit(1)
        tree_sha = result["sha"]

    # Create commit
    print("创建 commit...")
    commit = api("POST", f"/repos/{OWNER}/{REPO}/git/commits",
                 {"message": "Sync all Hermes Agent skills", "tree": tree_sha, "parents": []})
    if not commit or not commit.get("sha"):
        print("创建 commit 失败")
        sys.exit(1)

    # Update ref
    print("更新 refs/heads/main...")
    ref = api("PATCH", f"/repos/{OWNER}/{REPO}/git/refs/heads/main",
              {"sha": commit["sha"], "force": True})
    if not ref:
        ref = api("POST", f"/repos/{OWNER}/{REPO}/git/refs",
                  {"ref": "refs/heads/main", "sha": commit["sha"]})
    if ref and ref.get("ref"):
        print(f"✅ 已推送: {ref['ref']} ({commit['sha'][:12]})")
    else:
        print("❌ 更新分支失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
