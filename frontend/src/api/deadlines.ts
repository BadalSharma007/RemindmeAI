import { apiClient } from "./client";

export interface Deadline {
  id: string;
  user_id: string;
  title: string;
  due_at: string;
  confidence_score: number;
  source_text: string | null;
  status: "pending" | "reminded" | "dismissed" | "completed";
}

export interface DeadlinePatch {
  status?: Deadline["status"];
  title?: string;
}

export const deadlinesApi = {
  getDeadlines: async (params?: { status?: string; limit?: number }): Promise<Deadline[]> => {
    const response = await apiClient.get("/deadlines", { params });
    return response.data;
  },

  getDeadline: async (id: string): Promise<Deadline> => {
    const response = await apiClient.get(`/deadlines/${id}`);
    return response.data;
  },

  patchDeadline: async (id: string, patch: DeadlinePatch): Promise<Deadline> => {
    const response = await apiClient.patch(`/deadlines/${id}`, patch);
    return response.data;
  },
};
