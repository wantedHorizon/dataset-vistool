"""Load the Flickr8k parquet files into SQLite.

Idempotent: if the DB is already populated it does nothing. Run directly with
`python -m app.ingest` or it is invoked automatically on backend startup.
"""
import glob
import io
import os
import sqlite3

import pandas as pd
from PIL import Image

from .db import DB_PATH, db_exists_and_populated

CAPTION_COLS = [f"caption_{i}" for i in range(5)]
THUMB_MAX = 256  # longest-edge px for grid thumbnails

# Parquet files live under this directory (mounted in Docker).
DATA_DIR = os.environ.get(
    "PARQUET_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "flickr8k", "data")),
)


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
    caption_defs = ", ".join(f"{c} TEXT" for c in CAPTION_COLS)
    conn.executescript(
        f"""
        DROP TABLE IF EXISTS samples;
        DROP TABLE IF EXISTS samples_fts;
        CREATE TABLE samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            split TEXT NOT NULL,
            image_path TEXT,
            {caption_defs},
            width INTEGER,
            height INTEGER,
            image BLOB,
            thumbnail BLOB
        );
        CREATE INDEX idx_samples_split ON samples(split);
        CREATE VIRTUAL TABLE samples_fts USING fts5(
            {", ".join(CAPTION_COLS)},
            content='samples',
            content_rowid='id'
        );
        """
    )


def ingest() -> None:
    if db_exists_and_populated():
        print(f"[ingest] DB already populated at {DB_PATH}; skipping.")
        return

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.parquet")))
    if not files:
        raise SystemExit(f"[ingest] No parquet files found in {DATA_DIR}")

    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)

    total = 0
    for f in files:
        split = _split_from_filename(f)
        df = pd.read_parquet(f)
        print(f"[ingest] {os.path.basename(f)} -> split={split} rows={len(df)}")
        rows = []
        for _, r in df.iterrows():
            image = r["image"]
            img_bytes = image["bytes"]
            path = image.get("path")
            try:
                img = Image.open(io.BytesIO(img_bytes))
                width, height = img.size
                thumb = _make_thumbnail(img)
            except Exception:
                width = height = None
                thumb = None
            rows.append(
                (
                    split,
                    path,
                    *[r.get(c) for c in CAPTION_COLS],
                    width,
                    height,
                    img_bytes,
                    thumb,
                )
            )
        placeholders = ", ".join(["?"] * (2 + len(CAPTION_COLS) + 4))
        conn.executemany(
            f"INSERT INTO samples "
            f"(split, image_path, {', '.join(CAPTION_COLS)}, width, height, image, thumbnail) "
            f"VALUES ({placeholders})",
            rows,
        )
        conn.commit()
        total += len(rows)

    # Populate the FTS index from the base table.
    conn.execute(
        f"INSERT INTO samples_fts(rowid, {', '.join(CAPTION_COLS)}) "
        f"SELECT id, {', '.join(CAPTION_COLS)} FROM samples"
    )
    conn.commit()
    conn.close()
    print(f"[ingest] Done. Inserted {total} samples into {DB_PATH}")


if __name__ == "__main__":
    ingest()
