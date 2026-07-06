"""Tests for drop → populate round-trip."""
import json

import pandas as pd
import pytest

from app.services import ingest as ingest_mod
from app.services import registry as reg
from app.services.registry import init_registry


@pytest.fixture
def isolated_data_root(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir()
    datasets_dir = data_root / "datasets"
    datasets_dir.mkdir()
    parquet_dir = tmp_path / "parquet"
    parquet_dir.mkdir()
    df = pd.DataFrame(
        {
            "image": [b"\xff\xd8\xff\xe0\x00\x10JFIF"],
            "caption_0": ["test caption 0"],
            "caption_1": ["test caption 1"],
            "caption_2": ["test caption 2"],
            "caption_3": ["test caption 3"],
            "caption_4": ["test caption 4"],
        }
    )
    df.to_parquet(parquet_dir / "train-00000.parquet", index=False)

    monkeypatch.setattr(reg, "DATA_ROOT", str(data_root))
    monkeypatch.setattr(reg, "REGISTRY_PATH", str(data_root / "registry.json"))
    monkeypatch.setattr(reg, "DATASETS_DIR", str(datasets_dir))
    monkeypatch.setattr("app.config.LEGACY_PARQUET_DIR", str(parquet_dir))
    monkeypatch.setattr("app.config.LEGACY_DB_PATH", str(data_root / "flickr8k.db"))
    return data_root, parquet_dir


def test_drop_recreates_datasets_dir(isolated_data_root):
    data_root, _ = isolated_data_root
    init_registry()
    assert (data_root / "registry.json").exists()

    reg.drop_all_data()

    assert not (data_root / "registry.json").exists()
    assert (data_root / "datasets").is_dir()
    assert reg.list_dataset_ids() == []


def test_drop_populate_round_trip(isolated_data_root):
    data_root, _ = isolated_data_root

    init_registry()
    ingest_mod.ingest_all_pending()
    assert "flickr8k" in reg.list_dataset_ids()

    reg.drop_all_data()
    assert reg.list_dataset_ids() == []
    assert (data_root / "datasets").is_dir()

    init_registry()
    ingest_mod.ingest_all_pending()

    assert "flickr8k" in reg.list_dataset_ids()
    schema = reg.load_schema("flickr8k")
    assert schema.ingest.status == "done"
    assert schema.ingest.row_count > 0

    db_file = data_root / "datasets" / "flickr8k.db"
    assert db_file.exists()

    reg_data = json.loads((data_root / "registry.json").read_text())
    assert reg_data["active_dataset_id"] == "flickr8k"
