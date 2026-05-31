# Handoff: MedFlow — Marketing Site Navigation & Core Pages

## Overview
MedFlow is a **B2B virtual-care / employee well-being platform** (HR leaders, benefits managers, and organizational buyers are the audience; clinicians are a secondary audience who log in to provide care). This package covers the **public marketing site**: the global navigation system plus three core pages — **Home**, **EAP (Employee Assistance Program)**, and **Pricing**.

The central design question these wireframes explore is **navigation**, specifically how to serve **two distinct audiences — patients/members and clinicians — from a single front door.** Three navigation directions were prototyped. **Direction B (Role-First Split Entry) is the chosen/primary direction.** Directions A and C are included as documented alternates.

## About the Design Files
The files in this bundle are **design references created in HTML/CSS/vanilla-JS** — medium-fidelity *wireframes* showing intended structure, content, hierarchy, and interaction model. **They are not production code to copy directly.**

The task is to **recreate these designs in the target codebase's environment** using its established patterns, component library, and styling system. If no codebase exists yet, choose an appropriate framework — the original site was built on HubSpot CMS, but a modern **React/Next.js** marketing stack is recommended for a rebuild. Treat the HTML as a spec for layout + behavior, not as markup to paste in.

> The wireframes deliberately use a hand-drawn "sketch" aesthetic (wobbly borders, greybox image placeholders, handwritten margin annotations) that can be toggled off. **None of the sketch styling is part of the final design** — it's wireframe scaffolding. See "Fidelity" below.

## Fidelity
**Low-to-medium fidelity (lo-fi/medium).** These are wireframes:
- **Layout, hierarchy, content/copy, navigation model, and interaction patterns are intentional** — implement these faithfully.
- **Visual styling (the sketch borders, paper texture, greyboxes, exact spacing) is NOT final.** Apply MedFlow's real design system for production styling.
- **All images are greybox placeholders** with a monospace caption describing what belongs there (e.g. `EAP app — services screen`). Replace with real photography/screenshots.
- The **typography direction IS intentional** and should carry into production: an **editorial oldstyle serif for headlines/UI** paired with a **clean sans for body** (see Design Tokens).

## The Three Navigation Directions

All three render the **same three pages** (Home / EAP / Pricing) and the **same patient/clinician role concept** — they differ only in *how navigation and role selection are presented*. A top control bar switches Direction (A/B/C) and Page; two toggles control "annotations" and "straight lines."

### ⭐ Direction B — Role-First Split Entry (CHOSEN / PRIMARY — build this)
The opinionated, personal approach. A **persistent role bar** pinned above the header asks "First — who are you?" with a segmented **"I'm a patient" / "I'm a clinician"** control. The selected role **rewrites the nav labels, hero, and CTAs** in real time.

- **Role bar** (full-width, dark `#2c2b27` background, centered): label "First — who are you?" + a pill segmented control with two options + helper text "nav & content adapt to your answer."
  - Patient selected → segment highlights **warm peach** (`--patient`).
  - Clinician selected → segment highlights **cool blue** (`--clinician`).
- **Header below it**: brand mark (left), centered nav links, "Login" button, primary CTA button (right).
  - **Nav links are role-dependent:**
    - Patient: `Find care` · `Programs` · `How it works` · `Help`
    - Clinician: `Join the network` · `Tools` · `Scheduling` · `Resources`
  - **Primary CTA is role-dependent:** Patient → `Get started`; Clinician → `Apply to join`.
- **Home hero becomes a two-door split** (instead of the standard hero): two large cards side by side — "For patients / Get care in minutes" (peach) and "For clinicians / Practice without the noise" (cool blue). The **non-selected door dims to ~50% opacity**; the selected door is full strength. Each door has its own CTA that also sets the role.
- On EAP/Pricing pages, the role bar persists and CTAs stay tailored to the active role.

