import { describe, expect, it } from "vitest";
import { DatasetSchema } from "../api/client";
import { defaultVisibleKeys } from "./tableColumns";

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
  it("includes id, name (image_path), image, and captions for Flickr8k", () => {
    const keys = defaultVisibleKeys(flickr8kSchema);
    expect(keys).toContain("id");
    expect(keys).toContain("image_path");
    expect(keys).toContain("image");
    expect(keys).toContain("captions");
  });
});
