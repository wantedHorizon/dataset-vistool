import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#2563eb" },
    background: { default: "#f6f7f9" },
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
  },
});
