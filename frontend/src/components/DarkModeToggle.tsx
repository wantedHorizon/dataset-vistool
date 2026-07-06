import { Button, Tooltip } from "@mui/material";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import LightModeIcon from "@mui/icons-material/LightMode";
import { useColorMode } from "../ColorModeProvider";

export default function DarkModeToggle() {
  const { mode, toggleColorMode } = useColorMode();
  const isDark = mode === "dark";
  const label = isDark ? "Light mode" : "Dark mode";

  return (
    <Tooltip title={label}>
      <Button
        size="small"
        variant="outlined"
        onClick={toggleColorMode}
        aria-label="toggle color mode"
        startIcon={isDark ? <LightModeIcon /> : <DarkModeIcon />}
        sx={{ ml: 1 }}
      >
        {isDark ? "Light" : "Dark"}
      </Button>
    </Tooltip>
  );
}
