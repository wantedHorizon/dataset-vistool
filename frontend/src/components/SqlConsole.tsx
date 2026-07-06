import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { useSql } from "../hooks/queries";
import { useDatasetContext } from "../context/DatasetContext";

const EXAMPLE = "SELECT id, split, image_path FROM samples LIMIT 20;";

export default function SqlConsole() {
  const { activeDatasetId } = useDatasetContext();
  const [query, setQuery] = useState(EXAMPLE);
  const { mutate, data, error, isPending } = useSql(activeDatasetId);

  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
      <Typography variant="subtitle2" gutterBottom>
        SQL query (read-only, table: <code>samples</code>)
      </Typography>
      <TextField
        multiline
        fullWidth
        minRows={3}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        sx={{ fontFamily: "monospace", mb: 1 }}
      />
      <Button
        variant="contained"
        size="small"
        startIcon={<PlayArrowIcon />}
        disabled={isPending || !activeDatasetId}
        onClick={() => mutate(query)}
      >
        Run
      </Button>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {(error as Error).message}
        </Alert>
      )}

      {data && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="caption" color="text.secondary">
            {data.row_count} row(s)
          </Typography>
          <TableContainer sx={{ maxHeight: 400, mt: 1 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  {data.columns.map((c) => (
                    <TableCell key={c}>{c}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {data.rows.map((row, i) => (
                  <TableRow key={i}>
                    {row.map((v, j) => (
                      <TableCell key={j} sx={{ maxWidth: 300, overflowWrap: "break-word" }}>
                        {v === null ? <em>null</em> : String(v)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}
    </Paper>
  );
}
