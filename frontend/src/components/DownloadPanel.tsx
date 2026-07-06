import {
  Alert,
  Box,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Paper,
  Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import { DownloadStatus } from "../api/client";

function formatBytes(bytes?: number | null): string {
  if (!bytes) return "—";
  const mb = bytes / (1024 * 1024);
  if (mb < 1024) return `${mb.toFixed(0)} MB`;
  return `${(mb / 1024).toFixed(1)} GB`;
}

function stepIcon(done: boolean, active: boolean) {
  if (done) return <CheckCircleIcon color="success" fontSize="small" />;
  if (active) return <HourglassEmptyIcon color="primary" fontSize="small" />;
  return <RadioButtonUncheckedIcon color="disabled" fontSize="small" />;
}

interface Props {
  status: DownloadStatus;
}

export default function DownloadPanel({ status }: Props) {
  const s = status.status;
  const metadataDone = ["schema_ready", "downloading", "ready"].includes(s);
  const schemaDone = ["schema_ready", "downloading", "ready"].includes(s);
  const parquetDone = s === "ready";
  const parquetActive = s === "downloading" || s === "schema_ready";
  const metadataActive = s === "fetching_metadata";

  const parquetProgress =
    status.parquet_files_total && status.parquet_files_total > 0
      ? Math.min(
          100,
          Math.round(
            ((status.parquet_files_done ?? 0) / status.parquet_files_total) * 100,
          ),
        )
      : parquetDone
        ? 100
        : parquetActive
          ? 30
          : 0;

  return (
    <Paper variant="outlined" sx={{ p: 2, height: "100%" }}>
      <Typography variant="subtitle2" gutterBottom>
        Download progress
      </Typography>

      <List dense disablePadding>
        <ListItem disableGutters>
          <ListItemIcon sx={{ minWidth: 32 }}>
            {stepIcon(metadataDone, metadataActive)}
          </ListItemIcon>
          <ListItemText
            primary="Fetch metadata"
            secondary={metadataActive ? status.progress : metadataDone ? "Done" : "Pending"}
          />
        </ListItem>
        <ListItem disableGutters>
          <ListItemIcon sx={{ minWidth: 32 }}>
            {stepIcon(schemaDone, metadataActive && !schemaDone)}
          </ListItemIcon>
          <ListItemText
            primary="Extract schema"
            secondary={
              schemaDone
                ? `${status.field_count ?? 0} fields from ${status.schema_source ?? "card"}`
                : "Pending"
            }
          />
        </ListItem>
        <ListItem disableGutters>
          <ListItemIcon sx={{ minWidth: 32 }}>
            {stepIcon(parquetDone, parquetActive)}
          </ListItemIcon>
          <ListItemText
            primary="Download parquet"
            secondary={
              parquetDone
                ? `${status.parquet_files_done ?? status.parquet_files_total ?? 0} file(s)`
                : status.progress ?? "Pending"
            }
          />
        </ListItem>
      </List>

      {(parquetActive || parquetDone) && (
        <Box sx={{ mt: 2 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary">
              Parquet files
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {formatBytes(status.bytes_total)}
            </Typography>
          </Box>
          <LinearProgress variant="determinate" value={parquetProgress} />
        </Box>
      )}

      {status.message && s !== "ready" && (
        <Alert severity="info" sx={{ mt: 2 }}>
          {status.message}
        </Alert>
      )}

      {s === "error" && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {status.message ?? "Download failed"}
        </Alert>
      )}
    </Paper>
  );
}
