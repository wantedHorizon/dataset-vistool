// Typed wrappers around the backend API. All URLs are same-origin (/api/*),
// proxied to FastAPI in dev and served by nginx in production.

// Field metadata served from /api/fields — the backend reads it from the
// repo-root fields.json, the single source of truth for dataset columns.
export interface FieldMeta {
  key: string;
  label: string;
  type: "string" | "integer" | "string_list";
  role?: "name" | "split" | null;
  visible: boolean;
  searchable: boolean;
  // Item count for string_list fields (null for scalars); drives per-item
  // table columns like "caption 1" … "caption N".
  item_count?: number | null;
}

export interface DatasetMeta {
  name: string;
  title: string;
}

export interface FieldsResponse {
  dataset: DatasetMeta;
  fields: FieldMeta[];
}

export interface Sample {
  id: number;
  name: string;
  fields: Record<string, unknown>;
  image_url: string;
  thumb_url: string;
}

export interface SamplesPage {
  total: number;
  page: number;
  page_size: number;
  rows: Sample[];
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

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore parse errors */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export interface SamplesParams {
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
  return handle<SamplesPage>(await fetch(`/api/samples?${q.toString()}`));
}

export async function fetchSample(id: number): Promise<Sample> {
  return handle<Sample>(await fetch(`/api/samples/${id}`));
}

export async function fetchFields(): Promise<FieldsResponse> {
  return handle<FieldsResponse>(await fetch("/api/fields"));
}

export async function fetchStats(): Promise<Stats> {
  return handle<Stats>(await fetch("/api/stats"));
}

export async function runSql(query: string): Promise<SqlResponse> {
  return handle<SqlResponse>(
    await fetch("/api/sql", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    }),
  );
}
