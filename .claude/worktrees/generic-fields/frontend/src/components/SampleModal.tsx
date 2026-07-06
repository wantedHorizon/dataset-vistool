import { Box, CircularProgress, Dialog, DialogContent, DialogTitle, IconButton } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useSample } from "../hooks/queries";
import JsonViewer from "./JsonViewer";

interface Props {
  id: number | null;
  onClose: () => void;
}

// Full sample detail (image + JSON) shown in a modal. Only one instance is ever
// rendered, so "only one open at a time" is structural rather than state-tracked.
export default function SampleModal({ id, onClose }: Props) {
  const open = id !== null;
  const { data, isLoading, error } = useSample(id);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        {data ? data.name : "Sample"}
        <IconButton onClick={onClose} size="small">
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers>
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          {id !== null && (
            <Box sx={{ flexShrink: 0 }}>
              <img
                src={`/api/images/${id}`}
                alt={`sample ${id}`}
                style={{ maxWidth: 280, maxHeight: 280, borderRadius: 8, display: "block" }}
              />
            </Box>
          )}
          <Box sx={{ flex: 1, minWidth: 240 }}>
            {isLoading && <CircularProgress size={20} />}
            {error && <Box color="error.main">{(error as Error).message}</Box>}
            {data && <JsonViewer value={data} />}
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
