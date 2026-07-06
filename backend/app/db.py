"""SQLite connection helpers."""
import os
import sqlite3

# DB path is configurable so Docker can point it at a mounted volume.
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "flickr8k.db"))
DB_PATH = os.path.abspath(DB_PATH)

EXPECTED_SPLITS = {"train", "validation", "test"}


def get_connection() -> sqlite3.Connection:
    """A normal read/write connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_readonly_connection() -> sqlite3.Connection:
    """A read-only connection, used for the user-facing SQL console."""
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def db_exists_and_populated() -> bool:
    if not os.path.exists(DB_PATH):
        return False
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='samples'"
        )
        if cur.fetchone() is None:
            return False
        cur = conn.execute("SELECT COUNT(*) FROM samples")
        if cur.fetchone()[0] == 0:
            return False
        splits = {row[0] for row in conn.execute("SELECT DISTINCT split FROM samples")}
        return EXPECTED_SPLITS.issubset(splits)
    except sqlite3.Error:
        return False
    finally:
        conn.close()
