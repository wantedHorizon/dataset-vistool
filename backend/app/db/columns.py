"""Canonical schema → SQLite column derivation (shared by ingest and queries)."""
from typing import List

from app.models.dataset import DatasetSchema, FieldType


def db_columns(schema: DatasetSchema) -> List[str]:
    """SQLite column names for the samples table (no id)."""
    cols = ["split"]
    for f in schema.fields:
        if f.type == FieldType.split:
            continue
        if f.type == FieldType.text_list:
            if f.group_members:
                cols.extend(f.group_members)
            continue
        if f.type == FieldType.image:
            cols.append(f.name)
            for extra in ("width", "height", "thumbnail"):
                if extra not in cols:
                    cols.append(extra)
            continue
        if f.type != FieldType.blob:
            cols.append(f.name)
    return _dedupe(cols)


def fts_columns(schema: DatasetSchema) -> List[str]:
    """FTS5-indexed column names."""
    cols: List[str] = []
    for f in schema.fields:
        if f.type == FieldType.text_list and f.group_members:
            cols.extend(m for m in f.group_members if _is_searchable_member(schema, m))
        elif f.searchable and f.type not in (
            FieldType.split,
            FieldType.image,
            FieldType.blob,
        ):
            cols.append(f.name)
    return _dedupe(cols)


def select_columns(schema: DatasetSchema) -> List[str]:
    """Qualified SELECT columns for sample list queries."""
    cols = ["samples.id", "samples.split"]
    for f in schema.fields:
        if f.type == FieldType.split:
            continue
        if f.type == FieldType.text_list and f.group_members:
            cols.extend(f"samples.{m}" for m in f.group_members)
        elif f.type == FieldType.image:
            cols.append(f"samples.{f.name}")
            cols.extend(["samples.width", "samples.height"])
        elif f.type != FieldType.blob:
            cols.append(f"samples.{f.name}")
    return _dedupe(cols)


def _is_searchable_member(schema: DatasetSchema, name: str) -> bool:
    for f in schema.fields:
        if f.name == name:
            return f.searchable
        if f.group_members and name in f.group_members:
            return f.searchable
    return False


def _dedupe(cols: List[str]) -> List[str]:
    seen: set[str] = set()
    return [c for c in cols if not (c in seen or seen.add(c))]
