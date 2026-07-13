"""API request/response DTOs."""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from .dataset import FieldDef


class DownloadMode(str, Enum):
    ids = "ids"
    all = "all"
    range = "range"


class DownloadRequest(BaseModel):
    mode: DownloadMode
    split: Optional[str] = None
    search: Optional[str] = None
    ids: Optional[List[int]] = None
    offset: Optional[int] = Field(None, ge=0)
    limit: Optional[int] = Field(None, ge=1)
    exclude_ids: Optional[List[int]] = None

    @model_validator(mode="after")
    def validate_mode_fields(self) -> "DownloadRequest":
        if self.mode == DownloadMode.all:
            if self.ids is not None:
                raise ValueError("ids must not be set when mode is 'all'")
            if self.offset is not None or self.limit is not None:
                raise ValueError("offset and limit must not be set when mode is 'all'")
        elif self.mode == DownloadMode.range:
            if self.ids is not None:
                raise ValueError("ids must not be set when mode is 'range'")
            if self.offset is None or self.limit is None:
                raise ValueError("offset and limit are required when mode is 'range'")
        elif self.mode == DownloadMode.ids:
            if not self.ids:
                raise ValueError("ids is required and must be non-empty when mode is 'ids'")
            if self.offset is not None or self.limit is not None:
                raise ValueError("offset and limit must not be set when mode is 'ids'")
            if self.exclude_ids is not None:
                raise ValueError("exclude_ids must not be set when mode is 'ids'")
        return self


class DatasetSummary(BaseModel):
    id: str
    name: str
    source_url: Optional[str] = None
    download_status: str
    ingest_status: str
    row_count: int = 0


class CreateDatasetRequest(BaseModel):
    url: str


class CreateDatasetResponse(BaseModel):
    id: str
    status: str


class UpdateDatasetRequest(BaseModel):
    name: Optional[str] = None
    fields: Optional[List[FieldDef]] = None


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
    schema_source: Optional[str] = None
