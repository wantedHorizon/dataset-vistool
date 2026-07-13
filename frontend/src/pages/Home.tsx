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
import DownloadBar from "../components/DownloadBar";
import SampleModal from "../components/SampleModal";
import SqlConsole from "../components/SqlConsole";
import { useDataset, useDownloadSamples, useSamples, useStats } from "../hooks/queries";
import { useDebounced } from "../hooks/useDebounced";
import { useDatasetContext } from "../context/DatasetContext";
import { buildColumns, defaultVisibleKeys, searchableLabels } from "../components/tableColumns";
import { loadVisibleColumns, saveVisibleColumns } from "../lib/columnStorage";
import { DownloadRequest } from "../api/client";

export default function Home() {
  const { activeDatasetId, ingestedDatasets, isLoading: ctxLoading } = useDatasetContext();
  const { data: schema } = useDataset(activeDatasetId);
  const columns = useMemo(() => (schema ? buildColumns(schema) : []), [schema]);
  const columnKeys = useMemo(() => columns.map((c) => c.key), [columns]);
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

  const [rowMarks, setRowMarks] = useState<Map<number, "include" | "exclude">>(
    () => new Map(),
  );
  const [selectAllMatching, setSelectAllMatching] = useState(false);

  const included = useMemo(() => {
    const s = new Set<number>();
    for (const [id, mark] of rowMarks) if (mark === "include") s.add(id);
    return s;
  }, [rowMarks]);
  const excluded = useMemo(() => {
    const s = new Set<number>();
    for (const [id, mark] of rowMarks) if (mark === "exclude") s.add(id);
    return s;
  }, [rowMarks]);

  const download = useDownloadSamples(activeDatasetId);

  useEffect(() => {
    if (activeDatasetId && defaultVisible.length && columnKeys.length) {
      setVisibleColumns(
        loadVisibleColumns(activeDatasetId, defaultVisible, columnKeys),
      );
    } else {
      setVisibleColumns([]);
    }
  }, [activeDatasetId, defaultVisible, columnKeys]);

  useEffect(() => {
    setSplit("");
    setSearchInput("");
    setPage(0);
  }, [activeDatasetId]);

  useEffect(() => {
    setRowMarks(new Map());
    setSelectAllMatching(false);
  }, [activeDatasetId, split, search]);

  useEffect(() => {
    download.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeDatasetId, split, search]);

  const handleToggleColumn = (key: string) => {
    setVisibleColumns((cols) => {
      const next = cols.includes(key) ? cols.filter((c) => c !== key) : [...cols, key];
      if (activeDatasetId) {
        saveVisibleColumns(activeDatasetId, next);
      }
      return next;
    });
  };

  const clearSelection = () => {
    setRowMarks(new Map());
    setSelectAllMatching(false);
  };

  const onToggleRow = (id: number) => {
    setSelectAllMatching(false);
    setRowMarks((prev) => {
      const next = new Map(prev);
      if (next.has(id)) next.delete(id);
      else next.set(id, "include");
      return next;
    });
  };

  const onExcludeRow = (id: number) => {
    setRowMarks((prev) => {
      const next = new Map(prev);
      next.set(id, "exclude");
      return next;
    });
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

  const onTogglePage = (select: boolean) => {
    const pageIds = data?.rows.map((r) => r.id) ?? [];
    setSelectAllMatching(false);
    setRowMarks((prev) => {
      const next = new Map(prev);
      for (const id of pageIds) {
        if (select) next.set(id, "include");
        else if (next.get(id) === "include") next.delete(id);
      }
      return next;
    });
  };

  const runDownload = (partial: Omit<DownloadRequest, "split" | "search">) => {
    const base: DownloadRequest = {
      ...partial,
      ...(split ? { split } : {}),
      ...(search ? { search } : {}),
    };
    if (partial.mode === "ids") {
      download.mutate({
        mode: "ids",
        ids: [...included],
        ...(split ? { split } : {}),
        ...(search ? { search } : {}),
      });
      return;
    }
    const exclude_ids = excluded.size > 0 ? [...excluded] : undefined;
    download.mutate({
      ...base,
      ...(exclude_ids ? { exclude_ids } : {}),
    });
  };

  const searchPlaceholder = schema
    ? `Search ${searchableLabels(schema)}…`
    : "Search…";

  const filterActive = Boolean(split || search);
  const matchLabel =
    data && stats
      ? filterActive
        ? `${data.total} matches (of ${stats.total})`
        : `${stats.total} samples`
      : stats
        ? `${stats.total} samples`
        : null;

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
        {matchLabel && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {matchLabel}
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

        {data && (
          <DownloadBar
            total={data.total}
            includedCount={included.size}
            excludedCount={excluded.size}
            selectAllMatching={selectAllMatching}
            onSelectAllMatching={() => setSelectAllMatching(true)}
            onClearSelection={clearSelection}
            isPending={download.isPending}
            error={download.error ? (download.error as Error).message : null}
            onDownload={runDownload}
          />
        )}

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
                included={included}
                excluded={excluded}
                onToggleRow={onToggleRow}
                onExcludeRow={onExcludeRow}
                onTogglePage={onTogglePage}
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
