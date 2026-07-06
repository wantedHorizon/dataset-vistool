import { useEffect, useState } from "react";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Container,
  FormControl,
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
import { FieldDef, FieldType } from "../api/client";
import { useDataset, useTriggerIngest, useUpdateDataset } from "../hooks/queries";

const FIELD_TYPES: FieldType[] = ["text", "text_list", "image", "integer", "split", "blob"];

export default function SchemaEditor() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: schema, isLoading, error } = useDataset(id ?? null);
  const update = useUpdateDataset(id ?? "");
  const ingest = useTriggerIngest(id ?? "");
  const [fields, setFields] = useState<FieldDef[]>([]);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (schema?.fields) {
      setFields(schema.fields);
      setSaved(false);
    }
  }, [schema]);

  if (!id) return null;

  const handleSave = async () => {
    await update.mutateAsync({ fields });
    setSaved(true);
  };

  const handleIngest = async () => {
    if (!saved) await handleSave();
    await ingest.mutateAsync(false);
  };

  const updateField = (index: number, patch: Partial<FieldDef>) => {
    setFields((prev) => prev.map((f, i) => (i === index ? { ...f, ...patch } : f)));
    setSaved(false);
  };

  const ingestDone = schema?.ingest.status === "done";
  const ingestRunning = schema?.ingest.status === "running" || ingest.isPending;

  return (
    <AppLayout>
      <Container maxWidth="lg" sx={{ py: 4 }}>
        {isLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
            <CircularProgress />
          </Box>
        )}

        {error && <Alert severity="error">{(error as Error).message}</Alert>}

        {schema && (
          <>
            <Typography variant="h5" gutterBottom>
              Schema: {schema.name}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {schema.source_url}
            </Typography>

            {schema.download.message && (
              <Alert severity="info" sx={{ mb: 2 }}>
                {schema.download.message}
              </Alert>
            )}

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
                    {fields.map((field, i) => (
                      <TableRow key={`${field.name}-${i}`}>
                        <TableCell>{field.name}</TableCell>
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
                                updateField(i, { type: e.target.value as FieldType })
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
                            onChange={(e) => updateField(i, { visible: e.target.checked })}
                          />
                        </TableCell>
                        <TableCell>
                          <Checkbox
                            checked={field.searchable}
                            disabled={field.type === "image" || field.type === "blob"}
                            onChange={(e) =>
                              updateField(i, { searchable: e.target.checked })
                            }
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>

            <Paper variant="outlined" sx={{ p: 2, mb: 3, bgcolor: "action.hover" }}>
              <Typography variant="subtitle2" gutterBottom>
                Ingest mapping
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Parquet ({schema.source.path}) → SQLite table <code>samples</code> → API →
                browse table. Split inferred from parquet filename prefix. Image fields decode
                bytes and generate width, height, and thumbnail columns.
              </Typography>
            </Paper>

            <Box sx={{ display: "flex", gap: 2, alignItems: "center", flexWrap: "wrap" }}>
              <Button
                variant="outlined"
                onClick={handleSave}
                disabled={update.isPending}
              >
                Save schema
              </Button>
              <Button
                variant="contained"
                onClick={handleIngest}
                disabled={ingestRunning || fields.length === 0}
              >
                {ingestRunning ? "Importing…" : "Import data"}
              </Button>
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

            {(update.error || ingest.error) && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {((update.error ?? ingest.error) as Error).message}
              </Alert>
            )}
          </>
        )}
      </Container>
    </AppLayout>
  );
}
