import { useState, useEffect } from "react";
import { format, parseISO, formatDistanceToNow, isPast } from "date-fns";
import {
  CalendarClock, Check, X, Clock, AlertTriangle, CheckCircle2, XCircle,
  Filter, Search,
} from "lucide-react";

/* ── Types ────────────────────────────────────────────────────────────── */
interface Deadline {
  id: string;
  user_id: string;
  title: string;
  due_at: string;
  confidence_score: number;
  source_text: string | null;
  status: "pending" | "reminded" | "completed" | "dismissed";
}

/* ── Status Config ────────────────────────────────────────────────────── */
const STATUS_CONFIG: Record<string, { bg: string; text: string; icon: React.ElementType; label: string }> = {
  pending: { bg: "bg-tertiary/10", text: "text-tertiary", icon: Clock, label: "Pending" },
  reminded: { bg: "bg-primary/10", text: "text-primary", icon: AlertTriangle, label: "Reminded" },
  completed: { bg: "bg-green-500/10", text: "text-green-400", icon: CheckCircle2, label: "Completed" },
  dismissed: { bg: "bg-on-surface-variant/10", text: "text-on-surface-variant/60", icon: XCircle, label: "Dismissed" },
};

/* ── Mock Data ────────────────────────────────────────────────────────── */
const MOCK_DEADLINES: Deadline[] = [
  { id: "dl-1", user_id: "u1", title: "Submit project proposal to client", due_at: new Date(Date.now() + 86400000).toISOString(), confidence_score: 0.95, source_text: "From: manager@company.com — 'Please have the proposal ready by tomorrow EOD'", status: "pending" },
  { id: "dl-2", user_id: "u1", title: "Complete quarterly tax filing", due_at: new Date(Date.now() + 172800000).toISOString(), confidence_score: 0.88, source_text: "From: accounting@firm.com — 'Tax documents due in 2 days'", status: "pending" },
  { id: "dl-3", user_id: "u1", title: "Review pull request #247", due_at: new Date(Date.now() + 43200000).toISOString(), confidence_score: 0.92, source_text: "From: dev-team@company.com — 'PR needs review before sprint ends'", status: "reminded" },
  { id: "dl-4", user_id: "u1", title: "Renew cloud subscription", due_at: new Date(Date.now() + 604800000).toISOString(), confidence_score: 0.78, source_text: "From: billing@cloudprovider.io — 'Your subscription expires next week'", status: "pending" },
  { id: "dl-5", user_id: "u1", title: "Send weekly status update", due_at: new Date(Date.now() + 7200000).toISOString(), confidence_score: 0.99, source_text: "From: pm@company.com — 'Status report needed by 5 PM'", status: "pending" },
];

/* ── Loading Skeleton ─────────────────────────────────────────────────── */
function DeadlinesSkeleton() {
  return (
    <div className="animate-fade-in">
      <div className="skeleton h-8 w-40 mb-2" />
      <div className="skeleton h-4 w-64 mb-8" />
      <div className="space-y-4">
        {[1, 2, 3, 4].map((i) => <div key={i} className="skeleton h-28 rounded-xl" />)}
      </div>
    </div>
  );
}

