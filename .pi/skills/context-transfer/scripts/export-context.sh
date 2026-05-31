#!/usr/bin/env bash
# export-context.sh — Export context from a pi session JSONL file to a portable JSON format
# Part of the context-transfer skill for pi
#
# Usage:
#   .pi/skills/context-transfer/scripts/export-context.sh
#   .pi/skills/context-transfer/scripts/export-context.sh --session /path/to/session.jsonl
#   .pi/skills/context-transfer/scripts/export-context.sh --output ./context.json
#   .pi/skills/context-transfer/scripts/export-context.sh --name "My task" --tags "auth,api"
#   .pi/skills/context-transfer/scripts/export-context.sh --dry-run

set -euo pipefail

# --- Defaults ---
SESSION_DIR="${HOME}/.pi/agent/sessions"
OUTPUT_FILE=""
SESSION_FILE=""
CONTEXT_NAME=""
CONTEXT_TAGS=""
DRY_RUN=false

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --session) SESSION_FILE="$2"; shift 2 ;;
    --output) OUTPUT_FILE="$2"; shift 2 ;;
    --name) CONTEXT_NAME="$2"; shift 2 ;;
    --tags) CONTEXT_TAGS="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    *) echo "Unknown option: $1"; echo "Usage: $0 [--session <file>] [--output <file>] [--name <name>] [--tags <tags>] [--dry-run]"; exit 1 ;;
  esac
done

# --- Auto-detect session file if not provided ---
if [[ -z "$SESSION_FILE" ]]; then
  CWD_HASH="--$(echo "$PWD" | sed 's/\//-/g')--"
  SESSION_GLOB="${SESSION_DIR}/${CWD_HASH}/*.jsonl"
  # Find most recent session file
  LATEST_SESSION=$(ls -t "$SESSION_GLOB" 2>/dev/null | head -1)
  if [[ -z "$LATEST_SESSION" ]]; then
    # Fallback: list all sessions and find one for current dir
    SESSION_FILE=$(find "${SESSION_DIR}" -name "*.jsonl" -type f 2>/dev/null | head -1)
    if [[ -z "$SESSION_FILE" ]]; then
      echo "Error: No session files found in ${SESSION_DIR}" >&2
      exit 1
    fi
    echo "Warning: No session found for current directory. Using most recent: ${SESSION_FILE}" >&2
  else
    SESSION_FILE="$LATEST_SESSION"
  fi
fi

if [[ ! -f "$SESSION_FILE" ]]; then
  echo "Error: Session file not found: $SESSION_FILE" >&2
  exit 1
fi

echo "Reading session: $SESSION_FILE" >&2

# --- Default output path ---
if [[ -z "$OUTPUT_FILE" ]]; then
  OUTPUT_FILE="./context-transfer-$(date +%Y%m%d-%H%M%S).json"
fi

# --- Extract context ---
# We use python3 for reliable JSONL parsing
DRY_RUN_FLAG="false"
if [[ "$DRY_RUN" == "true" ]]; then
    DRY_RUN_FLAG="true"
fi
python3 - "$SESSION_FILE" "$OUTPUT_FILE" "$CONTEXT_NAME" "$CONTEXT_TAGS" "$DRY_RUN_FLAG" << 'PYEOF'
import json
import sys
import os
from datetime import datetime, timezone

session_file = sys.argv[1]
output_file = sys.argv[2]
context_name = sys.argv[3] if len(sys.argv) > 3 else ""
context_tags = sys.argv[4] if len(sys.argv) > 4 else ""
dry_run = sys.argv[5].lower() == "true" if len(sys.argv) > 5 else False

entries = []
with open(session_file, 'r') as f:
    for line in f:
        line = line.strip()
        if line:
            entries.append(json.loads(line))

if not entries:
    print("Error: Empty session file", file=sys.stderr)
    sys.exit(1)

header = entries[0] if entries[0].get("type") == "session" else {}
conversation = []
summary_data = {
    "goals": [],
    "decisions": [],
    "keyFindings": [],
    "openQuestions": [],
    "nextSteps": []
}
files = {
    "created": [],
    "modified": [],
    "deleted": [],
    "read": []
}
message_count = 0
total_tokens = 0
current_model = None
session_name = ""

for entry in entries:
    etype = entry.get("type")

    if etype == "message":
        msg = entry.get("message", {})
        role = msg.get("role")
        content = msg.get("content", "")
        ts = msg.get("timestamp", 0)
        message_count += 1

        if role == "user":
            text = content if isinstance(content, str) else ""
            conversation.append({
                "role": "user",
                "content": text[:2000],  # Truncate long messages
                "timestamp": ts
            })

        elif role == "assistant":
            text_parts = []
            provider = msg.get("provider", "")
            model = msg.get("model", "")
            usage = msg.get("usage", {})
            total_tokens += usage.get("totalTokens", 0)

            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif isinstance(block, dict) and block.get("type") == "thinking":
                        text_parts.append(block.get("thinking", ""))

            text = " ".join(text_parts)
            if text.strip():
                conversation.append({
                    "role": "assistant",
                    "content": text[:2000],
                    "model": f"{provider}/{model}" if provider else model,
                    "timestamp": ts
                })

            if provider and model:
                current_model = f"{provider}/{model}"

        elif role == "toolResult":
            tool_name = msg.get("toolName", "")
            tool_content = msg.get("content", "")
            # Track file operations from tool calls
            if isinstance(tool_content, list):
                for block in tool_content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        txt = block.get("text", "")
                        # Bash command output containing file operations
                        if tool_name == "bash" and any(kw in txt for kw in ["created", "modified", "written"]):
                            pass  # We'll detect specific files elsewhere

    elif etype == "model_change":
        current_model = f"{entry.get('provider', '')}/{entry.get('modelId', '')}"

    elif etype == "compaction":
        summary = entry.get("summary", "")
        if summary:
            conversation.insert(0, {
                "role": "system",
                "content": f"[Compacted Summary]: {summary[:1000]}",
                "timestamp": 0
            })

    elif etype == "session_info":
        session_name = entry.get("name", "")

