"""Tests for YAML frontmatter parsing."""
from app.schema_extraction.md_parser import parse_readme, parse_yaml_frontmatter

FLICKR8K_YAML = """---
dataset_info:
  features:
  - name: image
    dtype: image
  - name: caption_0
    dtype: string
---
# body
"""


def test_parse_yaml_frontmatter():
    meta = parse_yaml_frontmatter(FLICKR8K_YAML)
    assert meta is not None
    assert "dataset_info" in meta


def test_parse_readme_prose_captions():
    md = "# Fields\nThe dataset has `caption_0` … `caption_4`.\n"
    fields, _warnings = parse_readme(md)
    names = {f.name for f in fields}
    assert "caption_0" in names
    assert "caption_4" in names


def test_parse_readme_prose_image():
    md = "Each row has an `image` field.\n"
    fields, _warnings = parse_readme(md)
    names = {f.name for f in fields}
    assert "image" in names