/* ── Deadlines Page ───────────────────────────────────────────────────── */
export function Deadlines() {
  const [deadlines, setDeadlines] = useState<Deadline[]>(MOCK_DEADLINES);
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
    fetch(`${baseUrl}/deadlines?limit=200`, {
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    })
      .then(res => {
        if (!res.ok) throw new Error("API error");
        return res.json();
      })
      .then(data => {
        if (Array.isArray(data)) {
          setDeadlines(data);
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

  if (isLoading) return <DeadlinesSkeleton />;

  const handleAction = async (id: string, status: "completed" | "dismissed") => {
    const token = localStorage.getItem("access_token");
    const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
    try {
      await fetch(`${baseUrl}/deadlines/${id}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token ?? ""}`, "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
    } catch { /* optimistic update still applies */ }
    setDeadlines(prev => prev.map(dl => dl.id === id ? { ...dl, status } : dl));
  };

  // Filter & search
  const filteredDeadlines = deadlines.filter(dl => {
    if (activeFilter !== "all" && dl.status !== activeFilter) return false;
    if (searchQuery && !dl.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const filters = ["all", "pending", "reminded", "completed", "dismissed"];

  return (
    <div>
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <CalendarClock className="w-5 h-5 text-primary" />
          <h1 className="text-headline-md text-on-surface">Deadlines</h1>
          {isDemoMode && (
            <span className="text-label-sm bg-tertiary/10 text-tertiary px-2.5 py-1 rounded-full">Demo Mode</span>
          )}
        </div>
        <p className="text-body-md text-on-surface-variant ml-8">Track and manage your upcoming deadlines.</p>
      </div>

      {/* ── Search & Filter ─────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 mb-6">
        <div className="relative flex-1 w-full sm:max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant/50" />
          <input
            id="deadline-search"
            type="text"
            placeholder="Search deadlines..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-surface-container-high text-on-surface rounded-lg pl-10 pr-4 py-2.5 text-sm ghost-border ghost-border-focus transition-premium placeholder:text-on-surface-variant/40"
          />
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
      {!filteredDeadlines.length ? (
        <div className="bg-surface-container rounded-2xl p-12 text-center animate-slide-up">
          <div className="w-16 h-16 rounded-2xl bg-surface-container-high flex items-center justify-center mx-auto mb-5">
            <CalendarClock className="w-7 h-7 text-on-surface-variant/40" />
          </div>
          <h3 className="text-title-md text-on-surface mb-2">{searchQuery ? "No matches found" : activeFilter !== "all" ? `No ${activeFilter} deadlines` : "No deadlines yet"}</h3>
          <p className="text-body-md text-on-surface-variant max-w-sm mx-auto">
            {searchQuery ? `No deadlines matching "${searchQuery}".` : isDemoMode ? "Connect Gmail to start detecting deadlines from your emails." : "Your emails are being processed. New deadlines will appear here automatically."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredDeadlines.map((dl, idx) => {
            const cfg = STATUS_CONFIG[dl.status] ?? STATUS_CONFIG.pending;
            const StatusIcon = cfg.icon;
            const isActionable = dl.status === "pending" || dl.status === "reminded";

            return (
              <div key={dl.id} className="bg-surface-container rounded-xl p-5 card-hover animate-slide-up group" style={{ animationDelay: `${idx * 50}ms` }}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className={`text-title-md truncate transition-premium ${
                      dl.status === "completed" ? "text-on-surface-variant/50 line-through" :
                      dl.status === "dismissed" ? "text-on-surface-variant/40" : "text-on-surface group-hover:text-primary"
                    }`}>{dl.title}</p>
                    {dl.source_text && <p className="text-xs text-on-surface-variant/40 mt-1.5 truncate">{dl.source_text}</p>}
                    <div className="flex flex-wrap items-center gap-3 mt-3">
                      <div className="flex items-center gap-1.5">
                        <Clock className={`w-3.5 h-3.5 ${isPast(parseISO(dl.due_at)) && dl.status === "pending" ? "text-error" : "text-on-surface-variant/50"}`} />
                        <span className={`text-body-md ${isPast(parseISO(dl.due_at)) && dl.status === "pending" ? "text-error font-medium" : "text-on-surface-variant"}`}>
                          {format(parseISO(dl.due_at), "MMM d, yyyy · h:mm a")}
                          <span className="ml-1.5 text-xs opacity-70">({formatDistanceToNow(parseISO(dl.due_at), { addSuffix: true })})</span>
                        </span>
                      </div>
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
                        <StatusIcon className="w-3 h-3" />{cfg.label}
                      </span>
                      {dl.confidence_score && <span className="text-xs text-on-surface-variant/40">{Math.round(dl.confidence_score * 100)}% confidence</span>}
                    </div>
                  </div>
                  {isActionable && (
                    <div className="flex gap-2 shrink-0 pt-1">
                      <button onClick={() => handleAction(dl.id, "completed")} className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-green-500/10 text-green-400 text-xs font-semibold hover:bg-green-500/20 transition-premium">
                        <Check className="w-3.5 h-3.5" />Done
                      </button>
                      <button onClick={() => handleAction(dl.id, "dismissed")} className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-surface-container-high text-on-surface-variant text-xs font-semibold hover:bg-surface-container-highest transition-premium">
                        <X className="w-3.5 h-3.5" />Dismiss
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {filteredDeadlines.length > 0 && (
        <div className="mt-6 flex items-center justify-between text-xs text-on-surface-variant/50">
          <span>{filteredDeadlines.length} deadline{filteredDeadlines.length !== 1 ? "s" : ""} shown</span>
          <span>{deadlines.filter(d => d.status === "pending").length} pending</span>
        </div>
      )}
    </div>
  );
}
