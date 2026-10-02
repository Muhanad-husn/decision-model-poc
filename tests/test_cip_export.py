"""The CIP schema dump and export (PRD §5.2, RULES.md): the read-only URI rule, the WAL stop,
the provenance rule and the event-edge link, on a toy SQLite fixture shaped like the dumped
schema. The real database is never opened here."""

import json
import sqlite3

import pytest

from src import cip_export, cip_schema_dump
from src.cip_export import SchemaGap, export
from src.cip_schema_dump import RefusedDb, WalStop, db_path, dump, open_ro

DDL = """
CREATE TABLE source (node_id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, type TEXT,
    language_of_origin TEXT);
CREATE TABLE actor (node_id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL, aliases TEXT,
    actor_type TEXT, acled_actor_id TEXT, ucdp_actor_id TEXT, deleted INTEGER DEFAULT 0);
CREATE TABLE claim (node_id TEXT PRIMARY KEY, claim_text TEXT NOT NULL, claim_language TEXT,
    claim_type TEXT, claim_subject_type TEXT, deleted INTEGER DEFAULT 0);
CREATE TABLE event (node_id TEXT PRIMARY KEY, description TEXT, deleted INTEGER DEFAULT 0);
CREATE TABLE assertions (assertion_id TEXT PRIMARY KEY, entity_type TEXT NOT NULL,
    node_id TEXT, edge_id TEXT, property_name TEXT NOT NULL, asserted_value TEXT NOT NULL,
    is_current INTEGER NOT NULL DEFAULT 1);
CREATE TABLE ops (op_id TEXT PRIMARY KEY, agent TEXT NOT NULL, entity_type TEXT NOT NULL,
    operation TEXT NOT NULL, target_node_id TEXT);
"""
EDGES = (
    "edge_sourced_by", "edge_made_by", "edge_asserts_event", "edge_perpetrated",
    "edge_associated_with_event", "edge_claimed_responsibility", "edge_targeted_in",
)

LONG = " It went on for long enough to pass any length rule in the sampling slice."


def build(path, *, wal=False, extra=None):
    con = sqlite3.connect(path)
    if wal:
        con.execute("PRAGMA journal_mode=WAL")
    con.executescript(DDL)
    for t in EDGES:
        con.execute(
            f"CREATE TABLE {t} (edge_id TEXT PRIMARY KEY, source_node_id TEXT NOT NULL, "
            "target_node_id TEXT NOT NULL, deleted INTEGER DEFAULT 0)"
        )
    rows = {
        "source": [
            ("s-tg", "some_channel_tg", "social_media", "en"),
            ("s-fa", "persian_channel", "television", "fa"),
            ("s-gdelt", "gdelt", "academic_dataset", "en"),
            ("s-ucdp", "ucdp", "academic_dataset", "en"),
        ],
        "event": [
            ("e1", "Forces of the Northern Brigade shelled the town." + LONG, 0),
            ("e2", "The NB denied the report and the ministry said nothing." + LONG, 0),
            ("e3", "Coded feed line: Northern Brigade, material conflict.", 0),
            ("e4", "A passage that names nobody in particular." + LONG, 0),
            ("e5", "Deleted event naming the Northern Brigade." + LONG, 1),
            ("e6", "Persian channel text naming the Ministry." + LONG, 0),
        ],
        "edge_sourced_by": [
            ("sb1", "e1", "s-tg"), ("sb2", "e2", "s-tg"), ("sb3", "e3", "s-gdelt"),
            ("sb4", "e4", "s-tg"), ("sb5", "e5", "s-tg"), ("sb6", "e6", "s-fa"),
        ],
        "actor": [
            ("a1", "Northern Brigade", json.dumps(["NB"]), "rebel_group", None, None, 0),
            ("a2", "Ministry", None, "government", None, None, 0),
            ("a3", "Nobody Linked", None, "civilian_group", None, None, 0),
            ("a4", "Coded Actor", None, "military", "acled-17", None, 0),
            ("a5", "Gdelt Only", None, "state", None, None, 0),
        ],
        "assertions": [
            # a1's current assertion overrides the column; the superseded one is ignored.
            ("as1", "node", "a1", None, "actor_type", '"political_militia"', 1),
            ("as1b", "node", "a1", None, "actor_type", '"military"', 0),
            ("as2", "node", "a2", None, "actor_type", '"government"', 1),
            ("as3", "node", "a3", None, "actor_type", '"civilian_group"', 1),
            ("as4", "node", "a4", None, "actor_type", '"military"', 1),
            ("as5", "node", "a5", None, "actor_type", '"state"', 1),
        ],
        "edge_perpetrated": [("p1", "a1", "e1"), ("p2", "a1", "e5"), ("p3", "a4", "e1")],
        "edge_associated_with_event": [
            ("w1", "a1", "e2"), ("w2", "a2", "e2"), ("w3", "a2", "e4"), ("w4", "a5", "e3"),
            ("w5", "a2", "e6"),
        ],
        "edge_claimed_responsibility": [],
        "edge_targeted_in": [("t1", "e3", "a1")],
        "claim": [
            ("c1", "The town was shelled.", "en", "factual_assertion", "event_occurrence", 0),
            ("c2", "The NB denies it.", "en", "denial", "actor_involvement", 0),
            ("c3", "Coded claim.", "en", "factual_assertion", "event_occurrence", 0),
            ("c4", "Made by a coded feed too.", "en", "threat", "policy_intent", 0),
            ("c5", "Written by a person.", "en", "other", "other", 0),
        ],
        "edge_asserts_event": [
            ("ae1", "c1", "e1"), ("ae2", "c2", "e2"), ("ae3", "c3", "e3"), ("ae4", "c4", "e4"),
            ("ae5", "c5", "e4"),
        ],
        "edge_made_by": [
            ("m1", "c1", "s-tg"), ("m2", "c2", "s-tg"), ("m3", "c3", "s-gdelt"),
            ("m4", "c4", "s-tg"), ("m4b", "c4", "s-ucdp"), ("m5", "c5", "s-tg"),
        ],
        "ops": [
            ("o1", "actor_network_agent", "Actor", "create_node", "a1"),
            ("o2", "actor_network_agent", "Actor", "create_node", "a2"),
            ("o3", "actor_network_agent", "Actor", "create_node", "a3"),
            ("o4", "actor_network_agent", "Actor", "create_node", "a4"),
            ("o5", "actor_network_agent", "Actor", "create_node", "a5"),
            ("o6", "claim_verification_agent", "Claim", "create_node", "c1"),
            ("o7", "claim_verification_agent", "Claim", "create_node", "c2"),
            ("o8", "claim_verification_agent", "Claim", "create_node", "c3"),
            ("o9", "claim_verification_agent", "Claim", "create_node", "c4"),
            ("o10", "admin_manual", "Claim", "create_node", "c5"),
        ],
    }
    if extra:
        extra(rows)
    for table, values in rows.items():
        for v in values:
            con.execute(f"INSERT INTO {table} VALUES ({', '.join('?' * len(v))})", v)
    con.commit()
    con.close()
    return path


