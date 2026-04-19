import { apiClient } from "./client";

export interface Reminder {
  id: string;
  deadline_id: string;
  user_id: string;
  scheduled_at: string;
  channel: string;
  status: "pending" | "sent" | "failed" | "snoozed";
  sent_at: string | null;
}

export const remindersApi = {
  getReminders: async (params?: { status?: string; limit?: number }): Promise<Reminder[]> => {
    const response = await apiClient.get("/reminders", { params });
    return response.data;
  },

  snooze: async (id: string, snoozeUntil: string): Promise<Reminder> => {
    const response = await apiClient.post(`/reminders/${id}/snooze`, {
      snooze_until: snoozeUntil,
    });
    return response.data;
  },
};
