import { useMemo, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider, CssBaseline } from "@mui/material";
import { makeTheme } from "./theme";
import { ColorMode, ColorModeContext, COLOR_MODE_KEY, initialColorMode } from "./colorMode";
import App from "./App";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 60_000, refetchOnWindowFocus: false } },
});

// Providers + color-mode state; the mode persists to localStorage.
export default function Root() {
  const [mode, setMode] = useState<ColorMode>(initialColorMode);
  const colorMode = useMemo(
    () => ({
      mode,
      toggle: () =>
        setMode((m) => {
          const next = m === "light" ? "dark" : "light";
          localStorage.setItem(COLOR_MODE_KEY, next);
          return next;
        }),
    }),
    [mode],
  );
  const theme = useMemo(() => makeTheme(mode), [mode]);

  return (
    <QueryClientProvider client={queryClient}>
      <ColorModeContext.Provider value={colorMode}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <App />
        </ThemeProvider>
      </ColorModeContext.Provider>
    </QueryClientProvider>
  );
}
