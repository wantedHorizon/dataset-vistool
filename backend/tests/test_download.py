"""Tests for POST /api/datasets/{id}/download (modes ids|all|range)."""
from __future__ import annotations

import io
import json
import zipfile

import pytest
import sqlite3
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.dataset import (
    DatasetSchema,
    FieldDef,
    FieldType,
    JobStatus,
    SourceConfig,
)
from app.services import registry as reg
from app.services.ingest import create_schema
from app.api import samples as samples_api

JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00"


def _schema_with_image(dataset_id: str = "testds") -> DatasetSchema:
    return DatasetSchema(
        id=dataset_id,
        name="Test",
        source=SourceConfig(type="parquet", path="/tmp"),
        fields=[
            FieldDef(name="image", source="image.bytes", type=FieldType.image, visible=True),
            FieldDef(
                name="caption",
                source="caption",
                type=FieldType.text,
                visible=True,
                searchable=True,
            ),
            FieldDef(name="split", source="_split", type=FieldType.split, visible=True),
        ],
        ingest=JobStatus(status="done", row_count=0),
    )


def _schema_no_image(dataset_id: str = "noimg") -> DatasetSchema:
    return DatasetSchema(
        id=dataset_id,
        name="NoImage",
        source=SourceConfig(type="parquet", path="/tmp"),
        fields=[
            FieldDef(
                name="caption",
                source="caption",
                type=FieldType.text,
                visible=True,
                searchable=True,
            ),
            FieldDef(name="split", source="_split", type=FieldType.split, visible=True),
        ],
        ingest=JobStatus(status="done", row_count=0),
    )


def _populate(dataset_id: str, schema: DatasetSchema, rows: list[tuple]) -> None:
    """rows: (split, caption, image_bytes|None)"""
    reg.save_schema(schema)
    path = reg.db_path(dataset_id)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        create_schema(conn, schema)
        has_image = any(f.type == FieldType.image for f in schema.fields)
        for split, caption, image in rows:
            if has_image:
                conn.execute(
                    "INSERT INTO samples (split, caption, image, width, height, thumbnail) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (split, caption, image, 10, 10, image),
                )
            else:
                conn.execute(
                    "INSERT INTO samples (split, caption) VALUES (?, ?)",
                    (split, caption),
                )
        conn.execute("INSERT INTO samples_fts(samples_fts) VALUES('rebuild')")
        conn.commit()
        schema.ingest = JobStatus(status="done", row_count=len(rows))
        reg.save_schema(schema)
    finally:
        conn.close()


