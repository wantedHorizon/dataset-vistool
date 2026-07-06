"""Download HuggingFace datasets by URL."""
import os
import re
import threading
from typing import Optional, Tuple
from urllib.parse import urlparse

from huggingface_hub import hf_hub_download, list_repo_files

from .dataset_registry import (
    load_schema,
    save_schema,
    schema_path,
    slug_from_repo_id,
    source_dir,
    update_download_status,
)
from .dataset_schema import DatasetSchema, DownloadStatus, SourceConfig, SplitConfig
from .md_parser import parse_readme

HF_DATASET_RE = re.compile(
    r"huggingface\.co/datasets/(?P<repo>[^/\s?#]+/[^/\s?#]+)"
)


def parse_hf_url(url: str) -> str:
    """Extract repo_id (org/name) from a HuggingFace dataset URL."""
    match = HF_DATASET_RE.search(url)
    if match:
        return match.group("repo")
    parsed = urlparse(url.strip())
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and parts[0] == "datasets":
        return f"{parts[1]}/{parts[2]}" if len(parts) >= 3 else parts[1]
    raise ValueError(f"Not a valid HuggingFace dataset URL: {url}")


def _find_parquet_subdir(repo_id: str) -> str:
    """Return relative subdir containing parquet files, preferring data/."""
    files = list_repo_files(repo_id, repo_type="dataset")
    parquet_files = [f for f in files if f.endswith(".parquet")]
    if not parquet_files:
        raise ValueError(f"No parquet files found in dataset {repo_id}")
    data_parquet = [f for f in parquet_files if f.startswith("data/")]
    if data_parquet:
        return "data"
    # Use common parent directory of parquet files
    dirs = {f.rsplit("/", 1)[0] for f in parquet_files if "/" in f}
    if len(dirs) == 1:
        return dirs.pop()
    return ""


def start_download(url: str) -> str:
    """Create dataset entry and start background download. Returns dataset id."""
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
        download=DownloadStatus(status="downloading", progress="Starting…"),
    )
    save_schema(schema)

    thread = threading.Thread(
        target=_download_worker, args=(dataset_id, repo_id, dest), daemon=True
    )
    thread.start()
    return dataset_id


def _download_worker(dataset_id: str, repo_id: str, dest: str) -> None:
    try:
        update_download_status(dataset_id, "downloading", progress="Listing files…")
        files = list_repo_files(repo_id, repo_type="dataset")

        # Download README
        readme_name = next((f for f in files if f.upper().startswith("README")), None)
        if readme_name:
            update_download_status(
                dataset_id, "downloading", progress=f"Downloading {readme_name}…"
            )
            hf_hub_download(
                repo_id,
                filename=readme_name,
                repo_type="dataset",
                local_dir=dest,
                local_dir_use_symlinks=False,
            )
        else:
            update_download_status(
                dataset_id,
                "downloading",
                progress="No README found; will use parquet schema",
                message="README.md not found",
            )

        parquet_subdir = _find_parquet_subdir(repo_id)
        parquet_files = [f for f in files if f.endswith(".parquet")]
        if parquet_subdir:
            parquet_files = [
                f for f in parquet_files if f.startswith(f"{parquet_subdir}/")
            ]

        for i, pf in enumerate(parquet_files):
            update_download_status(
                dataset_id,
                "downloading",
                progress=f"Downloading {pf} ({i + 1}/{len(parquet_files)})…",
            )
            hf_hub_download(
                repo_id,
                filename=pf,
                repo_type="dataset",
                local_dir=dest,
                local_dir_use_symlinks=False,
            )

        # Update source path to parquet directory
        schema = load_schema(dataset_id)
        if parquet_subdir:
            schema.source.path = os.path.join(dest, parquet_subdir)
        else:
            schema.source.path = dest
        save_schema(schema)

        update_download_status(dataset_id, "parsing", progress="Parsing README…")
        _parse_and_save_schema(dataset_id, dest, readme_name)

        update_download_status(
            dataset_id, "ready", progress="Done", message="Schema draft created"
        )
    except Exception as e:
        update_download_status(dataset_id, "error", message=str(e))


def _parse_and_save_schema(
    dataset_id: str, dest: str, readme_name: Optional[str]
) -> None:
    schema = load_schema(dataset_id)
    readme_path = None
    if readme_name:
        readme_path = os.path.join(dest, readme_name)
    else:
        for candidate in ("README.md", "readme.md", "Readme.md"):
            p = os.path.join(dest, candidate)
            if os.path.exists(p):
                readme_path = p
                break

    if readme_path and os.path.exists(readme_path):
        with open(readme_path, encoding="utf-8") as f:
            markdown = f.read()
        fields, warnings = parse_readme(markdown)
        schema.fields = fields
        if warnings:
            schema.download.message = "; ".join(warnings)
    else:
        # Fallback: infer from first parquet file columns
        schema.fields = _infer_from_parquet(schema.source.path)
        schema.download.message = "Fields inferred from parquet (no README)"

    save_schema(schema)


def _infer_from_parquet(parquet_dir: str) -> list:
    import glob

    import pandas as pd

    from .dataset_schema import FieldDef, FieldType

    files = sorted(glob.glob(os.path.join(parquet_dir, "**", "*.parquet"), recursive=True))
    if not files:
        files = sorted(glob.glob(os.path.join(parquet_dir, "*.parquet")))
    if not files:
        return []
    df = pd.read_parquet(files[0], columns=None)
    fields = []
    for col in df.columns:
        if col == "image":
            fields.append(
                FieldDef(name="image_path", source="image.path", type=FieldType.text, visible=True)
            )
            fields.append(
                FieldDef(name="image", source="image.bytes", type=FieldType.image, visible=True)
            )
        else:
            fields.append(
                FieldDef(
                    name=col,
                    source=col,
                    type=FieldType.text,
                    visible=True,
                    searchable=col.startswith("caption"),
                )
            )
    fields.append(
        FieldDef(name="split", source="_split", type=FieldType.split, visible=True)
    )
    return fields
