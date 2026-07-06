import JsonView from "@uiw/react-json-view";
import { githubDarkTheme } from "@uiw/react-json-view/githubDark";

// Interactive, collapsible JSON tree (replaces the old static <pre> highlighter).
export default function JsonViewer({ value }: { value: unknown }) {
  return (
    <JsonView
      value={value as object}
      collapsed={2}
      displayDataTypes={false}
      style={{
        ...githubDarkTheme,
        padding: 12,
        borderRadius: 8,
        fontSize: 12.5,
        maxHeight: 420,
        overflow: "auto",
      }}
    />
  );
}
