# Slice 02: turn the codebook into per-axis criteria and instructions

**Milestone:** M2 · **Size:** S · **Issue:** #7
**Spec:** [specs/PRD.md#61-jev-calls](../../specs/PRD.md#61-jev-calls) · **Depends on:** none

## Goal
A pure function builds, for each of the five Axial axes, the option-to-criterion map in the PRD §6.1 form `"<definition> Example: <positive> Not this: <negative>"` plus a one-sentence instruction carrying the axis decision rule (theory_school: decide `not-applicable` first, `unlisted` is a real unlisted school; empirical_scope: most specific level). The same text is the single source for the Jev request and the S55 prompt.

## Mechanism
Library: `pyyaml` reading `data/axial/config/domains/syria/codebook.yaml`. No model call.

## Acceptance criterion
Given the copied codebook, when the questions are built, then each axis has exactly its PRD §5.1 option count (3, 5, 7, 22, 30), every criterion has all three parts, and the two decision rules appear in their axes' instructions; a test asserts all of it.

## Files
```aeo-independence
slice: 02-codebook-questions
edits: pyproject.toml
edits: uv.lock
creates: src/codebook.py
creates: tests/test_codebook.py
```

## Out of scope
CIP options (slice 09). Sending anything to an API.
