import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import { useActiveDatasetId, useDatasets, useSetActiveDataset } from "../hooks/queries";

const STORAGE_KEY = "explorer.activeDataset";

interface DatasetContextValue {
  datasets: ReturnType<typeof useDatasets>["data"];
  activeDatasetId: string | null;
  setActiveDatasetId: (id: string) => void;
  isLoading: boolean;
  ingestedDatasets: { id: string; name: string }[];
}

const DatasetContext = createContext<DatasetContextValue | null>(null);

export function DatasetProvider({ children }: { children: ReactNode }) {
  const { data: datasets, isLoading: dsLoading } = useDatasets();
  const { data: activeData, isLoading: activeLoading } = useActiveDatasetId();
  const setActive = useSetActiveDataset();
  const [localId, setLocalId] = useState<string | null>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  });

  const ingestedDatasets = useMemo(
    () =>
      (datasets ?? [])
        .filter((d) => d.ingest_status === "done")
        .map((d) => ({ id: d.id, name: d.name })),
    [datasets],
  );

  const activeDatasetId = useMemo(() => {
    const serverId = activeData?.id ?? null;
    const candidate = localId ?? serverId;
    if (candidate && ingestedDatasets.some((d) => d.id === candidate)) {
      return candidate;
    }
    return ingestedDatasets[0]?.id ?? null;
  }, [activeData, localId, ingestedDatasets]);

  useEffect(() => {
    if (activeDatasetId) {
      localStorage.setItem(STORAGE_KEY, activeDatasetId);
      if (activeData?.id !== activeDatasetId) {
        setActive.mutate(activeDatasetId);
      }
    }
  }, [activeDatasetId]); // eslint-disable-line react-hooks/exhaustive-deps

  const value: DatasetContextValue = {
    datasets,
    activeDatasetId,
    setActiveDatasetId: (id: string) => {
      setLocalId(id);
      setActive.mutate(id);
    },
    isLoading: dsLoading || activeLoading,
    ingestedDatasets,
  };

  return <DatasetContext.Provider value={value}>{children}</DatasetContext.Provider>;
}

export function useDatasetContext() {
  const ctx = useContext(DatasetContext);
  if (!ctx) throw new Error("useDatasetContext must be used within DatasetProvider");
  return ctx;
}
