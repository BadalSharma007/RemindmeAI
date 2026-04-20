import { useState, useEffect } from "react";
import { format, parseISO, addHours, formatDistanceToNow } from "date-fns";
import {
  Bell, Clock, AlarmClock, CheckCircle2, XCircle, Send,
  Filter, Search,
} from "lucide-react";

/* ── Types ────────────────────────────────────────────────────────────── */
interface Reminder {
  id: string;
  deadline_id: string;
  user_id: string;
  scheduled_at: string;
  channel: string;
  status: "pending" | "sent" | "failed" | "snoozed";
  sent_at: string | null;
}

/* ── Status Config ────────────────────────────────────────────────────── */
const STATUS_CONFIG: Record<string, { bg: string; text: string; icon: React.ElementType; label: string }> = {
  pending: { bg: "bg-tertiary/10", text: "text-tertiary", icon: Clock, label: "Pending" },
  sent: { bg: "bg-green-500/10", text: "text-green-400", icon: CheckCircle2, label: "Sent" },
  failed: { bg: "bg-error/10", text: "text-error", icon: XCircle, label: "Failed" },
  snoozed: { bg: "bg-primary/10", text: "text-primary", icon: AlarmClock, label: "Snoozed" },
};

/* ── Mock Data ────────────────────────────────────────────────────────── */
const MOCK_REMINDERS: Reminder[] = [
  { id: "rm-1", deadline_id: "dl-1", user_id: "u1", scheduled_at: new Date(Date.now() + 3600000).toISOString(), channel: "email", status: "pending", sent_at: null },
  { id: "rm-2", deadline_id: "dl-2", user_id: "u1", scheduled_at: new Date(Date.now() + 7200000).toISOString(), channel: "email", status: "pending", sent_at: null },
  { id: "rm-3", deadline_id: "dl-3", user_id: "u1", scheduled_at: new Date(Date.now() - 3600000).toISOString(), channel: "email", status: "sent", sent_at: new Date(Date.now() - 3500000).toISOString() },
  { id: "rm-4", deadline_id: "dl-4", user_id: "u1", scheduled_at: new Date(Date.now() + 86400000).toISOString(), channel: "push", status: "pending", sent_at: null },
  { id: "rm-5", deadline_id: "dl-5", user_id: "u1", scheduled_at: new Date(Date.now() - 7200000).toISOString(), channel: "email", status: "failed", sent_at: null },
  { id: "rm-6", deadline_id: "dl-1", user_id: "u1", scheduled_at: new Date(Date.now() + 14400000).toISOString(), channel: "sms", status: "snoozed", sent_at: null },
];

/* ── Loading Skeleton ─────────────────────────────────────────────────── */
function RemindersSkeleton() {
  return (
    <div className="animate-fade-in">
      <div className="skeleton h-8 w-40 mb-2" />
      <div className="skeleton h-4 w-56 mb-8" />
      <div className="space-y-4">
        {[1, 2, 3].map((i) => <div key={i} className="skeleton h-24 rounded-xl" />)}
      </div>
    </div>
  );
}