# --- Heuristic extraction of goals, decisions, findings ---
# Look at user messages for goals
for msg in conversation:
    if msg["role"] == "user":
        text = msg["content"].lower()
        # Detect goals from common patterns
        goal_indicators = [
            "implement", "add", "create", "build", "make", "write",
            "refactor", "fix", "update", "change", "migrate",
            "need to", "want to", "goal", "objective", "task"
        ]
        for indicator in goal_indicators:
            if indicator in text:
                # Find the sentence containing the goal indicator
                sentences = msg["content"].replace("!", ".").replace("?", ".").split(".")
                for sentence in sentences:
                    if indicator in sentence.lower() and len(sentence.strip()) > 10:
                        goal = sentence.strip()
                        if len(goal) > 20 and goal not in summary_data["goals"]:
                            summary_data["goals"].append(goal)
                        break
                break

# Extract tool calls to track file operations
for entry in entries:
    if entry.get("type") == "message":
        msg = entry.get("message", {})
        if msg.get("role") == "assistant":
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "toolCall":
                        tool_name = block.get("name", "")
                        args = block.get("arguments", {})
                        if tool_name == "read":
                            path = args.get("path", "")
                            if path and path not in files["read"]:
                                files["read"].append(path)
                        elif tool_name == "write":
                            path = args.get("path", "")
                            if path and path not in files["created"]:
                                files["created"].append(path)
                        elif tool_name == "edit":
                            path = args.get("path", "")
                            if path and path not in files["modified"]:
                                files["modified"].append(path)
                        elif tool_name == "bash":
                            cmd = args.get("command", "")
                            # Try to infer file paths from bash commands
                            for token in cmd.split():
                                if "/" in token and "." in token and not token.startswith("--"):
                                    if token not in files["read"] and \
                                       token not in files["created"] and \
                                       token not in files["modified"]:
                                        files["read"].append(token)

# Build the context JSON
context = {
    "version": "1.0",
    "sourceSession": {
        "id": header.get("id", ""),
        "file": os.path.abspath(session_file),
        "name": session_name or context_name,
        "cwd": header.get("cwd", ""),
        "model": current_model or "",
        "timestamp": header.get("timestamp", ""),
        "messageCount": message_count,
        "totalTokens": total_tokens
    },
    "summary": summary_data,
    "files": files,
    "conversation": conversation[-20:],  # Keep last 20 messages for context
    "metadata": {
        "gitBranch": "",
        "gitCommit": "",
        "tags": [t.strip() for t in context_tags.split(",") if t.strip()]
    },
    "extractedBy": "context-transfer-skill",
    "extractedAt": datetime.now(timezone.utc).isoformat()
}

# Try to get git info
try:
    import subprocess
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, timeout=3
    )
    if branch.returncode == 0:
        context["metadata"]["gitBranch"] = branch.stdout.strip()
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=3
    )
    if commit.returncode == 0:
        context["metadata"]["gitCommit"] = commit.stdout.strip()
except Exception:
    pass

output = json.dumps(context, indent=2, ensure_ascii=False)

if dry_run:
    # Print to stdout for preview
    print(output)
    print("=" * 60, file=sys.stderr)
    print("DRY RUN — No file written", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
else:
    with open(output_file, 'w') as f:
        f.write(output)
        f.write("\n")
    print(f"Extracted {message_count} messages, {len(conversation)} conversation entries", file=sys.stderr)
    print(f"Found {len(files['created'])} created, {len(files['modified'])} modified, {len(files['read'])} read files", file=sys.stderr)
    print(f"Context exported to: {os.path.abspath(output_file)}", file=sys.stderr)
    # Print a summary
    print("=" * 60, file=sys.stderr)
    print("CONTEXT SUMMARY", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Session: {context['sourceSession'].get('name') or context['sourceSession']['id']}", file=sys.stderr)
    print(f"Model: {context['sourceSession'].get('model', 'N/A')}", file=sys.stderr)
    print(f"Messages: {message_count}", file=sys.stderr)
    print(f"Files changed: {len(files['created']) + len(files['modified'])}", file=sys.stderr)
    if summary_data["goals"]:
        print(f"Goals: {len(summary_data['goals'])} detected", file=sys.stderr)
    print(f"Output: {os.path.abspath(output_file)}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
PYEOF
