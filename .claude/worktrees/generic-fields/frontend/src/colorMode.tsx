import { createContext, useContext } from "react";

export type ColorMode = "light" | "dark";

export const COLOR_MODE_KEY = "color-mode";

export function initialColorMode(): ColorMode {
  const stored = localStorage.getItem(COLOR_MODE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export const ColorModeContext = createContext<{ mode: ColorMode; toggle: () => void }>({
  mode: "light",
  toggle: () => {},
});

export function useColorMode() {
  return useContext(ColorModeContext);
}
