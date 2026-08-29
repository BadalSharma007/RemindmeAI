import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { format, parseISO, formatDistanceToNow, isPast, isToday, isTomorrow } from "date-fns";
import {
  CalendarClock, Check, X, Clock, AlertTriangle, CheckCircle2, XCircle,
  Filter, Search, Plus, Sparkles, ArrowRight,
} from "lucide-react";
import { deadlinesApi, type Deadline } from "../api/deadlines";

const STATUS_CONFIG: Record<string, { bg: string; text: string; icon: React.ElementType; label: string }> = {
  pending: { bg: "bg-amber-500/10", text: "text-amber-400", icon: Clock, label: "Pending" },
  reminded: { bg: "bg-primary/10", text: "text-primary", icon: AlertTriangle, label: "Reminded" },
  completed: { bg: "bg-green-500/10", text: "text-green-400", icon: CheckCircle2, label: "Completed" },
  dismissed: { bg: "bg-on-surface-variant/10", text: "text-on-surface-variant/60", icon: XCircle, label: "Dismissed" },
};

function formatDue(iso: string) {
  const d = parseISO(iso);
  if (isToday(d)) return `Today · ${format(d, "h:mm a")}`;
  if (isTomorrow(d)) return `Tomorrow · ${format(d, "h:mm a")}`;
  return format(d, "MMM d, yyyy · h:mm a");
}

function DeadlinesSkeleton() {
  return (
    <div className="animate-fade-in space-y-4">
      <div className="skeleton h-8 w-40 rounded-xl" />
      <div className="skeleton h-4 w-64 rounded-lg" />
      <div className="space-y-3 mt-6">
        {[1, 2, 3, 4].map(i => <div key={i} className="skeleton h-28 rounded-xl" />)}
      </div>
    </div>
  );
}

function EmptyState({ filter, search }: { filter: string; search: string }) {
  const navigate = useNavigate();
  const messages: Record<string, { title: string; desc: string }> = {
    all: { title: "No deadlines yet", desc: "Connect Gmail or create a deadline manually." },
    pending: { title: "No pending deadlines", desc: "You're all caught up! Nothing pending right now." },
    completed: { title: "Nothing completed yet", desc: "Mark deadlines done as you finish them." },
    dismissed: { title: "No dismissed deadlines", desc: "Dismissed deadlines will appear here." },
    reminded: { title: "No reminded deadlines", desc: "Reminders that have fired will appear here." },
  };
  const msg = search
    ? { title: "No matches found", desc: `No deadlines matching "${search}"` }
    : messages[filter] ?? messages.all;

  return (
    <div className="bg-surface-container rounded-2xl p-12 text-center border border-white/5 animate-slide-up">
      <div className="w-16 h-16 rounded-2xl bg-surface-container-high flex items-center justify-center mx-auto mb-5">
        <CalendarClock className="w-7 h-7 text-on-surface-variant/40" />
      </div>
      <h3 className="text-title-md text-on-surface mb-2">{msg.title}</h3>
      <p className="text-body-md text-on-surface-variant max-w-sm mx-auto mb-6">{msg.desc}</p>
      {!search && filter === "all" && (
        <button onClick={() => navigate("/deadlines/create")} className="btn-primary-gradient px-5 py-2.5 rounded-xl text-sm inline-flex items-center gap-2">
          <Plus className="w-4 h-4" /> Create Deadline
        </button>
      )}
    </div>
  );
}

