"""Load the dataset's parquet files into SQLite.

The table schema and column mapping are driven entirely by fields.json (see
app/fields.py). Only fields declared with source="derived" have
dataset-specific extraction code here (image decoding, filename parsing);
source="passthrough" fields are copied from the parquet columns generically.

Idempotent: if the DB is already populated it does nothing. Run directly with
`python -m app.ingest` or it is invoked automatically on backend startup.
"""
import glob
import io
import os
import sqlite3
from typing import Optional

import pandas as pd
from PIL import Image

from .db import DB_PATH, db_exists_and_populated
from .fields import all_columns, load_dataset, load_fields, searchable_columns

THUMB_MAX = 256  # longest-edge px for grid thumbnails

# Parquet files live under $PARQUET_ROOT/<dataset_name> (mounted in Docker).
PARQUET_ROOT = os.environ.get(
    "PARQUET_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data")),
)


def data_dir() -> str:
    return os.path.join(PARQUET_ROOT, load_dataset().name)


def _split_from_filename(path: str) -> str:
    name = os.path.basename(path)
    for split in ("train", "validation", "test"):
        if name.startswith(split):
            return split
    return "unknown"


def _make_thumbnail(img: Image.Image) -> bytes:
    thumb = img.copy()
    thumb.thumbnail((THUMB_MAX, THUMB_MAX))
    buf = io.BytesIO()
    thumb.convert("RGB").save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def create_schema(conn: sqlite3.Connection) -> None:
    col_defs = ", ".join(
        f"{col} {f.sql_type}" for f in load_fields() for col in f.columns
    )
    fts_cols = searchable_columns()
    fts_ddl = (
        f"""
        CREATE VIRTUAL TABLE samples_fts USING fts5(
            {", ".join(fts_cols)},
            content='samples',
            content_rowid='id'
        );
        """
        if fts_cols
        else ""
    )
    conn.executescript(
        f"""
        DROP TABLE IF EXISTS samples;
        DROP TABLE IF EXISTS samples_fts;
        CREATE TABLE samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {col_defs},
            image BLOB,
            thumbnail BLOB
        );
        CREATE INDEX idx_samples_split ON samples(split);
        {fts_ddl}
        """
    )


def _derive_values(row: pd.Series, split: str) -> tuple[dict, bytes, Optional[bytes]]:
    """Dataset-specific extraction for source='derived' fields, plus the
    image/thumbnail blobs. Decodes the image once per row."""
    image = row["image"]
    img_bytes = image["bytes"]
    try:
        img = Image.open(io.BytesIO(img_bytes))
        width, height = img.size
        thumb = _make_thumbnail(img)
    except Exception:
        width = height = None
        thumb = None
    derived = {
        "split": split,
        "image_path": image.get("path"),
        "width": width,
        "height": height,
    }
    return derived, img_bytes, thumb


def ingest() -> None:
    if db_exists_and_populated():
        print(f"[ingest] DB already populated at {DB_PATH}; skipping.")
        return

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    files = sorted(glob.glob(os.path.join(data_dir(), "*.parquet")))
    if not files:
        raise SystemExit(f"[ingest] No parquet files found in {data_dir()}")

    fields = load_fields()
    for f in fields:
        if f.source not in ("derived", "passthrough"):
            raise SystemExit(f"[ingest] Unknown source '{f.source}' for field '{f.key}'")

    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)

    data_cols = all_columns()
    insert_sql = (
        f"INSERT INTO samples ({', '.join(data_cols)}, image, thumbnail) "
        f"VALUES ({', '.join(['?'] * (len(data_cols) + 2))})"
    )

    total = 0
    for path in files:
        split = _split_from_filename(path)
        df = pd.read_parquet(path)
        print(f"[ingest] {os.path.basename(path)} -> split={split} rows={len(df)}")
        rows = []
        for _, r in df.iterrows():
            derived, img_bytes, thumb = _derive_values(r, split)
            values = []
            for field in fields:
                if field.source == "derived":
                    if field.key not in derived:
                        raise SystemExit(
                            f"[ingest] fields.json declares derived field "
                            f"'{field.key}' but no extractor produces it"
                        )
                    values.append(derived[field.key])
                else:  # passthrough: copy the raw parquet column(s)
                    values.extend(r.get(c) for c in field.columns)
            rows.append((*values, img_bytes, thumb))
        conn.executemany(insert_sql, rows)
        conn.commit()
        total += len(rows)

    # Populate the FTS index from the base table.
    fts_cols = searchable_columns()
    if fts_cols:
        conn.execute(
            f"INSERT INTO samples_fts(rowid, {', '.join(fts_cols)}) "
            f"SELECT id, {', '.join(fts_cols)} FROM samples"
        )
        conn.commit()
    conn.close()
    print(f"[ingest] Done. Inserted {total} samples into {DB_PATH}")


if __name__ == "__main__":
    ingest()
