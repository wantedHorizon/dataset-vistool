import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createDataset,
  fetchActiveDataset,
  fetchDataset,
  fetchDatasets,
  fetchDownloadStatus,
  fetchSample,
  fetchSamples,
  fetchStats,
  FieldDef,
  runSql,
  SamplesParams,
  setActiveDataset,
  triggerIngest,
  updateDataset,
} from "../api/client";

export function useDatasets() {
  return useQuery({ queryKey: ["datasets"], queryFn: fetchDatasets });
}

export function useDataset(id: string | null) {
  return useQuery({
    queryKey: ["dataset", id],
    queryFn: () => fetchDataset(id as string),
    enabled: id !== null,
    refetchInterval: (query) =>
      query.state.data?.ingest.status === "running" ? 2000 : false,
  });
}

export function useActiveDatasetId() {
  return useQuery({ queryKey: ["activeDataset"], queryFn: fetchActiveDataset });
}

export function useSetActiveDataset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: setActiveDataset,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["activeDataset"] });
    },
  });
}

export function useCreateDataset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createDataset,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["datasets"] }),
  });
}

export function useDownloadStatus(id: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ["downloadStatus", id],
    queryFn: () => fetchDownloadStatus(id as string),
    enabled: id !== null && enabled,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "downloading" || s === "parsing" ? 1500 : false;
    },
  });
}

export function useUpdateDataset(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name?: string; fields?: FieldDef[] }) => updateDataset(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dataset", id] });
      qc.invalidateQueries({ queryKey: ["datasets"] });
    },
  });
}

export function useTriggerIngest(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (force?: boolean) => triggerIngest(id, force),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dataset", id] });
      qc.invalidateQueries({ queryKey: ["datasets"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
      qc.invalidateQueries({ queryKey: ["samples"] });
    },
  });
}

export function useStats(datasetId: string | null) {
  return useQuery({
    queryKey: ["stats", datasetId],
    queryFn: () => fetchStats(datasetId as string),
    enabled: datasetId !== null,
  });
}

export function useSamples(params: SamplesParams | null) {
  return useQuery({
    queryKey: ["samples", params],
    queryFn: () => fetchSamples(params as SamplesParams),
    enabled: params !== null,
    placeholderData: keepPreviousData,
  });
}

export function useSample(datasetId: string | null, id: number | null) {
  return useQuery({
    queryKey: ["sample", datasetId, id],
    queryFn: () => fetchSample(datasetId as string, id as number),
    enabled: datasetId !== null && id !== null,
  });
}

export function useSql(datasetId: string | null) {
  return useMutation({
    mutationFn: (query: string) => runSql(datasetId as string, query),
  });
}
