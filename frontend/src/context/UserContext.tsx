import React, { createContext, useContext, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { authApi, preferencesApi, type UserProfile, type Preferences } from "../api";

interface UserContextValue {
  user: UserProfile | null;
  preferences: Preferences | null;
  timezone: string;
  isLoading: boolean;
  refetchUser: () => void;
  refetchPreferences: () => void;
}

const UserContext = createContext<UserContextValue>({
  user: null,
  preferences: null,
  timezone: "Asia/Kolkata",
  isLoading: false,
  refetchUser: () => {},
  refetchPreferences: () => {},
});

export function useUser() {
  return useContext(UserContext);
}

export function UserProvider({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("access_token");

  const { data: user, isLoading: userLoading, refetch: refetchUser } = useQuery({
    queryKey: ["me"],
    queryFn: authApi.me,
    enabled: !!token,
    staleTime: 60_000,
  });

  const { data: preferences, isLoading: prefsLoading, refetch: refetchPreferences } = useQuery({
    queryKey: ["preferences"],
    queryFn: preferencesApi.get,
    enabled: !!token,
    staleTime: 60_000,
  });

  const timezone = preferences?.timezone || user?.timezone || "Asia/Kolkata";

  return (
    <UserContext.Provider
      value={{
        user: user ?? null,
        preferences: preferences ?? null,
        timezone,
        isLoading: userLoading || prefsLoading,
        refetchUser,
        refetchPreferences,
      }}
    >
      {children}
    </UserContext.Provider>
  );
}
