"""Generic parquet → SQLite ingestion driven by dataset schema."""
import glob
import io
import os
import sqlite3
from typing import Any, Dict, List, Optional

import pandas as pd
from PIL import Image

from app.db.columns import db_columns, fts_columns
from app.db.connection import db_exists_and_populated
from app.models.dataset import DatasetSchema, FieldType
from app.services.registry import db_path, load_schema, update_ingest_status

THUMB_MAX = 256


def _split_from_filename(path: str, known_splits: Optional[List[str]] = None) -> str:
    name = os.path.basename(path)
    splits = known_splits or ["train", "validation", "test"]
    for split in splits:
        if name.startswith(split):
            return split
    return "unknown"


def _make_thumbnail(img: Image.Image, max_size: int = THUMB_MAX) -> bytes:
    thumb = img.copy()
    thumb.thumbnail((max_size, max_size))
    buf = io.BytesIO()
    thumb.convert("RGB").save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def _storage_sql(ftype: FieldType) -> str:
    if ftype in (FieldType.image, FieldType.blob):
        return "BLOB"
    if ftype == FieldType.integer:
        return "INTEGER"
    return "TEXT"


def create_schema(conn: sqlite3.Connection, schema: DatasetSchema) -> None:
    cols = db_columns(schema)
    col_defs = ", ".join(f"{c} {_storage_sql_for_col(c, schema)}" for c in cols)
    fts_cols = fts_columns(schema)

    conn.executescript(
        f"""
        DROP TABLE IF EXISTS samples;
        DROP TABLE IF EXISTS samples_fts;
        CREATE TABLE samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {col_defs}
        );
        CREATE INDEX idx_samples_split ON samples(split);
        """
    )
    if fts_cols:
        conn.execute(
            f"""
            CREATE VIRTUAL TABLE samples_fts USING fts5(
                {", ".join(fts_cols)},
                content='samples',
                content_rowid='id'
            )
            """
        )


def _storage_sql_for_col(col: str, schema: DatasetSchema) -> str:
    if col in ("width", "height"):
        return "INTEGER"
    if col == "thumbnail":
        return "BLOB"
    for f in schema.fields:
        if f.name == col or (f.group_members and col in f.group_members):
            return _storage_sql(f.type)
    return "TEXT"


def _get_nested(row: dict, path: str) -> Any:
    if path == "_split":
        return None
    parts = path.split(".")
    val = row
    for p in parts:
        if val is None:
            return None
        if isinstance(val, dict):
            val = val.get(p)
        else:
            return None
    return val


def _extract_row_values(
    r: dict, schema: DatasetSchema, split: str, thumb_max: int
) -> tuple:
    cols = db_columns(schema)
    values: Dict[str, Any] = {"split": split}

    for f in schema.fields:
        if f.type == FieldType.split:
            continue
        if f.type == FieldType.text_list:
            continue
        if f.type == FieldType.image:
            img_bytes = _get_nested(r, f.source)
            values[f.name] = img_bytes
            if img_bytes:
                try:
                    img = Image.open(io.BytesIO(img_bytes))
                    values["width"] = img.size[0]
                    values["height"] = img.size[1]
                    values["thumbnail"] = _make_thumbnail(img, thumb_max)
                except Exception:
                    values["width"] = values["height"] = None
                    values["thumbnail"] = None
            else:
                values["width"] = values["height"] = None
                values["thumbnail"] = None
            continue
        val = _get_nested(r, f.source) if "." in f.source else r.get(f.source)
        if f.type == FieldType.integer and val is not None:
            try:
                val = int(val)
            except (TypeError, ValueError):
                val = None
        values[f.name] = val

    for f in schema.fields:
        if f.type == FieldType.text_list and f.group_members:
            for m in f.group_members:
                values[m] = r.get(m)

    return tuple(values.get(c) for c in cols)


def ingest_dataset(dataset_id: str, force: bool = False) -> int:
    """Ingest parquet into SQLite for a dataset. Returns row count."""
    schema = load_schema(dataset_id)
    path = db_path(dataset_id)

    if not force and db_exists_and_populated(dataset_id):
        conn = sqlite3.connect(path)
        try:
            fts_cols = fts_columns(schema)
            if fts_cols:
                conn.execute("INSERT INTO samples_fts(samples_fts) VALUES('rebuild')")
                conn.commit()
        finally:
            conn.close()
        count = _count_rows(path)
        update_ingest_status(dataset_id, "done", row_count=count)
        return count

    parquet_dir = schema.source.path
    files = sorted(glob.glob(os.path.join(parquet_dir, "**", "*.parquet"), recursive=True))
    if not files:
        files = sorted(glob.glob(os.path.join(parquet_dir, "*.parquet")))
    if not files:
        update_ingest_status(dataset_id, "error", message=f"No parquet in {parquet_dir}")
        raise FileNotFoundError(f"No parquet files in {parquet_dir}")

    update_ingest_status(dataset_id, "running", message="Ingesting…")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    conn = sqlite3.connect(path)
    create_schema(conn, schema)
    cols = db_columns(schema)
    thumb_max = 256

    total = 0
    try:
        for f in files:
            split = _split_from_filename(f, schema.source.split.values)
            df = pd.read_parquet(f)
            rows = []
            for _, row in df.iterrows():
                r = row.to_dict()
                rows.append(_extract_row_values(r, schema, split, thumb_max))
            placeholders = ", ".join(["?"] * len(cols))
            conn.executemany(
                f"INSERT INTO samples ({', '.join(cols)}) VALUES ({placeholders})",
                rows,
            )
            conn.commit()
            total += len(rows)

        fts_cols = fts_columns(schema)
        if fts_cols:
            conn.execute("INSERT INTO samples_fts(samples_fts) VALUES('rebuild')")
            conn.commit()
    except Exception as e:
        update_ingest_status(dataset_id, "error", message=str(e))
        raise
    finally:
        conn.close()

    update_ingest_status(dataset_id, "done", row_count=total, message="Ingest complete")
    return total


def _count_rows(path: str) -> int:
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


def ingest_all_pending() -> None:
    from app.services.registry import get_active_dataset_id, list_dataset_ids

    for did in list_dataset_ids():
        schema = load_schema(did)
        if schema.ingest.status != "done" and schema.download.status == "ready":
            try:
                ingest_dataset(did)
            except Exception as e:
                print(f"[ingest] {did}: {e}")
    active = get_active_dataset_id()
    if active:
        ingest_dataset(active)


if __name__ == "__main__":
    ingest_all_pending()
