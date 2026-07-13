import { useRef } from "react";
import {
  Checkbox,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
} from "@mui/material";
import CheckBoxOutlineBlankIcon from "@mui/icons-material/CheckBoxOutlineBlank";
import CheckBoxIcon from "@mui/icons-material/CheckBox";
import DisabledByDefaultIcon from "@mui/icons-material/DisabledByDefault";
import { SampleRecord } from "../api/client";
import { ColumnDef, CellContext } from "./tableColumns";

export type RowMark = "include" | "exclude";

interface Props {
  rows: SampleRecord[];
  columns: ColumnDef[];
  onOpenSample: (id: number) => void;
  visibleColumns: string[];
  search?: string;
  included: Set<number>;
  excluded: Set<number>;
  onToggleRow: (id: number) => void;
  onExcludeRow: (id: number) => void;
  onTogglePage: (select: boolean) => void;
}

const CLICK_DELAY_MS = 250;

function RowSelectControl({
  mark,
  onToggle,
  onExclude,
}: {
  mark: RowMark | null;
  onToggle: () => void;
  onExclude: () => void;
}) {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = () => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
  };

  const icon =
    mark === "include" ? (
      <CheckBoxIcon fontSize="small" color="primary" />
    ) : mark === "exclude" ? (
      <DisabledByDefaultIcon fontSize="small" color="error" />
    ) : (
      <CheckBoxOutlineBlankIcon fontSize="small" />
    );

  const title =
    mark === "include"
      ? "Selected — click to clear, double-click to exclude"
      : mark === "exclude"
        ? "Excluded — click to clear"
        : "Click to select, double-click to exclude";

  return (
    <Tooltip title={title}>
      <IconButton
        size="small"
        aria-label={title}
        onClick={(e) => {
          e.stopPropagation();
          clearTimer();
          timer.current = setTimeout(() => {
            timer.current = null;
            onToggle();
          }, CLICK_DELAY_MS);
        }}
        onDoubleClick={(e) => {
          e.stopPropagation();
          clearTimer();
          onExclude();
        }}
      >
        {icon}
      </IconButton>
    </Tooltip>
  );
}

export default function SamplesTable({
  rows,
  columns,
  onOpenSample,
  visibleColumns,
  search,
  included,
  excluded,
  onToggleRow,
  onExcludeRow,
  onTogglePage,
}: Props) {
  const visible = new Set(visibleColumns);
  const cols = columns.filter((c) => c.fixed || visible.has(c.key));
  const ctx: CellContext = { onOpenSample, search };

  const pageIds = rows.map((r) => r.id);
  const includedOnPage = pageIds.filter((id) => included.has(id)).length;
  const allPageSelected = pageIds.length > 0 && includedOnPage === pageIds.length;
  const somePageSelected = includedOnPage > 0 && !allPageSelected;

  return (
    <TableContainer
      sx={{ bgcolor: "background.paper", borderRadius: 2, border: 1, borderColor: "divider" }}
    >
      <Table size="small" stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell padding="checkbox" sx={{ width: 48 }}>
              <Checkbox
                size="small"
                checked={allPageSelected}
                indeterminate={somePageSelected}
                onChange={() => onTogglePage(!allPageSelected)}
                inputProps={{ "aria-label": "Select page" }}
              />
            </TableCell>
            {cols.map((c) => (
              <TableCell key={c.key} width={c.width}>
                {c.label}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => {
            const mark: RowMark | null = included.has(row.id)
              ? "include"
              : excluded.has(row.id)
                ? "exclude"
                : null;
            return (
              <TableRow hover key={row.id} selected={mark === "include"}>
                <TableCell padding="checkbox" onClick={(e) => e.stopPropagation()}>
                  <RowSelectControl
                    mark={mark}
                    onToggle={() => onToggleRow(row.id)}
                    onExclude={() => onExcludeRow(row.id)}
                  />
                </TableCell>
                {cols.map((c) => (
                  <TableCell key={c.key}>{c.render(row, ctx)}</TableCell>
                ))}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
