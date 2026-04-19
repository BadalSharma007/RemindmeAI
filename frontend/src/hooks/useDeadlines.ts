import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { deadlinesApi, type DeadlinePatch } from "../api/deadlines";

export function useDeadlines(status?: string) {
  return useQuery({
    queryKey: ["deadlines", status],
    queryFn: () => deadlinesApi.getDeadlines({ status }),
    staleTime: 30_000,
  });
}

export function usePatchDeadline() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: DeadlinePatch }) =>
      deadlinesApi.patchDeadline(id, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["deadlines"] }),
  });
}
