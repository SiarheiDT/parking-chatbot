#!/usr/bin/env python3
"""Run a read-only SQLite query; uses DB_PATH from .env in project root."""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    from dotenv import load_dotenv

    load_dotenv()
    db = Path(os.getenv("DB_PATH", "data/db/parking_dev.db")).resolve()
    sql = " ".join(sys.argv[1:]).strip()
    if not sql:
        sql = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"

    uri = f"file:{db}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql)
        rows = cur.fetchall()
    except sqlite3.Error as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

    if not rows:
        print("(no rows)")
        return

    cols = list(rows[0].keys())
    print(" | ".join(cols))
    print("-" * max(40, len(" | ".join(cols))))
    for r in rows:
        print(" | ".join(str(r[c]) for c in cols))


if __name__ == "__main__":
    main()
