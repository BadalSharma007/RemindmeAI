import { apiClient } from "./client";

export interface Preferences {
  timezone: string;
  reminder_lead_minutes: number;
  channels: string[];
}

export const preferencesApi = {
  get: () => apiClient.get<Preferences>("/preferences").then(r => r.data),
  update: (body: Partial<Preferences>) =>
    apiClient.put<Preferences>("/preferences", body).then(r => r.data),
};

export interface UserProfile {
  id: string;
  email: string;
  display_name: string | null;
  timezone: string;
}

export const authApi = {
  me: () => apiClient.get<UserProfile>("/auth/me").then(r => r.data),
  disconnect: (provider: string) => apiClient.delete(`/auth/disconnect/${provider}`),
};

export interface DashboardStats {
  total_deadlines: number;
  pending_deadlines: number;
  upcoming_reminders: number;
  emails_processed_today: number;
  connected_accounts: number;
  total_emails_read: number;
  important_emails_today: number;
  completed_deadlines: number;
}

export const statsApi = {
  dashboard: () => apiClient.get<DashboardStats>("/stats/dashboard").then(r => r.data),
};
