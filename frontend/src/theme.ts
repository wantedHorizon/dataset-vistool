import { createTheme } from "@mui/material/styles";
import type { PaletteMode } from "@mui/material";

export function getTheme(mode: PaletteMode) {
  return createTheme({
    palette: {
      mode,
      primary: { main: "#2563eb" },
      ...(mode === "light"
        ? { background: { default: "#f6f7f9" } }
        : { background: { default: "#0f172a" } }),
    },
    shape: { borderRadius: 8 },
    typography: {
      fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
    },
  });
}
