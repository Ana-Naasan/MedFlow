---
name: context-transfer
description: Extract context from one pi session and transfer it to another using a structured JSON file. Use when you need to move context, decisions, file changes, and conversation history between pi sessions — for handoffs, continuing work in a fresh session, or sharing context across projects.
---

# Context Transfer: Session-to-Session Context Transfer

This skill provides a structured way to transfer context between pi sessions using a JSON file. It works by:

1. **Exporting** — Parsing a session JSONL file and extracting relevant context (decisions, files changed, conversation highlights, next steps) into a portable JSON file
2. **Transferring** — Loading that JSON file into a new session, giving the new agent all the context it needs to continue the work

The context JSON file is self-contained, so it works across projects, machines, or even with other developers.

## How Pi Sessions Work

Pi stores sessions as JSONL (JSON Lines) files at `~/.pi/agent/sessions/--<path>--/<timestamp>_<uuid>.jsonl`.

Each line is a JSON object. Key entry types:
- `{"type":"session",...}` — Session header (first line)
- `{"type":"message",...,"message":{"role":"user","content":"..."}}` — User/assistant/tool messages
- `{"type":"message",...,"message":{"role":"assistant","content":[...],"provider":"...","model":"..."}}` — Assistant responses
- `{"type":"compaction",...,"summary":"...","firstKeptEntryId":"..."}` — Context compaction entries
- `{"type":"model_change",...,"provider":"...","modelId":"..."}` — Model switches

