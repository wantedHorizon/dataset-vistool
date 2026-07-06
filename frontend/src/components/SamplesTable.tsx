import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import { SampleRecord } from "../api/client";
import { ColumnDef, CellContext } from "./tableColumns";

interface Props {
  rows: SampleRecord[];
  columns: ColumnDef[];
  onOpenSample: (id: number) => void;
  visibleColumns: string[];
  search?: string;
}

export default function SamplesTable({ rows, columns, onOpenSample, visibleColumns, search }: Props) {
  const visible = new Set(visibleColumns);
  const cols = columns.filter((c) => c.fixed || visible.has(c.key));
  const ctx: CellContext = { onOpenSample, search };

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
                <TableCell key={c.key}>{c.render(row, ctx)}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
