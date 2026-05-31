#!/usr/bin/env bash
# import-context.sh — Load and display a context transfer JSON file for a new pi session
# Part of the context-transfer skill for pi
#
# Usage:
#   .pi/skills/context-transfer/scripts/import-context.sh ./context-transfer.json
#   .pi/skills/context-transfer/scripts/import-context.sh ./context-transfer.json --write-context

set -euo pipefail

CONTEXT_FILE="${1:-}"
WRITE_CONTEXT=false

if [[ -z "$CONTEXT_FILE" ]]; then
  echo "Error: No context file specified." >&2
  echo "Usage: $0 <context.json> [--write-context]" >&2
  exit 1
fi

shift
while [[ $# -gt 0 ]]; do
  case "$1" in
    --write-context) WRITE_CONTEXT=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ ! -f "$CONTEXT_FILE" ]]; then
  echo "Error: Context file not found: $CONTEXT_FILE" >&2
  exit 1
fi

# Validate JSON
if ! python3 -c "import json; json.load(open('$CONTEXT_FILE'))" 2>/dev/null; then
  echo "Error: Invalid JSON in context file." >&2
  exit 1
fi

echo "Loading context from: $CONTEXT_FILE"
echo ""

# Parse and display using python3 for clean output
python3 - "$CONTEXT_FILE" << 'PYEOF'
import json
import sys
import os

with open(sys.argv[1]) as f:
    ctx = json.load(f)

version = ctx.get("version", "unknown")
source = ctx.get("sourceSession", {})
summary = ctx.get("summary", {})
files_data = ctx.get("files", {})
conversation = ctx.get("conversation", [])
metadata = ctx.get("metadata", {})

print("=" * 72)
print("  CONTEXT TRANSFER — Imported Session Context")
print("=" * 72)
print()
print(f"  Format Version:  {version}")
print(f"  Source Session:  {source.get('name') or source.get('id', 'N/A')}")
print(f"  Source File:     {source.get('file', 'N/A')}")
print(f"  Working Dir:     {source.get('cwd', 'N/A')}")
print(f"  Model Used:      {source.get('model', 'N/A')}")
print(f"  Messages:        {source.get('messageCount', 'N/A')}")
if source.get('totalTokens'):
    print(f"  Total Tokens:    {source['totalTokens']}")
if metadata.get('gitBranch'):
    print(f"  Git Branch:      {metadata['gitBranch']}")
    print(f"  Git Commit:      {metadata.get('gitCommit', 'N/A')}")
if metadata.get('tags'):
    print(f"  Tags:            {', '.join(metadata['tags'])}")
print(f"  Extracted At:    {ctx.get('extractedAt', 'N/A')}")
print()

# --- Summary ---
if summary.get("goals"):
    print("=" * 72)
    print("  GOALS")
    print("=" * 72)
    for g in summary["goals"]:
        print(f"    • {g}")
    print()

if summary.get("decisions"):
    print("=" * 72)
    print("  KEY DECISIONS")
    print("=" * 72)
    for d in summary["decisions"]:
        what = d.get("what", "")
        rationale = d.get("rationale", "")
        print(f"    • {what}")
        if rationale:
            print(f"      Rationale: {rationale}")
    print()

if summary.get("keyFindings"):
    print("=" * 72)
    print("  KEY FINDINGS")
    print("=" * 72)
    for f_item in summary["keyFindings"]:
        print(f"    • {f_item}")
    print()

if summary.get("openQuestions"):
    print("=" * 72)
    print("  OPEN QUESTIONS")
    print("=" * 72)
    for q in summary["openQuestions"]:
        print(f"    • {q}")
    print()

if summary.get("nextSteps"):
    print("=" * 72)
    print("  NEXT STEPS")
    print("=" * 72)
    for s in summary["nextSteps"]:
        print(f"    ☐ {s}")
    print()

# --- Files ---
has_files = files_data.get("created") or files_data.get("modified") or files_data.get("deleted") or files_data.get("read")
if has_files:
    print("=" * 72)
    print("  FILES")
    print("=" * 72)
    for f_item in files_data.get("created", []):
        print(f"    + {f_item}  (created)")
    for f_item in files_data.get("modified", []):
        print(f"    M {f_item}  (modified)")
    for f_item in files_data.get("deleted", []):
        print(f"    D {f_item}  (deleted)")
    for f_item in files_data.get("read", []):
        print(f"    R {f_item}  (read)")
    print()

