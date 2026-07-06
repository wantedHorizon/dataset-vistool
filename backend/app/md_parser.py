"""Parse dataset README.md into suggested field definitions."""
import re
from typing import List, Optional, Tuple

from .dataset_schema import FieldDef, FieldType


def _expand_range(match: re.Match) -> List[str]:
    """Expand caption_0 … caption_4 style ranges."""
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


def _parse_image_dict(line: str) -> List[FieldDef]:
    """Parse `image`: `{ bytes, path }` patterns."""
    fields = []
    if re.search(r"\bpath\b", line, re.I):
        fields.append(
            FieldDef(
                name="image_path",
                source="image.path",
                type=FieldType.text,
                visible=True,
                searchable=False,
            )
        )
    if re.search(r"\bbytes\b", line, re.I):
        fields.append(
            FieldDef(
                name="image",
                source="image.bytes",
                type=FieldType.image,
                visible=True,
                searchable=False,
            )
        )
    return fields


def parse_readme(markdown: str) -> Tuple[List[FieldDef], List[str]]:
    """Return suggested fields and parser warnings."""
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
        if not stripped:
            continue

        # image dict pattern
        if "`image`" in stripped and ("bytes" in stripped or "path" in stripped):
            for f in _parse_image_dict(stripped):
                add_field(f)
            continue

        # range: `caption_0` … `caption_4`
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

        # single backtick field names
        for name in re.findall(r"`([a-zA-Z_][a-zA-Z0-9_]*)`", stripped):
            if name.lower() in ("bytes", "path", "train", "validation", "test"):
                continue
            ftype = FieldType.text
            searchable = False
            visible = True
            source = name

            if name == "image":
                add_field(
                    FieldDef(
                        name="image",
                        source="image.bytes",
                        type=FieldType.image,
                        visible=True,
                        searchable=False,
                    )
                )
                continue
            if name.startswith("caption"):
                searchable = True
            if name in ("width", "height") or name.endswith("_id"):
                ftype = FieldType.integer
                visible = False
            if name == "split":
                ftype = FieldType.split
                source = "_split"

            add_field(
                FieldDef(
                    name=name,
                    source=source,
                    type=ftype,
                    visible=visible,
                    searchable=searchable,
                )
            )

    # Auto-group caption_* fields into text_list display hint
    caption_fields = [f for f in fields if f.name.startswith("caption_")]
    if len(caption_fields) >= 2:
        for f in caption_fields:
            f.visible = False
        add_field(
            FieldDef(
                name="captions",
                source="captions",
                type=FieldType.text_list,
                visible=True,
                searchable=True,
                group_members=[f.name for f in caption_fields],
            )
        )

    # Ensure split field exists
    if not any(f.type == FieldType.split for f in fields):
        add_field(
            FieldDef(
                name="split",
                source="_split",
                type=FieldType.split,
                visible=True,
                searchable=False,
            )
        )

    # Ensure image fields if any caption-like content found
    if caption_fields and not any(f.type == FieldType.image for f in fields):
        warnings.append("No image field detected in README; add manually if needed.")

    if not fields:
        warnings.append("Could not parse fields from README; add them manually.")

    return fields, warnings
