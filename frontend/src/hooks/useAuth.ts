import { useQuery } from "@tanstack/react-query";
import { authApi } from "../api";

export function useAuth() {
  const token = localStorage.getItem("access_token");
  const { data: user, isLoading } = useQuery({
    queryKey: ["me"],
    queryFn: authApi.me,
    enabled: !!token,
  });
  return { user, isLoading, isAuthenticated: !!token };
}
