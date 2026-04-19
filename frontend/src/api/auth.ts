import { apiClient } from "./client";

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_email: string;
}

export interface UserProfile {
  id: string;
  email: string;
  display_name: string | null;
  timezone: string;
}

export const authApi = {
  connectGmail: async (): Promise<{ redirect_url: string; state: string }> => {
    const response = await apiClient.post("/auth/connect/gmail");
    return response.data;
  },

  getMe: async (): Promise<UserProfile> => {
    const response = await apiClient.get("/auth/me");
    return response.data;
  },

  disconnect: async (provider: string): Promise<void> => {
    await apiClient.delete(`/auth/disconnect/${provider}`);
  },
};
