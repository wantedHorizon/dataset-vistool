import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import AppLayout from "../components/AppLayout";
import { useCreateDataset, useDownloadStatus } from "../hooks/queries";

export default function AddDataset() {
  const [url, setUrl] = useState("https://huggingface.co/datasets/jxie/flickr8k");
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const create = useCreateDataset();
  const navigate = useNavigate();
  const { data: status } = useDownloadStatus(
    datasetId,
    datasetId !== null && create.isSuccess,
  );

  useEffect(() => {
    if (
      (status?.status === "schema_ready" || status?.status === "ready") &&
      datasetId
    ) {
      navigate(`/datasets/${datasetId}/schema`);
    }
  }, [status?.status, datasetId, navigate]);

  const handleSubmit = async () => {
    const result = await create.mutateAsync(url.trim());
    setDatasetId(result.id);
  };

  const isWorking =
    create.isPending ||
    status?.status === "fetching_metadata" ||
    status?.status === "downloading" ||
    status?.status === "schema_ready" ||
    status?.status === "parsing";

  return (
    <AppLayout>
      <Container maxWidth="sm" sx={{ py: 4 }}>
        <Typography variant="h5" gutterBottom>
          Add Dataset
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Paste a HuggingFace dataset URL. Schema is extracted from the dataset card immediately;
          parquet files download in the background while you edit fields.
        </Typography>

        <Paper variant="outlined" sx={{ p: 3 }}>
          <TextField
            fullWidth
            label="HuggingFace dataset URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://huggingface.co/datasets/org/name"
            disabled={isWorking}
            sx={{ mb: 2 }}
          />

          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={!url.trim() || isWorking}
          >
            {isWorking ? "Working…" : "Add Dataset"}
          </Button>

          {create.error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {(create.error as Error).message}
            </Alert>
          )}

          {isWorking && (
            <Box sx={{ display: "flex", alignItems: "center", gap: 2, mt: 3 }}>
              <CircularProgress size={24} />
              <Box>
                <Typography variant="body2">
                  {status?.progress ?? "Starting download…"}
                </Typography>
                {status?.message && (
                  <Typography variant="caption" color="text.secondary">
                    {status.message}
                  </Typography>
                )}
              </Box>
            </Box>
          )}

          {status?.status === "error" && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {status.message ?? "Download failed"}
            </Alert>
          )}
        </Paper>
      </Container>
    </AppLayout>
  );
}
