# Issue #19 — Doctor App: Suggestion Card with Clickable Citation

**Date:** 2026-05-31  
**Branch:** feat/issue-19-citation-result-card  
**PR target:** planning

---

## Goal

Replace the `app/(provider)/packet/page.tsx` shell with a working result view that:
1. Fetches the decision packet for demo patient `pat-001`
2. Renders each hypothesis as a `SuggestionCard` (why-line, severity, confidence)
3. Renders each citation as a `CitationChip` — clicking one resolves it via the typed client and shows the snippet in a modal dialog

---

## Architecture

**Pattern:** Page-level client component + pure presentational sub-components.

`packet/page.tsx` owns the React Query call and renders the list. `SuggestionCard` and `CitationChip` are isolated presentational/stateful components that can be tested independently.

```
frontend/
  app/(provider)/packet/
    page.tsx                       ← "use client", fetches packet, renders card list
  components/
    SuggestionCard.tsx             ← new: pure presentational
    CitationChip.tsx               ← new: chip + modal + resolution query
  tests/
    SuggestionCard.test.tsx        ← new: 100% coverage
    CitationChip.test.tsx          ← new: 100% coverage
    api-client.test.ts             ← existing, untouched
  vitest.config.ts                 ← add jsdom env + plugin-react
  package.json                     ← add @testing-library/react, @testing-library/jest-dom, @vitejs/plugin-react
```

---

## Component Interfaces

```ts
// from backend/app/dtos.py — mirrored in frontend
interface Citation {
  kind: "resource" | "evidence";
  ref: string;
  label: string | null;
}

interface Hypothesis {
  id: string;
  title: string;
  why: string;
  severity: string;
  confidence: string;
  citations: Citation[];
}

interface DecisionPacket {
  patient_id: string;
  summary_markdown: string;
  hypotheses: Hypothesis[];
  data_gaps: string[];
  cache_status: string | null;
}
```

### SuggestionCard

```ts
interface SuggestionCardProps {
  hypothesis: Hypothesis;
  patientId: string;
}
```

Renders:
- `.eyebrow` — `Hypothesis · {hypothesis.id}`
- title (`hypothesis.title`)
- why-line (`hypothesis.why`)  
- severity badge (amber pill)
- confidence badge (accent pill)
- chip row of `CitationChip` components

### CitationChip

```ts
interface CitationChipProps {
  citation: Citation;
  patientId: string;
}
```

Internal state: `open: boolean` (initially `false`).

Clicking the chip sets `open = true`, which enables the resolution query. The query is lazy (`enabled: open`) so it only fires on first click.

**Citation routing:**
- `kind="resource"`: `ref="Patient/pat-001"` → split on `/` → `GET /patients/{patientId}/resource/{resource_type}/{resource_id}`
- `kind="evidence"`: `ref="ddinter-aspirin-warfarin"` → `GET /evidence/{evidence_id}`

Modal (native `<dialog>`) shows: source label + snippet text + close button.

---

## Data Flow

```
packet/page.tsx
  └─ $api.useQuery("GET /patients/{patient_id}/packet", { params: { path: { patient_id: "pat-001" } } })
       ├─ loading → skeleton message
       ├─ error  → error message
       └─ data   → hypotheses[].map(h => <SuggestionCard hypothesis={h} patientId="pat-001" />)
                       └─ citations[].map(c => <CitationChip citation={c} patientId="pat-001" />)
                                           └─ on click: lazy $api.useQuery for resource or evidence
                                           └─ modal: snippet + source + close
```

---

## Error Handling

- Packet fetch error → visible error message in page (not silent)
- Citation fetch error → modal shows error text instead of snippet
- 404 on citation → modal shows "Source not found"

---

## Styling

Follow existing globals.css design tokens:
- Cards: `.panel .card` classes
- Chips: `.chip` class + hover state for interactive chips
- Badges: inline pill styling (amber for severity, accent for confidence)
- Modal: native `<dialog>` with backdrop, white panel, close button

No new CSS files — extend globals.css with minimal additions for badges and modal.

---

## Testing

### Vitest config changes

Add `@vitejs/plugin-react` plugin and `environment: "jsdom"` for component test files. Split config to keep existing API tests in node environment.

### New packages

```
@testing-library/react
@testing-library/jest-dom
@vitejs/plugin-react
```

### Test plan

**`SuggestionCard.test.tsx`** — 100% coverage:
- `renders why-line, severity, and confidence` — given mock `Hypothesis`, assert all three visible in DOM
- `renders citation chips for each citation` — assert chip count matches `citations.length`

**`CitationChip.test.tsx`** — 100% coverage:
- `renders chip label` — chip text matches `citation.label`
- `click opens modal and shows snippet` — mock `$api` at module boundary; click chip; assert `<dialog>` is open and snippet text visible
- `click on evidence citation resolves via /evidence endpoint` — assert correct endpoint called
- `click on resource citation resolves via /resource endpoint` — assert correct endpoint called

**`api-client.test.ts`** — existing, no change. Already covers typed client smoke test.

---

## Definition of Done

- Demo patient `pat-001` result renders in `/packet` with why-line, severity, confidence visible
- Clicking at least one citation chip opens a modal showing its source/snippet
- `jest --coverage` (vitest) passes with 100% on new files
- All tests pass clean
- PR into `planning` with coverage output in description
