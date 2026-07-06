import { describe, expect, it, beforeEach, vi } from "vitest";
import { loadVisibleColumns, saveVisibleColumns } from "./columnStorage";

const store = new Map<string, string>();

describe("columnStorage", () => {
  beforeEach(() => {
    store.clear();
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => {
        store.set(key, value);
      },
      removeItem: (key: string) => {
        store.delete(key);
      },
      clear: () => store.clear(),
    });
  });

  it("round-trips visible columns per dataset", () => {
    saveVisibleColumns("flickr8k", ["name", "id", "image"]);
    expect(loadVisibleColumns("flickr8k", ["name", "id"], ["name", "id", "image", "captions"])).toEqual(
      ["name", "id", "image"],
    );
  });

  it("migrates image_path to name when loading", () => {
    store.set(
      "explorer.flickr8k.visibleColumns",
      JSON.stringify(["image_path", "id", "image", "captions"]),
    );
    expect(
      loadVisibleColumns("flickr8k", ["name", "id", "image", "captions"], [
        "name",
        "id",
        "image",
        "captions",
        "split",
      ]),
    ).toEqual(["name", "id", "image", "captions"]);
  });

  it("falls back to defaults when nothing saved", () => {
    expect(
      loadVisibleColumns("flickr8k", ["name", "id", "image", "captions"], [
        "name",
        "id",
        "image",
        "captions",
      ]),
    ).toEqual(["name", "id", "image", "captions"]);
  });

  it("drops keys that are not valid for the current schema", () => {
    saveVisibleColumns("flickr8k", ["name", "id", "removed_col"]);
    expect(
      loadVisibleColumns("flickr8k", ["name", "id", "image"], ["name", "id", "image"]),
    ).toEqual(["name", "id"]);
  });
});
