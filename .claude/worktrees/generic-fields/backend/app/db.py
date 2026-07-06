"""SQLite connection helpers."""
import os
import sqlite3

from .fields import load_dataset

# DB lives at $DB_DIR/<dataset_name>.db; both pieces are configurable so
# Docker can point them at a mounted volume, and DB_PATH can still override
# the full path directly.
DB_DIR = os.environ.get("DB_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
DB_PATH = os.environ.get("DB_PATH") or os.path.join(DB_DIR, f"{load_dataset().name}.db")
DB_PATH = os.path.abspath(DB_PATH)


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
        return cur.fetchone()[0] > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()
