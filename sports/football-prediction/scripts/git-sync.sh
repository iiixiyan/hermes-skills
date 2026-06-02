#!/usr/bin/env bash
# git-sync.sh — Commit and push football-prediction skill changes to GitHub + Gitee
# Usage: bash scripts/git-sync.sh [commit_message]
# Designed to be called after daily review optimization.
# Detects the git root automatically and only commits files under sports/football-prediction/.

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
GIT_ROOT="$(git -C "$SKILL_DIR" rev-parse --show-toplevel)"
RELATIVE_DIR="$(realpath --relative-to="$GIT_ROOT" "$SKILL_DIR")"

DEFAULT_MSG="daily-review: $(date '+%Y-%m-%d') skill update"
COMMIT_MSG="${1:-$DEFAULT_MSG}"

cd "$GIT_ROOT"

# Stage changed files under the skill directory
git add "${RELATIVE_DIR}/SKILL.md" "${RELATIVE_DIR}/references/" "${RELATIVE_DIR}/scripts/" 2>/dev/null || true

# Check if anything was staged
if git diff --cached --quiet; then
    echo "No changes to commit under ${RELATIVE_DIR}."
    exit 0
fi

# Commit
git commit -m "$COMMIT_MSG"

# Push to all remotes
REMOTES=$(git remote)
for remote in $REMOTES; do
    echo "Pushing to $remote..."
    git push "$remote" HEAD 2>&1 || echo "  ⚠️  Push to $remote failed (network/auth?), continuing."
done

echo "✅ git-sync complete: $COMMIT_MSG"
