import { apiClient } from "./client";

export interface Deadline {
  id: string;
  user_id: string;
  title: string;
  due_at: string;
  confidence_score: number;
  source_text: string | null;
  status: "pending" | "reminded" | "completed" | "dismissed";
  created_at?: string | null;
}

export interface DeadlineCreate {
  title: string;
  due_at: string;
  source_text?: string;
}

export interface DeadlinePatch {
  status?: "pending" | "reminded" | "completed" | "dismissed";
  title?: string;
}

export const deadlinesApi = {
  list: (status?: string) =>
    apiClient.get<Deadline[]>("/deadlines", { params: { limit: 200, ...(status && status !== "all" ? { status } : {}) } }).then(r => r.data),

  get: (id: string) =>
    apiClient.get<Deadline>(`/deadlines/${id}`).then(r => r.data),

  create: (body: DeadlineCreate) =>
    apiClient.post<Deadline>("/deadlines", body).then(r => r.data),

  patch: (id: string, body: DeadlinePatch) =>
    apiClient.patch<Deadline>(`/deadlines/${id}`, body).then(r => r.data),

  delete: (id: string) =>
    apiClient.delete(`/deadlines/${id}`),

  feedback: (id: string, helpful: boolean) =>
    apiClient.post(`/deadlines/${id}/feedback`, { helpful }),
};
