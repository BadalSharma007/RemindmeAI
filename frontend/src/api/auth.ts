import { apiClient } from "./client";

export const authApi = {
  startGmail: (redirectUrl: string) => {
    const base = import.meta.env.VITE_API_BASE_URL ?? "";
    window.location.href = `${base}/auth/start/gmail?redirect_url=${encodeURIComponent(redirectUrl)}`;
  },
  connectGmail: () =>
    apiClient.post<{ redirect_url: string }>("/auth/connect/gmail").then(r => r.data),
};