### Direction A — Editorial Mega-Menu (alternate)
Classic, content-rich, familiar. A sticky header: brand (left), three top-level links with **click/hover mega-menu panels** (`Platform`, `Why MedFlow`, `Resources`), and a utility cluster (right): `Get pricing`, `Help ▾`, **`Login ▾`** (dual dropdown), and a `Book a demo` primary CTA.
- **Mega-menus**: each opens a full-width panel with a 4-column grid — 3 link columns + 1 featured greybox card. Only one open at a time; clicking the active one closes it; clicking outside closes it.
- **Role lives in the Login dropdown**: a popover with two stacked options — "Patient login / Members & families" (peach) and "Clinician login / Care providers & staff" (cool blue), each with an icon tile.
- Standard split hero (copy left, image right) with in-hero "I'm a patient / I'm a clinician" buttons.

### Direction C — Slim Rail + Command (alternate)
App-like, compact, scales toward a logged-in product feel. A **74px fixed left vertical rail**: brand mark at top, icon nav items (`Home ⌂`, `EAP ❤`, `Plans $`, `More ▦`), a flexible spring, and a **persistent role pill at the bottom** that toggles patient↔clinician. To the right of the rail, a **command bar**: a `⌘K` search field ("Search care, programs, docs…") + utility links (`Book a demo`, `Login ▾`). Page content fills the area below the command bar.

---

## Screens / Views

### 1. Home
**Purpose:** Convert HR/org buyers; route patients and clinicians to the right path.

**Sections (top → bottom):**
1. **Hero** — *calm/clinical* tone.
   - Standard (Dir A/C): eyebrow `Virtual care for every employee`; H1 **"Clinical-grade care, calmly delivered."**; body "MedFlow connects your people to licensed clinicians in minutes — mental health, primary care and everyday wellness, in one quietly trusted platform."; primary CTA `See it in action`, secondary `Book a call`; below, role buttons `🧑 I'm a patient` / `⚕ I'm a clinician`. Right side: large image placeholder.
   - Role-first (Dir B): the **two-door split** described above.
2. **Social proof** — H2 `Trusted by 52,000+ organizations` + a row of 5 logo placeholders (VIA RAIL, SUNLIFE, NAT. BANK, LIGHTSPEED, SAMSUNG).
3. **Benefits** (tinted background, carousel) — H2 `Experience the MedFlow difference`, sub "Satisfaction, utilization and wait-time guarantees." 3 cards, each: image + title + metric bullets:
   - "Members navigate care with clarity" — 4.7/5 appointment satisfaction; 4.6/5 overall satisfaction
   - "The safest care, on time" — 98%+ triage accuracy; 1,000+ monthly audits; 700+ compliance criteria
   - "White-glove rollout & success" — 9.4/10 onboarding score; 1-hour support response; live reporting dashboards
4. **Integrated Care Platform** (tabs) — H2 `MedFlow's Integrated Care Platform`, sub "One care hub, 24/7/365 — programs that are stronger together." Four program tabs: **Employee Assistance**, **Mental Health+**, **Primary Care**, **Wellness**. Active tab shows a description, a feature bullet list, a `Learn more →` link, and **two phone mockup screenshots**. (In the wireframe only the first tab's content is wired; production should make all four switch.)
5. **Impact stats** (warm background) — H2 `Having real impact.` 3 columns:
   - **40%** — Avg. improvement in mental-health scores (PHQ-9) within ~30 days
   - **30 days** — Avg. leave-of-absence duration vs. 65-day industry average
   - **4+ hrs** — Saved per consultation, on average
6. **Testimonials** (carousel) — H2 `Over 26,000 five-star app ratings`. 2-up cards with quote + author + 5 stars; pagination dots. Quotes from Moon K., Anne C., Patsy R., Laura J. (see `data.js`).
7. **ROI lead-magnet banner** (tinted) — H2 "The cost-benefit analysis your leadership needs to see." sub "Discover **13× the ROI**: the business case for virtual mental-health care." CTA `Download the report` + report-cover image.
8. **Footer** — dark, 5 columns (brand blurb + Platform / Company / Resources / Apps), legal bar "© 2026 MedFlow · Privacy · Terms · AODA · Cookies."

### 2. EAP (Employee Assistance Program)
**Purpose:** Deep-dive product page for the EAP program.
1. **Hero** — eyebrow `Employee Assistance Program`; H1 **"The EAP people actually use."**; body "Outdated EAPs gather dust. MedFlow's is digital-first, employee-designed and built for the moment someone finally reaches out."; CTAs `See it in action` / `Download overview`; role buttons (Dir A/C) or a note that CTAs are already role-tailored (Dir B). Right: app screenshot placeholder.
2. **What's included** (tinted) — H2 + 3×2 grid of 6 cards: Confidential counselling / Work–life services / Manager support / Crisis response / Self-guided toolkits / Reporting (each with a one-line description — see `render.js` `pageEAP()`).
3. **How it works** — H2 + 3 numbered steps: 1) Reach out, 2) Get matched, 3) Follow through.
4. **Impact stats** — same 3-column stat block as Home.
5. **CTA banner** — "Give your people an EAP worth opening." + `Book a demo` / `Talk to sales`.
6. **Footer.**

