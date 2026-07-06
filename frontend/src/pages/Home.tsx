import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
  TablePagination,
  Typography,
} from "@mui/material";
import AppLayout from "../components/AppLayout";
import Toolbar from "../components/Toolbar";
import SamplesTable from "../components/SamplesTable";
import SampleModal from "../components/SampleModal";
import SqlConsole from "../components/SqlConsole";
import { useDataset, useSamples, useStats } from "../hooks/queries";
import { useDebounced } from "../hooks/useDebounced";
import { useDatasetContext } from "../context/DatasetContext";
import { buildColumns, defaultVisibleKeys, searchableLabels } from "../components/tableColumns";

function loadVisibleColumns(datasetId: string, defaults: string[]): string[] {
  try {
    const raw = localStorage.getItem(`explorer.${datasetId}.visibleColumns`);
    if (raw) return JSON.parse(raw) as string[];
  } catch {
    /* ignore */
  }
  return defaults;
}

export default function Home() {
  const { activeDatasetId, ingestedDatasets, isLoading: ctxLoading } = useDatasetContext();
  const { data: schema } = useDataset(activeDatasetId);
  const columns = useMemo(() => (schema ? buildColumns(schema) : []), [schema]);
  const defaultVisible = useMemo(
    () => (schema ? defaultVisibleKeys(schema) : []),
    [schema],
  );

  const [split, setSplit] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const search = useDebounced(searchInput, 300);
  const [sqlOpen, setSqlOpen] = useState(false);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [visibleColumns, setVisibleColumns] = useState<string[]>([]);

  useEffect(() => {
    if (activeDatasetId && defaultVisible.length) {
      setVisibleColumns(loadVisibleColumns(activeDatasetId, defaultVisible));
    }
  }, [activeDatasetId, defaultVisible]);

  useEffect(() => {
    if (activeDatasetId) {
      localStorage.setItem(
        `explorer.${activeDatasetId}.visibleColumns`,
        JSON.stringify(visibleColumns),
      );
    }
  }, [visibleColumns, activeDatasetId]);

  useEffect(() => {
    setSplit("");
    setSearchInput("");
    setPage(0);
  }, [activeDatasetId]);

  const handleToggleColumn = (key: string) => {
    setVisibleColumns((cols) =>
      cols.includes(key) ? cols.filter((c) => c !== key) : [...cols, key],
    );
  };

  const sampleParams =
    activeDatasetId !== null
      ? {
          datasetId: activeDatasetId,
          split: split || undefined,
          search: search || undefined,
          page,
          pageSize,
        }
      : null;

  const { data: stats } = useStats(activeDatasetId);
  const { data, isLoading, isFetching, error } = useSamples(sampleParams);

  const searchPlaceholder = schema
    ? `Search ${searchableLabels(schema)}…`
    : "Search…";

  if (ctxLoading) {
    return (
      <AppLayout showDatasetSelector>
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      </AppLayout>
    );
  }

  if (ingestedDatasets.length === 0) {
    return (
      <AppLayout>
        <Container maxWidth="sm" sx={{ py: 8, textAlign: "center" }}>
          <Typography variant="h6" gutterBottom>
            No datasets yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Add a HuggingFace dataset to get started.
          </Typography>
          <Button component={RouterLink} to="/datasets/new" variant="contained">
            Add Dataset
          </Button>
        </Container>
      </AppLayout>
    );
  }

  return (
    <AppLayout showDatasetSelector>
      <Container maxWidth="xl" sx={{ py: 3 }}>
        {stats && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {stats.total} samples
          </Typography>
        )}

        <Toolbar
          split={split}
          onSplitChange={(v) => {
            setSplit(v);
            setPage(0);
          }}
          search={searchInput}
          onSearchChange={(v) => {
            setSearchInput(v);
            setPage(0);
          }}
          sqlOpen={sqlOpen}
          onToggleSql={() => setSqlOpen((v) => !v)}
          splitCounts={stats?.splits ?? {}}
          visibleColumns={visibleColumns}
          onToggleColumn={handleToggleColumn}
          columns={columns}
          searchPlaceholder={searchPlaceholder}
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
                columns={columns}
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
    </AppLayout>
  );
}
