import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Link,
  TextField,
  Typography,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import { DownloadRequest } from "../api/client";

const MAX_DOWNLOAD_ROWS = 2000;

interface Props {
  total: number;
  includedCount: number;
  excludedCount: number;
  selectAllMatching: boolean;
  onSelectAllMatching: () => void;
  onClearSelection: () => void;
  isPending: boolean;
  error: string | null;
  onDownload: (req: Omit<DownloadRequest, "split" | "search">) => void;
}

export default function DownloadBar({
  total,
  includedCount,
  excludedCount,
  selectAllMatching,
  onSelectAllMatching,
  onClearSelection,
  isPending,
  error,
  onDownload,
}: Props) {
  const [rangeOpen, setRangeOpen] = useState(false);
  const [from, setFrom] = useState("1");
  const [to, setTo] = useState(String(Math.min(total, 50) || 1));
  const [rangeError, setRangeError] = useState<string | null>(null);

  const openRange = () => {
    setFrom("1");
    setTo(String(Math.min(total, 50) || 1));
    setRangeError(null);
    setRangeOpen(true);
  };

  const submitRange = () => {
    const start = parseInt(from, 10);
    const end = parseInt(to, 10);
    if (!Number.isFinite(start) || !Number.isFinite(end)) {
      setRangeError("Enter valid numbers");
      return;
    }
    if (start < 1 || end < start || end > total) {
      setRangeError(`Range must be within 1–${total} (from ≤ to)`);
      return;
    }
    if (end - start + 1 > MAX_DOWNLOAD_ROWS) {
      setRangeError(`Range cannot exceed ${MAX_DOWNLOAD_ROWS} rows`);
      return;
    }
    setRangeOpen(false);
    onDownload({
      mode: "range",
      offset: start - 1,
      limit: end - start + 1,
    });
  };

  const downloadAll = () => {
    if (total > MAX_DOWNLOAD_ROWS) {
      const ok = window.confirm(
        `This filter matches ${total} samples (max download is ${MAX_DOWNLOAD_ROWS}). ` +
          "The server will reject this request. Continue anyway?",
      );
      if (!ok) return;
    }
    onDownload({ mode: "all" });
  };

  return (
    <Box sx={{ mb: 2 }}>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: 1.5,
          alignItems: "center",
        }}
      >
        <Typography variant="body2" color="text.secondary">
          {includedCount} selected · {excludedCount} excluded
          {selectAllMatching ? " · all matching" : ""}
        </Typography>

        {!selectAllMatching && total > 0 && (
          <Link
            component="button"
            type="button"
            variant="body2"
            onClick={onSelectAllMatching}
            disabled={isPending}
          >
            Select all {total} matching this filter
          </Link>
        )}

        {(includedCount > 0 || excludedCount > 0 || selectAllMatching) && (
          <Link
            component="button"
            type="button"
            variant="body2"
            onClick={onClearSelection}
            disabled={isPending}
          >
            Clear
          </Link>
        )}

        <Box sx={{ flex: 1 }} />

        <Button
          size="small"
          variant="outlined"
          startIcon={isPending ? <CircularProgress size={14} /> : <DownloadIcon />}
          disabled={isPending || includedCount === 0}
          onClick={() => onDownload({ mode: "ids" })}
        >
          Download selected
        </Button>
        <Button
          size="small"
          variant="outlined"
          startIcon={isPending ? <CircularProgress size={14} /> : <DownloadIcon />}
          disabled={isPending || total === 0}
          onClick={downloadAll}
        >
          Download all ({total})
        </Button>
        <Button
          size="small"
          variant="outlined"
          startIcon={isPending ? <CircularProgress size={14} /> : <DownloadIcon />}
          disabled={isPending || total === 0}
          onClick={openRange}
        >
          Download range…
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mt: 1 }}>
          {error}
        </Alert>
      )}

      <Dialog open={rangeOpen} onClose={() => setRangeOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Download range</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            1-based positions in the current filtered results (1–{total}).
          </Typography>
          <Box sx={{ display: "flex", gap: 2 }}>
            <TextField
              label="From"
              type="number"
              size="small"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              inputProps={{ min: 1, max: total }}
              fullWidth
            />
            <TextField
              label="To"
              type="number"
              size="small"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              inputProps={{ min: 1, max: total }}
              fullWidth
            />
          </Box>
          {rangeError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {rangeError}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRangeOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={submitRange} disabled={isPending}>
            Download
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
