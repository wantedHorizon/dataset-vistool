import { ReactNode } from "react";
import {
  AppBar,
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Toolbar as MuiToolbar,
  Typography,
} from "@mui/material";
import StorageIcon from "@mui/icons-material/Storage";
import { Link as RouterLink, useLocation } from "react-router-dom";
import DarkModeToggle from "./DarkModeToggle";
import { useDatasetContext } from "../context/DatasetContext";

interface Props {
  children: ReactNode;
  showDatasetSelector?: boolean;
}

export default function AppLayout({ children, showDatasetSelector = false }: Props) {
  const { ingestedDatasets, activeDatasetId, setActiveDatasetId } = useDatasetContext();
  const location = useLocation();

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <AppBar
        position="static"
        color="default"
        elevation={0}
        sx={{ borderBottom: 1, borderColor: "divider" }}
      >
        <MuiToolbar>
          <StorageIcon sx={{ mr: 1 }} />
          <Typography variant="h6" component="div" sx={{ mr: 3 }}>
            Dataset Explorer
          </Typography>

          <Button
            component={RouterLink}
            to="/"
            color={location.pathname === "/" ? "primary" : "inherit"}
            size="small"
          >
            Browse
          </Button>
          <Button
            component={RouterLink}
            to="/datasets/new"
            color={location.pathname.startsWith("/datasets") ? "primary" : "inherit"}
            size="small"
            sx={{ ml: 1 }}
          >
            Add Dataset
          </Button>

          <Box sx={{ flexGrow: 1 }} />

          {showDatasetSelector && ingestedDatasets.length > 0 && (
            <FormControl size="small" sx={{ minWidth: 180, mr: 2 }}>
              <InputLabel id="dataset-select-label">Dataset</InputLabel>
              <Select
                labelId="dataset-select-label"
                label="Dataset"
                value={activeDatasetId ?? ""}
                onChange={(e) => setActiveDatasetId(e.target.value)}
              >
                {ingestedDatasets.map((d) => (
                  <MenuItem key={d.id} value={d.id}>
                    {d.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          <DarkModeToggle />
        </MuiToolbar>
      </AppBar>
      {children}
    </Box>
  );
}
