import { apiClient } from "./client";

export interface DashboardStats {
  total_deadlines: number;
  pending_deadlines: number;
  upcoming_reminders: number;
  emails_processed_today: number;
  connected_accounts: number;
}

export const statsApi = {
  getDashboard: async (): Promise<DashboardStats> => {
    const response = await apiClient.get("/stats/dashboard");
    return response.data;
  },
};
