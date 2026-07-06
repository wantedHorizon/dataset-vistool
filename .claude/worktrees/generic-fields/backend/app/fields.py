"""Dataset field metadata loaded from fields.json.

fields.json (repo root) is the single source of truth for the dataset's
logical columns. The backend derives the SQLite schema, ingestion mapping,
FTS index, and API row shape from it, and re-exposes it to the frontend via
GET /api/fields so the table renders whatever columns are declared here.

Field semantics:
- source="passthrough": value(s) copied verbatim from the parquet column(s)
  named in source_columns (defaults to [key]) — zero code to add/remove.
- source="derived": value produced by dataset-specific extraction code in
  ingest.py (image decoding, filename parsing); the key must be handled there.
- type="string_list": N physical TEXT columns (source_columns) collapse into
  one logical list-valued field in API responses.
"""
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional, Tuple

FIELDS_PATH = os.path.abspath(
    os.environ.get(
        "FIELDS_PATH",
        os.path.join(os.path.dirname(__file__), "..", "..", "fields.json"),
    )
)


@dataclass(frozen=True)
class DatasetMeta:
    name: str
    title: str


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    type: str  # "string" | "integer" | "string_list"
    source: str  # "derived" | "passthrough"
    visible: bool = True
    searchable: bool = False
    role: Optional[str] = None  # "name" | "split"
    source_columns: Optional[Tuple[str, ...]] = None

    @property
    def columns(self) -> List[str]:
        """Physical SQLite column name(s) backing this logical field."""
        return list(self.source_columns) if self.source_columns else [self.key]

    @property
    def sql_type(self) -> str:
        return "INTEGER" if self.type == "integer" else "TEXT"


@lru_cache(maxsize=1)
def _load() -> Tuple[DatasetMeta, Tuple[Field, ...]]:
    with open(FIELDS_PATH) as f:
        raw = json.load(f)
    dataset = DatasetMeta(**raw["dataset"])
    fields = tuple(
        Field(**{**spec, "source_columns": tuple(spec["source_columns"])})
        if "source_columns" in spec
        else Field(**spec)
        for spec in raw["fields"]
    )
    return dataset, fields


def load_dataset() -> DatasetMeta:
    return _load()[0]


def load_fields() -> Tuple[Field, ...]:
    return _load()[1]


def all_columns() -> List[str]:
    """Every physical data column, in declaration order."""
    return [c for f in load_fields() for c in f.columns]


def searchable_columns() -> List[str]:
    """Physical columns included in the FTS index."""
    return [c for f in load_fields() if f.searchable for c in f.columns]


def name_field() -> Optional[Field]:
    return next((f for f in load_fields() if f.role == "name"), None)
