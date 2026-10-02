# Slice 07: read-only CIP schema dump and export, run by the builder

**Milestone:** M4 · **Size:** M · **Issue:** #12
**Spec:** [specs/PRD.md#52-cip-set-c-400-items-results-only-publication](../../specs/PRD.md#52-cip-set-c-400-items-results-only-publication) · **Depends on:** Muhanad-husn/AEO#246 (sandbox guard passes read-only sqlite opens; start once merged and the project picks up the new plugin version)

## Goal
Two scripts, each taking the database only as `--db "file:D:/CIP-data/db/cip.sqlite?mode=ro"`, run from the repo root, writing only under `data/cip/`; the path is never hardcoded in source. First `src/cip_schema_dump.py` writes `data/cip/schema.txt`: table definitions, row counts, and distinct values with counts for the provenance/source columns and the three label enums (no text fields, no rows). It checks the journal mode first: if the database is in WAL mode and a read-only open cannot proceed, it stops and reports; it never uses `immutable=1` or any other workaround. Then `src/cip_export.py` writes the C1 and C2 candidate pools (LLM-extracted records only, `is_current = 1` labels, the linked English source passage). If C1 actors cannot be linked to a source passage through the event edges, it stops and reports the schema gap. Both scripts refuse any `--db` value without `mode=ro`. The builder runs both. Blocked until the AEO sandbox-guard fix that passes read-only sqlite opens has landed.

## Mechanism
Stdlib `sqlite3` with a URI read-only connection. The export is written against the dumped schema, not a guessed one.

## Acceptance criterion
Given a toy SQLite fixture shaped like the dumped schema, when the export runs, then it writes the pools, excludes coded-feed provenance, and refuses any `--db` without `mode=ro`; a test covers the WAL stop. Given the real database and the AEO guard fix, the builder's runs produce schema.txt and both pools, and the provenance rule is written down.

## Files
```aeo-independence
slice: 07-cip-export
creates: src/cip_schema_dump.py
creates: src/cip_export.py
creates: tests/test_cip_export.py
```

## Out of scope
Sampling (slice 08). Any write, migration or vacuum of the database. Any change to CIP code.
