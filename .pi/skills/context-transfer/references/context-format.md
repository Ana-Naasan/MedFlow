# Context Transfer JSON Format Reference

This document describes the schema and fields of the context transfer JSON file used by the `context-transfer` skill.

## Schema

```json
{
  "version": "1.0",
  "sourceSession": { ... },
  "summary": { ... },
  "files": { ... },
  "conversation": [ ... ],
  "metadata": { ... },
  "extractedBy": "context-transfer-skill",
  "extractedAt": "2024-01-01T00:00:00.000Z"
}
```

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | yes | Schema version (currently `"1.0"`) |
| `sourceSession` | object | yes | Information about the source pi session |
| `summary` | object | yes | Extracted semantic summary of the session |
| `files` | object | yes | File operations tracked during the session |
| `conversation` | array | no | Key conversation messages (last ~20) |
| `metadata` | object | no | Additional context (git, tags) |
| `extractedBy` | string | yes | Tool that created this file |
| `extractedAt` | string | yes | ISO 8601 timestamp of extraction |
| `mergedFrom` | array | no | Present only if merged from multiple files |

## `sourceSession` Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Session UUID from the JSONL header |
| `file` | string | Absolute path to the session JSONL file |
| `name` | string | Human-readable session name (if set via `/name`) |
| `cwd` | string | Working directory when the session was active |
| `model` | string | Last model used, in `provider/model` format |
| `timestamp` | string | ISO 8601 timestamp of session start |
| `messageCount` | number | Total number of message entries |
| `totalTokens` | number | Total tokens used across all assistant messages |

## `summary` Object

| Field | Type | Description |
|-------|------|-------------|
| `goals` | array of string | High-level goals detected from user messages |
| `decisions` | array of object | Key decisions made during the session |
| `keyFindings` | array of string | Important discoveries or insights |
| `openQuestions` | array of string | Questions left unresolved |
| `nextSteps` | array of string | Action items for continuation |

### `decisions[]` Object

| Field | Type | Description |
|-------|------|-------------|
| `what` | string | The decision that was made |
| `rationale` | string | Why this decision was chosen |

## `files` Object

| Field | Type | Description |
|-------|------|-------------|
| `created` | array of string | Files that were created (via `write` tool) |
| `modified` | array of string | Files that were modified (via `edit` tool) |
| `deleted` | array of string | Files that were deleted |
| `read` | array of string | Files that were read (via `read` tool or bash) |

## `conversation[]` Array

Each entry in the conversation array:

| Field | Type | Description |
|-------|------|-------------|
| `role` | string | One of `"user"`, `"assistant"`, or `"system"` (for compaction summaries) |
| `content` | string | The message text (truncated to ~2000 chars) |
| `model` | string | Present on assistant messages: `provider/model` |
| `timestamp` | number | Unix milliseconds timestamp |

## `metadata` Object

| Field | Type | Description |
|-------|------|-------------|
| `gitBranch` | string | Git branch name at extraction time |
| `gitCommit` | string | Git commit hash at extraction time |
| `tags` | array of string | User-provided tags for categorization |

## Example

```json
{
  "version": "1.0",
  "sourceSession": {
    "id": "019e7d0f-c395-73a1-91de-318e2aecc65f",
    "file": "/Users/me/.pi/agent/sessions/--Users-me-project--/2026-05-31T08-04-05-653Z_019e7d0f...jsonl",
    "name": "Auth implementation",
    "cwd": "/Users/me/project",
    "model": "anthropic/claude-sonnet-4-5",
    "timestamp": "2026-05-31T08:04:05.653Z",
    "messageCount": 42,
    "totalTokens": 35000
  },
  "summary": {
    "goals": [
      "Implement user authentication with JWT",
      "Add refresh token rotation"
    ],
    "decisions": [
      {
        "what": "Use bcrypt for password hashing",
        "rationale": "Industry standard, well-audited, constant-time comparison"
      },
      {
        "what": "Store refresh tokens in httpOnly cookies",
        "rationale": "Prevents XSS-based token theft"
      }
    ],
    "keyFindings": [
      "Legacy auth middleware has a race condition in token validation"
    ],
    "openQuestions": [
      "Should we rate-limit the login endpoint?"
    ],
    "nextSteps": [
      "Implement refresh token rotation logic",
      "Add rate limiting to auth endpoints",
      "Write integration tests for the auth flow"
    ]
  },
  "files": {
    "created": [
      "src/auth/hash.ts",
      "src/auth/login.ts",
      "src/auth/refresh.ts"
    ],
    "modified": [
      "src/middleware/auth.ts",
      "package.json",
      "src/routes/index.ts"
    ],
    "deleted": [],
    "read": [
      "src/config.ts",
      "docs/api.md",
      "src/db/schema.ts"
    ]
  },
  "conversation": [
    {
      "role": "user",
      "content": "Let's implement authentication with JWT tokens",
      "timestamp": 1704067200000
    },
    {
      "role": "assistant",
      "content": "I'll help you set up authentication with JWT. Let me start by looking at your project structure...",
      "model": "anthropic/claude-sonnet-4-5",
      "timestamp": 1704067210000
    }
  ],
  "metadata": {
    "gitBranch": "feature/auth",
    "gitCommit": "a1b2c3d4e5f67890abcdef1234567890abcdef12",
    "tags": ["auth", "jwt", "security"]
  },
  "extractedBy": "context-transfer-skill",
  "extractedAt": "2026-05-31T09:00:00.000Z"
}
```

## Usage Notes

- **Version field**: Future schema changes will increment the version number. Consumers should check `version` for compatibility.
- **Conversation truncation**: The conversation array typically contains the last ~20 messages. For full history, reference the original session file.
- **Empty arrays**: Missing data should use empty arrays (`[]`) rather than null.
- **Timestamps**: All timestamps use Unix milliseconds (JavaScript `Date.now()` convention) for consistency with pi's session format.
- **File paths**: Paths should be relative to the project root where possible. Absolute paths may be preserved from the session data.
- **Merging**: When merging multiple context files, the `mergedFrom` field lists the source files. Goals, decisions, findings, questions, and next steps are deduplicated by content.
