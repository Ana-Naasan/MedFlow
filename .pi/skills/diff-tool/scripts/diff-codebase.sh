#!/usr/bin/env bash
# diff-codebase.sh — Gather codebase diff, excluding generated/lock files
#
# Usage:
#   ./scripts/diff-codebase.sh                          # uncommitted changes
#   ./scripts/diff-codebase.sh --since <ref>             # diff from <ref> to HEAD
#   ./scripts/diff-codebase.sh --since-merge             # diff from merge-base with main to HEAD
#   ./scripts/diff-codebase.sh --since-merge <branch>    # diff from merge-base with <branch> to HEAD
#
# Output is written to stdout. Pipe to a file if needed.

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_DIR="$(cd "$SKILL_DIR/../../.." && pwd)"  # .pi/skills/diff-tool/../../.. -> repo root

EXCLUDE_SPEC=":(exclude)package-lock.json :(exclude)pnpm-lock.yaml :(exclude)yarn.lock :(exclude)__pycache__ :(exclude).venv :(exclude)node_modules :(exclude).next :(exclude)dist :(exclude)build"

cd "$PROJECT_DIR"

MODE="${1:-working}"

case "$MODE" in
  --since)
    SINCE_REF="${2?usage: --since <ref>}"
    echo "=== Diff from $SINCE_REF..HEAD ==="
    git diff "$SINCE_REF"..HEAD -- $EXCLUDE_SPEC
    echo ""
    echo "=== Files changed ==="
    git diff --stat "$SINCE_REF"..HEAD -- $EXCLUDE_SPEC
    ;;
  --since-merge)
    BASE_BRANCH="${2:-main}"
    MERGE_BASE=$(git merge-base HEAD "$BASE_BRANCH" 2>/dev/null || echo "")
    if [ -z "$MERGE_BASE" ]; then
      echo "Error: Could not find merge-base with $BASE_BRANCH" >&2
      exit 1
    fi
    echo "=== Diff from merge-base ($MERGE_BASE) with $BASE_BRANCH ==="
    echo ""
    git diff "$MERGE_BASE"..HEAD -- $EXCLUDE_SPEC
    echo ""
    echo "=== Files changed ==="
    git diff --stat "$MERGE_BASE"..HEAD -- $EXCLUDE_SPEC
    ;;
  working|--working|"")
    echo "=== Uncommitted changes ==="
    git diff -- $EXCLUDE_SPEC
    echo ""
    echo "=== Staged changes ==="
    git diff --cached -- $EXCLUDE_SPEC
    echo ""
    echo "=== Untracked files (names only) ==="
    git status --short | grep '^??' | cut -c4- || true
    ;;
  *)
    echo "Usage: $0 [--since <ref> | --since-merge [<branch>]]" >&2
    exit 1
    ;;
esac
