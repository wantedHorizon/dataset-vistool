"""Parse dataset README.md — YAML frontmatter and prose fallback."""
import re
from typing import Any, Dict, List, Optional, Tuple

import yaml

from app.models.dataset import FieldDef, FieldType


def parse_yaml_frontmatter(markdown: str) -> Optional[Dict[str, Any]]:
    """Extract and parse YAML metadata block between --- markers."""
    match = re.match(r"^---\s*\n(.*?)\n---", markdown, re.DOTALL)
    if not match:
        return None
    try:
        data = yaml.safe_load(match.group(1))
        return data if isinstance(data, dict) else None
    except yaml.YAMLError:
        return None


def _expand_range(match: re.Match) -> List[str]:
    start = match.group(1)
    end = match.group(2)
    prefix_match = re.match(r"([a-zA-Z_]+?)(\d+)$", start)
    if not prefix_match:
        return [start, end]
    prefix, start_num = prefix_match.group(1), int(prefix_match.group(2))
    end_match = re.match(r"([a-zA-Z_]+?)(\d+)$", end)
    if not end_match or end_match.group(1) != prefix:
        return [start, end]
    end_num = int(end_match.group(2))
    return [f"{prefix}{i}" for i in range(start_num, end_num + 1)]


def parse_readme(markdown: str) -> Tuple[List[FieldDef], List[str]]:
    """Parse markdown prose for field hints (fallback when YAML/API unavailable)."""
    fields: List[FieldDef] = []
    warnings: List[str] = []
    seen_names: set[str] = set()

    def add_field(f: FieldDef) -> None:
        if f.name in seen_names:
            return
        seen_names.add(f.name)
        fields.append(f)

    lines = markdown.splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("---"):
            continue

        range_match = re.search(r"`([^`]+)`\s*[.…]+\s*`([^`]+)`", stripped)
        if range_match:
            for name in _expand_range(range_match):
                add_field(
                    FieldDef(
                        name=name,
                        source=name,
                        type=FieldType.text,
                        visible=True,
                        searchable=name.startswith("caption"),
                    )
                )
            continue

        for name in re.findall(r"`([a-zA-Z_][a-zA-Z0-9_]*)`", stripped):
            if name.lower() in ("bytes", "path", "train", "validation", "test"):
                continue
            if name == "image":
                add_field(
                    FieldDef(
                        name="image",
                        source="image.bytes",
                        type=FieldType.image,
                        visible=True,
                    )
                )
                continue
            ftype = FieldType.text
            searchable = name.startswith("caption")
            if name in ("width", "height") or name.endswith("_id"):
                ftype = FieldType.integer
            if name == "split":
                ftype = FieldType.split
            add_field(
                FieldDef(
                    name=name,
                    source="_split" if name == "split" else name,
                    type=ftype,
                    visible=ftype != FieldType.integer,
                    searchable=searchable,
                )
            )

    if not fields:
        warnings.append("Could not parse fields from README prose")

    return fields, warnings
