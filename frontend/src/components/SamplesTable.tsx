import {
  Box,
  Chip,
  IconButton,
  Link,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
} from "@mui/material";
import DataObjectIcon from "@mui/icons-material/DataObject";
import { Sample } from "../api/client";

interface Props {
  rows: Sample[];
  onOpenSample: (id: number) => void;
}

// "Viewer" mode, styled after the Hugging Face dataset viewer: a thumbnail,
// a clickable image name, and the captions. Clicking either opens the JSON modal.
export default function SamplesTable({ rows, onOpenSample }: Props) {
  return (
    <TableContainer sx={{ bgcolor: "#fff", borderRadius: 2, border: "1px solid #e2e8f0" }}>
      <Table size="small" stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell width={130}>image</TableCell>
            <TableCell width={200}>name</TableCell>
            <TableCell>captions</TableCell>
            <TableCell width={56} />
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => {
            const name = row.image_path || `sample_${row.id}`;
            return (
              <TableRow hover key={row.id}>
                <TableCell>
                  <img
                    src={row.thumb_url}
                    alt={name}
                    loading="lazy"
                    style={{
                      width: 110,
                      height: 90,
                      objectFit: "cover",
                      borderRadius: 6,
                      cursor: "pointer",
                      background: "#e2e8f0",
                    }}
                    onClick={() => onOpenSample(row.id)}
                  />
                </TableCell>
                <TableCell>
                  <Link
                    component="button"
                    underline="hover"
                    onClick={() => onOpenSample(row.id)}
                    sx={{ textAlign: "left", wordBreak: "break-all", fontWeight: 600 }}
                  >
                    {name}
                  </Link>
                  <Box sx={{ mt: 0.5 }}>
                    <Chip label={row.split} size="small" variant="outlined" />
                    {row.width && (
                      <Chip
                        label={`${row.width}×${row.height}`}
                        size="small"
                        variant="outlined"
                        sx={{ ml: 0.5 }}
                      />
                    )}
                  </Box>
                </TableCell>
                <TableCell>
                  <Box component="ol" sx={{ m: 0, pl: 2.5 }}>
                    {row.captions.map((c, i) => (
                      <li key={i} style={{ marginBottom: 2 }}>
                        {c}
                      </li>
                    ))}
                  </Box>
                </TableCell>
                <TableCell>
                  <Tooltip title="View JSON">
                    <IconButton size="small" onClick={() => onOpenSample(row.id)}>
                      <DataObjectIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
