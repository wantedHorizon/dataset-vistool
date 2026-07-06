const storageKey = (datasetId: string) => `explorer.${datasetId}.visibleColumns`;

function migrateColumnKey(key: string): string {
  return key === "image_path" ? "name" : key;
}

/** Load saved visible column keys, falling back to defaults. */
export function loadVisibleColumns(
  datasetId: string,
  defaults: string[],
  validKeys: string[],
): string[] {
  const valid = new Set(validKeys);
  try {
    const raw = localStorage.getItem(storageKey(datasetId));
    if (raw) {
      const saved = (JSON.parse(raw) as string[]).map(migrateColumnKey);
      const filtered = saved.filter((k) => valid.has(k));
      if (filtered.length > 0) return filtered;
    }
  } catch {
    /* ignore corrupt storage */
  }
  return defaults.filter((k) => valid.has(k));
}

/** Persist visible column keys for a dataset. */
export function saveVisibleColumns(datasetId: string, columns: string[]): void {
  try {
    localStorage.setItem(storageKey(datasetId), JSON.stringify(columns));
  } catch {
    /* ignore quota / private mode */
  }
}
