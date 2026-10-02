# Slice 09: freeze CIP option descriptions in options.yaml before any model call

**Milestone:** M4 · **Size:** S · **Issue:** #14
**Spec:** [specs/PRD.md#52-cip-set-c-400-items-results-only-publication](../../specs/PRD.md#52-cip-set-c-400-items-results-only-publication) · **Depends on:** none

## Goal
`data/cip/options.yaml` gives a one-line meaning per option for `actor_type` (16), `claim_type` (8) and `claim_subject_type` (7), taken from CIP's own enum documentation where it exists and written neutrally where not. The source is `D:/CIP-code/planning/contracts/CIP_Schema_Artifact_v1.0.0.yaml` (all 31 ids; only state, government, military and police carry a meaning, so the rest are neutral one-liners). `CIP_Schema_Documentation.md` line 176 lists a different, stale claim_type enum (factual, attribution, casualty, territorial, denial); it is not used, and the slice 07 schema dump confirms the values the database holds. Because `data/` is git-ignored and option text counts as CIP text, the freeze is proven by a committed SHA-256 in `manifests/cip_options.json`; both runners refuse to run on a mismatch (slices 10 and 11).

## Mechanism
Read the CIP schema artifact read-only; a hand-written YAML file. No library, no model call.

## Acceptance criterion
Given options.yaml, when the test runs, then each question has exactly its PRD §5.2 option ids and one non-empty description each, and the file's SHA-256 equals the committed manifest.

## Files
```aeo-independence
slice: 09-cip-options
creates: manifests/cip_options.json
creates: tests/test_cip_options.py
```

## Out of scope
Any change to CIP code or docs.
