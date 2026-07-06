"""Tests for dataset registry delete and drop."""
import json

import pytest

from app.services import registry as reg


@pytest.fixture
def isolated_data_root(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir()
    datasets_dir = data_root / "datasets"
    datasets_dir.mkdir()
    monkeypatch.setattr(reg, "DATA_ROOT", str(data_root))
    monkeypatch.setattr(reg, "REGISTRY_PATH", str(data_root / "registry.json"))
    monkeypatch.setattr(reg, "DATASETS_DIR", str(datasets_dir))
    return data_root


def _write_registry(data_root, datasets, active=None):
    path = data_root / "registry.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"datasets": datasets, "active_dataset_id": active}, f)


def test_delete_dataset_removes_all_artifacts(isolated_data_root):
    dataset_id = "test-ds"
    ddir = isolated_data_root / "datasets" / dataset_id
    ddir.mkdir()
    (ddir / "schema.json").write_text('{"id":"test-ds"}', encoding="utf-8")
    db_file = isolated_data_root / "datasets" / f"{dataset_id}.db"
    db_file.write_text("", encoding="utf-8")
    _write_registry(isolated_data_root, [dataset_id], dataset_id)

    reg.delete_dataset(dataset_id)

    assert not ddir.exists()
    assert not db_file.exists()
    remaining = json.loads((isolated_data_root / "registry.json").read_text())
    assert remaining["datasets"] == []
    assert remaining["active_dataset_id"] is None


def test_delete_dataset_updates_active_id(isolated_data_root):
    for did in ("a", "b"):
        ddir = isolated_data_root / "datasets" / did
        ddir.mkdir()
        (ddir / "schema.json").write_text("{}", encoding="utf-8")
    _write_registry(isolated_data_root, ["a", "b"], "a")

    reg.delete_dataset("a")

    remaining = json.loads((isolated_data_root / "registry.json").read_text())
    assert remaining["datasets"] == ["b"]
    assert remaining["active_dataset_id"] == "b"


def test_drop_all_data_clears_everything(isolated_data_root, monkeypatch):
    legacy = isolated_data_root / "flickr8k.db"
    monkeypatch.setattr("app.config.LEGACY_DB_PATH", str(legacy))

    dataset_id = "flickr8k"
    ddir = isolated_data_root / "datasets" / dataset_id
    ddir.mkdir()
    (ddir / "schema.json").write_text("{}", encoding="utf-8")
    db_file = isolated_data_root / "datasets" / f"{dataset_id}.db"
    db_file.write_text("", encoding="utf-8")
    legacy.write_text("", encoding="utf-8")
    _write_registry(isolated_data_root, [dataset_id], dataset_id)

    reg.drop_all_data()

    assert not (isolated_data_root / "registry.json").exists()
    assert (isolated_data_root / "datasets").is_dir()
    assert not legacy.exists()


def test_delete_unknown_dataset_raises(isolated_data_root):
    _write_registry(isolated_data_root, [], None)
    with pytest.raises(KeyError):
        reg.delete_dataset("missing")
