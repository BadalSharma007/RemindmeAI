import { useQuery } from "@tanstack/react-query";
import { authApi } from "../api/auth";

export function useCurrentUser() {
  const token = localStorage.getItem("access_token");
  return useQuery({
    queryKey: ["me"],
    queryFn: authApi.getMe,
    enabled: !!token,
    retry: false,
  });
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem("access_token");
}
