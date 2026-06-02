# Contributing

## Branching

- Branch from `main` for each change.
- Keep branches short-lived and scope them to one phase or one coherent slice.
- Prefer mergeable, reviewable increments over large mixed-purpose commits.

## Pull requests

- Open a PR for every change.
- Include what changed, why it changed, and how you validated it.
- Keep the PR focused on the active phase; do not mix polish work into a correctness-critical slice.

## Test policy

- Run the narrowest meaningful test first, then widen only if the result is clean.
- Backend work must pass `pytest` and the lint/type checks in `make lint`.
- Frontend work must pass `npm run lint`, `npm run typecheck`, and the frontend test suite.

## Two-tier rigor

- Correctness-critical work includes contracts, mappers, cache behavior, citations, and any code that can fabricate or drop a clinical claim.
- Correctness-critical work gets the full test pass, focused review, and explicit validation notes.
- Polish and layout work may move faster, but it still needs to compile, type-check, and stay aligned with the contract.

## Communication

- Leave a short note in the PR when a change deliberately narrows scope or defers a later phase item.
- If a requirement is blocked, state the blocker plainly and link to the relevant issue.