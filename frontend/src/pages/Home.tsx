import { useEffect, useState } from "react";
import {
  Alert,
  AppBar,
  Box,
  CircularProgress,
  Container,
  TablePagination,
  Toolbar as MuiToolbar,
  Typography,
} from "@mui/material";
import ImageSearchIcon from "@mui/icons-material/ImageSearch";
import Toolbar from "../components/Toolbar";
import SamplesTable from "../components/SamplesTable";
import SampleModal from "../components/SampleModal";
import SqlConsole from "../components/SqlConsole";
import { useSamples, useStats } from "../hooks/queries";
import { useDebounced } from "../hooks/useDebounced";
import { DEFAULT_VISIBLE } from "../components/tableColumns";

const COLUMNS_STORAGE_KEY = "flickr8k.visibleColumns";

function loadVisibleColumns(): string[] {
  try {
    const raw = localStorage.getItem(COLUMNS_STORAGE_KEY);
    if (raw) return JSON.parse(raw) as string[];
  } catch {
    /* ignore malformed/unavailable storage */
  }
  return DEFAULT_VISIBLE;
}

export default function Home() {
  const [split, setSplit] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const search = useDebounced(searchInput, 300);
  const [sqlOpen, setSqlOpen] = useState(false);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [visibleColumns, setVisibleColumns] = useState<string[]>(loadVisibleColumns);

  useEffect(() => {
    localStorage.setItem(COLUMNS_STORAGE_KEY, JSON.stringify(visibleColumns));
  }, [visibleColumns]);

  const handleToggleColumn = (key: string) => {
    setVisibleColumns((cols) =>
      cols.includes(key) ? cols.filter((c) => c !== key) : [...cols, key],
    );
  };

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

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <AppBar position="static" color="default" elevation={0} sx={{ borderBottom: "1px solid #e2e8f0" }}>
        <MuiToolbar>
          <ImageSearchIcon sx={{ mr: 1 }} />
          <Typography variant="h6" component="div">
            Flickr8k Explorer
          </Typography>
          {stats && (
            <Typography variant="body2" color="text.secondary" sx={{ ml: 2 }}>
              {stats.total} samples
            </Typography>
          )}
        </MuiToolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Toolbar
          split={split}
          onSplitChange={handleSplitChange}
          search={searchInput}
          onSearchChange={handleSearchChange}
          sqlOpen={sqlOpen}
          onToggleSql={() => setSqlOpen((v) => !v)}
          splitCounts={stats?.splits ?? {}}
          visibleColumns={visibleColumns}
          onToggleColumn={handleToggleColumn}
        />

        {sqlOpen && <SqlConsole />}

        {error && <Alert severity="error">{(error as Error).message}</Alert>}

        {isLoading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
            <CircularProgress />
          </Box>
        ) : data ? (
          <>
            <Box sx={{ opacity: isFetching ? 0.6 : 1, transition: "opacity 0.15s" }}>
              <SamplesTable
                rows={data.rows}
                onOpenSample={setActiveId}
                visibleColumns={visibleColumns}
                search={search}
              />
            </Box>
            <TablePagination
              component="div"
              count={data.total}
              page={page}
              onPageChange={(_, p) => setPage(p)}
              rowsPerPage={pageSize}
              onRowsPerPageChange={(e) => {
                setPageSize(parseInt(e.target.value, 10));
                setPage(0);
              }}
              rowsPerPageOptions={[10, 20, 50, 100]}
            />
          </>
        ) : null}
      </Container>

      <SampleModal id={activeId} onClose={() => setActiveId(null)} />
    </Box>
  );
}
