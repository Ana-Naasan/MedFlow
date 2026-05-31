---
name: diff-tool
description: Diff the codebase against a user-provided task to check alignment of new code with the task prompt. Use when you need to verify that code changes (committed or uncommitted) match a given specification, feature request, bug fix, or task description. Detects scope creep, missing implementations, over-engineered code, incorrect edge-case handling, and deviations from the prompt.
---

# Diff-Tool: Code-Task Alignment Checker

This skill helps you verify that recent code changes align with a task/prompt you specify. It works by:

1. Collecting the diff of the codebase (git diff from a reference point)
2. You provide the task/prompt the changes are supposed to implement
3. The skill analyzes the diff for alignment — checking what matches, what's missing, what's over-engineered, and what deviates

## Setup

No setup required. The skill relies on `git` available in PATH.

## Usage

Invoke the skill and provide a task/prompt. The workflow is:

### Step 1: Gather the diff

Use the helper script or `git diff` directly. By default, diff against the merge-base with the target branch.

**Using the helper script (recommended):**

```bash
# Uncommitted + staged changes
.pi/skills/diff-tool/scripts/diff-codebase.sh

# Changes against a specific commit/reference
.pi/skills/diff-tool/scripts/diff-codebase.sh --since <commit>

# Changes on current branch vs a base branch (e.g., main, origin/main, planning)
.pi/skills/diff-tool/scripts/diff-codebase.sh --since-merge origin/main
```

**Using git directly:**

```bash
# Uncommitted changes
git diff -- . ':(exclude)package-lock.json' ':(exclude)node_modules'

# Changes since a specific commit
git diff <commit>..HEAD -- . ':(exclude)package-lock.json'

# Changes on current branch vs main
git diff $(git merge-base HEAD origin/main)..HEAD -- . ':(exclude)package-lock.json'
```

### Step 2: Collect the task/prompt from the user

The user will provide the task prompt. Read it and keep it in context.

### Step 3: Analyze alignment

Analyze the diff against the task prompt, covering these dimensions:

1. **Scope match** — Does the diff implement exactly what the task asks? Any scope creep (extra features not requested)? Any missing pieces?
2. **Implementation correctness** — Does the code follow best practices? Does it handle edge cases the task mentions or implies?
3. **Architecture alignment** — Does the code fit the existing project structure and patterns? Check imports, naming conventions, file locations.
4. **Potential issues** — Are there bugs, security concerns, performance problems, or testing gaps?
5. **Prompt adherence** — For each requirement in the task prompt, does the diff satisfy it? Call out any deviations explicitly.

### Step 4: Report findings

Provide a structured report with:
- Summary of changes (brief)
- What aligns with the task
- What is missing or deviates
- Recommendations for fixing deviations
- Confidence level

## Example

```text
User task: "Add a /healthz endpoint that returns system status including DB connectivity"

Skill output:
- Changes: added app/api/healthz.py, modified app/api/router.py, added tests/test_healthz.py
- ✅ /healthz endpoint present at GET /healthz
- ✅ Returns JSON with status and db_connected fields
- ⚠️ Task mentions caching but no cache integration
- ✅ Tests cover success and failure cases
- ❌ No documentation of the new endpoint
- Recommendation: add endpoint docs to docs/api.md
```

## Helper Script

[scripts/diff-codebase.sh](scripts/diff-codebase.sh) — Gathers codebase diffs excluding generated/lock files. Supports `--since <ref>`, `--since-merge [<branch>]`, and default (working tree) modes.

## Project context

The project root is the current working directory. Use relative paths from there.

## Notes

- The skill does not modify any code — it only analyzes.
- For the best results, ensure your working tree is clean (`git stash` if needed) so the diff is accurate.
- If there are no changes, report that and suggest checking the correct branch or commit range.
