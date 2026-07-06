import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import { Sample } from "../api/client";
import { COLUMNS } from "./tableColumns";

interface Props {
  rows: Sample[];
  onOpenSample: (id: number) => void;
  visibleColumns: string[];
  search?: string;
}

// "Viewer" mode, styled after the Hugging Face dataset viewer. Columns are
// driven by the catalog in tableColumns.tsx and filtered to the user's
// selection; clicking a thumbnail/name/JSON icon opens the JSON modal.
export default function SamplesTable({ rows, onOpenSample, visibleColumns, search }: Props) {
  const visible = new Set(visibleColumns);
  const cols = COLUMNS.filter((c) => c.fixed || visible.has(c.key));

  return (
    <TableContainer
      sx={{ bgcolor: "background.paper", borderRadius: 2, border: 1, borderColor: "divider" }}
    >
      <Table size="small" stickyHeader>
        <TableHead>
          <TableRow>
            {cols.map((c) => (
              <TableCell key={c.key} width={c.width}>
                {c.label}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <TableRow hover key={row.id}>
              {cols.map((c) => (
                <TableCell key={c.key}>{c.render(row, { onOpenSample, search })}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
