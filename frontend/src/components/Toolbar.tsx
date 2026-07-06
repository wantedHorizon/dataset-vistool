import { useState } from "react";
import {
  Box,
  Button,
  Checkbox,
  InputAdornment,
  ListItemText,
  Menu,
  MenuItem,
  TextField,
  ToggleButton,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import CodeIcon from "@mui/icons-material/Code";
import ViewColumnIcon from "@mui/icons-material/ViewColumn";
import { ColumnDef } from "./tableColumns";

interface Props {
  split: string;
  onSplitChange: (v: string) => void;
  search: string;
  onSearchChange: (v: string) => void;
  sqlOpen: boolean;
  onToggleSql: () => void;
  splitCounts: Record<string, number>;
  visibleColumns: string[];
  onToggleColumn: (key: string) => void;
  columns: ColumnDef[];
  searchPlaceholder?: string;
}

export default function Toolbar({
  split,
  onSplitChange,
  search,
  onSearchChange,
  sqlOpen,
  onToggleSql,
  splitCounts,
  visibleColumns,
  onToggleColumn,
  columns,
  searchPlaceholder = "Search…",
}: Props) {
  const [colsAnchor, setColsAnchor] = useState<null | HTMLElement>(null);
  const visible = new Set(visibleColumns);
  const toggleable = columns.filter((c) => !c.fixed);

  return (
    <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", alignItems: "center", mb: 2 }}>
      <TextField
        select
        size="small"
        label="Split"
        value={split}
        onChange={(e) => onSplitChange(e.target.value)}
        sx={{ minWidth: 160 }}
      >
        <MenuItem value="">All ({Object.values(splitCounts).reduce((a, b) => a + b, 0)})</MenuItem>
        {Object.entries(splitCounts).map(([name, count]) => (
          <MenuItem key={name} value={name}>
            {name} ({count})
          </MenuItem>
        ))}
      </TextField>

      <TextField
        size="small"
        placeholder={searchPlaceholder}
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        sx={{ minWidth: 260, flex: 1 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon fontSize="small" />
            </InputAdornment>
          ),
        }}
      />

      <Button
        size="small"
        variant="outlined"
        color="inherit"
        startIcon={<ViewColumnIcon fontSize="small" />}
        onClick={(e) => setColsAnchor(e.currentTarget)}
        sx={{ height: 40 }}
      >
        Columns
      </Button>
      <Menu anchorEl={colsAnchor} open={Boolean(colsAnchor)} onClose={() => setColsAnchor(null)}>
        {toggleable.map((c) => (
          <MenuItem key={c.key} dense onClick={() => onToggleColumn(c.key)}>
            <Checkbox edge="start" size="small" checked={visible.has(c.key)} disableRipple />
            <ListItemText primary={c.label || c.key} />
          </MenuItem>
        ))}
      </Menu>

      <ToggleButton size="small" value="sql" selected={sqlOpen} onChange={onToggleSql}>
        <CodeIcon fontSize="small" sx={{ mr: 0.5 }} /> SQL
      </ToggleButton>
    </Box>
  );
}
