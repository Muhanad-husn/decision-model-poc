"""Export the C1 and C2 candidate pools from the CIP database, read-only (PRD §5.2, RULES.md).

Written against data/cip/schema.txt (src/cip_schema_dump.py), not a guessed schema. The database
is taken only as a `--db` URI carrying `mode=ro`, through the same open as the dump, so the
refusal and the WAL stop are the dump's. Writes only under data/cip/: c1_pool.jsonl,
c2_pool.jsonl and export_summary.json. Sampling is slice 08's; this keeps every candidate.

Provenance rule (PRD §5.2: only labels that came from LLM extraction of free text):
- The record was created by one of CIP's LLM extraction agents (`ops.agent` on its
  `create_node` op is in LLM_AGENTS). The database holds no finer per-label provenance:
  the `actor_type` assertions point at op and run ids that resolve to no ops or runs row.
- No coded feed is involved. A passage is an event description, and an event sourced by a
  coded feed (CODED_FEEDS, matched on `source.name`) is never a passage. An actor carrying an
  ACLED or UCDP actor id is out. A claim made by, or asserting an event sourced by, a coded
  feed is out.
- Deleted records and deleted events are out.

C1 (actor_type): an actor's passages are the descriptions of the events it reaches through
the event edges (perpetrated, associated_with_event, claimed_responsibility, targeted_in) that
name it, by canonical name or an alias, as a whole word. PROD-C is the one current
(`is_current = 1`) `actor_type` assertion. If no actor links to a passage this way, the export
stops and reports the schema gap; it never guesses a join.

C2 (claim_type, claim_subject_type): a claim's passage is the description of the event it
asserts (edge_asserts_event). PROD-C is the current assertion where one exists; CIP keeps no
assertions for these two properties, so in practice it is the claim row's own value, which is
the current one.

Run from the repo root, after the dump:
    uv run python src/cip_export.py --db "file:D:/CIP-data/db/cip.sqlite?mode=ro"
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from src.cip_schema_dump import RefusedDb, WalStop, open_ro  # noqa: E402

OUT_DIR = ROOT / "data" / "cip"
C1_POOL = "c1_pool.jsonl"
C2_POOL = "c2_pool.jsonl"
SUMMARY = "export_summary.json"

CODED_FEEDS = ("acled", "gdelt", "ucdp", "firms", "adsb-lol", "opensky")
LLM_AGENTS = ("actor_network_agent", "claim_verification_agent", "event_chain_agent")
# (table, actor end, event end) for each edge joining an actor to an event.
ACTOR_EVENT_EDGES = (
    ("edge_perpetrated", "source_node_id", "target_node_id"),
    ("edge_associated_with_event", "source_node_id", "target_node_id"),
    ("edge_claimed_responsibility", "source_node_id", "target_node_id"),
    ("edge_targeted_in", "target_node_id", "source_node_id"),
)
C2_QUESTIONS = ("claim_type", "claim_subject_type")

REQUIRED = {
    "source": ("node_id", "name", "language_of_origin"),
    "actor": ("node_id", "canonical_name", "aliases", "actor_type", "acled_actor_id", "ucdp_actor_id",
              "deleted"),
    "claim": ("node_id", "claim_text", "claim_language", "deleted") + C2_QUESTIONS,
    "event": ("node_id", "description", "deleted"),
    "assertions": ("node_id", "property_name", "asserted_value", "is_current"),
    "ops": ("agent", "operation", "target_node_id"),
    "edge_sourced_by": ("source_node_id", "target_node_id", "deleted"),
    "edge_made_by": ("source_node_id", "target_node_id", "deleted"),
    "edge_asserts_event": ("source_node_id", "target_node_id", "deleted"),
    **{t: ("source_node_id", "target_node_id", "deleted") for t, _, _ in ACTOR_EVENT_EDGES},
}


class SchemaGap(RuntimeError):
    """The schema does not support the join the PRD asks for: stop and report."""


def check_schema(con):
    gaps = []
    for table, cols in REQUIRED.items():
        have = {r[1] for r in con.execute(f'PRAGMA table_info("{table}")')}
        if not have:
            gaps.append(f"{table} (table missing)")
        else:
            gaps += [f"{table}.{c}" for c in cols if c not in have]
    if gaps:
        raise SchemaGap("schema gap, not exported: " + ", ".join(gaps))


def creators(con):
    """node_id -> the agent of its create_node op."""
    return dict(con.execute(
        "SELECT target_node_id, agent FROM ops WHERE operation = 'create_node' "
        "AND target_node_id IS NOT NULL"
    ))


def current_labels(con, prop):
    """node_id -> [decoded asserted values with is_current = 1]."""
    out = defaultdict(list)
    for node, value in con.execute(
        "SELECT node_id, asserted_value FROM assertions "
        "WHERE property_name = ? AND is_current = 1 AND node_id IS NOT NULL", (prop,)
    ):
        try:
            out[node].append(json.loads(value))
        except json.JSONDecodeError:
            out[node].append(value)
    return out


def events(con):
    """event_id -> {text, source_lang, coded}, live events with a description only, and the
    set of event ids sourced by a coded feed."""
    coded_sources = {
        r[0] for r in con.execute(
            f"SELECT node_id FROM source WHERE lower(name) IN ({','.join('?' * len(CODED_FEEDS))})",
            CODED_FEEDS,
        )
    }
    source_of = defaultdict(list)
    for event, source, lang in con.execute(
        "SELECT e.source_node_id, e.target_node_id, s.language_of_origin "
        "FROM edge_sourced_by e LEFT JOIN source s ON s.node_id = e.target_node_id "
        "WHERE coalesce(e.deleted, 0) = 0"
    ):
        source_of[event].append((source, lang))
    coded = {ev for ev, srcs in source_of.items() if any(s in coded_sources for s, _ in srcs)}
    live = {}
    for node, text in con.execute(
        "SELECT node_id, description FROM event WHERE coalesce(deleted, 0) = 0 "
        "AND description IS NOT NULL AND description != ''"
    ):
        langs = sorted({lang for _, lang in source_of.get(node, []) if lang})
        live[node] = {"text": text, "source_lang": langs[0] if len(langs) == 1 else langs or None}
    return live, coded, coded_sources


def names_of(canonical, aliases):
    names = [canonical]
    if aliases:
        try:
            parsed = json.loads(aliases)
            names += [a for a in parsed if isinstance(a, str)] if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            pass
    names = sorted({n.strip() for n in names if n and len(n.strip()) >= 2}, key=len, reverse=True)
    if not names:
        return None
    return re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, names)) + r")(?!\w)", re.IGNORECASE)


def passage(event_id, ev):
    return {"event_id": event_id, "text": ev["text"], "source_lang": ev["source_lang"],
            "chars": len(ev["text"])}


def c1_pool(con, live, coded, made_by_agent):
    links = defaultdict(set)
    for table, actor_end, event_end in ACTOR_EVENT_EDGES:
        for actor, event in con.execute(
            f"SELECT {actor_end}, {event_end} FROM {table} WHERE coalesce(deleted, 0) = 0"
        ):
            links[actor].add(event)
    labels = current_labels(con, "actor_type")
    pool, excluded, column_disagrees = [], Counter(), 0
    for node, name, aliases, acled, ucdp, deleted, column in con.execute(
        "SELECT node_id, canonical_name, aliases, acled_actor_id, ucdp_actor_id, deleted, "
        "actor_type FROM actor ORDER BY node_id"
    ):
        if deleted:
            excluded["deleted"] += 1
            continue
        if made_by_agent.get(node) not in LLM_AGENTS:
            excluded["not_llm_extracted"] += 1
            continue
        if acled or ucdp:
            excluded["coded_feed_actor_id"] += 1
            continue
        if not links.get(node):
            excluded["no_event_edge"] += 1
            continue
        free = sorted(e for e in links[node] if e not in coded and e in live)
        if not free:
            excluded["coded_feed_event" if links[node] & coded else "no_passage"] += 1
            continue
        current = labels.get(node, [])
        if len(current) != 1:
            excluded["no_current_label" if not current else "several_current_labels"] += 1
            continue
        pattern = names_of(name, aliases)
        passages = [passage(e, live[e]) for e in free if pattern and pattern.search(live[e]["text"])]
        if not passages:
            excluded["no_passage_naming_actor"] += 1
            continue
        column_disagrees += current[0] != column
        pool.append({"id": node, "name": name, "prod_c": {"actor_type": current[0]},
                     "passages": passages})
    return pool, excluded, column_disagrees


def c2_pool(con, live, coded, coded_sources, made_by_agent):
    makers = defaultdict(set)
    for claim, source in con.execute(
        "SELECT source_node_id, target_node_id FROM edge_made_by WHERE coalesce(deleted, 0) = 0"
    ):
        makers[claim].add(source)
    asserted = defaultdict(set)
    for claim, event in con.execute(
        "SELECT source_node_id, target_node_id FROM edge_asserts_event "
        "WHERE coalesce(deleted, 0) = 0"
    ):
        asserted[claim].add(event)
    labels = {q: current_labels(con, q) for q in C2_QUESTIONS}
    pool, excluded, from_assertion = [], Counter(), Counter()
    for node, text, lang, deleted, *columns in con.execute(
        "SELECT node_id, claim_text, claim_language, deleted, "
        + ", ".join(C2_QUESTIONS) + " FROM claim ORDER BY node_id"
    ):
        if deleted:
            excluded["deleted"] += 1
            continue
        if made_by_agent.get(node) not in LLM_AGENTS:
            excluded["not_llm_extracted"] += 1
            continue
        if makers[node] & coded_sources or asserted[node] & coded:
            excluded["coded_feed"] += 1
            continue
        passages = [passage(e, live[e]) for e in sorted(asserted[node]) if e in live]
        if not passages:
            excluded["no_passage"] += 1
            continue
        prod_c = {}
        for q, column in zip(C2_QUESTIONS, columns):
            current = labels[q].get(node, [])
            if len(current) == 1:
                prod_c[q] = current[0]
                from_assertion[q] += 1
            else:
                prod_c[q] = column
        pool.append({"id": node, "claim_text": text, "claim_language": lang, "prod_c": prod_c,
                     "passages": passages})
    return pool, excluded, from_assertion


def export(con, out_dir):
    """Build both pools, stop on a schema gap before writing, then write the pools and the
    summary under out_dir. Returns the summary."""
    check_schema(con)
    live, coded, coded_sources = events(con)
    made_by_agent = creators(con)
    c1, c1_out, c1_disagree = c1_pool(con, live, coded, made_by_agent)
    if not c1:
        raise SchemaGap(
            "C1: no actor links to a source passage that names it through the event edges "
            f"({', '.join(t for t, _, _ in ACTOR_EVENT_EDGES)}); not exported"
        )
    c2, c2_out, c2_from_assertion = c2_pool(con, live, coded, coded_sources, made_by_agent)
    summary = {
        "provenance_rule": __doc__.split("Provenance rule", 1)[1].split("\n\nC1 ", 1)[0].strip(),
        "coded_feeds_listed": list(CODED_FEEDS),
        "coded_feed_sources_found": len(coded_sources),
        "coded_feed_events": len(coded),
        "c1": {"pool": len(c1), "excluded": dict(sorted(c1_out.items())),
               "prod_c_differs_from_actor_column": c1_disagree,
               "labels": dict(Counter(r["prod_c"]["actor_type"] for r in c1).most_common())},
        "c2": {"pool": len(c2), "excluded": dict(sorted(c2_out.items())),
               "prod_c_from_assertion": dict(c2_from_assertion),
               "labels": {q: dict(Counter(r["prod_c"][q] for r in c2).most_common())
                          for q in C2_QUESTIONS}},
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in ((C1_POOL, c1), (C2_POOL, c2)):
        with open(out_dir / name, "w", encoding="utf-8", newline="\n") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    (out_dir / SUMMARY).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", required=True, help='"file:<path>?mode=ro"')
    args = parser.parse_args(argv)
    try:
        con = open_ro(args.db)
    except (RefusedDb, WalStop) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 2
    try:
        summary = export(con, OUT_DIR)
    except SchemaGap as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 3
    finally:
        con.close()
    print(json.dumps({k: summary[k] for k in ("c1", "c2")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
