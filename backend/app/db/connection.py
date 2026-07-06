"""SQLite connection helpers."""
import os
import sqlite3
from typing import Optional

from app.config import DATA_ROOT
from app.models.dataset import DatasetSchema
from app.services.registry import db_path, init_registry, load_schema


def get_db_path(dataset_id: Optional[str] = None) -> str:
    if dataset_id is None:
        from app.services.registry import get_active_dataset_id

        dataset_id = get_active_dataset_id()
        if dataset_id is None:
            raise RuntimeError("No active dataset")
    return db_path(dataset_id)


def get_connection(dataset_id: Optional[str] = None) -> sqlite3.Connection:
    path = get_db_path(dataset_id)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_readonly_connection(dataset_id: Optional[str] = None) -> sqlite3.Connection:
    path = get_db_path(dataset_id)
    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def db_exists_and_populated(dataset_id: str) -> bool:
    path = db_path(dataset_id)
    if not os.path.exists(path):
        return False
    try:
        schema = load_schema(dataset_id)
    except KeyError:
        return False
    conn = sqlite3.connect(path)
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='samples'"
        )
        if cur.fetchone() is None:
            return False
        cur = conn.execute("SELECT COUNT(*) FROM samples")
        if cur.fetchone()[0] == 0:
            return False
        if schema.source.split.values:
            splits = {row[0] for row in conn.execute("SELECT DISTINCT split FROM samples")}
            return set(schema.source.split.values).issubset(splits)
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def ensure_registry() -> None:
    init_registry()
