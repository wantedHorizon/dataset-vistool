"""Dataset registry: API-backed storage for schemas and metadata."""
import json
import os
import re
import shutil
from typing import List, Optional

from .dataset_schema import (
    DatasetSchema,
    DatasetSummary,
    DownloadStatus,
    FieldDef,
    FieldType,
    JobStatus,
    SourceConfig,
    SplitConfig,
)

DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
REGISTRY_PATH = os.path.join(DATA_ROOT, "registry.json")
DATASETS_DIR = os.path.join(DATA_ROOT, "datasets")

# Legacy paths for migration
LEGACY_DB_PATH = os.path.abspath(
    os.environ.get(
        "DB_PATH",
        os.path.join(os.path.dirname(__file__), "..", "data", "flickr8k.db"),
    )
)
LEGACY_PARQUET_DIR = os.path.abspath(
    os.environ.get(
        "PARQUET_DIR",
        os.path.join(
            os.path.dirname(__file__), "..", "..", "datasets", "jxie-flickr8k", "data"
        ),
    )
)


def _ensure_dirs() -> None:
    os.makedirs(DATASETS_DIR, exist_ok=True)


def _registry_data() -> dict:
    if not os.path.exists(REGISTRY_PATH):
        return {"datasets": [], "active_dataset_id": None}
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_registry(data: dict) -> None:
    _ensure_dirs()
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def dataset_dir(dataset_id: str) -> str:
    return os.path.join(DATASETS_DIR, dataset_id)


def schema_path(dataset_id: str) -> str:
    return os.path.join(dataset_dir(dataset_id), "schema.json")


def source_dir(dataset_id: str) -> str:
    return os.path.join(dataset_dir(dataset_id), "source")


def db_path(dataset_id: str) -> str:
    return os.path.join(DATA_ROOT, "datasets", f"{dataset_id}.db")


def slug_from_repo_id(repo_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", repo_id).strip("-").lower()


def load_schema(dataset_id: str) -> DatasetSchema:
    path = schema_path(dataset_id)
    if not os.path.exists(path):
        raise KeyError(f"Dataset not found: {dataset_id}")
    with open(path, encoding="utf-8") as f:
        return DatasetSchema.model_validate(json.load(f))


def save_schema(schema: DatasetSchema) -> None:
    _ensure_dirs()
    os.makedirs(dataset_dir(schema.id), exist_ok=True)
    with open(schema_path(schema.id), "w", encoding="utf-8") as f:
        json.dump(schema.model_dump(), f, indent=2)
    reg = _registry_data()
    if schema.id not in reg["datasets"]:
        reg["datasets"].append(schema.id)
        if reg["active_dataset_id"] is None:
            reg["active_dataset_id"] = schema.id
        _save_registry(reg)


def list_dataset_ids() -> List[str]:
    return _registry_data()["datasets"]


def list_summaries() -> List[DatasetSummary]:
    summaries = []
    for did in list_dataset_ids():
        try:
            s = load_schema(did)
            summaries.append(
                DatasetSummary(
                    id=s.id,
                    name=s.name,
                    source_url=s.source_url,
                    download_status=s.download.status,
                    ingest_status=s.ingest.status,
                    row_count=s.ingest.row_count,
                )
            )
        except (KeyError, json.JSONDecodeError):
            continue
    return summaries


def get_active_dataset_id() -> Optional[str]:
    reg = _registry_data()
    active = reg.get("active_dataset_id")
    if active and active in reg["datasets"]:
        return active
    if reg["datasets"]:
        return reg["datasets"][0]
    return None


def set_active_dataset_id(dataset_id: str) -> None:
    reg = _registry_data()
    if dataset_id not in reg["datasets"]:
        raise KeyError(f"Dataset not found: {dataset_id}")
    reg["active_dataset_id"] = dataset_id
    _save_registry(reg)


def delete_dataset(dataset_id: str) -> None:
    reg = _registry_data()
    if dataset_id not in reg["datasets"]:
        raise KeyError(f"Dataset not found: {dataset_id}")
    reg["datasets"].remove(dataset_id)
    if reg["active_dataset_id"] == dataset_id:
        reg["active_dataset_id"] = reg["datasets"][0] if reg["datasets"] else None
    _save_registry(reg)
    ddir = dataset_dir(dataset_id)
    if os.path.isdir(ddir):
        shutil.rmtree(ddir)
    db = db_path(dataset_id)
    if os.path.exists(db):
        os.remove(db)


def update_download_status(
    dataset_id: str, status: str, progress: Optional[str] = None, message: Optional[str] = None
) -> None:
    schema = load_schema(dataset_id)
    schema.download = DownloadStatus(status=status, progress=progress, message=message)
    save_schema(schema)


def update_ingest_status(
    dataset_id: str, status: str, row_count: int = 0, message: Optional[str] = None
) -> None:
    schema = load_schema(dataset_id)
    schema.ingest = JobStatus(status=status, row_count=row_count, message=message)
    save_schema(schema)


def flickr8k_default_fields() -> List[FieldDef]:
    caption_members = [f"caption_{i}" for i in range(5)]
    fields = [
        FieldDef(
            name="image_path",
            source="image.path",
            type=FieldType.text,
            visible=True,
            searchable=False,
        ),
        *[
            FieldDef(
                name=name,
                source=name,
                type=FieldType.text,
                visible=False,
                searchable=True,
            )
            for name in caption_members
        ],
        FieldDef(
            name="captions",
            source="captions",
            type=FieldType.text_list,
            visible=True,
            searchable=True,
            group_members=caption_members,
        ),
        FieldDef(
            name="image",
            source="image.bytes",
            type=FieldType.image,
            visible=True,
            searchable=False,
        ),
        FieldDef(
            name="split",
            source="_split",
            type=FieldType.split,
            visible=True,
            searchable=False,
        ),
    ]
    return fields


def seed_flickr8k_if_needed() -> None:
    """Seed flickr8k dataset on first boot when registry is empty."""
    _ensure_dirs()
    reg = _registry_data()
    if reg["datasets"]:
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

    # Migrate legacy DB if present
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
    import sqlite3

    if not os.path.exists(db):
        return 0
    conn = sqlite3.connect(db)
    try:
        return conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


def init_registry() -> None:
    _ensure_dirs()
    seed_flickr8k_if_needed()
