# MedFlow — Session Handoff

A clinical EMR demo (synthetic data) built with Next.js 16. This doc gets the next session productive immediately.

> ?? This is **NOT** the Next.js you may know. v16 has breaking changes (e.g. `middleware.ts` ? `proxy.ts`, async `params`). Read `node_modules/next/dist/docs/` before writing routing/API code. See `AGENTS.md`.

---

## Run it

```bash
cd /Users/vivek/Desktop/doctorwebsite/medflow
npm run build && npm run start    # production mode — pages load instantly
# or:  npm run dev                # dev mode — SLOW (Turbopack compiles routes on demand)
```

- App runs on `http://localhost:3001`.
- **Use production mode** (`build` + `start`) for demos. Dev mode recompiles each route on first visit, which the user previously flagged as slow.
- **Login:** `dr.wu@umraa.ca` / `password123`

### Environment (`.env.local`, already present)
```
AUTH_SECRET=medflow-dev-secret-key-change-in-production
NEXTAUTH_URL=http://localhost:3001
AUTH_TRUST_HOST=true        # required — without it NextAuth throws UntrustedHost in prod
```

---

## Stack
- **Next.js 16.2.6** (App Router, Turbopack), **React 19.2.4**, TypeScript strict (zero `any`)
- **Tailwind CSS v4** — design tokens are CSS custom properties in `app/globals.css`
- **shadcn/ui v4** built on **`@base-ui/react`** primitives (NOT Radix). Select/Tabs `onValueChange` passes `string | null` — wrap setters: `onValueChange={(v) => setX(v ?? "all")}`
- **Framer Motion v12** — `ease` must be a cubic array like `[0.25, 0.1, 0.25, 1]`, NOT the string `"easeOut"` (string fails strict typing)
- **Recharts v3** (billing chart) — Tooltip `formatter` value is `ValueType` (use `Number(value)`)
- **Tiptap v3** (notes editor) — set `immediatelyRender: false` in `useEditor` to avoid SSR hydration warnings
- **NextAuth v5 beta** (credentials), **Zustand** (`lib/store.ts`), **Lucide** icons

## Design tokens (`app/globals.css`)
```
--primary/--accent: #0F62FE (IBM Blue)   --foreground: #111827
--background: #F7F8FA  --bg-surface: #FFFFFF  --bg-subtle: #EEF0F4
--border: #DDE1E9  --text-secondary: #6B7280  --text-muted: #9CA3AF
--success: #0DA36B  --warning: #F59E0B  --danger: #DC2626
```
Use tokens / Tailwind token classes (`bg-primary`, `text-muted-foreground`, `border-border`). **No hardcoded hex** in components.

---

## Routes

| Route | Status |
|---|---|
| `/login` | ? Split-screen login w/ ECG SVG + Framer Motion |
| `/` (dashboard) | ? Greeting, stat cards, recently-accessed patients |
| `/directory` | ? Patient table with links |
| `/scheduler` `/memos` `/tasks` `/utilities` | ?? `ComingSoon` placeholders (`components/layout/ComingSoon.tsx`) |
| `/patients/[id]` | ? redirects ? `/profile` |

### Patient tabs (`components/layout/PatientTabs.tsx`) — all 6 FULLY built
Order: **Profile · Records · eDocuments · Investigations · Notes · Billing**

| Tab | File | What it does |
|---|---|---|
| Profile | `app/(dashboard)/patients/[id]/profile/page.tsx` | Demographics (inline-edit pencil), allergies, meds, ICD problems, immunization status |
| Records | `.../records/page.tsx` | ? Visit timeline + attached docs. Uses `components/records/VisitDetailDrawer.tsx` (SOAP/vitals/Rx drawer) + `FilePreviewModal.tsx`. Search + type filter. |
| eDocuments | `.../edocuments/page.tsx` | CareConnect / Compose sub-tabs, doc list, `EDocViewer` modal (body + metadata sidebar) |
| Investigations | `.../investigations/page.tsx` | Source dropdown, All/Requisitions/Referrals/OR/Misc sub-tabs, table, detail Sheet |
| Notes | `.../notes/page.tsx` | Two-pane: note list (tag filter + search) + Tiptap editor w/ toolbar, autosave indicator, sign & lock |
| Billing | `.../billing/page.tsx` | 3 stat cards, Recharts 12-month bar chart, claims table, `BillingDetailDrawer` |

?? **Leftover stub routes** (exist but NOT in tab nav): `.../encounters/page.tsx`, `.../files/page.tsx` — old "Coming soon" stubs. Either delete or wire in if needed.

---

## Mock data (`lib/mock-data/`)
Each file exports an array + `getXByPatientId(id)` helpers (re-exported via `index.ts`).
**Exact helper names** (note casing): `getPatientById`, `getEncountersByPatientId`, `getInvestigationsByPatientId`, `getNotesByPatientId`, `getBillingByPatientId` / `getBillingTotalByPatientId`, `getFilesByPatientId`, **`getEDocumentsByPatientId`** (capital ED).

Types live in `lib/types.ts`.

### Patients (6)
| ID | Name | Profile |
|---|---|---|
| 24884 | Test Patient | Pediatric asthma |
| 10231 | Margaret Chen | Elderly T2DM/HTN |
| 33591 | Raj Patel | MDD + GERD |
| 57720 | Sophie Dubois | Tree-nut anaphylaxis/eczema |
| 68103 | Gerald Morrison | HFrEF/AFib/CKD |
| **99021** | **Harold Whitmore** | **NEW — 16-yr HTN?T2DM?cardiac story (2010–2026), 7 encounters, 10 investigations, 5 notes, 6 bills, 6 files, 4 edocs.** All IDs prefixed `hw-`/`enc-hw-`/etc. |

Note content for Whitmore uses HTML (Tiptap-friendly); older patients' notes are plain text — both render fine.

---

## Conventions / gotchas learned this project
- Tab pages are **`"use client"`** and read the id via `useParams<{ id: string }>()` (the patient `layout.tsx` already validates the patient & 404s).
- The patient `layout.tsx` renders sticky `PatientHeader` + `PatientTabs`; tab pages render only their content (no header).
- `git` history does NOT track `medflow/` work yet (project was never committed) — there's no fallback if a file is overwritten. Be careful with full-file rewrites.
- Keep large page files modular (extract drawers/modals into `components/<area>/`).

## Verification status (end of session)
- ? `npx tsc --noEmit` clean
- ? `npm run build` compiled successfully, all 16 routes registered
- ? `ReadLints` clean on all new pages
- ?? Live `curl`/server smoke test was blocked by a sandbox network-interface restriction, not a code issue — verify by running `npm run start` locally and visiting `/patients/99021/records`.

## Suggested next steps
- Decide fate of leftover `encounters` / `files` stub routes.
- Wire "New Note" / "Create New" / "Download" buttons (currently UI-only).
- Optionally `git init` commit the `medflow/` app so future overwrites are recoverable.
