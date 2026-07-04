import { useMutation, useQuery } from "@tanstack/react-query";
import { api, ApiError } from "./client";
import { queryClient } from "./query";
import { toast } from "@/shared/ui/Toast";

/** Список с сервера (пагинация/фильтры на бэке §6.5). */
export function useList<T = any>(key: unknown[], path: string, enabled = true) {
  return useQuery<{ items: T[]; total: number }>({
    queryKey: key,
    queryFn: () => api.get(path),
    enabled,
  });
}

export function useOne<T = any>(key: unknown[], path: string, enabled = true) {
  return useQuery<T>({ queryKey: key, queryFn: () => api.get(path), enabled });
}

/** Мутация с тостами ошибок и инвалидацией кешей. */
export function useApiMutation<TVars = any, TData = any>(opts: {
  mutationFn: (vars: TVars) => Promise<TData>;
  invalidate?: unknown[][];
  successMsg?: string;
  onSuccess?: (data: TData, vars: TVars) => void;
}) {
  return useMutation({
    mutationFn: opts.mutationFn,
    onSuccess: (data, vars) => {
      opts.invalidate?.forEach((key) => queryClient.invalidateQueries({ queryKey: key }));
      if (opts.successMsg) toast.success(opts.successMsg);
      opts.onSuccess?.(data, vars);
    },
    onError: (e) => {
      toast.error(e instanceof ApiError ? e.message : "Ошибка операции");
    },
  });
}
