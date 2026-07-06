/* eslint-disable react-refresh/only-export-components */
import { ReactNode } from "react";
import { Box, Chip, IconButton, Link, Tooltip } from "@mui/material";
import DataObjectIcon from "@mui/icons-material/DataObject";
import { DatasetSchema, FieldDef, SampleRecord } from "../api/client";

export interface CellContext {
  onOpenSample: (id: number) => void;
  search?: string;
}

export interface ColumnDef {
  key: string;
  label: string;
  width?: number;
  fixed?: boolean;
  defaultVisible?: boolean;
  render: (row: SampleRecord, ctx: CellContext) => ReactNode;
}

const SPLIT_COLORS: Record<string, "success" | "warning" | "info" | "default"> = {
  train: "success",
  validation: "warning",
  test: "info",
};

function HighlightedText({ text, search }: { text: string; search?: string }) {
  const tokens = (search ?? "").match(/\w+/g);
  if (!tokens || tokens.length === 0) return <>{text}</>;
  const pattern = tokens
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("|");
  const re = new RegExp(`(${pattern})`, "gi");
  const parts = text.split(re);
  return (
    <>
      {parts.map((part, i) =>
        re.test(part) && i % 2 === 1 ? (
          <Box key={i} component="mark" sx={{ bgcolor: "warning.light", p: 0 }}>
            {part}
          </Box>
        ) : (
          part
        ),
      )}
    </>
  );
}

function SampleThumbnail({
  src,
  alt,
  onClick,
}: {
  src: string;
  alt: string;
  onClick: () => void;
}) {
  return (
    <Box
      component="img"
      src={src}
      alt={alt}
      loading="lazy"
      onClick={onClick}
      sx={{
        width: 110,
        height: 90,
        objectFit: "cover",
        borderRadius: 1.5,
        cursor: "pointer",
        bgcolor: "action.hover",
        display: "block",
      }}
    />
  );
}

function aspectLabel(w: number, h: number): string {
  const r = w / h;
  if (Math.abs(r - 1) < 0.05) return "square";
  return r > 1 ? "landscape" : "portrait";
}

function labelField(schema: DatasetSchema): FieldDef | undefined {
  return (
    schema.fields.find((f) => f.name === "image_path") ??
    schema.fields.find((f) => f.type === "text" && f.visible)
  );
}

function renderTextList(row: SampleRecord, field: FieldDef, ctx: CellContext) {
  const items = row[field.name];
  if (!Array.isArray(items)) return "—";
  return (
    <Box component="ol" sx={{ m: 0, pl: 2.5 }}>
      {items.map((c, i) => (
        <li key={i} style={{ marginBottom: 2 }}>
          <HighlightedText text={String(c)} search={ctx.search} />
        </li>
      ))}
    </Box>
  );
}

function fieldToColumn(field: FieldDef, schema: DatasetSchema): ColumnDef | null {
  const labelFieldDef = labelField(schema);

  switch (field.type) {
    case "image":
      return {
        key: field.name,
        label: field.name,
        width: 130,
        defaultVisible: field.visible,
        render: (row, ctx) =>
          row.thumb_url ? (
            <SampleThumbnail
              src={String(row.thumb_url)}
              alt={String(row[labelFieldDef?.name ?? "id"] ?? `sample_${row.id}`)}
              onClick={() => ctx.onOpenSample(row.id)}
            />
          ) : (
            "—"
          ),
      };
    case "split":
      return {
        key: field.name,
        label: field.name,
        width: 120,
        defaultVisible: field.visible,
        render: (row) => (
          <Chip
            label={String(row.split ?? "—")}
            size="small"
            color={SPLIT_COLORS[String(row.split)] ?? "default"}
            variant="outlined"
          />
        ),
      };
    case "text_list":
      return {
        key: field.name,
        label: field.name,
        defaultVisible: field.visible,
        render: (row, ctx) => renderTextList(row, field, ctx),
      };
    case "text":
      if (field.name === "image_path") {
        return {
          key: field.name,
          label: "name",
          width: 200,
          defaultVisible: field.visible,
          render: (row, ctx) => (
            <Link
              component="button"
              underline="hover"
              onClick={() => ctx.onOpenSample(row.id)}
              sx={{ textAlign: "left", wordBreak: "break-all", fontWeight: 600 }}
            >
              {String(row[field.name] ?? `sample_${row.id}`)}
            </Link>
          ),
        };
      }
      return {
        key: field.name,
        label: field.name,
        defaultVisible: field.visible,
        render: (row, ctx) => (
          <HighlightedText text={String(row[field.name] ?? "—")} search={ctx.search} />
        ),
      };
    case "integer":
      if (field.name === "width" || field.name === "height") return null;
      return {
        key: field.name,
        label: field.name,
        width: 100,
        defaultVisible: field.visible,
        render: (row) => String(row[field.name] ?? "—"),
      };
    default:
      return null;
  }
}

export function buildColumns(schema: DatasetSchema): ColumnDef[] {
  const cols: ColumnDef[] = [
    {
      key: "id",
      label: "id",
      width: 70,
      defaultVisible: true,
      render: (row) => row.id,
    },
  ];

  for (const field of schema.fields) {
    if (field.type === "blob") continue;
    const col = fieldToColumn(field, schema);
    if (col) cols.push(col);
  }

  // Derived dimension columns when width/height present in data
  const hasDims = schema.fields.some((f) => f.name === "width") ||
    schema.fields.some((f) => f.type === "image");
  if (hasDims) {
    cols.push(
      {
        key: "dimensions",
        label: "dimensions",
        width: 120,
        defaultVisible: false,
        render: (row) =>
          row.width && row.height ? (
            <Chip label={`${row.width}×${row.height}`} size="small" variant="outlined" />
          ) : (
            "—"
          ),
      },
      {
        key: "aspect",
        label: "aspect",
        width: 120,
        defaultVisible: false,
        render: (row) =>
          row.width && row.height ? (
            <Chip
              label={aspectLabel(Number(row.width), Number(row.height))}
              size="small"
              variant="outlined"
            />
          ) : (
            "—"
          ),
      },
    );
  }

  cols.push({
    key: "actions",
    label: "",
    width: 56,
    fixed: true,
    render: (row, ctx) => (
      <Tooltip title="View JSON">
        <IconButton size="small" onClick={() => ctx.onOpenSample(row.id)}>
          <DataObjectIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    ),
  });

  return cols;
}

export function defaultVisibleKeys(schema: DatasetSchema): string[] {
  return buildColumns(schema)
    .filter((c) => c.fixed || c.defaultVisible)
    .map((c) => c.key);
}

export function searchableLabels(schema: DatasetSchema): string {
  const labels = schema.fields.filter((f) => f.searchable).map((f) => f.name);
  return labels.length ? labels.join(", ") : "fields";
}

// Legacy export for any remaining imports
export const COLUMNS: ColumnDef[] = [];
export const DEFAULT_VISIBLE: string[] = [];
