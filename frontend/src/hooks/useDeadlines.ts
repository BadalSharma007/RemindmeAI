import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { deadlinesApi } from "../api/deadlines";

export function useDeadlines(status?: string) {
  return useQuery({
    queryKey: ["deadlines", status ?? "all"],
    queryFn: () => deadlinesApi.list(status),
  });
}

export function usePatchDeadline() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Parameters<typeof deadlinesApi.patch>[1] }) =>
      deadlinesApi.patch(id, body),
    onSettled: () => qc.invalidateQueries({ queryKey: ["deadlines"] }),
  });
}