export function Deadlines() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [activeFilter, setActiveFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  const { data: deadlines = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["deadlines", "all"],
    queryFn: () => deadlinesApi.list(),
  });

  const patchMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: "completed" | "dismissed" }) =>
      deadlinesApi.patch(id, { status }),
    onMutate: async ({ id, status }) => {
      await qc.cancelQueries({ queryKey: ["deadlines"] });
      const prev = qc.getQueryData<Deadline[]>(["deadlines", "all"]);
      qc.setQueryData<Deadline[]>(["deadlines", "all"], old =>
        old?.map(d => d.id === id ? { ...d, status } : d)
      );
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      qc.setQueryData(["deadlines", "all"], ctx?.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["deadlines"] }),
  });

  const feedbackMut = useMutation({
    mutationFn: ({ id, helpful }: { id: string; helpful: boolean }) =>
      deadlinesApi.feedback(id, helpful),
  });

  if (isLoading) return <DeadlinesSkeleton />;

  if (isError) return (
    <div className="bg-surface-container rounded-2xl p-12 text-center border border-white/5">
      <AlertTriangle className="w-8 h-8 text-error mx-auto mb-4" />
      <h3 className="text-title-md text-on-surface mb-2">Could not load deadlines</h3>
      <button onClick={() => refetch()} className="btn-primary-gradient px-5 py-2.5 rounded-xl text-sm mt-4">Try again</button>
    </div>
  );

  const filtered = deadlines.filter(dl => {
    if (activeFilter !== "all" && dl.status !== activeFilter) return false;
    if (searchQuery && !dl.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const pendingCount = deadlines.filter(d => d.status === "pending").length;
  const filters = ["all", "pending", "reminded", "completed", "dismissed"];

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between gap-4 mb-1">
          <div className="flex items-center gap-3">
            <CalendarClock className="w-5 h-5 text-primary" />
            <h1 className="text-headline-md text-on-surface">Deadlines</h1>
            {pendingCount > 0 && (
              <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-primary/10 text-primary">{pendingCount} pending</span>
            )}
          </div>
          <button
            onClick={() => navigate("/deadlines/create")}
            className="btn-primary-gradient px-4 py-2.5 rounded-xl text-sm flex items-center gap-2 shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">New Deadline</span>
          </button>
        </div>
        <p className="text-body-md text-on-surface-variant ml-8">Track and manage your upcoming deadlines.</p>
      </div>

      {/* Search & Filter */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-6">
        <div className="relative flex-1 w-full sm:max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant/50" />
          <input
            id="deadline-search"
            type="text"
            placeholder="Search deadlines..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
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

      {/* Content */}
      {filtered.length === 0 ? (
        <EmptyState filter={activeFilter} search={searchQuery} />
      ) : (
        <div className="space-y-3">
          {filtered.map((dl, idx) => {
            const cfg = STATUS_CONFIG[dl.status] ?? STATUS_CONFIG.pending;
            const StatusIcon = cfg.icon;
            const isActionable = dl.status === "pending" || dl.status === "reminded";
            const overdue = isPast(parseISO(dl.due_at)) && dl.status === "pending";
            const isAI = dl.source_text && dl.source_text !== "Manual entry" && dl.confidence_score < 1.0;

            return (
              <div
                key={dl.id}
                className={`bg-surface-container rounded-xl p-5 card-hover animate-slide-up group border border-white/5 relative overflow-hidden ${overdue ? "border-error/20" : ""}`}
                style={{ animationDelay: `${idx * 40}ms` }}
              >
                {/* Overdue left stripe */}
                {overdue && <div className="absolute left-0 top-0 bottom-0 w-1 bg-error rounded-l-xl" />}

                <div className="flex items-start justify-between gap-4" style={{ paddingLeft: overdue ? "8px" : "0" }}>
                  <div className="flex-1 min-w-0 cursor-pointer" onClick={() => navigate(`/deadlines/${dl.id}`)}>
                    <div className="flex items-center gap-2 mb-1">
                      <p className={`text-title-md truncate transition-premium ${
                        dl.status === "completed" ? "text-on-surface-variant/50 line-through" :
                        dl.status === "dismissed" ? "text-on-surface-variant/40" :
                        "text-on-surface group-hover:text-primary"
                      }`}>{dl.title}</p>
                      {isAI && (
                        <span className="shrink-0 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-primary/10 text-primary flex items-center gap-1">
                          <Sparkles className="w-2.5 h-2.5" />AI
                        </span>
                      )}
                      {overdue && (
                        <span className="shrink-0 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-error/10 text-error">Overdue</span>
                      )}
                    </div>
                    {dl.source_text && dl.source_text !== "Manual entry" && (
                      <p className="text-xs text-on-surface-variant/40 mt-0.5 truncate">{dl.source_text}</p>
                    )}
                    <div className="flex flex-wrap items-center gap-3 mt-2">
                      <div className="flex items-center gap-1.5">
                        <Clock className={`w-3.5 h-3.5 ${overdue ? "text-error" : "text-on-surface-variant/50"}`} />
                        <span className={`text-body-md ${overdue ? "text-error font-medium" : "text-on-surface-variant"}`}>
                          {formatDue(dl.due_at)}
                          <span className="ml-1.5 text-xs opacity-60">({formatDistanceToNow(parseISO(dl.due_at), { addSuffix: true })})</span>
                        </span>
                      </div>
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
                        <StatusIcon className="w-3 h-3" />{cfg.label}
                      </span>
                      {isAI && (
                        <span className="text-xs text-on-surface-variant/40">{Math.round(dl.confidence_score * 100)}% confidence</span>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-col gap-2 shrink-0 items-end pt-1">
                    {isActionable && (
                      <div className="flex gap-2">
                        <button
                          onClick={e => { e.stopPropagation(); patchMut.mutate({ id: dl.id, status: "completed" }); }}
                          className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-green-500/10 text-green-400 text-xs font-semibold hover:bg-green-500/20 transition-premium"
                        >
                          <Check className="w-3.5 h-3.5" />Done
                        </button>
                        <button
                          onClick={e => { e.stopPropagation(); patchMut.mutate({ id: dl.id, status: "dismissed" }); }}
                          className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-surface-container-high text-on-surface-variant text-xs font-semibold hover:bg-surface-container-highest transition-premium"
                        >
                          <X className="w-3.5 h-3.5" />Dismiss
                        </button>
                      </div>
                    )}
                    <button onClick={() => navigate(`/deadlines/${dl.id}`)} className="text-xs text-on-surface-variant/40 hover:text-primary transition-premium flex items-center gap-1">
                      Details <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>

                {/* AI Feedback prompt */}
                {isAI && dl.status === "pending" && (
                  <div className="mt-3 pt-3 border-t border-white/5 flex items-center gap-3">
                    <Sparkles className="w-3.5 h-3.5 text-primary shrink-0" />
                    <p className="text-xs text-on-surface-variant flex-1">Was this correctly detected?</p>
                    <button
                      onClick={() => feedbackMut.mutate({ id: dl.id, helpful: true })}
                      className="text-xs px-3 py-1 rounded-full bg-green-500/10 text-green-400 hover:bg-green-500/20 font-semibold transition-premium"
                    >Yes</button>
                    <button
                      onClick={() => feedbackMut.mutate({ id: dl.id, helpful: false })}
                      className="text-xs px-3 py-1 rounded-full bg-error/10 text-error hover:bg-error/20 font-semibold transition-premium"
                    >No</button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {filtered.length > 0 && (
        <div className="mt-6 flex items-center justify-between text-xs text-on-surface-variant/50">
          <span>{filtered.length} deadline{filtered.length !== 1 ? "s" : ""} shown</span>
          <span>{pendingCount} pending</span>
        </div>
      )}
    </div>
  );
}