# --- Conversation highlights ---
if conversation:
    print("=" * 72)
    print("  CONVERSATION HIGHLIGHTS (last {})".format(len(conversation)))
    print("=" * 72)
    print()
    for msg in conversation[-10:]:  # Show last 10 messages
        role = msg.get("role", "?").upper()
        content = msg.get("content", "")
        model = msg.get("model", "")
        timestamp = msg.get("timestamp", 0)

        # Truncate for display
        if len(content) > 300:
            content = content[:300] + "..."

        header = role
        if model:
            header += f" [{model}]"

        print(f"  [{header}]")
        for line in content.split("\n"):
            print(f"    {line}")
        print()

print("=" * 72)
PYEOF

# Optionally write a .context.md for reference
if [[ "$WRITE_CONTEXT" == "true" ]]; then
    CONTEXT_MD="${CONTEXT_FILE%.json}.context.md"
    python3 - "$CONTEXT_FILE" "$CONTEXT_MD" << 'PYEOF'
import json, sys, os
from datetime import datetime

with open(sys.argv[1]) as f:
    ctx = json.load(f)

md_path = sys.argv[2]
source = ctx.get("sourceSession", {})
summary = ctx.get("summary", {})
files_data = ctx.get("files", {})
conversation = ctx.get("conversation", [])
metadata = ctx.get("metadata", {})

md = f"""# Context Transfer: {source.get('name') or source.get('id', 'N/A')}

> Imported from session transfer file: `{source.get('file', 'N/A')}`
> Extracted: {ctx.get('extractedAt', 'N/A')}

## Session Info

- **Session ID:** {source.get('id', 'N/A')}
- **Working Directory:** {source.get('cwd', 'N/A')}
- **Model:** {source.get('model', 'N/A')}
- **Message Count:** {source.get('messageCount', 'N/A')}
- **Total Tokens:** {source.get('totalTokens', 'N/A')}
- **Git Branch:** {metadata.get('gitBranch', 'N/A')}

"""

if summary.get("goals"):
    md += "## Goals\n\n"
    for g in summary["goals"]:
        md += f"- {g}\n"
    md += "\n"

if summary.get("decisions"):
    md += "## Key Decisions\n\n"
    for d in summary["decisions"]:
        what = d.get("what", "")
        rationale = d.get("rationale", "")
        md += f"- **{what}**"
        if rationale:
            md += f" — {rationale}"
        md += "\n"
    md += "\n"

if summary.get("keyFindings"):
    md += "## Key Findings\n\n"
    for f_item in summary["keyFindings"]:
        md += f"- {f_item}\n"
    md += "\n"

if summary.get("openQuestions"):
    md += "## Open Questions\n\n"
    for q in summary["openQuestions"]:
        md += f"- {q}\n"
    md += "\n"

if summary.get("nextSteps"):
    md += "## Next Steps\n\n"
    for s in summary["nextSteps"]:
        md += f"- [ ] {s}\n"
    md += "\n"

if files_data.get("created") or files_data.get("modified") or files_data.get("deleted"):
    md += "## Files\n\n"
    for f_item in files_data.get("created", []):
        md += f"- `{f_item}` (created)\n"
    for f_item in files_data.get("modified", []):
        md += f"- `{f_item}` (modified)\n"
    for f_item in files_data.get("deleted", []):
        md += f"- `{f_item}` (deleted)\n"
    md += "\n"

if conversation:
    md += "## Conversation Highlights\n\n"
    for msg in conversation[-5:]:
        role = msg.get("role", "?").upper()
        content = msg.get("content", "")
        model = msg.get("model", "")
        header = role
        if model:
            header += f" ({model})"
        md += f"### {header}\n\n{content}\n\n---\n\n"

with open(md_path, 'w') as f:
    f.write(md)

print(f"Context markdown written to: {md_path}", file=sys.stderr)
PYEOF
fi

echo ""
echo "Context loaded. Use this information to continue the work from the previous session."
