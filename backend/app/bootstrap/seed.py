"""One-time bootstrap: Flickr8k seeding and legacy DB migration."""
import os
import shutil
import sqlite3

from app.config import LEGACY_DB_PATH, LEGACY_PARQUET_DIR
from app.models.dataset import (
    DatasetSchema,
    DownloadStatus,
    FieldDef,
    JobStatus,
    SourceConfig,
    SplitConfig,
)
from app.services.registry import db_path, list_dataset_ids, save_schema


def flickr8k_default_fields() -> list[FieldDef]:
    from app.schema_extraction.card_mapper import extract_from_yaml_metadata, map_dataset_info
    from app.schema_extraction.md_parser import parse_yaml_frontmatter

    readme_path = os.path.join(os.path.dirname(LEGACY_PARQUET_DIR), "README.md")
    if not os.path.exists(readme_path):
        readme_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "datasets", "jxie-flickr8k", "README.md"
        )
    if os.path.exists(readme_path):
        with open(readme_path, encoding="utf-8") as f:
            metadata = parse_yaml_frontmatter(f.read())
        if metadata:
            result = extract_from_yaml_metadata(metadata)
            if result:
                return result.fields

    result = map_dataset_info(
        {
            "features": [
                {"name": "image", "dtype": "image"},
                *[{"name": f"caption_{i}", "dtype": "string"} for i in range(5)],
            ],
            "splits": [
                {"name": "train"},
                {"name": "validation"},
                {"name": "test"},
            ],
        }
    )
    return result.fields


def seed_flickr8k_if_needed() -> None:
    """Seed flickr8k dataset on first boot when registry is empty."""
    if list_dataset_ids():
        return

    dataset_id = "flickr8k"
    parquet_path = LEGACY_PARQUET_DIR
    if not os.path.isdir(parquet_path):
        return

    schema = DatasetSchema(
        id=dataset_id,
        name="Flickr8k",
        source_url="https://huggingface.co/datasets/jxie/flickr8k",
        source=SourceConfig(
            type="parquet",
            path=parquet_path,
            split=SplitConfig(strategy="filename_prefix"),
        ),
        fields=flickr8k_default_fields(),
        download=DownloadStatus(status="ready", message="Local parquet"),
        ingest=JobStatus(status="idle"),
    )
    save_schema(schema)

    new_db = db_path(dataset_id)
    if os.path.exists(LEGACY_DB_PATH) and not os.path.exists(new_db):
        os.makedirs(os.path.dirname(new_db), exist_ok=True)
        shutil.copy2(LEGACY_DB_PATH, new_db)
        schema.ingest = JobStatus(status="done", row_count=_count_rows(new_db))
        save_schema(schema)
    elif os.path.exists(new_db):
        schema.ingest = JobStatus(status="done", row_count=_count_rows(new_db))
        save_schema(schema)


def _count_rows(db: str) -> int:
    if not os.path.exists(db):
        return 0
    conn = sqlite3.connect(db)
    try:
        return conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
    except sqlite3.Error:
        return 0
    finally:
        conn.close()
