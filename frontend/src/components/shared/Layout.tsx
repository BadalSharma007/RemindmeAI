import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { LayoutDashboard, CalendarClock, Bell, Settings, Sparkles, Search } from "lucide-react";
import { deadlinesApi } from "../../api/deadlines";
import { remindersApi } from "../../api/reminders";

function useBadgeCounts() {
  const token = localStorage.getItem("access_token");
  const { data: deadlines } = useQuery({
    queryKey: ["deadlines", "all"],
    queryFn: () => deadlinesApi.list(),
    enabled: !!token,
    staleTime: 30_000,
  });
  const { data: reminders } = useQuery({
    queryKey: ["reminders", "all"],
    queryFn: () => remindersApi.list(),
    enabled: !!token,
    staleTime: 30_000,
  });
  const pendingDeadlines = deadlines?.filter(d => d.status === "pending").length ?? 0;
  const pendingReminders = reminders?.filter(r => r.status === "pending").length ?? 0;
  return { pendingDeadlines, pendingReminders };
}

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { pendingDeadlines, pendingReminders } = useBadgeCounts();

  const navItems = [
    { path: "/", label: "Dashboard", icon: LayoutDashboard, badge: 0 },
    { path: "/deadlines", label: "Deadlines", icon: CalendarClock, badge: pendingDeadlines },
    { path: "/reminders", label: "Reminders", icon: Bell, badge: pendingReminders },
    { path: "/settings", label: "Settings", icon: Settings, badge: 0 },
  ];

  return (
    <div className="min-h-screen bg-background font-inter flex flex-col">
      {/* ── Top Nav ─────────────────────────────────────────────── */}
      <nav className="glass sticky top-0 z-50 px-6 py-4 border-b border-white/5">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          {/* Brand */}
          <Link to="/" className="flex items-center gap-2.5 group shrink-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-primary-container flex items-center justify-center transition-premium group-hover:shadow-glow">
              <Sparkles className="w-4 h-4 text-on-primary" />
            </div>
            <span className="text-on-surface font-semibold text-lg tracking-tight">
              Remindme<span className="text-primary">AI</span>
            </span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path ||
                (item.path === "/deadlines" && location.pathname.startsWith("/deadlines"));
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`relative flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-premium ${
                    isActive
                      ? "bg-surface-container-high text-primary"
                      : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                  {item.badge > 0 && (
                    <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] bg-primary text-on-primary text-[10px] font-bold rounded-full flex items-center justify-center px-1">
                      {item.badge > 99 ? "99+" : item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>

          {/* Search icon */}
          <Link
            to="/search"
            className={`p-2 rounded-lg transition-premium ${
              location.pathname === "/search"
                ? "bg-surface-container-high text-primary"
                : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
            }`}
          >
            <Search className="w-4 h-4" />
          </Link>
        </div>
      </nav>

      {/* ── Main Content ─────────────────────────────────────────── */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8 animate-fade-in">
        {children}
      </main>

      {/* ── Mobile Bottom Bar ────────────────────────────────────── */}
      <nav className="md:hidden glass fixed bottom-0 left-0 right-0 z-50 px-2 py-2 border-t border-white/5">
        <div className="flex items-center justify-around">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path ||
              (item.path === "/deadlines" && location.pathname.startsWith("/deadlines"));
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`relative flex flex-col items-center gap-1 px-3 py-2 rounded-xl transition-premium ${
                  isActive ? "text-primary" : "text-on-surface-variant"
                }`}
              >
                <div className={`p-1.5 rounded-lg transition-premium ${isActive ? "bg-surface-container-high" : ""}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <span className="text-[10px] font-medium">{item.label}</span>
                {item.badge > 0 && (
                  <span className="absolute top-0 right-1 min-w-[16px] h-[16px] bg-primary text-on-primary text-[9px] font-bold rounded-full flex items-center justify-center px-0.5">
                    {item.badge > 99 ? "99+" : item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Spacer for mobile bottom nav */}
      <div className="md:hidden h-20" />
    </div>
  );
}
