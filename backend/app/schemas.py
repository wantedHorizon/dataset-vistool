"""Pydantic response/request models."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .dataset_schema import (
    CreateDatasetRequest,
    CreateDatasetResponse,
    DatasetSchema,
    DatasetSummary,
    DownloadStatus,
    FieldDef,
    UpdateDatasetRequest,
)


class SampleRecord(BaseModel):
    id: int
    data: Dict[str, Any]


class SamplesPage(BaseModel):
    total: int
    page: int
    page_size: int
    rows: List[Dict[str, Any]]


class Stats(BaseModel):
    total: int
    splits: dict


class SqlRequest(BaseModel):
    query: str


class SqlResponse(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    row_count: int


class ActiveDatasetResponse(BaseModel):
    id: Optional[str]


class ReparseResponse(BaseModel):
    fields: List[FieldDef]
    warnings: List[str]
