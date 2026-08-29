import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { remindersApi } from "../api/reminders";

export function useReminders(status?: string) {
  return useQuery({
    queryKey: ["reminders", status ?? "all"],
    queryFn: () => remindersApi.list(status),
  });
}

export function useSnoozeReminder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, snooze_until }: { id: string; snooze_until: string }) =>
      remindersApi.snooze(id, snooze_until),
    onSettled: () => qc.invalidateQueries({ queryKey: ["reminders"] }),
  });
}