/* ── Reminders Page ───────────────────────────────────────────────────── */
export function Reminders() {
  const [reminders, setReminders] = useState<Reminder[]>(MOCK_REMINDERS);
  const [isLoading, setIsLoading] = useState(true);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [activeFilter, setActiveFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Try to fetch from API, fall back to mock data
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setIsDemoMode(true);
      setIsLoading(false);
      return;
    }

    const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
    fetch(`${baseUrl}/reminders`, {
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    })
      .then(res => {
        if (!res.ok) throw new Error("API error");
        return res.json();
      })
      .then(data => {
        if (Array.isArray(data)) {
          setReminders(data);
          setIsDemoMode(false);
        } else {
          setIsDemoMode(true);
        }
      })
      .catch(() => {
        setIsDemoMode(true);
      })
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) return <RemindersSkeleton />;

  const handleSnooze1h = async (id: string) => {
    const token = localStorage.getItem("access_token");
    const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
    const snoozeUntil = addHours(new Date(), 1).toISOString();
    try {
      await fetch(`${baseUrl}/reminders/${id}/snooze`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token ?? ""}`, "Content-Type": "application/json" },
        body: JSON.stringify({ snooze_until: snoozeUntil }),
      });
    } catch { /* optimistic update still applies */ }
    setReminders(prev =>
      prev.map(r => r.id === id ? { ...r, status: "snoozed" as const, scheduled_at: snoozeUntil } : r)
    );
  };

  // Filter & search
  const filteredReminders = reminders.filter(r => {
    if (activeFilter !== "all" && r.status !== activeFilter) return false;
    if (searchQuery && !r.channel.toLowerCase().includes(searchQuery.toLowerCase()) && !r.status.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const filters = ["all", "pending", "sent", "snoozed", "failed"];
  const pendingCount = reminders.filter(r => r.status === "pending").length;
  const sentCount = reminders.filter(r => r.status === "sent").length;

  return (
    <div>
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <Bell className="w-5 h-5 text-primary" />
          <h1 className="text-headline-md text-on-surface">Reminders</h1>
          {isDemoMode && <span className="text-label-sm bg-tertiary/10 text-tertiary px-2.5 py-1 rounded-full">Demo Mode</span>}
        </div>
        <p className="text-body-md text-on-surface-variant ml-8">Scheduled notifications for your deadlines.</p>
      </div>

      {/* ── Quick Stats ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <div className="bg-surface-container rounded-xl p-4 text-center animate-slide-up">
          <p className="text-2xl font-bold text-on-surface">{reminders.length}</p>
          <p className="text-label-sm text-on-surface-variant mt-1">Total</p>
        </div>
        <div className="bg-surface-container rounded-xl p-4 text-center animate-slide-up" style={{ animationDelay: "50ms" }}>
          <p className="text-2xl font-bold text-tertiary">{pendingCount}</p>
          <p className="text-label-sm text-on-surface-variant mt-1">Pending</p>
        </div>
        <div className="bg-surface-container rounded-xl p-4 text-center animate-slide-up" style={{ animationDelay: "100ms" }}>
          <p className="text-2xl font-bold text-green-400">{sentCount}</p>
          <p className="text-label-sm text-on-surface-variant mt-1">Sent</p>
        </div>
        <div className="bg-surface-container rounded-xl p-4 text-center animate-slide-up" style={{ animationDelay: "150ms" }}>
          <p className="text-2xl font-bold text-error">{reminders.filter(r => r.status === "failed").length}</p>
          <p className="text-label-sm text-on-surface-variant mt-1">Failed</p>
        </div>
      </div>

      {/* ── Search & Filter ─────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 mb-6">
        <div className="relative flex-1 w-full sm:max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant/50" />
          <input id="reminder-search" type="text" placeholder="Search reminders..."
            value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-surface-container-high text-on-surface rounded-lg pl-10 pr-4 py-2.5 text-sm ghost-border ghost-border-focus transition-premium placeholder:text-on-surface-variant/40" />
        </div>
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          <Filter className="w-4 h-4 text-on-surface-variant/50 shrink-0" />
          {filters.map(f => (
            <button key={f} onClick={() => setActiveFilter(f)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-premium ${activeFilter === f ? "chip-selected" : "chip-unselected hover:bg-surface-container-high"}`}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* ── Content ─────────────────────────────────────────────── */}
      {!filteredReminders.length ? (
        <div className="bg-surface-container rounded-2xl p-12 text-center animate-slide-up">
          <div className="w-16 h-16 rounded-2xl bg-surface-container-high flex items-center justify-center mx-auto mb-5">
            <Bell className="w-7 h-7 text-on-surface-variant/40" />
          </div>
          <h3 className="text-title-md text-on-surface mb-2">{searchQuery ? "No matches found" : "No reminders yet"}</h3>
          <p className="text-body-md text-on-surface-variant max-w-sm mx-auto">
            {searchQuery ? `No reminders matching "${searchQuery}".` : "Reminders will appear here once the AI detects deadlines."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredReminders.map((r, idx) => {
            const cfg = STATUS_CONFIG[r.status] ?? STATUS_CONFIG.pending;
            const Icon = cfg.icon;
            return (
              <div key={r.id} className="bg-surface-container rounded-xl p-5 card-hover animate-slide-up group" style={{ animationDelay: `${idx * 50}ms` }}>
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2.5">
                      <Clock className="w-3.5 h-3.5 text-on-surface-variant/50" />
                      <p className="text-body-md text-on-surface-variant">
                        Scheduled: <span className="text-on-surface font-medium">{format(parseISO(r.scheduled_at), "MMM d, yyyy · h:mm a")}</span>
                        <span className="ml-1.5 text-xs opacity-60">({formatDistanceToNow(parseISO(r.scheduled_at), { addSuffix: true })})</span>
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2.5">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container-high text-on-surface-variant text-xs font-medium">
                        <Send className="w-3 h-3" />{r.channel}
                      </span>
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
                        <Icon className="w-3 h-3" />{cfg.label}
                      </span>
                      {r.sent_at && <span className="text-xs text-on-surface-variant/40">Sent {format(parseISO(r.sent_at), "MMM d · h:mm a")}</span>}
                    </div>
                  </div>
                  {r.status === "pending" && (
                    <button onClick={() => handleSnooze1h(r.id)}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary/10 text-primary text-xs font-semibold hover:bg-primary/20 transition-premium shrink-0">
                      <AlarmClock className="w-3.5 h-3.5" />Snooze 1h
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {filteredReminders.length > 0 && (
        <div className="mt-6 flex items-center justify-between text-xs text-on-surface-variant/50">
          <span>{filteredReminders.length} reminder{filteredReminders.length !== 1 ? "s" : ""} shown</span>
          <span>{pendingCount} pending · {sentCount} sent</span>
        </div>
      )}
    </div>
  );
}
