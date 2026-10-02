# Slice 03: Jev runner with spend guard, smoke-run on 5 Axial items

**Milestone:** M2 · **Size:** M · **Issue:** #8
**Spec:** [specs/PRD.md#61-jev-calls](../../specs/PRD.md#61-jev-calls) · **Depends on:** #6 (slice 01), #7 (slice 02)

## Goal
`src/jev.py` sends one call per item (all five questions) to `jev-1.13.0` through the pinned `typesafe-sdk`, concurrency at most 4, exponential backoff on 429/529, 401/422 reported as failures, a running cost from `usage.input_tokens` at $0.042/M that aborts past $2.00 cumulative, and every raw response stored in `runs/jev/<run_id>/responses.jsonl` with request hash, latency and input tokens. A smoke run on 5 Axial items proves parsing and cost.

## Mechanism
Library: `typesafe-sdk` (installed version pinned in pyproject). Key from `TYPESAFE_API_KEY` in `.env`.

## Acceptance criterion
Given a valid key and items.jsonl, when the smoke run sends 5 items, then 5 responses parse with a `choice` and full `probabilities` for all 5 axes, the cost is logged and booked in LEDGER.md; and unit tests (stubbed client) show the guard aborting past $2.00 and the backoff firing on 429 and 529.

## Files
```aeo-independence
slice: 03-jev-runner-smoke
edits: pyproject.toml
edits: uv.lock
edits: LEDGER.md
edits: .env.example
creates: src/jev.py
creates: tests/test_jev.py
depends-on: 01-axial-items
depends-on: 02-codebook-questions
```

## Out of scope
Full runs (slice 04). CIP questions (slice 10).
