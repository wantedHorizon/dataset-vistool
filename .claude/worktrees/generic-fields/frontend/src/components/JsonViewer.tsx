import JsonView from "@uiw/react-json-view";
import { githubDarkTheme } from "@uiw/react-json-view/githubDark";
import { githubLightTheme } from "@uiw/react-json-view/githubLight";
import { useTheme } from "@mui/material";

// Interactive, collapsible JSON tree (replaces the old static <pre> highlighter).
export default function JsonViewer({ value }: { value: unknown }) {
  const mode = useTheme().palette.mode;
  return (
    <JsonView
      value={value as object}
      collapsed={2}
      displayDataTypes={false}
      style={{
        ...(mode === "dark" ? githubDarkTheme : githubLightTheme),
        padding: 12,
        borderRadius: 8,
        fontSize: 12.5,
        maxHeight: 420,
        overflow: "auto",
      }}
    />
  );
}
