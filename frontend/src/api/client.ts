// Typed wrappers around the backend API. All URLs are same-origin (/api/*),
// proxied to FastAPI in dev and served by nginx in production.

export interface Sample {
  id: number;
  split: string;
  image_path: string | null;
  captions: string[];
  width: number | null;
  height: number | null;
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
