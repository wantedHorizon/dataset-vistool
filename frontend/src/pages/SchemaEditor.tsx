import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControl,
  Grid,
  Link,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import AppLayout from "../components/AppLayout";
import DownloadPanel from "../components/DownloadPanel";
import { FieldDef, FieldType } from "../api/client";
import {
  useDataset,
  useDeleteDataset,
  useDownloadStatus,
  useReparseSchema,
  useTriggerIngest,
  useUpdateDataset,
} from "../hooks/queries";

const FIELD_TYPES: FieldType[] = ["text", "text_list", "image", "integer", "split", "blob"];

interface FieldRow {
  field: FieldDef;
  index: number;
  isMember: boolean;
  parentName?: string;
}

function buildFieldRows(fields: FieldDef[]): FieldRow[] {
  const memberNames = new Set<string>();
  fields.forEach((f) => f.group_members?.forEach((m) => memberNames.add(m)));

  const rows: FieldRow[] = [];
  fields.forEach((field, index) => {
    if (memberNames.has(field.name)) return;
    rows.push({ field, index, isMember: false });
    if (field.type === "text_list" && field.group_members) {
      for (const member of field.group_members) {
        const memberIndex = fields.findIndex((f) => f.name === member);
        if (memberIndex >= 0) {
          rows.push({
            field: fields[memberIndex],
            index: memberIndex,
            isMember: true,
            parentName: field.name,
          });
        }
      }
    }
  });
  return rows;
}

