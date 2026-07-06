import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Button,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import AppLayout from "../components/AppLayout";
import { useDatasetContext } from "../context/DatasetContext";
import { useDatasets, useDeleteDataset, useSetActiveDataset } from "../hooks/queries";

function statusLabel(downloadStatus: string, ingestStatus: string): string {
  if (ingestStatus === "done") return "Imported";
  if (ingestStatus === "running") return "Populating DB…";
  if (downloadStatus === "ready") return "Ready to import";
  if (downloadStatus === "error") return "Error";
  return downloadStatus.replace(/_/g, " ");
}

function isInProgress(downloadStatus: string, ingestStatus: string): boolean {
  return ingestStatus !== "done" && downloadStatus !== "error";
}

export default function Datasets() {
  const navigate = useNavigate();
  const { data: datasets, isLoading } = useDatasets();
  const setActive = useSetActiveDataset();
  const remove = useDeleteDataset();
  const { setActiveDatasetId } = useDatasetContext();
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleteName, setDeleteName] = useState("");

  const handleBrowse = async (id: string) => {
    setActiveDatasetId(id);
    await setActive.mutateAsync(id);
    navigate("/");
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    await remove.mutateAsync(deleteId);
    setDeleteId(null);
  };

  return (
    <AppLayout>
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box sx={{ display: "flex", alignItems: "center", mb: 3, gap: 2 }}>
          <Typography variant="h5" sx={{ flexGrow: 1 }}>
            Datasets
          </Typography>
          <Button variant="contained" onClick={() => navigate("/datasets/new")}>
            Add dataset
          </Button>
        </Box>

        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Rows</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading && (
                <TableRow>
                  <TableCell colSpan={4}>Loading…</TableCell>
                </TableRow>
              )}
              {!isLoading && (datasets ?? []).length === 0 && (
                <TableRow>
                  <TableCell colSpan={4}>
                    <Typography color="text.secondary">No datasets yet.</Typography>
                  </TableCell>
                </TableRow>
              )}
              {(datasets ?? []).map((d) => {
                const done = d.ingest_status === "done";
                const inProgress = isInProgress(d.download_status, d.ingest_status);
                return (
                  <TableRow key={d.id}>
                    <TableCell>{d.name}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={statusLabel(d.download_status, d.ingest_status)}
                        color={done ? "success" : inProgress ? "info" : "default"}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="right">{done ? d.row_count : "—"}</TableCell>
                    <TableCell align="right">
                      {done && (
                        <>
                          <Button size="small" onClick={() => handleBrowse(d.id)}>
                            Browse
                          </Button>
                          <Button
                            size="small"
                            color="error"
                            onClick={() => {
                              setDeleteId(d.id);
                              setDeleteName(d.name);
                            }}
                            sx={{ ml: 1 }}
                          >
                            Delete
                          </Button>
                        </>
                      )}
                      {inProgress && !done && (
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => navigate(`/datasets/${d.id}/schema`)}
                        >
                          Continue setup
                        </Button>
                      )}
                      {!done && !inProgress && d.download_status === "error" && (
                        <Button
                          size="small"
                          color="error"
                          onClick={() => {
                            setDeleteId(d.id);
                            setDeleteName(d.name);
                          }}
                        >
                          Delete
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>

        <Dialog open={deleteId !== null} onClose={() => setDeleteId(null)}>
          <DialogTitle>Delete dataset?</DialogTitle>
          <DialogContent>
            <DialogContentText>
              This removes the schema, downloaded source files, and SQLite database for{" "}
              <strong>{deleteName}</strong>. This cannot be undone.
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDeleteId(null)}>Cancel</Button>
            <Button color="error" onClick={handleDelete} disabled={remove.isPending}>
              {remove.isPending ? "Deleting…" : "Delete"}
            </Button>
          </DialogActions>
        </Dialog>
      </Container>
    </AppLayout>
  );
}