### 3. Pricing
**Purpose:** Communicate plans and drive a quote/demo.
1. **Hero** — eyebrow `Pricing`; H1 **"Pricing that scales with your people."**; body "Simple per-employee-per-month pricing. Every plan includes unlimited access — no surprise per-visit fees."; a **billing toggle pill** ("Per employee / mo" | "Annual (−15%)").
2. **Plans** (tinted) — 3 cards: **Essential $6**, **Plus $11** (featured, "Most popular"), **Complete $16** — all per-employee/month. Feature bullets per plan (see `render.js` `pagePricing()`). Featured plan has accent-tinted background + primary CTA.
3. **Comparison table** — H2 `Compare plans` + a 5-row feature matrix across Essential/Plus/Complete.
4. **FAQ** — H2 `Questions, answered` + 4 expandable rows (accordion `+` affordance).
5. **CTA banner** — "Get a quote built around your headcount." + CTAs.
6. **Footer.**

---

## Interactions & Behavior
- **Role switching (core):** selecting patient vs. clinician updates a single `role` state and re-renders role-dependent nav labels, CTAs, hero treatment, and the role indicator chip. In Dir B it's the role bar; in Dir A it's the Login dropdown; in Dir C it's the rail pill / hero buttons. **Persist the choice** (e.g. localStorage / cookie) so returning users keep their context.
- **Mega-menus (Dir A):** one panel open at a time; toggling the active trigger closes it; outside-click closes. Production should also support hover-open with a close delay and full keyboard/focus support.
- **Command launcher (Dir C):** `⌘K` opens a search/command palette (wireframe shows the trigger only).
- **Tabs (Home platform section):** four program tabs swap the description + phone screenshots. (Wire all four in production.)
- **Carousels:** Benefits and Testimonials are carousels (arrows + pagination dots). Wireframe shows them as static grids — implement real sliders (e.g. Embla/Swiper) or a responsive grid that collapses to a swipe carousel on mobile.
- **Accordion:** Pricing FAQ rows expand/collapse.
- **Billing toggle (Pricing):** switches displayed prices between monthly and annual (−15%).
- **Responsive:** at ≤920px the multi-column grids (split hero, 3-/4-up grids, doors, mega-menu columns, footer) collapse to 2 columns or stack. The Dir C rail would convert to a bottom bar or hamburger on mobile.

## State Management
- `direction` — `"A" | "B" | "C"` (this is a *prototype-only* selector for comparing nav options; **production ships one direction — B**). Not needed in the real app.
- `page` — current route (`home | eap | pricing`) — becomes real routes in production.
- `role` — `"patient" | "clinician"` — **the one piece of real app state to carry forward.** Drives nav labels, CTA copy, hero variant, and the role chip. Persist it.
- Tab state for the platform section (active program), accordion open state (FAQ), billing-period state (Pricing), and carousel indices are all local component state.

## Design Tokens
Pulled from `wf.css` `:root`. **The color and type intent is real; the sketch primitives (wobble radius, paper texture, dashed greyboxes) are wireframe-only — drop them in production.**

