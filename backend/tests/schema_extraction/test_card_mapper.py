"""Tests for HF dataset card → schema mapping."""
import os

import pytest

from app.models.dataset import FieldType
from app.schema_extraction.card_mapper import (
    extract_from_yaml_metadata,
    extract_schema,
    map_dataset_info,
)
from app.schema_extraction.md_parser import parse_yaml_frontmatter

FLICKR8K_README = """---
dataset_info:
  features:
  - name: image
    dtype: image
  - name: caption_0
    dtype: string
  - name: caption_1
    dtype: string
  - name: caption_2
    dtype: string
  - name: caption_3
    dtype: string
  - name: caption_4
    dtype: string
  splits:
  - name: train
  - name: validation
  - name: test
---
# Flickr8k
"""

FLICKR8K_DATASET_INFO = {
    "features": [
        {"name": "image", "dtype": "image"},
        *[{"name": f"caption_{i}", "dtype": "string"} for i in range(5)],
    ],
    "splits": [{"name": "train"}, {"name": "validation"}, {"name": "test"}],
}


def test_map_dataset_info_flickr8k():
    result = map_dataset_info(FLICKR8K_DATASET_INFO)
    names = {f.name for f in result.fields}
    assert "image" in names
    assert "captions" in names
    assert result.split_values == ["train", "validation", "test"]


def test_extract_from_yaml_metadata():
    meta = parse_yaml_frontmatter(FLICKR8K_README)
    assert meta is not None
    result = extract_from_yaml_metadata(meta)
    assert result is not None
    assert result.schema_source == "yaml"
    assert any(f.type == FieldType.image for f in result.fields)


def test_extract_schema_from_readme_yaml():
    result = extract_schema(readme_markdown=FLICKR8K_README)
    assert result.fields
    assert result.schema_source in ("yaml", "prose", "api")


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "datasets",
            "jxie-flickr8k",
            "README.md",
        )
    ),
    reason="Flickr8k README not present",
)
def test_extract_schema_from_local_readme_file():
    readme_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "datasets",
        "jxie-flickr8k",
        "README.md",
    )
    with open(readme_path, encoding="utf-8") as f:
        md = f.read()
    result = extract_schema(readme_markdown=md)
    assert len(result.fields) >= 5
    assert any(f.type == FieldType.image for f in result.fields)
