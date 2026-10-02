"""Dump the CIP database schema to data/cip/schema.txt, read-only (PRD §5.2, RULES.md).

Writes table definitions, row counts, and distinct values with counts for the provenance and
source columns and the label enums. No text field and no row is written. The database is taken
only as a `--db` URI carrying `mode=ro`; any other value is refused, and the path never appears
in this source. The journal mode is read from the file header first: if the database is in WAL
mode and the read-only open cannot proceed, the script stops and reports. It never uses
`immutable=1` or any other workaround.

Run from the repo root:
    uv run python src/cip_schema_dump.py --db "file:D:/CIP-data/db/cip.sqlite?mode=ro"
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "cip"
SCHEMA = OUT_DIR / "schema.txt"

# Columns whose distinct values are dumped: provenance and source columns, the label enums,
# and the currency flag. Matched on the column name, never on content.
ENUM_COLUMN = re.compile(
    r"(provenance|source_type|source_kind|source_name|^source$|feed|origin|extract|method|"
    r"pipeline|model|actor_type|claim_type|claim_subject_type|subject_type|^type$|kind|"
    r"field|label|value_enum|is_current|language|lang|property_name|agent|entity_type|operation|"
    r"resolution_status|stance|credibility_tier)",
    re.IGNORECASE,
)
MAX_DISTINCT = 60  # above this a column is reported by its distinct count only


class RefusedDb(ValueError):
    """The --db value is not a read-only SQLite URI."""


class WalStop(RuntimeError):
    """The database is in WAL mode and a read-only open could not proceed: stop and report."""


def db_path(uri):
    """The file path inside a read-only URI. Refuses anything that is not `file:...?mode=ro`
    or that carries `immutable`."""
    if not isinstance(uri, str) or not uri.startswith("file:"):
        raise RefusedDb(f"--db must be a file: URI with mode=ro, got {uri!r}")
    parts = urlsplit(uri)
    query = parse_qs(parts.query)
    if query.get("mode") != ["ro"]:
        raise RefusedDb(f"--db must carry mode=ro, got {uri!r}")
    if "immutable" in query:
        raise RefusedDb(f"--db must not carry immutable, got {uri!r}")
    return Path(unquote(uri[len("file:"):].split("?", 1)[0]))


def is_wal(path):
    """True when the header's read/write format bytes (offsets 18, 19) say WAL (value 2)."""
    with open(path, "rb") as f:
        header = f.read(20)
    return len(header) == 20 and (header[18] == 2 or header[19] == 2)


def open_ro(uri):
    """A read-only connection, probed with one read. A failed probe on a WAL database raises
    WalStop; nothing is retried with another mode."""
    path = db_path(uri)
    if not path.exists():
        raise FileNotFoundError(f"no database at the --db path: {path}")
    wal = is_wal(path)
    try:
        con = sqlite3.connect(uri, uri=True)
        con.execute("SELECT count(*) FROM sqlite_master").fetchone()
    except sqlite3.OperationalError as exc:
        if wal:
            raise WalStop(
                f"database is in WAL mode and the read-only open failed ({exc}); "
                "stopping without any workaround"
            ) from exc
        raise
    return con


def tables(con):
    return con.execute(
        "SELECT name, sql FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()


def columns(con, table):
    """(name, declared type) per column."""
    return [(r[1], r[2]) for r in con.execute(f'PRAGMA table_info("{table}")')]


def distinct(con, table, column):
    """(distinct count, [(value, count), ...] or None when above MAX_DISTINCT)."""
    n = con.execute(f'SELECT count(DISTINCT "{column}") FROM "{table}"').fetchone()[0]
    if n > MAX_DISTINCT:
        return n, None
    rows = con.execute(
        f'SELECT "{column}", count(*) FROM "{table}" GROUP BY "{column}" '
        f"ORDER BY count(*) DESC, 1"
    ).fetchall()
    return n, rows


def dump(con):
    """The schema.txt text: DDL, row counts and enum distributions. No text fields, no rows."""
    journal = con.execute("PRAGMA journal_mode").fetchone()[0]
    out = [f"journal_mode: {journal}", ""]
    for name, sql in tables(con):
        if sql.lstrip().upper().startswith("CREATE VIRTUAL TABLE"):
            # Its module (for example an embedding index) is not loaded here; the
            # definition is enough, and its shadow tables are counted on their own.
            out += [f"== {name} (virtual, not counted)", sql.strip(), ""]
            continue
        count = con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
        out += [f"== {name} ({count} rows)", sql.strip(), ""]
        for column, decl in columns(con, name):
            if not ENUM_COLUMN.search(column):
                continue
            n, rows = distinct(con, name, column)
            if rows is None:
                out.append(f"  {column} [{decl}]: {n} distinct (not listed)")
                continue
            out.append(f"  {column} [{decl}]: {n} distinct")
            out += [f"    {value!r}: {c}" for value, c in rows]
        out.append("")
    for name, sql in con.execute(
        "SELECT name, sql FROM sqlite_master WHERE type IN ('index', 'view') "
        "AND sql IS NOT NULL ORDER BY type, name"
    ):
        out += [f"-- {name}", sql.strip()]
    return "\n".join(out) + "\n"


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
        text = dump(con)
    finally:
        con.close()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SCHEMA.write_text(text, encoding="utf-8")
    print(f"wrote {SCHEMA.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
