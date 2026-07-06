import { describe, expect, it } from "vitest";
import { DatasetSchema } from "../api/client";
import { buildColumns, defaultVisibleKeys } from "./tableColumns";

/** Fixture matching Flickr8k fields after card_mapper post-process. */
const flickr8kSchema: DatasetSchema = {
  id: "flickr8k",
  name: "Flickr8k",
  source_url: "https://huggingface.co/datasets/jxie/flickr8k",
  source: {
    type: "parquet",
    path: "/data/parquet",
    split: { strategy: "filename_prefix", values: ["train", "validation", "test"] },
  },
  fields: [
    {
      name: "image_path",
      source: "image.path",
      type: "text",
      visible: true,
      searchable: false,
    },
    {
      name: "image",
      source: "image.bytes",
      type: "image",
      visible: true,
      searchable: false,
    },
    {
      name: "caption_0",
      source: "caption_0",
      type: "text",
      visible: false,
      searchable: true,
    },
    {
      name: "caption_1",
      source: "caption_1",
      type: "text",
      visible: false,
      searchable: true,
    },
    {
      name: "caption_2",
      source: "caption_2",
      type: "text",
      visible: false,
      searchable: true,
    },
    {
      name: "caption_3",
      source: "caption_3",
      type: "text",
      visible: false,
      searchable: true,
    },
    {
      name: "caption_4",
      source: "caption_4",
      type: "text",
      visible: false,
      searchable: true,
    },
    {
      name: "captions",
      source: "captions",
      type: "text_list",
      visible: true,
      searchable: true,
      group_members: ["caption_0", "caption_1", "caption_2", "caption_3", "caption_4"],
    },
    {
      name: "split",
      source: "_split",
      type: "split",
      visible: true,
      searchable: false,
    },
  ],
  ingest: { status: "done", row_count: 8000 },
  download: { status: "ready" },
};

describe("defaultVisibleKeys", () => {
  it("returns name, id, image, captions in order for Flickr8k", () => {
    expect(defaultVisibleKeys(flickr8kSchema)).toEqual(["name", "id", "image", "captions"]);
    expect(defaultVisibleKeys(flickr8kSchema)).not.toContain("split");
    expect(defaultVisibleKeys(flickr8kSchema)).not.toContain("image_path");
  });
});

describe("buildColumns", () => {
  it("orders preferred columns before split and actions", () => {
    const keys = buildColumns(flickr8kSchema).map((c) => c.key);
    expect(keys.slice(0, 4)).toEqual(["name", "id", "image", "captions"]);
    expect(keys[keys.length - 1]).toBe("actions");
  });

  it("includes name column when schema has no image_path field", () => {
    const schemaWithoutPath: DatasetSchema = {
      ...flickr8kSchema,
      fields: flickr8kSchema.fields.filter((f) => f.name !== "image_path"),
    };
    expect(defaultVisibleKeys(schemaWithoutPath)).toEqual(["name", "id", "image", "captions"]);
    expect(buildColumns(schemaWithoutPath).some((c) => c.key === "name")).toBe(true);
  });
});