For a full reference, see [the session format docs](https://github.com/earendil-works/pi-mono/blob/main/packages/coding-agent/docs/session-format.md).

## Context JSON Format

The transfer file uses this format:

```json
{
  "version": "1.0",
  "sourceSession": {
    "id": "019e7d0f-...",
    "file": "~/.pi/agent/sessions/--path--/2024-01-01T00:00:00.000Z_uuid.jsonl",
    "name": "Session display name (if set)",
    "cwd": "/path/to/project",
    "model": "provider/model-id",
    "timestamp": "2024-01-01T00:00:00.000Z",
    "messageCount": 42,
    "totalTokens": 15000
  },
  "summary": {
    "goals": ["Implement user authentication", "Add JWT token refresh"],
    "decisions": [
      {"what": "Use bcrypt for password hashing", "rationale": "Industry standard, well-audited"},
      {"what": "Store refresh tokens in httpOnly cookies", "rationale": "Prevents XSS token theft"}
    ],
    "keyFindings": ["Discovered that the legacy auth middleware has a race condition"],
    "openQuestions": ["Should we rate-limit the login endpoint?"],
    "nextSteps": [
      "Add refresh token rotation logic",
      "Write integration tests for auth flow"
    ]
  },
  "files": {
    "created": ["src/auth/hash.ts", "src/auth/login.ts"],
    "modified": ["src/middleware/auth.ts", "package.json"],
    "deleted": [],
    "read": ["src/config.ts", "docs/api.md"]
  },
  "conversation": [
    {
      "role": "user",
      "content": "Let's implement authentication",
      "timestamp": 1704067200000
    },
    {
      "role": "assistant",
      "content": "Here's the approach...",
      "model": "anthropic/claude-sonnet-4-5",
      "timestamp": 1704067210000
    }
  ],
  "metadata": {
    "gitBranch": "feature/auth",
    "gitCommit": "a1b2c3d4e5f6...",
    "tags": ["auth", "security"]
  },
  "extractedBy": "context-transfer-skill",
  "extractedAt": "2024-01-01T01:00:00.000Z"
}
```

## Setup

No setup required. The skill relies on `bash`, `read`, and `jq` (optional, for nicer JSON processing). If `jq` is not available, the scripts fall back to using `python3` or `node`.

## Usage

### Step 1: Export context from a session

**Option A: Use the helper script (recommended)**

Export from the current session (finds most recent session for the current directory):

```bash
.pi/skills/context-transfer/scripts/export-context.sh
```

Export from a specific session file:

```bash
.pi/skills/context-transfer/scripts/export-context.sh --session ~/.pi/agent/sessions/--path--/session.jsonl
```

Export with custom output path:

```bash
.pi/skills/context-transfer/scripts/export-context.sh --output ./context-transfer.json
```

**Option B: Let the agent do it manually**

The agent can read the session file, extract key information, and write a context JSON file.

### Step 2: Review and edit the context JSON

The exported JSON should be reviewed before transferring. The agent can read it and present a summary:

```bash
.pi/skills/context-transfer/scripts/export-context.sh --session <file> --output /tmp/ctx.json
```

### Step 3: Transfer into a new session

**Option A: Start a new session with the context**

```bash
pi --name "Continue: <task name>"
```

Then in the new session, load the context file:

```bash
.pi/skills/context-transfer/scripts/import-context.sh ./context-transfer.json
```

**Option B: Use `/fork` from the session tree**

Navigate with `/tree` to the point you want to fork from, then use `/fork` and edit the prompt to reference the context.

### Step 4: The agent loads and uses the context

When you start a new session, the agent should:
1. Read the context JSON file
2. Understand the full picture from the summary, decisions, file changes, and conversation
3. Continue the work from where the previous session left off

## Detailed Workflow

### Exporting: What the agent should extract

When exporting context from a session, the agent should:

1. **Locate the session file**: Either the most recent one at `~/.pi/agent/sessions/--$(pwd | sed 's/\\//-/g')--/` or a specific file the user provides.

2. **Parse the JSONL file**: Read each line, which is a JSON object. Focus on:
   - `type: "message"` with `role: "user"` — User messages (goals, questions, instructions)
   - `type: "message"` with `role: "assistant"` — Assistant responses with text content (decisions, code, explanations)
   - `type: "compaction"` — Compaction summaries (high-level overviews)
   - `type: "model_change"` — Which models were used
   - `type: "session_info"` — Session display name
   - `type: "session"` — Session header (parent session link, cwd)

3. **Build the summary** by analyzing the conversation:
   - **Goals**: What the user set out to do
   - **Decisions**: Architecture choices, tool selections, approach decisions
   - **Key Findings**: Bugs discovered, insights gained, performance observations
   - **Open Questions**: Things left unresolved
   - **Next Steps**: What should happen next

4. **Track files** mentioned in assistant messages and tool results:
   - Files read via `read` tool calls
   - Files written/created via `write` tool calls
   - Files modified via `edit` tool calls
   - Commands run via `bash` tool calls that mention file paths

5. **Extract conversation highlights**: Key user-assistant exchanges, not every tool call.

6. **Write the context JSON** using the format above.

### Importing: What the agent should do with context

When a context JSON is loaded in a new session, the agent should:

1. **Read the file** and parse it
2. **Acknowledge the context**: Summarize what it understands from the previous session
3. **Continue the work**: Use the summary, decisions, and next steps to drive the new conversation
4. **Reference the file list**: Know which files were created/modified to avoid redundant work or conflicts
5. **Address open questions**: If there are open questions, ask the user or resolve them

## Helper Scripts

### `scripts/export-context.sh`

Exports context from a pi session JSONL file into the standard context JSON format.

**Usage:**
```bash
# Export most recent session for current directory
.pi/skills/context-transfer/scripts/export-context.sh

# Export specific session
.pi/skills/context-transfer/scripts/export-context.sh --session /path/to/session.jsonl

# Export to specific output file
.pi/skills/context-transfer/scripts/export-context.sh --output ./my-context.json

# Export with custom name/tags for the context
.pi/skills/context-transfer/scripts/export-context.sh --name "Auth implementation" --tags "auth,security"

# Show preview without writing file
.pi/skills/context-transfer/scripts/export-context.sh --dry-run
```

### `scripts/import-context.sh`

Reads a context JSON and displays a formatted summary for the agent to consume. Also copies the content to a structured markdown file for easy reference in the new session.

**Usage:**
```bash
# Import and display context summary
.pi/skills/context-transfer/scripts/import-context.sh ./context-transfer.json

# Import and write a .context.md file for reference
.pi/skills/context-transfer/scripts/import-context.sh ./context-transfer.json --write-context
```

### `scripts/merge-context.sh`

Merges multiple context JSON files into one. Useful when collecting context from multiple sessions.

```bash
.pi/skills/context-transfer/scripts/merge-context.sh ctx1.json ctx2.json --output merged.json
```

## Reference

For details on the context JSON schema, field descriptions, and examples, see [references/context-format.md](references/context-format.md).

## Example

### Export from a session

User:
> I've been working on user authentication in my pi session. I need to transfer that context to a new session for implementing JWT refresh tokens. Use the context-transfer skill.

Agent action:
1. Find the most recent session file at `~/.pi/agent/sessions/--Users-me-project--/2024-*.jsonl`
2. Read the file and parse entries
3. Extract user messages, assistant text content, tool calls
4. Build summary: goals (implement auth), decisions (bcrypt, httpOnly cookies), files (src/auth/*.ts), next steps (refresh tokens)
5. Write context JSON to `./context-transfer.json`
6. Present summary to the user

### Import into a new session

User (in new session):
> I have a context file from my previous auth work. Continue from where I left off.

Agent action:
1. Read `./context-transfer.json`
2. Acknowledge context: "From the previous session, you were implementing authentication. You decided on bcrypt for hashing and httpOnly cookies for refresh tokens. The next step is implementing refresh token rotation."
3. Read the files listed in the context
4. Continue implementing based on the next steps

## Notes

- The context JSON is designed to be human-readable and machine-parseable
- Session files contain full conversation history including tool calls and results. The export extracts only the semantically meaningful parts for transfer
- For large sessions, focus the export on the most recent and relevant parts of the conversation
- Context files can be checked into version control to document decision history
- The skill does not modify session files — it only reads from them and writes new context JSON files
