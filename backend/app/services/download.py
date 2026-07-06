"""Download HuggingFace datasets by URL."""
import glob
import os
import re
import threading
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from huggingface_hub import HfApi, hf_hub_download, snapshot_download

from app.models.dataset import DatasetSchema, DownloadStatus, SourceConfig, SplitConfig
from app.schema_extraction.card_mapper import extract_schema
from app.services.registry import (
    load_schema,
    save_schema,
    slug_from_repo_id,
    source_dir,
    update_download_status,
)

HF_DATASET_RE = re.compile(
    r"huggingface\.co/datasets/(?P<repo>[^/\s?#]+/[^/\s?#]+)"
)


def parse_hf_url(url: str) -> str:
    match = HF_DATASET_RE.search(url)
    if match:
        return match.group("repo")
    parsed = urlparse(url.strip())
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and parts[0] == "datasets":
        return f"{parts[1]}/{parts[2]}" if len(parts) >= 3 else parts[1]
    raise ValueError(f"Not a valid HuggingFace dataset URL: {url}")


def _find_parquet_subdir(repo_id: str, files: List[str]) -> str:
    parquet_files = [f for f in files if f.endswith(".parquet")]
    if not parquet_files:
        raise ValueError(f"No parquet files found in dataset {repo_id}")
    data_parquet = [f for f in parquet_files if f.startswith("data/")]
    if data_parquet:
        return "data"
    dirs = {f.rsplit("/", 1)[0] for f in parquet_files if "/" in f}
    if len(dirs) == 1:
        return dirs.pop()
    return ""


def _parquet_file_count(path: str) -> int:
    files = glob.glob(os.path.join(path, "**", "*.parquet"), recursive=True)
    if not files:
        files = glob.glob(os.path.join(path, "*.parquet"))
    return len(files)


def start_download(url: str) -> str:
    repo_id = parse_hf_url(url)
    dataset_id = slug_from_repo_id(repo_id)
    name = repo_id.split("/")[-1].replace("-", " ").title()

    dest = source_dir(dataset_id)
    os.makedirs(dest, exist_ok=True)

    schema = DatasetSchema(
        id=dataset_id,
        name=name,
        source_url=url.strip(),
        source=SourceConfig(
            type="parquet",
            path=dest,
            split=SplitConfig(strategy="filename_prefix"),
        ),
        fields=[],
        download=DownloadStatus(status="fetching_metadata", progress="Fetching metadata…"),
    )
    save_schema(schema)

    thread = threading.Thread(
        target=_download_worker, args=(dataset_id, repo_id, dest), daemon=True
    )
    thread.start()
    return dataset_id


def _apply_extract_result(dataset_id: str, result, parquet_subdir: str, dest: str) -> None:
    schema = load_schema(dataset_id)
    schema.fields = result.fields
    if result.split_values:
        schema.source.split.values = result.split_values
    if parquet_subdir:
        schema.source.path = os.path.join(dest, parquet_subdir)
    else:
        schema.source.path = dest
    if result.warnings:
        schema.download.message = "; ".join(result.warnings)
    save_schema(schema)


def _download_worker(dataset_id: str, repo_id: str, dest: str) -> None:
    try:
        api = HfApi()
        update_download_status(
            dataset_id,
            "fetching_metadata",
            progress="Fetching dataset card…",
            phase="metadata",
        )
        ds_info = api.dataset_info(repo_id, files_metadata=True)
        bytes_total = sum(
            s.size or 0 for s in (ds_info.siblings or []) if s.rfilename.endswith(".parquet")
        )
        parquet_files = [
            s for s in (ds_info.siblings or []) if s.rfilename.endswith(".parquet")
        ]
        parquet_subdir = _find_parquet_subdir(repo_id, [s.rfilename for s in parquet_files])

        update_download_status(
            dataset_id,
            "fetching_metadata",
            progress="Extracting schema from dataset card…",
            phase="schema",
            bytes_total=bytes_total,
            parquet_files_total=len(parquet_files),
        )
        extract_result = extract_schema(repo_id=repo_id)
        if not extract_result.fields:
            readme_name = next(
                (
                    s.rfilename
                    for s in (ds_info.siblings or [])
                    if s.rfilename.upper().startswith("README")
                ),
                None,
            )
            readme_md = None
            if readme_name:
                hf_hub_download(
                    repo_id,
                    filename=readme_name,
                    repo_type="dataset",
                    local_dir=dest,
                    local_dir_use_symlinks=False,
                )
                readme_path = os.path.join(dest, readme_name)
                if os.path.exists(readme_path):
                    with open(readme_path, encoding="utf-8") as f:
                        readme_md = f.read()
            extract_result = extract_schema(
                repo_id=repo_id,
                readme_markdown=readme_md,
                parquet_dir=None,
            )

        _apply_extract_result(dataset_id, extract_result, parquet_subdir, dest)
        update_download_status(
            dataset_id,
            "schema_ready",
            progress="Schema ready — downloading parquet files…",
            phase="parquet",
            schema_source=extract_result.schema_source,
            field_count=len(extract_result.fields),
            bytes_total=bytes_total,
            parquet_files_total=len(parquet_files),
            parquet_files_done=0,
        )

        update_download_status(
            dataset_id,
            "downloading",
            progress=f"Downloading {len(parquet_files)} parquet file(s)…",
            phase="parquet",
            schema_source=extract_result.schema_source,
            field_count=len(extract_result.fields),
            bytes_total=bytes_total,
            parquet_files_total=len(parquet_files),
        )
        snapshot_download(
            repo_id,
            repo_type="dataset",
            local_dir=dest,
            allow_patterns=["**/*.parquet"],
            local_dir_use_symlinks=False,
        )

        schema = load_schema(dataset_id)
        if parquet_subdir:
            schema.source.path = os.path.join(dest, parquet_subdir)
        save_schema(schema)

        done_count = _parquet_file_count(schema.source.path)
        update_download_status(
            dataset_id,
            "ready",
            progress="Done",
            message="Dataset ready for import",
            phase="done",
            schema_source=extract_result.schema_source,
            field_count=len(extract_result.fields),
            bytes_total=bytes_total,
            parquet_files_total=len(parquet_files),
            parquet_files_done=done_count,
        )
    except Exception as e:
        update_download_status(dataset_id, "error", message=str(e), phase="error")


def reparse_schema(dataset_id: str, repo_id: Optional[str] = None) -> Tuple:
    """Re-extract schema from stored README or API."""
    schema = load_schema(dataset_id)
    dest = source_dir(dataset_id)
    readme_md = None
    for candidate in ("README.md", "readme.md", "Readme.md"):
        p = os.path.join(dest, candidate)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                readme_md = f.read()
            break

    rid = repo_id
    if not rid and schema.source_url:
        try:
            rid = parse_hf_url(schema.source_url)
        except ValueError:
            pass

    parquet_dir = schema.source.path if os.path.isdir(schema.source.path) else None
    result = extract_schema(repo_id=rid, readme_markdown=readme_md, parquet_dir=parquet_dir)
    schema.fields = result.fields
    if result.split_values:
        schema.source.split.values = result.split_values
    save_schema(schema)
    return result.fields, result.warnings, result.schema_source
