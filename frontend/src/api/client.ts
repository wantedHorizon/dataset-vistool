// Typed wrappers around the backend API. All URLs are same-origin (/api/*).

export type FieldType = "text" | "text_list" | "image" | "integer" | "split" | "blob";

export interface FieldDef {
  name: string;
  source: string;
  type: FieldType;
  visible: boolean;
  searchable: boolean;
  group_members?: string[] | null;
}

export interface DatasetSchema {
  id: string;
  name: string;
  source_url?: string | null;
  source: {
    type: string;
    path: string;
    split: { strategy: string; column?: string | null; values?: string[] | null };
  };
  fields: FieldDef[];
  ingest: { status: string; message?: string | null; row_count: number };
  download: DownloadStatus;
}

export interface DownloadStatus {
  status: string;
  progress?: string | null;
  message?: string | null;
  phase?: string | null;
  schema_source?: string | null;
  field_count?: number;
  bytes_total?: number | null;
  parquet_files_total?: number;
  parquet_files_done?: number;
}

export interface DatasetSummary {
  id: string;
  name: string;
  source_url?: string | null;
  download_status: string;
  ingest_status: string;
  row_count: number;
}

export type SampleRecord = Record<string, unknown> & {
  id: number;
  image_url?: string;
  thumb_url?: string;
};

export interface SamplesPage {
  total: number;
  page: number;
  page_size: number;
  rows: SampleRecord[];
}

export interface Stats {
  total: number;
  splits: Record<string, number>;
}

export interface SqlResponse {
  columns: string[];
  rows: unknown[][];
  row_count: number;
}

export interface ReparseResponse {
  fields: FieldDef[];
  warnings: string[];
  schema_source?: string | null;
}

function formatDetail(detail: unknown, fallback: string): string {
  if (detail == null) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) =>
        typeof item === "object" && item && "msg" in item
          ? String((item as { msg: unknown }).msg)
          : String(item),
      )
      .join("; ");
  }
  return String(detail);
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = formatDetail(body.detail, detail);
    } catch {
      /* ignore */
    }
    throw new Error(String(detail));
  }
  return res.json() as Promise<T>;
}

function dsBase(datasetId: string) {
  return `/api/datasets/${datasetId}`;
}

// --- Datasets ---

export async function fetchDatasets(): Promise<DatasetSummary[]> {
  return handle(await fetch("/api/datasets"));
}

export async function createDataset(url: string): Promise<{ id: string; status: string }> {
  return handle(
    await fetch("/api/datasets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    }),
  );
}

export async function fetchDataset(id: string): Promise<DatasetSchema> {
  return handle(await fetch(dsBase(id)));
}

export async function updateDataset(
  id: string,
  body: { name?: string; fields?: FieldDef[] },
): Promise<DatasetSchema> {
  return handle(
    await fetch(dsBase(id), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function deleteDataset(id: string): Promise<void> {
  await handle(await fetch(dsBase(id), { method: "DELETE" }));
}

export async function fetchDownloadStatus(id: string): Promise<DownloadStatus> {
  return handle(await fetch(`${dsBase(id)}/download-status`));
}

export async function triggerIngest(id: string, force = false): Promise<{ status: string; row_count: number }> {
  const q = force ? "?force=true" : "";
  return handle(await fetch(`${dsBase(id)}/ingest${q}`, { method: "POST" }));
}

export async function reparseSchema(id: string): Promise<ReparseResponse> {
  return handle(await fetch(`${dsBase(id)}/schema/reparse`, { method: "POST" }));
}

export async function fetchActiveDataset(): Promise<{ id: string | null }> {
  return handle(await fetch("/api/active-dataset"));
}

export async function setActiveDataset(id: string): Promise<{ id: string | null }> {
  return handle(
    await fetch("/api/active-dataset", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    }),
  );
}

// --- Browse ---

export interface SamplesParams {
  datasetId: string;
  split?: string;
  search?: string;
  page: number;
  pageSize: number;
}

export async function fetchSamples(p: SamplesParams): Promise<SamplesPage> {
  const q = new URLSearchParams();
  if (p.split) q.set("split", p.split);
  if (p.search) q.set("search", p.search);
  q.set("page", String(p.page));
  q.set("page_size", String(p.pageSize));
  return handle(await fetch(`${dsBase(p.datasetId)}/samples?${q.toString()}`));
}

export async function fetchSample(datasetId: string, id: number): Promise<SampleRecord> {
  return handle(await fetch(`${dsBase(datasetId)}/samples/${id}`));
}

export async function fetchStats(datasetId: string): Promise<Stats> {
  return handle(await fetch(`${dsBase(datasetId)}/stats`));
}

export async function runSql(datasetId: string, query: string): Promise<SqlResponse> {
  return handle(
    await fetch(`${dsBase(datasetId)}/sql`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    }),
  );
}

// --- Batch download ---

export type DownloadMode = "ids" | "all" | "range";

export interface DownloadRequest {
  mode: DownloadMode;
  split?: string;
  search?: string;
  ids?: number[];
  offset?: number;
  limit?: number;
  exclude_ids?: number[];
}

export async function downloadSamples(datasetId: string, req: DownloadRequest): Promise<void> {
  const res = await fetch(`${dsBase(datasetId)}/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = formatDetail(body.detail, detail);
    } catch {
      /* ignore */
    }
    throw new Error(String(detail));
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${datasetId}-samples.zip`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
