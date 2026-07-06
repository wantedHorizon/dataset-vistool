import { ReactNode } from "react";
import {
  Box,
  Chip,
  IconButton,
  Link,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
} from "@mui/material";
import DataObjectIcon from "@mui/icons-material/DataObject";
import { FieldMeta, Sample } from "../api/client";

interface Props {
  rows: Sample[];
  fields: FieldMeta[];
  onOpenSample: (id: number) => void;
}

interface Column {
  key: string;
  header: string;
  width?: number;
  render: (row: Sample, onOpenSample: (id: number) => void) => ReactNode;
}

function renderScalar(field: FieldMeta): Column["render"] {
  return (row, onOpenSample) => {
    const value = row.fields[field.key];
    if (field.role === "name") {
      return (
        <Link
          component="button"
          underline="hover"
          onClick={() => onOpenSample(row.id)}
          sx={{ textAlign: "left", wordBreak: "break-all", fontWeight: 600 }}
        >
          {row.name}
        </Link>
      );
    }
    if (value == null) return null;
    if (field.role === "split") {
      return <Chip label={String(value)} size="small" variant="outlined" />;
    }
    return String(value);
  };
}

// One table column per visible field; a string_list field fans out into
// item_count columns ("caption 1" … "caption N"). All metadata-driven — the
// frontend never hardcodes the dataset's column names or counts.
function buildColumns(fields: FieldMeta[]): Column[] {
  return fields
    .filter((f) => f.visible)
    .flatMap((f): Column[] => {
      if (f.type === "string_list" && f.item_count) {
        return Array.from({ length: f.item_count }, (_, i) => ({
          key: `${f.key}[${i}]`,
          header: `${f.label.toLowerCase()} ${i + 1}`,
          render: (row: Sample) => {
            const list = row.fields[f.key] as string[] | undefined;
            return list?.[i] ?? "";
          },
        }));
      }
      return [
        {
          key: f.key,
          header: f.label.toLowerCase(),
          width: f.role === "name" ? 180 : undefined,
          render: renderScalar(f),
        },
      ];
    });
}

// "Viewer" mode, styled after the Hugging Face dataset viewer: id, thumbnail,
// then one column per visible field from the dataset metadata. Clicking the
// thumbnail, the name, or the JSON icon opens the JSON modal.
export default function SamplesTable({ rows, fields, onOpenSample }: Props) {
  const columns = buildColumns(fields);
  return (
    <TableContainer
      sx={{ bgcolor: "background.paper", borderRadius: 2, border: "1px solid", borderColor: "divider" }}
    >
      <Table size="small" stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell width={60}>id</TableCell>
            <TableCell width={130}>image</TableCell>
            {columns.map((c) => (
              <TableCell key={c.key} width={c.width}>
                {c.header}
              </TableCell>
            ))}
            <TableCell width={56} />
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <TableRow hover key={row.id}>
              <TableCell sx={{ color: "text.secondary" }}>{row.id}</TableCell>
              <TableCell>
                <Box
                  component="img"
                  src={row.thumb_url}
                  alt={row.name}
                  loading="lazy"
                  onClick={() => onOpenSample(row.id)}
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
              </TableCell>
              {columns.map((c) => (
                <TableCell key={c.key}>{c.render(row, onOpenSample)}</TableCell>
              ))}
              <TableCell>
                <Tooltip title="View JSON">
                  <IconButton size="small" onClick={() => onOpenSample(row.id)}>
                    <DataObjectIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
