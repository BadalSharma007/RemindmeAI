import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { remindersApi } from "../api/reminders";

export function useReminders(status?: string) {
  return useQuery({
    queryKey: ["reminders", status],
    queryFn: () => remindersApi.getReminders({ status }),
    staleTime: 30_000,
  });
}

export function useSnoozeReminder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, snoozeUntil }: { id: string; snoozeUntil: string }) =>
      remindersApi.snooze(id, snoozeUntil),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reminders"] }),
  });
}
