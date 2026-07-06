import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import {
  fetchFields,
  fetchSample,
  fetchSamples,
  fetchStats,
  runSql,
  SamplesParams,
} from "../api/client";

export function useFields() {
  // Static metadata for the process lifetime — never refetch.
  return useQuery({ queryKey: ["fields"], queryFn: fetchFields, staleTime: Infinity });
}

export function useStats() {
  return useQuery({ queryKey: ["stats"], queryFn: fetchStats });
}

export function useSamples(params: SamplesParams) {
  return useQuery({
    queryKey: ["samples", params],
    queryFn: () => fetchSamples(params),
    placeholderData: keepPreviousData,
  });
}

export function useSample(id: number | null) {
  return useQuery({
    queryKey: ["sample", id],
    queryFn: () => fetchSample(id as number),
    enabled: id !== null,
  });
}

export function useSql() {
  return useMutation({ mutationFn: (query: string) => runSql(query) });
}
