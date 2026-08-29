import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format, parseISO, formatDistanceToNow, addMinutes, addHours, addDays, setHours, setMinutes } from "date-fns";
import {
  Bell, Clock, AlarmClock, CheckCircle2, XCircle, Send,
  Filter, Plus, AlertTriangle, X,
} from "lucide-react";
import { remindersApi, type Reminder } from "../api/reminders";
import { deadlinesApi } from "../api/deadlines";
import { getDeadlineUrgency } from "../utils/urgency";
import { Modal } from "./shared/Modal";
import { ConfirmDialog } from "./shared/ConfirmDialog";

const STATUS_CONFIG: Record<string, { bg: string; text: string; icon: React.ElementType; label: string }> = {
  pending: { bg: "bg-amber-500/10", text: "text-amber-400", icon: Clock, label: "Pending" },
  sent: { bg: "bg-green-500/10", text: "text-green-400", icon: CheckCircle2, label: "Sent" },
  failed: { bg: "bg-error/10", text: "text-error", icon: XCircle, label: "Failed" },
  snoozed: { bg: "bg-primary/10", text: "text-primary", icon: AlarmClock, label: "Snoozed" },
  dismissed: { bg: "bg-on-surface-variant/10", text: "text-on-surface-variant/60", icon: XCircle, label: "Dismissed" },
};

/* ── Snooze Modal ───────────────────────────────────────────────────── */
function SnoozeModal({ reminder, onClose }: { reminder: Reminder; onClose: () => void }) {
  const qc = useQueryClient();
  const [customDate, setCustomDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [customTime, setCustomTime] = useState("09:00");
  const [showCustom, setShowCustom] = useState(false);

  const snooze = useMutation({
    mutationFn: (until: Date) => remindersApi.snooze(reminder.id, until.toISOString()),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["reminders"] }); onClose(); },
  });

  const presets = [
    { label: "30 min", getDate: () => addMinutes(new Date(), 30) },
    { label: "1 hour", getDate: () => addHours(new Date(), 1) },
    { label: "4 hours", getDate: () => addHours(new Date(), 4) },
    { label: "Tomorrow 9am", getDate: () => setMinutes(setHours(addDays(new Date(), 1), 9), 0) },
    { label: "Custom", getDate: null },
  ];

  return (
    <Modal isOpen title="Snooze Reminder" onClose={onClose} size="sm">
      <div className="space-y-3">
        <p className="text-xs text-on-surface-variant mb-4">Choose when to be reminded again:</p>
        {presets.map(p => (
          p.getDate ? (
            <button
              key={p.label}
              onClick={() => snooze.mutate(p.getDate())}
              disabled={snooze.isPending}
              className="w-full py-3 rounded-xl bg-surface-container-high text-on-surface text-sm font-semibold hover:bg-primary/10 hover:text-primary transition-premium disabled:opacity-50 flex items-center justify-between px-4"
            >
              <span>{p.label}</span>
              <span className="text-xs text-on-surface-variant/50">{format(p.getDate(), "h:mm a")}</span>
            </button>
          ) : (
            <button key={p.label} onClick={() => setShowCustom(!showCustom)}
              className="w-full py-3 rounded-xl bg-surface-container-high text-on-surface text-sm font-semibold hover:bg-primary/10 hover:text-primary transition-premium flex items-center px-4 gap-2">
              <AlarmClock className="w-4 h-4" />Custom time
            </button>
          )
        ))}
        {showCustom && (
          <div className="space-y-2 pt-2">
            <input type="date" value={customDate} onChange={e => setCustomDate(e.target.value)}
              className="w-full bg-surface-container-high text-on-surface rounded-xl px-4 py-2.5 text-sm ghost-border ghost-border-focus" />
            <input type="time" value={customTime} onChange={e => setCustomTime(e.target.value)}
              className="w-full bg-surface-container-high text-on-surface rounded-xl px-4 py-2.5 text-sm ghost-border ghost-border-focus" />
            <button
              onClick={() => snooze.mutate(new Date(`${customDate}T${customTime}`))}
              disabled={snooze.isPending}
              className="w-full btn-primary-gradient py-2.5 rounded-xl text-sm font-semibold disabled:opacity-50"
            >Set Custom Snooze</button>
          </div>
        )}
        {snooze.isError && <p className="text-xs text-error text-center">Failed to snooze. Try again.</p>}
      </div>
    </Modal>
  );
}