export default function SchemaEditor() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: schema, isLoading, error } = useDataset(id ?? null);
  const { data: downloadStatus } = useDownloadStatus(id ?? null, id !== null);
  const update = useUpdateDataset(id ?? "");
  const ingest = useTriggerIngest(id ?? "");
  const reparse = useReparseSchema(id ?? "");
  const remove = useDeleteDataset();
  const [fields, setFields] = useState<FieldDef[]>([]);
  const [saved, setSaved] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  useEffect(() => {
    if (schema?.fields) {
      setFields(schema.fields);
      setSaved(false);
    }
  }, [schema]);

  const fieldRows = useMemo(() => buildFieldRows(fields), [fields]);
  const download = downloadStatus ?? schema?.download;
  const downloadReady = download?.status === "ready";
  const showDownloadPanel =
    download && !["ready", "idle"].includes(download.status) && schema?.ingest.status !== "done";

  if (!id) return null;

  const handleSave = async () => {
    await update.mutateAsync({ fields });
    setSaved(true);
  };

  const handleIngest = async () => {
    if (!saved) await handleSave();
    await ingest.mutateAsync(false);
  };

  const handleReparse = async () => {
    const result = await reparse.mutateAsync();
    setFields(result.fields);
    setSaved(false);
  };

  const handleDelete = async () => {
    await remove.mutateAsync(id);
    setDeleteOpen(false);
    navigate("/datasets/new");
  };

  const updateField = (index: number, patch: Partial<FieldDef>) => {
    setFields((prev) => prev.map((f, i) => (i === index ? { ...f, ...patch } : f)));
    setSaved(false);
  };

  const ingestDone = schema?.ingest.status === "done";
  const ingestRunning = schema?.ingest.status === "running" || ingest.isPending;
  const rawCount = fields.filter((f) => f.type !== "split").length;
  const schemaSource = download?.schema_source ?? "unknown";

  return (
    <AppLayout>
      <Container maxWidth="xl" sx={{ py: 4 }}>
        {isLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
            <CircularProgress />
          </Box>
        )}

        {error && <Alert severity="error">{(error as Error).message}</Alert>}

        {schema && (
          <>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2, flexWrap: "wrap" }}>
              <Typography variant="h5">Schema: {schema.name}</Typography>
              <Chip
                size="small"
                label={`${rawCount} fields · source: ${schemaSource}`}
                variant="outlined"
              />
              <Button size="small" onClick={handleReparse} disabled={reparse.isPending}>
                Re-extract
              </Button>
              <Button
                size="small"
                color="error"
                onClick={() => setDeleteOpen(true)}
                sx={{ ml: "auto" }}
              >
                Delete dataset
              </Button>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {schema.source_url}
            </Typography>

            <Grid container spacing={3}>
              {showDownloadPanel && download && (
                <Grid item xs={12} md={4}>
                  <DownloadPanel status={download} />
                </Grid>
              )}
              <Grid item xs={12} md={showDownloadPanel ? 8 : 12}>
                <Paper variant="outlined" sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" sx={{ p: 2, pb: 0 }}>
                    Fields (edit types and visibility)
                  </Typography>
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Name</TableCell>
                          <TableCell>Source</TableCell>
                          <TableCell>Type</TableCell>
                          <TableCell>Visible</TableCell>
                          <TableCell>Searchable</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {fieldRows.map(({ field, index, isMember, parentName }) => (
                          <TableRow
                            key={`${field.name}-${isMember ? "m" : "p"}`}
                            sx={isMember ? { bgcolor: "action.hover" } : undefined}
                          >
                            <TableCell sx={{ pl: isMember ? 4 : 2 }}>
                              {field.name}
                              {isMember && parentName && (
                                <Typography variant="caption" color="text.secondary" display="block">
                                  member of {parentName}
                                </Typography>
                              )}
                            </TableCell>
                            <TableCell>
                              <Typography variant="caption" color="text.secondary">
                                {field.source}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <FormControl size="small" fullWidth>
                                <Select
                                  value={field.type}
                                  onChange={(e) =>
                                    updateField(index, { type: e.target.value as FieldType })
                                  }
                                >
                                  {FIELD_TYPES.map((t) => (
                                    <MenuItem key={t} value={t}>
                                      {t}
                                    </MenuItem>
                                  ))}
                                </Select>
                              </FormControl>
                            </TableCell>
                            <TableCell>
                              <Checkbox
                                checked={field.visible}
                                onChange={(e) =>
                                  updateField(index, { visible: e.target.checked })
                                }
                              />
                            </TableCell>
                            <TableCell>
                              <Checkbox
                                checked={field.searchable}
                                disabled={field.type === "image" || field.type === "blob"}
                                onChange={(e) =>
                                  updateField(index, { searchable: e.target.checked })
                                }
                              />
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Paper>
              </Grid>
            </Grid>

            <Box sx={{ display: "flex", gap: 2, alignItems: "center", flexWrap: "wrap" }}>
              <Button variant="outlined" onClick={handleSave} disabled={update.isPending}>
                Save schema
              </Button>
              <Button
                variant="contained"
                onClick={handleIngest}
                disabled={ingestRunning || fields.length === 0 || !downloadReady}
              >
                {ingestRunning ? "Importing…" : "Import data"}
              </Button>
              {!downloadReady && fields.length > 0 && (
                <Typography variant="caption" color="text.secondary">
                  Import enabled after parquet download completes
                </Typography>
              )}
              {ingestDone && (
                <Button component={RouterLink} to="/" variant="text">
                  Browse dataset
                </Button>
              )}
              {ingestRunning && <CircularProgress size={20} />}
            </Box>

            {schema.ingest.status === "error" && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {schema.ingest.message}
              </Alert>
            )}

            {ingestDone && (
              <Alert severity="success" sx={{ mt: 2 }}>
                Imported {schema.ingest.row_count} rows.{" "}
                <Link component="button" onClick={() => navigate("/")}>
                  Go to browse
                </Link>
              </Alert>
            )}

            {(update.error || ingest.error || reparse.error || remove.error) && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {((update.error ?? ingest.error ?? reparse.error ?? remove.error) as Error)
                  .message}
              </Alert>
            )}

            <Dialog open={deleteOpen} onClose={() => setDeleteOpen(false)}>
              <DialogTitle>Delete dataset?</DialogTitle>
              <DialogContent>
                <DialogContentText>
                  This removes the schema, downloaded source files, and SQLite database for{" "}
                  <strong>{schema.name}</strong>. This cannot be undone.
                </DialogContentText>
              </DialogContent>
              <DialogActions>
                <Button onClick={() => setDeleteOpen(false)}>Cancel</Button>
                <Button color="error" onClick={handleDelete} disabled={remove.isPending}>
                  {remove.isPending ? "Deleting…" : "Delete"}
                </Button>
              </DialogActions>
            </Dialog>
          </>
        )}
      </Container>
    </AppLayout>
  );
}
