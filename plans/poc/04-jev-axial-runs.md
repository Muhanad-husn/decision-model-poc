# Slice 04: Jev runs 1 and 2 on all 120 Axial items

**Milestone:** M2 · **Size:** S · **Issue:** #9
**Spec:** [specs/PRD.md#11-build-plan](../../specs/PRD.md#11-build-plan) · **Depends on:** #8 (slice 03), #10 (slice 05)

## Goal
Two runs with identical requests over all 120 Axial items, each stored under its own run id, with a validity check that lists any response missing a label or probabilities. Starts only after both arms' Axial smoke runs (slices 03 and 05) have passed, per PRD §9.

## Mechanism
The slice 03 runner, invoked twice. No new library.

## Acceptance criterion
Given both arms' Axial smoke runs passed, when runs 1 and 2 complete, then there are 240 valid responses (or each invalid one is listed), request hashes match across the two runs item by item, cumulative spend is booked in LEDGER.md, the run is in REPORT.md's run log, and PLAN.md M2 turns `done`.

## Files
```aeo-independence
slice: 04-jev-axial-runs
edits: src/jev.py
edits: LEDGER.md
edits: REPORT.md
edits: PLAN.md
depends-on: 03-jev-runner-smoke
depends-on: 05-s55-runner-smoke
```

## Out of scope
Determinism scoring (slice 13).
