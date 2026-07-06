"""Pydantic response/request models."""
from typing import Any, List, Optional

from pydantic import BaseModel


class Sample(BaseModel):
    id: int
    split: str
    image_path: Optional[str]
    captions: List[str]
    width: Optional[int]
    height: Optional[int]
    image_url: str
    thumb_url: str


class SamplesPage(BaseModel):
    total: int
    page: int
    page_size: int
    rows: List[Sample]


class Stats(BaseModel):
    total: int
    splits: dict


class SqlRequest(BaseModel):
    query: str


class SqlResponse(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
