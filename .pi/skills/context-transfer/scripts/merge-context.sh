#!/usr/bin/env bash
# merge-context.sh — Merge multiple context transfer JSON files into one
# Part of the context-transfer skill for pi
#
# Usage:
#   .pi/skills/context-transfer/scripts/merge-context.sh ctx1.json ctx2.json --output merged.json

set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Error: At least 2 input files and --output required." >&2
  echo "Usage: $0 <file1.json> <file2.json> [<file3.json> ...] --output merged.json" >&2
  exit 1
fi

# Collect files and find --output
FILES=()
OUTPUT=""
for arg in "$@"; do
  if [[ "$arg" == "--output" ]]; then
    shift_to_output=true
  elif [[ "${shift_to_output:-false}" == "true" ]]; then
    OUTPUT="$arg"
    shift_to_output=false
  else
    FILES+=("$arg")
  fi
done

if [[ -z "$OUTPUT" ]]; then
  echo "Error: --output <file> is required." >&2
  exit 1
fi

if [[ ${#FILES[@]} -lt 2 ]]; then
  echo "Error: At least 2 input files required." >&2
  exit 1
fi

# Validate files exist
for f in "${FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "Error: File not found: $f" >&2
    exit 1
  fi
done

# Merge using python3
python3 - "$OUTPUT" "${FILES[@]}" << 'PYEOF'
import json
import sys
from datetime import datetime, timezone

output_file = sys.argv[1]
input_files = sys.argv[2:]

contexts = []
for f in input_files:
    with open(f) as fh:
        contexts.append(json.load(fh))

if not contexts:
    print("Error: No contexts to merge", file=sys.stderr)
    sys.exit(1)

# Start with the first context as base
merged = {
    "version": "1.0",
    "sourceSession": contexts[0].get("sourceSession", {}),
    "summary": {
        "goals": [],
        "decisions": [],
        "keyFindings": [],
        "openQuestions": [],
        "nextSteps": []
    },
    "files": {
        "created": [],
        "modified": [],
        "deleted": [],
        "read": []
    },
    "conversation": [],
    "metadata": {
        "gitBranch": "",
        "gitCommit": "",
        "tags": []
    },
    "extractedBy": "context-transfer-skill",
    "extractedAt": datetime.now(timezone.utc).isoformat(),
    "mergedFrom": input_files
}

# Merge summaries
seen_goals = set()
seen_decisions = set()
seen_findings = set()
seen_questions = set()
seen_steps = set()

for ctx in contexts:
    s = ctx.get("summary", {})
    for g in s.get("goals", []):
        if g not in seen_goals:
            merged["summary"]["goals"].append(g)
            seen_goals.add(g)
    for d in s.get("decisions", []):
        what = d.get("what", "")
        if what and what not in seen_decisions:
            merged["summary"]["decisions"].append(d)
            seen_decisions.add(what)
    for f_item in s.get("keyFindings", []):
        if f_item not in seen_findings:
            merged["summary"]["keyFindings"].append(f_item)
            seen_findings.add(f_item)
    for q in s.get("openQuestions", []):
        if q not in seen_questions:
            merged["summary"]["openQuestions"].append(q)
            seen_questions.add(q)
    for ns in s.get("nextSteps", []):
        if ns not in seen_steps:
            merged["summary"]["nextSteps"].append(ns)
            seen_steps.add(ns)

# Merge files (deduplicate)
seen_files = {"created": set(), "modified": set(), "deleted": set(), "read": set()}
for ctx in contexts:
    f = ctx.get("files", {})
    for category in ["created", "modified", "deleted", "read"]:
        for item in f.get(category, []):
            if item not in seen_files[category]:
                merged["files"][category].append(item)
                seen_files[category].add(item)

# Merge conversations (deduplicate by content)
seen_msgs = set()
for ctx in contexts:
    for msg in ctx.get("conversation", []):
        content = msg.get("content", "")
        role = msg.get("role", "")
        key = f"{role}:{content[:200]}"
        if key not in seen_msgs:
            merged["conversation"].append(msg)
            seen_msgs.add(key)

# Merge metadata
for ctx in contexts:
    md = ctx.get("metadata", {})
    if md.get("gitBranch") and not merged["metadata"]["gitBranch"]:
        merged["metadata"]["gitBranch"] = md["gitBranch"]
    if md.get("gitCommit") and not merged["metadata"]["gitCommit"]:
        merged["metadata"]["gitCommit"] = md["gitCommit"]
    for tag in md.get("tags", []):
        if tag not in merged["metadata"]["tags"]:
            merged["metadata"]["tags"].append(tag)

with open(output_file, 'w') as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"Merged {len(input_files)} context files into: {output_file}", file=sys.stderr)
print(f"  Goals: {len(merged['summary']['goals'])}", file=sys.stderr)
print(f"  Decisions: {len(merged['summary']['decisions'])}", file=sys.stderr)
print(f"  Files: {len(merged['files']['created']) + len(merged['files']['modified'])} changed", file=sys.stderr)
print(f"  Messages: {len(merged['conversation'])} entries", file=sys.stderr)
PYEOF