def uri(path):
    return f"file:{path.as_posix()}?mode=ro"


@pytest.fixture
def db(tmp_path):
    return build(tmp_path / "toy.sqlite")


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


# --- the read-only URI rule -------------------------------------------------------------

@pytest.mark.parametrize("value", [
    "D:/CIP-data/db/cip.sqlite",
    "file:D:/CIP-data/db/cip.sqlite",
    "file:D:/CIP-data/db/cip.sqlite?mode=rw",
    "file:D:/CIP-data/db/cip.sqlite?mode=rwc",
    "file:D:/CIP-data/db/cip.sqlite?mode=ro&immutable=1",
])
def test_db_value_without_mode_ro_is_refused(value):
    with pytest.raises(RefusedDb):
        db_path(value)


@pytest.mark.parametrize("main", [cip_schema_dump.main, cip_export.main])
def test_both_scripts_refuse_a_plain_path_before_writing(main, db, tmp_path, monkeypatch):
    monkeypatch.setattr(cip_schema_dump, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr(cip_export, "OUT_DIR", tmp_path / "out")
    assert main(["--db", str(db)]) == 2
    assert not (tmp_path / "out").exists()


def test_read_only_connection_cannot_write(db):
    con = open_ro(uri(db))
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        con.execute("DELETE FROM actor")
    con.close()


def test_wal_database_whose_read_only_open_fails_stops(tmp_path, monkeypatch):
    path = build(tmp_path / "wal.sqlite", wal=True)
    assert cip_schema_dump.is_wal(path)

    def refuse(*args, **kwargs):
        raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr(cip_schema_dump.sqlite3, "connect", refuse)
    with pytest.raises(WalStop, match="WAL"):
        open_ro(uri(path))
    monkeypatch.setattr(cip_schema_dump, "OUT_DIR", tmp_path / "out")
    assert cip_schema_dump.main(["--db", uri(path)]) == 2
    assert not (tmp_path / "out").exists()


def test_schema_dump_has_counts_and_enums_and_no_text(db):
    con = open_ro(uri(db))
    text = dump(con)
    con.close()
    assert "== actor (5 rows)" in text
    assert "'rebel_group': 1" in text
    assert "shelled" not in text and "Northern Brigade" not in text


# --- the export -------------------------------------------------------------------------

def run_export(db, tmp_path):
    con = open_ro(uri(db))
    summary = export(con, tmp_path / "out")
    con.close()
    c1 = {r["id"]: r for r in read_jsonl(tmp_path / "out" / "c1_pool.jsonl")}
    c2 = {r["id"]: r for r in read_jsonl(tmp_path / "out" / "c2_pool.jsonl")}
    return c1, c2, summary


def test_c1_pool_links_actors_to_passages_that_name_them(db, tmp_path):
    c1, _, _ = run_export(db, tmp_path)
    # a1 by its name (e1) and its alias (e2); e5 is deleted. a2 named in e2 and e6, not e4.
    assert [p["event_id"] for p in c1["a1"]["passages"]] == ["e1", "e2"]
    assert [p["event_id"] for p in c1["a2"]["passages"]] == ["e2", "e6"]
    assert c1["a2"]["passages"][1]["source_lang"] == "fa"
    assert c1["a1"]["name"] == "Northern Brigade"
    assert "shelled" in c1["a1"]["passages"][0]["text"]


def test_c1_prod_c_is_the_current_assertion(db, tmp_path):
    c1, _, _ = run_export(db, tmp_path)
    assert c1["a1"]["prod_c"] == {"actor_type": "political_militia"}
    assert c1["a2"]["prod_c"] == {"actor_type": "government"}


def test_c1_excludes_coded_feed_provenance_and_unlinked_actors(db, tmp_path):
    c1, _, summary = run_export(db, tmp_path)
    # a3: no event edge. a4: carries a coded-feed actor id. a5: linked only to a gdelt event.
    assert set(c1) == {"a1", "a2"}
    assert summary["c1"]["excluded"] == {
        "coded_feed_actor_id": 1, "coded_feed_event": 1, "no_passage_naming_actor": 1,
    }
    # a1 is also linked to e3 (gdelt) through targeted_in; that passage never appears.
    assert all(p["event_id"] != "e3" for p in c1["a1"]["passages"])


def test_c2_pool_holds_llm_claims_with_their_passage(db, tmp_path):
    _, c2, summary = run_export(db, tmp_path)
    # c3: its event and maker are gdelt. c4: one maker is ucdp. c5: not an LLM extraction.
    assert set(c2) == {"c1", "c2"}
    assert c2["c1"]["claim_text"] == "The town was shelled."
    assert c2["c1"]["prod_c"] == {
        "claim_type": "factual_assertion", "claim_subject_type": "event_occurrence",
    }
    assert [p["event_id"] for p in c2["c2"]["passages"]] == ["e2"]
    assert c2["c2"]["claim_language"] == "en"
    assert summary["c2"]["excluded"] == {"coded_feed": 2, "not_llm_extracted": 1}


def test_c2_prod_c_prefers_a_current_assertion_over_the_column(tmp_path):
    def add(rows):
        rows["assertions"].append(
            ("as9", "node", "c1", None, "claim_type", '"announcement"', 1)
        )

    path = build(tmp_path / "toy2.sqlite", extra=add)
    _, c2, _ = run_export(path, tmp_path)
    assert c2["c1"]["prod_c"]["claim_type"] == "announcement"
    assert c2["c2"]["prod_c"]["claim_type"] == "denial"


def test_export_stops_when_no_actor_links_to_a_passage(tmp_path):
    def unlink(rows):
        for t in ("edge_perpetrated", "edge_associated_with_event", "edge_targeted_in"):
            rows[t] = []

    path = build(tmp_path / "gap.sqlite", extra=unlink)
    con = open_ro(uri(path))
    with pytest.raises(SchemaGap, match="C1"):
        export(con, tmp_path / "out")
    con.close()
    assert not (tmp_path / "out" / "c1_pool.jsonl").exists()


def test_export_stops_when_an_event_edge_table_is_missing(tmp_path):
    path = build(tmp_path / "gap2.sqlite")
    con = sqlite3.connect(path)
    con.execute("DROP TABLE edge_asserts_event")
    con.commit()
    con.close()
    con = open_ro(uri(path))
    with pytest.raises(SchemaGap, match="edge_asserts_event"):
        export(con, tmp_path / "out")
    con.close()


def test_export_writes_only_the_pools_and_the_summary(db, tmp_path):
    run_export(db, tmp_path)
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == [
        "c1_pool.jsonl", "c2_pool.jsonl", "export_summary.json",
    ]
