import { apiClient } from "./client";

export interface Reminder {
  id: string;
  deadline_id: string;
  user_id: string;
  scheduled_at: string;
  channel: string;
  status: "pending" | "sent" | "failed" | "snoozed" | "dismissed";
  sent_at: string | null;
  snooze_until: string | null;
}

export interface ReminderCreate {
  deadline_id: string;
  scheduled_at: string;
  channel?: string;
}

export const remindersApi = {
  list: (status?: string) =>
    apiClient.get<Reminder[]>("/reminders", { params: { limit: 200, ...(status && status !== "all" ? { status } : {}) } }).then(r => r.data),

  create: (body: ReminderCreate) =>
    apiClient.post<Reminder>("/reminders", body).then(r => r.data),

  patch: (id: string, body: Partial<{ scheduled_at: string; channel: string }>) =>
    apiClient.patch<Reminder>(`/reminders/${id}`, body).then(r => r.data),

  dismiss: (id: string) =>
    apiClient.post(`/reminders/${id}/dismiss`),

  snooze: (id: string, snooze_until: string) =>
    apiClient.post<Reminder>(`/reminders/${id}/snooze`, { snooze_until }).then(r => r.data),
};