@pytest.fixture
def download_env(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir()
    datasets_dir = data_root / "datasets"
    datasets_dir.mkdir()

    monkeypatch.setattr(reg, "DATA_ROOT", str(data_root))
    monkeypatch.setattr(reg, "REGISTRY_PATH", str(data_root / "registry.json"))
    monkeypatch.setattr(reg, "DATASETS_DIR", str(datasets_dir))
    monkeypatch.setattr("app.config.DATA_ROOT", str(data_root))
    monkeypatch.setattr("app.config.DATASETS_DIR", str(datasets_dir))
    monkeypatch.setattr("app.config.REGISTRY_PATH", str(data_root / "registry.json"))

    schema = _schema_with_image("testds")
    _populate(
        "testds",
        schema,
        [
            ("train", "a dog running", JPEG),
            ("train", "a cat sleeping", JPEG),
            ("test", "dog at beach", JPEG),
            ("test", "bird flying", JPEG),
            ("train", "two dogs play", JPEG),
        ],
    )

    app = FastAPI()
    app.include_router(samples_api.router)
    client = TestClient(app)
    return client, "testds"


def _zip_meta(content: bytes) -> list[dict]:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        assert "metadata.jsonl" in zf.namelist()
        lines = zf.read("metadata.jsonl").decode().strip().splitlines()
        return [json.loads(line) for line in lines if line]


def _zip_names(content: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        return zf.namelist()


# --- validation ---


def test_all_rejects_ids(download_env):
    client, did = download_env
    r = client.post(
        f"/api/datasets/{did}/download",
        json={"mode": "all", "ids": [1]},
    )
    assert r.status_code == 422


def test_all_rejects_offset(download_env):
    client, did = download_env
    r = client.post(
        f"/api/datasets/{did}/download",
        json={"mode": "all", "offset": 0, "limit": 1},
    )
    assert r.status_code == 422


def test_range_requires_window(download_env):
    client, did = download_env
    r = client.post(
        f"/api/datasets/{did}/download",
        json={"mode": "range", "search": "dog"},
    )
    assert r.status_code == 422


def test_ids_requires_ids(download_env):
    client, did = download_env
    r = client.post(
        f"/api/datasets/{did}/download",
        json={"mode": "ids"},
    )
    assert r.status_code == 422


def test_ids_rejects_exclude_ids(download_env):
    client, did = download_env
    r = client.post(
        f"/api/datasets/{did}/download",
        json={"mode": "ids", "ids": [1], "exclude_ids": [2]},
    )
    assert r.status_code == 422


# --- behavior ---


def test_all_with_search(download_env):
    client, did = download_env
    r = client.post(
        f"/api/datasets/{did}/download",
        json={"mode": "all", "search": "dog"},
    )
    assert r.status_code == 200
    meta = _zip_meta(r.content)
    ids = [m["id"] for m in meta]
    assert ids == [1, 3, 5]
    names = _zip_names(r.content)
    assert "images/1.jpg" in names
    assert all(m.get("image_file") for m in meta)


def test_all_with_split(download_env):
    client, did = download_env
    r = client.post(
        f"/api/datasets/{did}/download",
        json={"mode": "all", "split": "test"},
    )
    assert r.status_code == 200
    meta = _zip_meta(r.content)
    assert [m["id"] for m in meta] == [3, 4]
    assert all(m["split"] == "test" for m in meta)


def test_range_slice_matches_browse_order(download_env):
    client, did = download_env
    browse = client.get(
        f"/api/datasets/{did}/samples",
        params={"search": "dog", "page": 0, "page_size": 100},
    )
    assert browse.status_code == 200
    browse_ids = [row["id"] for row in browse.json()["rows"]]

    r = client.post(
        f"/api/datasets/{did}/download",
        json={"mode": "range", "search": "dog", "offset": 1, "limit": 2},
    )
    assert r.status_code == 200
    meta = _zip_meta(r.content)
    assert [m["id"] for m in meta] == browse_ids[1:3]


def test_all_exclude_ids(download_env):
    client, did = download_env
    r = client.post(
        f"/api/datasets/{did}/download",
        json={"mode": "all", "search": "dog", "exclude_ids": [3]},
    )
    assert r.status_code == 200
    meta = _zip_meta(r.content)
    assert [m["id"] for m in meta] == [1, 5]


def test_ids_with_search_drops_stale(download_env):
    client, did = download_env
    # id 2 is "cat", outside search "dog"
    r = client.post(
        f"/api/datasets/{did}/download",
        json={"mode": "ids", "ids": [1, 2, 3], "search": "dog"},
    )
    assert r.status_code == 200
    meta = _zip_meta(r.content)
    assert [m["id"] for m in meta] == [1, 3]


def test_unknown_dataset_404(download_env):
    client, _ = download_env
    r = client.post(
        "/api/datasets/missing/download",
        json={"mode": "all"},
    )
    assert r.status_code == 404


def test_over_limit_413(download_env, monkeypatch):
    client, did = download_env
    monkeypatch.setattr("app.services.download_zip.MAX_DOWNLOAD_ROWS", 2)
    r = client.post(
        f"/api/datasets/{did}/download",
        json={"mode": "all", "search": "dog"},
    )
    assert r.status_code == 413
    assert "detail" in r.json()


def test_no_image_schema_jsonl_only(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir()
    datasets_dir = data_root / "datasets"
    datasets_dir.mkdir()
    monkeypatch.setattr(reg, "DATA_ROOT", str(data_root))
    monkeypatch.setattr(reg, "REGISTRY_PATH", str(data_root / "registry.json"))
    monkeypatch.setattr(reg, "DATASETS_DIR", str(datasets_dir))

    schema = _schema_no_image("noimg")
    _populate(
        "noimg",
        schema,
        [
            ("train", "hello world", None),
            ("train", "other text", None),
        ],
    )
    app = FastAPI()
    app.include_router(samples_api.router)
    client = TestClient(app)

    r = client.post(
        "/api/datasets/noimg/download",
        json={"mode": "all"},
    )
    assert r.status_code == 200
    names = _zip_names(r.content)
    assert names == ["metadata.jsonl"]
    meta = _zip_meta(r.content)
    assert len(meta) == 2
    assert all("image_file" not in m for m in meta)
