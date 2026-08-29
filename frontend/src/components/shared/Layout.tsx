import React, { useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard,
  CalendarClock,
  Bell,
  Settings,
  Sparkles,
  Search,
  Calendar as CalendarIcon,
  MailMinus,
  Command,
} from "lucide-react";
import { deadlinesApi } from "../../api/deadlines";
import { remindersApi } from "../../api/reminders";
import { OfflineBanner } from "../ui/OfflineBanner";
import { ShortcutsModal } from "./ShortcutsModal";

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
  const pendingDeadlines = deadlines?.filter((d) => d.status === "pending").length ?? 0;
  const pendingReminders = reminders?.filter((r) => r.status === "pending").length ?? 0;
  const pendingReview =
    deadlines?.filter(
      (d) => d.status === "pending" && d.source_text && d.source_text !== "Manual entry"
    ).length ?? 0;

  return { pendingDeadlines, pendingReminders, pendingReview };
}

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { pendingDeadlines, pendingReminders, pendingReview } = useBadgeCounts();
  const [showShortcuts, setShowShortcuts] = useState(false);

  // Global Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeTag = (document.activeElement?.tagName || "").toLowerCase();
      if (activeTag === "input" || activeTag === "textarea" || activeTag === "select") {
        return;
      }

      if (e.key === "n" || e.key === "N") {
        e.preventDefault();
        navigate("/deadlines/create");
      } else if (e.key === "d" || e.key === "D") {
        e.preventDefault();
        navigate("/deadlines");
      } else if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        navigate("/reminders");
      } else if (e.key === "c" || e.key === "C") {
        e.preventDefault();
        navigate("/calendar");
      } else if (e.key === "s" || e.key === "S") {
        e.preventDefault();
        navigate("/settings");
      } else if (e.key === "/") {
        e.preventDefault();
        navigate("/search");
      } else if (e.key === "?") {
        e.preventDefault();
        setShowShortcuts((prev) => !prev);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [navigate]);

  const navItems = [
    { path: "/", label: "Dashboard", icon: LayoutDashboard, badge: 0 },
    { path: "/deadlines", label: "Deadlines", icon: CalendarClock, badge: pendingDeadlines },
    { path: "/reminders", label: "Reminders", icon: Bell, badge: pendingReminders },
    { path: "/calendar", label: "Calendar", icon: CalendarIcon, badge: 0 },
    { path: "/review", label: "AI Review", icon: Sparkles, badge: pendingReview, highlight: true },
    { path: "/subscriptions", label: "Newsletters", icon: MailMinus, badge: 0 },
    { path: "/settings", label: "Settings", icon: Settings, badge: 0 },
  ];

  return (
    <div className="min-h-screen bg-background font-inter flex flex-col">
      <OfflineBanner />

      {/* ── Top Nav ─────────────────────────────────────────────── */}
      <nav className="glass sticky top-0 z-40 px-4 sm:px-6 py-3.5 border-b border-white/5">
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
              const isActive =
                location.pathname === item.path ||
                (item.path === "/deadlines" && location.pathname.startsWith("/deadlines"));
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-premium ${
                    isActive
                      ? "bg-surface-container-high text-primary"
                      : item.highlight && item.badge > 0
                      ? "text-primary/90 hover:bg-surface-container hover:text-primary"
                      : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {item.label}
                  {item.badge > 0 && (
                    <span
                      className={`min-w-[16px] h-[16px] text-[9px] font-bold rounded-full flex items-center justify-center px-1 ${
                        item.highlight ? "bg-primary text-on-primary animate-pulse" : "bg-primary text-on-primary"
                      }`}
                    >
                      {item.badge > 99 ? "99+" : item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>

          {/* Right Action Tools: Search & Shortcuts */}
          <div className="flex items-center gap-1.5">
            <Link
              to="/search"
              title="Search (/)"
              className={`p-2 rounded-lg transition-premium ${
                location.pathname === "/search"
                  ? "bg-surface-container-high text-primary"
                  : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
              }`}
            >
              <Search className="w-4 h-4" />
            </Link>

            <button
              onClick={() => setShowShortcuts(true)}
              title="Keyboard Shortcuts (?)"
              className="p-2 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-premium hidden sm:flex"
            >
              <Command className="w-4 h-4" />
            </button>
          </div>
        </div>
      </nav>

      {/* ── Main Content ─────────────────────────────────────────── */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8 animate-fade-in">
        {children}
      </main>

      {/* ── Mobile Bottom Bar ────────────────────────────────────── */}
      <nav className="md:hidden glass fixed bottom-0 left-0 right-0 z-40 px-2 py-2 border-t border-white/5">
        <div className="flex items-center justify-around">
          {navItems.slice(0, 5).map((item) => {
            const isActive =
              location.pathname === item.path ||
              (item.path === "/deadlines" && location.pathname.startsWith("/deadlines"));
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`relative flex flex-col items-center gap-1 px-2 py-1.5 rounded-xl transition-premium ${
                  isActive ? "text-primary" : "text-on-surface-variant"
                }`}
              >
                <div className={`p-1 rounded-lg transition-premium ${isActive ? "bg-surface-container-high" : ""}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <span className="text-[9px] font-medium">{item.label}</span>
                {item.badge > 0 && (
                  <span className="absolute top-0 right-1 min-w-[14px] h-[14px] bg-primary text-on-primary text-[8px] font-bold rounded-full flex items-center justify-center px-0.5">
                    {item.badge > 99 ? "99+" : item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Spacer for mobile bottom nav */}
      <div className="md:hidden h-16" />

      {/* Keyboard Shortcuts Modal */}
      <ShortcutsModal isOpen={showShortcuts} onClose={() => setShowShortcuts(false)} />
    </div>
  );
}
