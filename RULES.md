# Rules

The full specification is the PRD, [`specs/PRD.md`](specs/PRD.md). These are the rules that hold on
every slice of work; where this page and the PRD disagree, the PRD wins and this page is
fixed.

- **Kill line.** If M1 cannot reproduce every PRD §5.1 sanity value exactly, or S55 resolves to a model id that is not Sonnet 5.5, stop: the comparison would be scored against data or a model other than the one the bars were written for, and that is a broken method, not a failed attempt. A bar failing is a result to report, never a reason to stop.
- **Bars are frozen.** `bars.json` holds PRD §8 verbatim and is committed before any model call. No bar is edited after a result is seen; an ill-posed bar is reported as ill-posed.
- **Spend guard.** The Jev runner keeps a running cost from `usage.input_tokens` at $0.042 per million and aborts when cumulative spend passes $2.00. Concurrency is 4 at most. Back off exponentially on 429 and 529.
- **Smoke first.** Five items per set through both arms, with parsing and cost checked, before any full run.
- **Source data is read-only.** `D:\axial` is copied from, never written to. `D:\CIP-data\db\cip.sqlite` is opened only with `mode=ro`, exported once to `data/cip/`, and never written, migrated or vacuumed.
- **CIP is opened only through a read-only URI.** `AEO_LIVE_DATA_ROOT` is `D:/CIP-data`. The schema dump and the export take the database only as `--db "file:D:/CIP-data/db/cip.sqlite?mode=ro"`, run from the repo root and write only under `data/cip/`; the builder runs them once the guard passes read-only SQLite opens (Muhanad-husn/AEO#246). The database path is never hardcoded or hidden in script source. If a read-only open fails (for example a WAL database without its shared-memory file), stop and report; never work around it.
- **No text leaves in git.** `data/`, `runs/` and `.env` are ignored. No passage text, CIP text or key is ever committed.
- **No guessed joins.** If CIP actors cannot be linked to a source passage through the event edges, stop and report the schema gap.
- **Out of scope stays out.** No other decision models, no local GPUs, no fine-tuning, no prompt-injection tests, no change to Axial or CIP code, no manual labelling.
- **Publishing.** `PUBLISH.md` follows PRD §10: never quote a passage; every reference label is called an LLM label in the first paragraph; CIP is results only; no "OSINT", "open-source" or em dash.
