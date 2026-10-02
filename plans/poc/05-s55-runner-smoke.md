# Slice 05: S55 runner on claude -p, smoke-run on 5 Axial items

**Milestone:** M3 · **Size:** M · **Issue:** #10
**Spec:** [specs/PRD.md#62-s55-calls](../../specs/PRD.md#62-s55-calls) · **Depends on:** #6 (slice 01), #7 (slice 02)

## Goal
`src/s55.py` merges the blind-axis and head-axis gold-coder prompts from `data/axial/docs/_archive/gold-coder.md` into one prompt, inlines the slice 02 question text and a batch of up to 10 items, calls headless `claude -p --output-format json` with no tools, logs `duration_ms`, `usage` and the resolved model id, validates every label against the option list, re-asks an invalid item once alone and records `invalid` if it fails again. If the resolved model id is not Sonnet 5.5, it stops (kill line). Every call is isolated from the harness: working directory an empty temp dir outside the repo, `--model claude-sonnet-5-5`, `--tools ""`, `--strict-mcp-config` with no MCP config, `--disable-slash-commands`, `--setting-sources` at its narrowest accepted value (no user or project plugins or hooks), the merged gold-coder prompt as `--system-prompt`, `--no-session-persistence`. A calibration call per draw (fixed short system prompt, one-word user turn) measures total input tokens (input + cache read + cache creation); the run aborts if it exceeds the ceiling set in the smoke run, and the figure is logged as harness overhead (PRD §6.2). The builder session runs this script under the project allow rule for `uv run python src/s55.py`; the smoke run is the test of that rule: if the safety check still refuses it, stop and report, and the founder runs the draws by hand only as the fallback.

## Mechanism
Existing tool: the Claude Code CLI in headless mode, one subprocess per batch per draw. Stdlib `subprocess`, `json` and `tempfile`.

## Acceptance criterion
Given items.jsonl, when the smoke run labels 5 items, then each item has a valid label on all five axes or an `invalid` record, the logged model id is a Sonnet 5.5 id, tokens are logged, and the calibration call's input tokens are under the ceiling (no CLAUDE.md or session-start text reached the call) and recorded as harness overhead; unit tests with a canned CLI output cover the re-ask path, the wrong-model stop, the exact isolation flags and working directory, and the abort when calibration exceeds the ceiling. The builder ran the smoke under the allow rule without a refusal, or the refusal is reported.

## Files
```aeo-independence
slice: 05-s55-runner-smoke
creates: src/s55.py
creates: tests/test_s55.py
depends-on: 01-axial-items
depends-on: 02-codebook-questions
```

## Out of scope
Three full draws (slice 06). API-equivalent pricing (slice 14).
