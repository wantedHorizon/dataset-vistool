import { useState } from "react";
import {
  Alert,
  AppBar,
  Box,
  CircularProgress,
  Container,
  IconButton,
  TablePagination,
  Toolbar as MuiToolbar,
  Tooltip,
  Typography,
} from "@mui/material";
import ImageSearchIcon from "@mui/icons-material/ImageSearch";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import LightModeIcon from "@mui/icons-material/LightMode";
import Toolbar from "../components/Toolbar";
import { PAGE_SIZE_OPTIONS } from "../constants";
import SamplesTable from "../components/SamplesTable";
import SampleModal from "../components/SampleModal";
import SqlConsole from "../components/SqlConsole";
import { useFields, useSamples, useStats } from "../hooks/queries";
import { useDebounced } from "../hooks/useDebounced";
import { useColorMode } from "../colorMode";

export default function Home() {
  const [split, setSplit] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const search = useDebounced(searchInput, 300);
  const [sqlOpen, setSqlOpen] = useState(false);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [activeId, setActiveId] = useState<number | null>(null);
  const { mode, toggle } = useColorMode();

  const { data: fieldsMeta } = useFields();
  const { data: stats } = useStats();
  const { data, isLoading, isFetching, error } = useSamples({
    split: split || undefined,
    search: search || undefined,
    page,
    pageSize,
  });

  const handleSplitChange = (v: string) => {
    setSplit(v);
    setPage(0);
  };
  const handleSearchChange = (v: string) => {
    setSearchInput(v);
    setPage(0);
  };
  const handlePageSizeChange = (n: number) => {
    setPageSize(n);
    setPage(0);
  };

  const searchableLabels = (fieldsMeta?.fields ?? [])
    .filter((f) => f.searchable)
    .map((f) => f.label.toLowerCase());
  const searchPlaceholder = searchableLabels.length
    ? `Search ${searchableLabels.join(", ")}s…`
    : "Search…";

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <AppBar
        position="static"
        color="default"
        elevation={0}
        sx={{ borderBottom: "1px solid", borderColor: "divider" }}
      >
        <MuiToolbar>
          <ImageSearchIcon sx={{ mr: 1 }} />
          <Typography variant="h6" component="div">
            {fieldsMeta ? `${fieldsMeta.dataset.title} Explorer` : "Dataset Explorer"}
          </Typography>
          {stats && (
            <Typography variant="body2" color="text.secondary" sx={{ ml: 2 }}>
              {stats.total} samples
            </Typography>
          )}
          <Box sx={{ flexGrow: 1 }} />
          <Tooltip title={mode === "light" ? "Dark mode" : "Light mode"}>
            <IconButton onClick={toggle} color="inherit">
              {mode === "light" ? <DarkModeIcon /> : <LightModeIcon />}
            </IconButton>
          </Tooltip>
        </MuiToolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Toolbar
          split={split}
          onSplitChange={handleSplitChange}
          search={searchInput}
          onSearchChange={handleSearchChange}
          searchPlaceholder={searchPlaceholder}
          pageSize={pageSize}
          onPageSizeChange={handlePageSizeChange}
          sqlOpen={sqlOpen}
          onToggleSql={() => setSqlOpen((v) => !v)}
          splitCounts={stats?.splits ?? {}}
        />

        {sqlOpen && <SqlConsole />}

        {error && <Alert severity="error">{(error as Error).message}</Alert>}

        {isLoading || !fieldsMeta ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
            <CircularProgress />
          </Box>
        ) : data ? (
          <>
            <Box sx={{ opacity: isFetching ? 0.6 : 1, transition: "opacity 0.15s" }}>
              <SamplesTable rows={data.rows} fields={fieldsMeta.fields} onOpenSample={setActiveId} />
            </Box>
            <TablePagination
              component="div"
              count={data.total}
              page={page}
              onPageChange={(_, p) => setPage(p)}
              rowsPerPage={pageSize}
              onRowsPerPageChange={(e) => handlePageSizeChange(parseInt(e.target.value, 10))}
              rowsPerPageOptions={PAGE_SIZE_OPTIONS}
            />
          </>
        ) : null}
      </Container>

      <SampleModal id={activeId} onClose={() => setActiveId(null)} />
    </Box>
  );
}
