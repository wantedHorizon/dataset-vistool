"""Map HuggingFace dataset card metadata to app field definitions."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.models.dataset import FieldDef, FieldType

SEARCHABLE_NAME_RE = (
    "caption",
    "text",
    "question",
    "answer",
    "title",
    "description",
    "label",
    "prompt",
)


@dataclass
class ExtractResult:
    fields: List[FieldDef]
    split_values: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    source: str = "unknown"
    schema_source: Optional[str] = None


def _is_searchable_name(name: str) -> bool:
    lower = name.lower()
    return any(token in lower for token in SEARCHABLE_NAME_RE)


def _normalize_dataset_info(card_data: Any) -> Optional[Dict[str, Any]]:
    """Extract dataset_info dict from card_data (dict, DatasetCardData, or list)."""
    if card_data is None:
        return None
    if hasattr(card_data, "get"):
        info = card_data.get("dataset_info")
    elif hasattr(card_data, "to_dict"):
        info = card_data.to_dict().get("dataset_info")
    else:
        return None
    if info is None:
        return None
    if isinstance(info, list):
        if not info:
            return None
        return info[0]
    return info


def _map_dtype(name: str, dtype: str, feature: Dict[str, Any]) -> List[FieldDef]:
    """Map a single HF feature entry to one or more FieldDef objects."""
    dtype = (dtype or "string").lower()
    fields: List[FieldDef] = []

    if dtype == "image":
        path_name = "image_path" if name == "image" else f"{name}_path"
        fields.append(
            FieldDef(
                name=path_name,
                source=f"{name}.path",
                type=FieldType.text,
                visible=True,
                searchable=False,
            )
        )
        fields.append(
            FieldDef(
                name=name,
                source=f"{name}.bytes",
                type=FieldType.image,
                visible=True,
                searchable=False,
            )
        )
        return fields

    if dtype == "sequence":
        members = feature.get("sequence") or []
        member_names = [m.get("name") for m in members if m.get("name")]
        if member_names:
            fields.append(
                FieldDef(
                    name=name,
                    source=name,
                    type=FieldType.text_list,
                    visible=True,
                    searchable=True,
                    group_members=member_names,
                )
            )
            for m in member_names:
                fields.append(
                    FieldDef(
                        name=m,
                        source=m,
                        type=FieldType.text,
                        visible=False,
                        searchable=True,
                    )
                )
        return fields

    if dtype in ("int32", "int64", "float32", "float64"):
        fields.append(
            FieldDef(
                name=name,
                source=name,
                type=FieldType.integer,
                visible=False,
                searchable=False,
            )
        )
        return fields

    if dtype in ("audio", "video", "binary"):
        fields.append(
            FieldDef(
                name=name,
                source=name,
                type=FieldType.blob,
                visible=False,
                searchable=False,
            )
        )
        return fields

    # string, bool, and unknown dtypes
    searchable = _is_searchable_name(name)
    fields.append(
        FieldDef(
            name=name,
            source=name,
            type=FieldType.text,
            visible=True,
            searchable=searchable,
        )
    )
    return fields


def map_dataset_info(dataset_info: Dict[str, Any]) -> ExtractResult:
    """Map HF dataset_info block to FieldDef list and split values."""
    warnings: List[str] = []
    fields: List[FieldDef] = []
    seen: set[str] = set()

    for feat in dataset_info.get("features") or []:
        name = feat.get("name")
        if not name:
            continue
        for f in _map_dtype(name, feat.get("dtype", "string"), feat):
            if f.name not in seen:
                seen.add(f.name)
                fields.append(f)

    split_values = [s["name"] for s in (dataset_info.get("splits") or []) if s.get("name")]

    result = _post_process(fields, split_values, warnings)
    result.source = "card"
    return result


def _post_process(
    fields: List[FieldDef], split_values: List[str], warnings: List[str]
) -> ExtractResult:
    """Group captions, ensure split field, dedupe."""
    caption_fields = [f for f in fields if f.name.startswith("caption_")]
    has_captions_group = any(f.name == "captions" for f in fields)

    if len(caption_fields) >= 2 and not has_captions_group:
        for f in caption_fields:
            f.visible = False
        fields.append(
            FieldDef(
                name="captions",
                source="captions",
                type=FieldType.text_list,
                visible=True,
                searchable=True,
                group_members=[f.name for f in caption_fields],
            )
        )

    if not any(f.type == FieldType.split for f in fields):
        fields.append(
            FieldDef(
                name="split",
                source="_split",
                type=FieldType.split,
                visible=True,
                searchable=False,
            )
        )

    if not any(f.type == FieldType.image for f in fields) and caption_fields:
        warnings.append("No image field detected; add manually if needed.")

    return ExtractResult(fields=fields, split_values=split_values, warnings=warnings)


def extract_from_card_data(card_data: Any) -> Optional[ExtractResult]:
    info = _normalize_dataset_info(card_data)
    if not info or not info.get("features"):
        return None
    result = map_dataset_info(info)
    result.schema_source = "api"
    return result


def extract_from_yaml_metadata(metadata: Dict[str, Any]) -> Optional[ExtractResult]:
    info = _normalize_dataset_info(metadata)
    if not info or not info.get("features"):
        return None
    result = map_dataset_info(info)
    result.schema_source = "yaml"
    return result


def extract_from_api(repo_id: str) -> Optional[ExtractResult]:
    """Fetch dataset card via HfApi (no file download)."""
    try:
        from huggingface_hub import HfApi

        api = HfApi()
        info = api.dataset_info(repo_id)
        return extract_from_card_data(info.card_data)
    except Exception:
        return None


def infer_from_parquet(parquet_dir: str) -> ExtractResult:
    import glob
    import os

    import pandas as pd

    files = sorted(glob.glob(os.path.join(parquet_dir, "**", "*.parquet"), recursive=True))
    if not files:
        files = sorted(glob.glob(os.path.join(parquet_dir, "*.parquet")))
    if not files:
        return ExtractResult(fields=[], warnings=["No parquet files found"], source="parquet")

    df = pd.read_parquet(files[0])
    fields: List[FieldDef] = []
    for col in df.columns:
        if col == "image":
            fields.append(
                FieldDef(
                    name="image_path", source="image.path", type=FieldType.text, visible=True
                )
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
                    searchable=_is_searchable_name(col),
                )
            )

    result = _post_process(fields, [], [])
    result.source = "parquet"
    result.schema_source = "parquet"
    return result


def extract_schema(
    repo_id: Optional[str] = None,
    readme_markdown: Optional[str] = None,
    parquet_dir: Optional[str] = None,
) -> ExtractResult:
    """Try extraction sources in priority order: API, YAML, prose, parquet."""
    from app.schema_extraction.md_parser import parse_readme, parse_yaml_frontmatter

    if repo_id:
        api_result = extract_from_api(repo_id)
        if api_result and api_result.fields:
            return api_result

    if readme_markdown:
        metadata = parse_yaml_frontmatter(readme_markdown)
        if metadata:
            yaml_result = extract_from_yaml_metadata(metadata)
            if yaml_result and yaml_result.fields:
                return yaml_result

        prose_fields, warnings = parse_readme(readme_markdown)
        if prose_fields and len(prose_fields) > 1:
            split_values: List[str] = []
            result = _post_process(prose_fields, split_values, warnings)
            result.source = "prose"
            result.schema_source = "prose"
            return result

    if parquet_dir:
        return infer_from_parquet(parquet_dir)

    return ExtractResult(
        fields=[],
        warnings=["Could not extract schema from any source"],
        source="unknown",
    )
