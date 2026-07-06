import JsonView from "@uiw/react-json-view";
import { githubDarkTheme } from "@uiw/react-json-view/githubDark";
import { githubLightTheme } from "@uiw/react-json-view/githubLight";
import { useColorMode } from "../ColorModeProvider";

// Interactive, collapsible JSON tree (replaces the old static <pre> highlighter).
export default function JsonViewer({ value }: { value: unknown }) {
  const { mode } = useColorMode();
  const jsonTheme = mode === "dark" ? githubDarkTheme : githubLightTheme;

  return (
    <JsonView
      value={value as object}
      collapsed={2}
      displayDataTypes={false}
      style={{
        ...jsonTheme,
        padding: 12,
        borderRadius: 8,
        fontSize: 12.5,
        maxHeight: 420,
        overflow: "auto",
      }}
    />
  );
}
