"""Dataset registry: schema and metadata persistence."""
import json
import os
import re
import shutil
from typing import List, Optional

from app.config import DATA_ROOT, DATASETS_DIR, REGISTRY_PATH
from app.models.api import DatasetSummary
from app.models.dataset import (
    DatasetSchema,
    DownloadStatus,
    JobStatus,
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


def dataset_artifacts(dataset_id: str) -> List[str]:
    return [dataset_dir(dataset_id), db_path(dataset_id)]


def _remove_path(path: str) -> None:
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.isfile(path):
        os.remove(path)


def delete_dataset(dataset_id: str) -> None:
    reg = _registry_data()
    if dataset_id not in reg["datasets"]:
        raise KeyError(f"Dataset not found: {dataset_id}")
    reg["datasets"].remove(dataset_id)
    if reg["active_dataset_id"] == dataset_id:
        reg["active_dataset_id"] = reg["datasets"][0] if reg["datasets"] else None
    _save_registry(reg)
    for path in dataset_artifacts(dataset_id):
        _remove_path(path)


def drop_all_data() -> None:
    """Remove all explorer data: registry, datasets dir, legacy DB."""
    from app.config import LEGACY_DB_PATH

    reg = _registry_data()
    for dataset_id in list(reg.get("datasets", [])):
        for path in dataset_artifacts(dataset_id):
            _remove_path(path)

    if os.path.isdir(DATASETS_DIR):
        shutil.rmtree(DATASETS_DIR)

    if os.path.exists(LEGACY_DB_PATH):
        os.remove(LEGACY_DB_PATH)

    if os.path.exists(REGISTRY_PATH):
        os.remove(REGISTRY_PATH)

    os.makedirs(DATA_ROOT, exist_ok=True)


def update_download_status(
    dataset_id: str,
    status: str,
    progress: Optional[str] = None,
    message: Optional[str] = None,
    **extra,
) -> None:
    schema = load_schema(dataset_id)
    current = schema.download.model_dump()
    current.update(
        {
            "status": status,
            "progress": progress,
            "message": message,
            **extra,
        }
    )
    schema.download = DownloadStatus(**current)
    save_schema(schema)


def update_ingest_status(
    dataset_id: str, status: str, row_count: int = 0, message: Optional[str] = None
) -> None:
    schema = load_schema(dataset_id)
    schema.ingest = JobStatus(status=status, row_count=row_count, message=message)
    save_schema(schema)


def init_registry() -> None:
    from app.bootstrap.seed import seed_flickr8k_if_needed

    _ensure_dirs()
    seed_flickr8k_if_needed()