**Color**
| Token | Value | Use |
|---|---|---|
| `--paper` | `#f6f4ee` | Page background (warm off-white) |
| `--paper-2` | `#efece3` | Secondary surfaces, bars |
| `--ink` | `#2c2b27` | Primary text, borders, dark footer/role-bar |
| `--ink-soft` | `#76746c` | Muted text, captions |
| `--accent` | `oklch(0.60 0.072 215)` (~`#3f8a93` teal-blue) | Primary CTAs, links, stat numbers, accents |
| `--accent-soft` | `oklch(0.95 0.022 215)` | Tinted section backgrounds |
| `--patient` | `oklch(0.90 0.045 65)` (warm peach) | Patient role surfaces/chips |
| `--patient-line` | `oklch(0.66 0.09 60)` | Patient borders |
| `--clinician` | `oklch(0.92 0.03 215)` (cool blue-grey) | Clinician role surfaces/chips |
| `--clinician-line` | `oklch(0.58 0.07 220)` | Clinician borders |
| warm tint | `oklch(0.96 0.02 65)` | "Impact stats" / CTA section background |

> Role color-coding is meaningful: **peach = patient/member, cool blue = clinician.** Keep this consistent.

**Typography**
- **Headlines & UI (incl. nav, buttons):** `Newsreader` — an editorial oldstyle serif (Google Fonts). This is the intentional "formal" direction the client asked for (a stand-in for Dialogue's *Poynter Oldstyle*). Weights used: 500 (hero H1, `letter-spacing:-.01em`, line-height ~1.05), 600 (H2/H3, buttons).
- **Body / paragraphs:** `Source Sans 3` (Google Fonts), 400/600.
- **Eyebrows / section labels / code-y captions:** monospace (`Courier New`), 11px, uppercase, letter-spacing ~.16em, accent color.
- **Handwritten annotations (`--font-note`: `Gaegu`):** WIREFRAME-ONLY margin notes. **Do not ship.**
- Type scale (wireframe): H1 46px / H2 32px / H3 21px / body 15px / small 13px / caption 11–12px. Treat as relative guidance, not pixel-exact.

**Other**
- Spacing: sections ~34px vertical / 40px horizontal padding; grid gaps 18px; card padding 18px.
- Radius (production): use a restrained scale (e.g. 6–12px). The wireframe's `255px 14px…` "wobble" radius is sketch-only.
- The wireframe's hand-drawn borders (2.5px solid ink), paper shadows (`6px 7px 0`), dashed greyboxes, and `.frame`/`.frame-bar` browser chrome are all **prototype scaffolding** — not part of the product UI.

## Assets
- **No real image assets** are included — every image is a CSS greybox placeholder labeled with what belongs there (member/clinician lifestyle photos, app/phone screenshots, report cover, partner logos). Source real assets in production.
- **Fonts:** Google Fonts — `Newsreader`, `Source Sans 3` (ship these); `Gaegu` is wireframe-only.
- **Icons:** the wireframe uses emoji/Unicode glyphs (⌂ ❤ $ ▦ ⚕ 🧑 🔒 ⌘) as stand-ins. Replace with a real icon set (the original brand used Font Awesome).
- **Logos:** partner logos shown as text placeholders; use real (likely grayscale) logo assets.

## Files
All in this handoff folder:
- `MedFlow Wireframes.html` — entry point: control bar + script wiring. Open in a browser to interact (switch Direction/Page, toggle annotations & straight lines, switch role).
- `wf.css` — all styling + design tokens (`:root`). Note: most of this is wireframe aesthetic; mine it for tokens, layout structure, and type/color intent.
- `data.js` — all page content/copy (mega-menu structure, benefits, programs, stats, testimonials, logos). **This is the source of truth for copy.**
- `render.js` — renders nav per direction (`navA/navB/railC`), the shared page bodies (`pageHome/pageEAP/pagePricing`), and the interaction controller. Read this to understand structure and which elements are role-dependent.

## Recommended Build Order
1. Set up the project (React/Next.js recommended) + load `Newsreader` / `Source Sans 3` + define the design tokens above as CSS variables / theme.
2. Build the **Direction B** global chrome: role bar + role-aware header (role state persisted).
3. Build the **Home** page sections top-to-bottom using real copy from `data.js`.
4. Build **EAP** and **Pricing** pages.
5. Wire interactions: platform tabs, carousels, FAQ accordion, billing toggle, ⌘K (if desired).
6. Replace greyboxes with real photography/screenshots and partner logos.
