"""Tests for canonical schema → column derivation."""
from app.db.columns import db_columns, fts_columns, select_columns
from app.models.dataset import DatasetSchema, FieldDef, FieldType, SourceConfig


def _flickr8k_schema() -> DatasetSchema:
    captions = [f"caption_{i}" for i in range(5)]
    fields = [
        FieldDef(name="image", source="image.bytes", type=FieldType.image, visible=True),
        FieldDef(
            name="captions",
            source="captions",
            type=FieldType.text_list,
            visible=True,
            searchable=True,
            group_members=captions,
        ),
        *[
            FieldDef(
                name=c,
                source=c,
                type=FieldType.text,
                visible=False,
                searchable=True,
            )
            for c in captions
        ],
        FieldDef(name="split", source="_split", type=FieldType.split, visible=True),
    ]
    return DatasetSchema(
        id="flickr8k",
        name="Flickr8k",
        source=SourceConfig(type="parquet", path="/tmp"),
        fields=fields,
    )


def test_db_columns_include_group_members_and_image_extras():
    schema = _flickr8k_schema()
    cols = db_columns(schema)
    assert "split" in cols
    assert "image" in cols
    assert "width" in cols
    assert "height" in cols
    assert "thumbnail" in cols
    for i in range(5):
        assert f"caption_{i}" in cols
    assert "captions" not in cols


def test_fts_columns_match_searchable_fields():
    schema = _flickr8k_schema()
    fts = fts_columns(schema)
    for i in range(5):
        assert f"caption_{i}" in fts


def test_select_columns_cover_db_columns_for_reads():
    """SELECT columns must include every db column needed for row_to_dict."""
    schema = _flickr8k_schema()
    db_cols = set(db_columns(schema))
    selected = select_columns(schema)

    for col in db_cols:
        if col == "split":
            assert "samples.split" in selected
        elif col == "thumbnail":
            continue
        else:
            assert f"samples.{col}" in selected

    assert "samples.id" in selected
