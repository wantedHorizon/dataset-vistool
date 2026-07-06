import { Box, CircularProgress, Dialog, DialogContent, DialogTitle, IconButton } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useSample } from "../hooks/queries";
import { useDatasetContext } from "../context/DatasetContext";
import JsonViewer from "./JsonViewer";

interface Props {
  id: number | null;
  onClose: () => void;
}

export default function SampleModal({ id, onClose }: Props) {
  const { activeDatasetId } = useDatasetContext();
  const open = id !== null;
  const { data, isLoading, error } = useSample(activeDatasetId, id);

  const title =
    data && (data.image_path ?? data.name)
      ? String(data.image_path ?? data.name)
      : id !== null
        ? `sample_${id}`
        : "Sample";

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        {title}
        <IconButton onClick={onClose} size="small">
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers>
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          {data?.image_url && (
            <Box sx={{ flexShrink: 0 }}>
              <img
                src={String(data.image_url)}
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
