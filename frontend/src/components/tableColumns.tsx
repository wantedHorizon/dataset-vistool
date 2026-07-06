/* eslint-disable react-refresh/only-export-components -- column catalog module: exports data + cell renderers, not React components */
import { ReactNode } from "react";
import { Box, Chip, IconButton, Link, Tooltip } from "@mui/material";
import DataObjectIcon from "@mui/icons-material/DataObject";
import { Sample } from "../api/client";

// Context handed to each column's cell renderer. `search` is the active,
// debounced caption query, used to highlight matched tokens in the captions cell.
export interface CellContext {
  onOpenSample: (id: number) => void;
  search?: string;
}

export interface ColumnDef {
  key: string;
  label: string;
  width?: number;
  // Non-toggleable columns (e.g. the JSON action) never appear in the picker
  // and are always rendered.
  fixed?: boolean;
  // Whether the column is visible by default when no saved preference exists.
  defaultVisible?: boolean;
  render: (row: Sample, ctx: CellContext) => ReactNode;
}

const SPLIT_COLORS: Record<string, "success" | "warning" | "info" | "default"> = {
  train: "success",
  validation: "warning",
  test: "info",
};

// Wrap every occurrence of the search's \w+ tokens in <mark> so caption matches
// are visible at a glance. Falls back to plain text when there's nothing to match.
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

// The full column catalog. `SamplesTable` renders the subset the user has
// enabled; `ColumnsMenu` lists the toggleable ones. Add a column here and it
// shows up in both places automatically.
export const COLUMNS: ColumnDef[] = [
  {
    key: "id",
    label: "id",
    width: 70,
    defaultVisible: false,
    render: (row) => row.id,
  },
  {
    key: "image",
    label: "image",
    width: 130,
    defaultVisible: true,
    render: (row, ctx) => (
      <SampleThumbnail
        src={row.thumb_url}
        alt={row.image_path || `sample_${row.id}`}
        onClick={() => ctx.onOpenSample(row.id)}
      />
    ),
  },

  {
    key: "name",
    label: "name",
    width: 200,
    defaultVisible: true,
    render: (row, ctx) => (
      <Link
        component="button"
        underline="hover"
        onClick={() => ctx.onOpenSample(row.id)}
        sx={{ textAlign: "left", wordBreak: "break-all", fontWeight: 600 }}
      >
        {row.image_path || `sample_${row.id}`}
      </Link>
    ),
  },
  {
    key: "split",
    label: "split",
    width: 120,
    defaultVisible: true,
    render: (row) => (
      <Chip
        label={row.split}
        size="small"
        color={SPLIT_COLORS[row.split] ?? "default"}
        variant="outlined"
      />
    ),
  },
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
        <Chip label={aspectLabel(row.width, row.height)} size="small" variant="outlined" />
      ) : (
        "—"
      ),
  },
  {
    key: "captions",
    label: "captions",
    defaultVisible: true,
    render: (row, ctx) => (
      <Box component="ol" sx={{ m: 0, pl: 2.5 }}>
        {row.captions.map((c, i) => (
          <li key={i} style={{ marginBottom: 2 }}>
            <HighlightedText text={c} search={ctx.search} />
          </li>
        ))}
      </Box>
    ),
  },
  {
    key: "caption_count",
    label: "# captions",
    width: 90,
    defaultVisible: false,
    render: (row) => row.captions.length,
  },
  {
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
  },
];

export const DEFAULT_VISIBLE = COLUMNS.filter(
  (c) => c.fixed || c.defaultVisible,
).map((c) => c.key);