/* ── Create Reminder Modal ──────────────────────────────────────────── */
function CreateReminderModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const { data: deadlines = [] } = useQuery({ queryKey: ["deadlines", "all"], queryFn: () => deadlinesApi.list() });
  const pending = deadlines.filter(d => d.status === "pending" || d.status === "reminded");

  const [deadlineId, setDeadlineId] = useState(pending[0]?.id ?? "");
  const [date, setDate] = useState(format(new Date(Date.now() + 3600000), "yyyy-MM-dd"));
  const [time, setTime] = useState(format(new Date(Date.now() + 3600000), "HH:mm"));
  const [channel, setChannel] = useState("email");

  const mut = useMutation({
    mutationFn: () => remindersApi.create({
      deadline_id: deadlineId,
      scheduled_at: new Date(`${date}T${time}`).toISOString(),
      channel,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["reminders"] }); onClose(); },
  });

  return (
    <Modal isOpen title="New Reminder" onClose={onClose} size="sm">
      <div className="space-y-4">
        <div>
          <label className="text-xs font-semibold text-on-surface-variant mb-1.5 block">Deadline</label>
          {pending.length === 0 ? (
            <p className="text-xs text-on-surface-variant">No pending deadlines. Create a deadline first.</p>
          ) : (
            <select value={deadlineId} onChange={e => setDeadlineId(e.target.value)}
              className="w-full bg-surface-container-high text-on-surface rounded-xl px-4 py-2.5 text-sm ghost-border ghost-border-focus">
              {pending.map(d => <option key={d.id} value={d.id}>{d.title}</option>)}
            </select>
          )}
        </div>
        <div>
          <label className="text-xs font-semibold text-on-surface-variant mb-1.5 block">Date</label>
          <input type="date" value={date} onChange={e => setDate(e.target.value)}
            className="w-full bg-surface-container-high text-on-surface rounded-xl px-4 py-2.5 text-sm ghost-border ghost-border-focus" />
        </div>
        <div>
          <label className="text-xs font-semibold text-on-surface-variant mb-1.5 block">Time</label>
          <input type="time" value={time} onChange={e => setTime(e.target.value)}
            className="w-full bg-surface-container-high text-on-surface rounded-xl px-4 py-2.5 text-sm ghost-border ghost-border-focus" />
        </div>
        <div>
          <label className="text-xs font-semibold text-on-surface-variant mb-1.5 block">Channel</label>
          <div className="flex gap-2">
            {["email", "push"].map(c => (
              <button key={c} onClick={() => setChannel(c)}
                className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-premium ${channel === c ? "chip-selected" : "chip-unselected"}`}>
                {c.charAt(0).toUpperCase() + c.slice(1)}
              </button>
            ))}
          </div>
        </div>
        <button onClick={() => mut.mutate()} disabled={!deadlineId || mut.isPending}
          className="w-full btn-primary-gradient py-3 rounded-xl text-sm font-semibold disabled:opacity-50">
          {mut.isPending ? "Setting..." : "Set Reminder"}
        </button>
        {mut.isError && <p className="text-xs text-error text-center">Failed. Try again.</p>}
      </div>
    </Modal>
  );
}

/* ── Reminders Page ─────────────────────────────────────────────────── */
function RemindersSkeleton() {
  return (
    <div className="animate-fade-in space-y-4">
      <div className="skeleton h-8 w-40 rounded-xl" />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[1,2,3,4].map(i => <div key={i} className="skeleton h-20 rounded-xl" />)}
      </div>
      <div className="space-y-3">
        {[1,2,3].map(i => <div key={i} className="skeleton h-24 rounded-xl" />)}
      </div>
    </div>
  );
}

export function Reminders() {
  const qc = useQueryClient();
  const [activeFilter, setActiveFilter] = useState("all");
  const [snoozeTarget, setSnoozeTarget] = useState<Reminder | null>(null);
  const [dismissTarget, setDismissTarget] = useState<Reminder | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const { data: reminders = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["reminders", "all"],
    queryFn: () => remindersApi.list(),
  });

  const dismissMut = useMutation({
    mutationFn: (id: string) => remindersApi.dismiss(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ["reminders"] });
      const prev = qc.getQueryData<Reminder[]>(["reminders", "all"]);
      qc.setQueryData<Reminder[]>(["reminders", "all"], old =>
        old?.map(r => r.id === id ? { ...r, status: "dismissed" as const } : r)
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => qc.setQueryData(["reminders", "all"], ctx?.prev),
    onSettled: () => qc.invalidateQueries({ queryKey: ["reminders"] }),
  });

  if (isLoading) return <RemindersSkeleton />;

  if (isError) return (
    <div className="bg-surface-container rounded-2xl p-12 text-center border border-white/5">
      <AlertTriangle className="w-8 h-8 text-error mx-auto mb-4" />
      <h3 className="text-title-md text-on-surface mb-2">Could not load reminders</h3>
      <button onClick={() => refetch()} className="btn-primary-gradient px-5 py-2.5 rounded-xl text-sm mt-4">Try again</button>
    </div>
  );

  const pendingCount = reminders.filter(r => r.status === "pending").length;
  const sentCount = reminders.filter(r => r.status === "sent").length;
  const failedCount = reminders.filter(r => r.status === "failed").length;
  const snoozedCount = reminders.filter(r => r.status === "snoozed").length;

  const filtered = reminders.filter(r => activeFilter === "all" || r.status === activeFilter);
  const filters = ["all", "pending", "sent", "snoozed", "failed", "dismissed"];

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between gap-4 mb-1">
          <div className="flex items-center gap-3">
            <Bell className="w-5 h-5 text-primary" />
            <h1 className="text-headline-md text-on-surface">Reminders</h1>
            {pendingCount > 0 && (
              <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400">{pendingCount} pending</span>
            )}
          </div>
          <button onClick={() => setShowCreate(true)}
            className="btn-primary-gradient px-4 py-2.5 rounded-xl text-sm flex items-center gap-2 shrink-0">
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">New Reminder</span>
          </button>
        </div>
        <p className="text-body-md text-on-surface-variant ml-8">Scheduled notifications for your deadlines.</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[
          { label: "Pending", value: pendingCount, color: "text-amber-400" },
          { label: "Sent", value: sentCount, color: "text-green-400" },
          { label: "Snoozed", value: snoozedCount, color: "text-primary" },
          { label: "Failed", value: failedCount, color: "text-error" },
        ].map(s => (
          <div key={s.label} className="bg-surface-container rounded-xl p-4 text-center border border-white/5 animate-slide-up">
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            <p className="text-label-sm text-on-surface-variant mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Urgency Guide Bar */}
      <div className="flex items-center gap-3 flex-wrap text-xs text-on-surface-variant/70 mb-5 bg-surface-container-low px-4 py-2.5 rounded-xl border border-white/5">
        <span className="font-semibold text-on-surface">Reminder timing:</span>
        <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-red-500/10 text-red-400 font-medium">🔴 &le;2 Days</span>
        <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-400 font-medium">🔵 3-7 Days</span>
        <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 font-medium">🟢 &gt;7 Days</span>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 mb-6">
        <Filter className="w-4 h-4 text-on-surface-variant/50 shrink-0" />
        {filters.map(f => (
          <button key={f} onClick={() => setActiveFilter(f)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-premium ${activeFilter === f ? "chip-selected" : "chip-unselected hover:bg-surface-container-high"}`}>
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      {filtered.length === 0 ? (
        <div className="bg-surface-container rounded-2xl p-12 text-center border border-white/5">
          <Bell className="w-8 h-8 text-on-surface-variant/30 mx-auto mb-3" />
          <h3 className="text-title-md text-on-surface mb-2">
            {activeFilter === "all" ? "No reminders yet" : `No ${activeFilter} reminders`}
          </h3>
          <p className="text-body-md text-on-surface-variant max-w-sm mx-auto">
            {activeFilter === "pending" ? "No pending reminders. Great!" : "Add reminders to your deadlines to get notified at the right time."}
          </p>
          {activeFilter === "all" && (
            <button onClick={() => setShowCreate(true)} className="btn-primary-gradient px-5 py-2.5 rounded-xl text-sm mt-6 inline-flex items-center gap-2">
              <Plus className="w-4 h-4" />Add Reminder
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((r, idx) => {
            const cfg = STATUS_CONFIG[r.status] ?? STATUS_CONFIG.pending;
            const Icon = cfg.icon;
            const isPending = r.status === "pending";
            const urgency = getDeadlineUrgency(r.scheduled_at, r.status);

            return (
              <div
                key={r.id}
                className={`bg-surface-container rounded-xl p-5 card-hover animate-slide-up group border ${urgency.cardBorder} relative overflow-hidden`}
                style={{ animationDelay: `${idx * 40}ms` }}
              >
                {/* Dynamic Urgency Left Stripe */}
                <div className={`absolute left-0 top-0 bottom-0 w-1.5 ${urgency.stripeBg} rounded-l-xl`} />

                <div className="flex items-center justify-between gap-4 pl-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2.5 flex-wrap">
                      <Clock className={`w-3.5 h-3.5 ${urgency.iconColor} shrink-0`} />
                      <p className="text-body-md text-on-surface-variant">
                        <span className={`font-medium ${urgency.badgeText}`}>{format(parseISO(r.scheduled_at), "MMM d, yyyy · h:mm a")}</span>
                        <span className="ml-1.5 text-xs opacity-60">({formatDistanceToNow(parseISO(r.scheduled_at), { addSuffix: true })})</span>
                      </p>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${urgency.badgeBg} ${urgency.badgeText} ${urgency.badgeBorder}`}>
                        {urgency.label}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-2.5">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container-high text-on-surface-variant text-xs font-medium">
                        <Send className="w-3 h-3" />{r.channel}
                      </span>
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
                        <Icon className="w-3 h-3" />{cfg.label}
                      </span>
                      {r.sent_at && (
                        <span className="text-xs text-on-surface-variant/40">Sent {format(parseISO(r.sent_at), "MMM d · h:mm a")}</span>
                      )}
                      {r.snooze_until && r.status === "snoozed" && (
                        <span className="text-xs text-primary/60">Until {format(parseISO(r.snooze_until), "MMM d · h:mm a")}</span>
                      )}
                    </div>
                  </div>

                  {isPending && (
                    <div className="flex gap-2 shrink-0">
                      <button onClick={() => setSnoozeTarget(r)}
                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-primary/10 text-primary text-xs font-semibold hover:bg-primary/20 transition-premium">
                        <AlarmClock className="w-3.5 h-3.5" />Snooze
                      </button>
                      <button onClick={() => setDismissTarget(r)}
                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-surface-container-high text-on-surface-variant text-xs font-semibold hover:bg-error/10 hover:text-error transition-premium">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {filtered.length > 0 && (
        <div className="mt-6 flex items-center justify-between text-xs text-on-surface-variant/50">
          <span>{filtered.length} reminder{filtered.length !== 1 ? "s" : ""} shown</span>
          <span>{pendingCount} pending · {sentCount} sent</span>
        </div>
      )}

      {/* Snooze Modal */}
      {snoozeTarget && <SnoozeModal reminder={snoozeTarget} onClose={() => setSnoozeTarget(null)} />}

      {/* Dismiss Confirm */}
      <ConfirmDialog
        isOpen={!!dismissTarget}
        onClose={() => setDismissTarget(null)}
        onConfirm={() => { if (dismissTarget) { dismissMut.mutate(dismissTarget.id); setDismissTarget(null); } }}
        title="Dismiss Reminder"
        message="This reminder will be cancelled and won't fire. Are you sure?"
        confirmLabel="Dismiss"
        danger
        loading={dismissMut.isPending}
      />

      {/* Create Reminder */}
      {showCreate && <CreateReminderModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
