import { createTheme } from "@mui/material/styles";
import { ColorMode } from "./colorMode";

export function makeTheme(mode: ColorMode) {
  return createTheme({
    palette: {
      mode,
      primary: { main: "#2563eb" },
      ...(mode === "light" ? { background: { default: "#f6f7f9" } } : {}),
    },
    shape: { borderRadius: 8 },
    typography: {
      fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
    },
  });
}
