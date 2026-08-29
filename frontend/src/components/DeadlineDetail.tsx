import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format, parseISO, formatDistanceToNow } from "date-fns";
import {
  ArrowLeft, CalendarClock, Clock, Check, X, Trash2,
  Sparkles, Bell, Plus, AlertTriangle, CheckCircle2, Edit3,
} from "lucide-react";
import { deadlinesApi } from "../api/deadlines";
import { remindersApi } from "../api/reminders";
import { getDeadlineUrgency } from "../utils/urgency";
import { ConfirmDialog } from "./shared/ConfirmDialog";
import { Modal } from "./shared/Modal";

/* ── Create Reminder Mini-Form ─────────────────────────────────────── */
function CreateReminderModal({ deadlineId, onClose }: { deadlineId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [date, setDate] = useState(format(new Date(Date.now() + 3600000), "yyyy-MM-dd"));
  const [time, setTime] = useState(format(new Date(Date.now() + 3600000), "HH:mm"));
  const [channel, setChannel] = useState("email");

  const mut = useMutation({
    mutationFn: () => remindersApi.create({
      deadline_id: deadlineId,
      scheduled_at: new Date(`${date}T${time}`).toISOString(),
      channel,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reminders"] });
      onClose();
    },
  });

  return (
    <Modal isOpen title="Add Reminder" onClose={onClose} size="sm">
      <div className="space-y-4">
        <div>
          <label className="text-xs font-semibold text-on-surface-variant mb-1.5 block">Date</label>
          <input type="date" value={date} onChange={e => setDate(e.target.value)}
            className="w-full bg-surface-container-high text-on-surface rounded-lg px-4 py-2.5 text-sm ghost-border ghost-border-focus" />
        </div>
        <div>
          <label className="text-xs font-semibold text-on-surface-variant mb-1.5 block">Time</label>
          <input type="time" value={time} onChange={e => setTime(e.target.value)}
            className="w-full bg-surface-container-high text-on-surface rounded-lg px-4 py-2.5 text-sm ghost-border ghost-border-focus" />
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
        <button
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
          className="w-full btn-primary-gradient py-3 rounded-xl text-sm font-semibold disabled:opacity-50"
        >
          {mut.isPending ? "Setting reminder..." : "Set Reminder"}
        </button>
        {mut.isError && <p className="text-xs text-error text-center">Failed to create reminder. Try again.</p>}
      </div>
    </Modal>
  );
}

/* ── Deadline Detail Page with Dynamic Urgency Header ──────────────── */
export function DeadlineDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [showDelete, setShowDelete] = useState(false);
  const [showReminder, setShowReminder] = useState(false);

  const { data: dl, isLoading, isError } = useQuery({
    queryKey: ["deadline", id],
    queryFn: () => deadlinesApi.get(id!),
    enabled: !!id,
  });

  const { data: reminders = [] } = useQuery({
    queryKey: ["reminders", "all"],
    queryFn: () => remindersApi.list(),
  });

  const dlReminders = reminders.filter(r => r.deadline_id === id);

  const patchMut = useMutation({
    mutationFn: (status: "completed" | "dismissed" | "pending") => deadlinesApi.patch(id!, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["deadlines"] });
      qc.invalidateQueries({ queryKey: ["deadline", id] });
    },
  });

  const deleteMut = useMutation({
    mutationFn: () => deadlinesApi.delete(id!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["deadlines"] });
      navigate("/deadlines");
    },
  });

  const feedbackMut = useMutation({
    mutationFn: (helpful: boolean) => deadlinesApi.feedback(id!, helpful),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["deadline", id] }),
  });

  if (isLoading) return (
    <div className="animate-fade-in space-y-4">
      <div className="skeleton h-8 w-48 rounded-xl" />
      <div className="skeleton h-64 rounded-2xl" />
    </div>
  );

  if (isError || !dl) return (
    <div className="text-center py-20">
      <AlertTriangle className="w-10 h-10 text-error mx-auto mb-4" />
      <p className="text-on-surface-variant mb-4">Could not load this deadline.</p>
      <button onClick={() => navigate("/deadlines")} className="btn-primary-gradient px-5 py-2.5 rounded-xl text-sm">
        Back to Deadlines
      </button>
    </div>
  );

  const urgency = getDeadlineUrgency(dl.due_at, dl.status);
  const isAI = dl.source_text && dl.source_text !== "Manual entry" && dl.confidence_score < 1.0;
  const isActionable = dl.status === "pending" || dl.status === "reminded";

  const statusColors: Record<string, string> = {
    pending: "text-amber-400 bg-amber-500/10",
    reminded: "text-primary bg-primary/10",
    completed: "text-green-400 bg-green-500/10",
    dismissed: "text-on-surface-variant/60 bg-on-surface-variant/10",
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Back & Edit Action */}
      <div className="flex items-center justify-between mb-6">
        <button onClick={() => navigate("/deadlines")} className="flex items-center gap-2 text-on-surface-variant hover:text-on-surface transition-premium text-sm">
          <ArrowLeft className="w-4 h-4" />Back to Deadlines
        </button>
        <button
          onClick={() => navigate(`/deadlines/${id}/edit`)}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-surface-container text-on-surface hover:bg-surface-container-high border border-white/5 text-xs font-semibold transition-premium"
        >
          <Edit3 className="w-3.5 h-3.5 text-primary" />Edit Deadline
        </button>
      </div>

      {/* Main Card with Urgency Theme */}
      <div className={`bg-surface-container rounded-2xl border ${urgency.cardBorder} overflow-hidden mb-4`}>
        {/* Dynamic Urgency Top Banner Strip */}
        <div className={`h-1.5 ${urgency.stripeBg} w-full`} />

        <div className="p-6">
          {/* Title & Badges */}
          <div className="flex items-start gap-3 mb-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 flex-wrap mb-2">
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${urgency.badgeBg} ${urgency.badgeText} ${urgency.badgeBorder}`}>
                  {urgency.label}
                </span>
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${statusColors[dl.status] ?? statusColors.pending}`}>
                  {dl.status.charAt(0).toUpperCase() + dl.status.slice(1)}
                </span>
                {isAI && (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-primary/10 text-primary flex items-center gap-1">
                    <Sparkles className="w-3 h-3" />AI Detected
                  </span>
                )}
              </div>
              <h1 className={`text-xl font-semibold ${dl.status === "completed" ? "line-through text-on-surface-variant/50" : "text-on-surface"}`}>
                {dl.title}
              </h1>
            </div>
          </div>

          {/* Due date with Urgency Background */}
          <div className={`flex items-center gap-2 mb-4 p-3.5 rounded-xl border ${urgency.bannerBg} ${urgency.cardBorder}`}>
            <Clock className={`w-4 h-4 ${urgency.iconColor}`} />
            <div>
              <p className={`text-sm font-semibold ${urgency.badgeText}`}>
                {format(parseISO(dl.due_at), "EEEE, MMMM d, yyyy · h:mm a")}
              </p>
              <p className="text-xs text-on-surface-variant/60">
                {formatDistanceToNow(parseISO(dl.due_at), { addSuffix: true })}
              </p>
            </div>
          </div>

          {/* Source text */}
          {isAI && dl.source_text && (
            <div className="bg-primary/5 border border-primary/10 rounded-xl p-4 mb-4">
              <p className="text-xs font-semibold text-primary mb-1.5 flex items-center gap-1.5">
                <Sparkles className="w-3 h-3" />Detected from email
              </p>
              <p className="text-sm text-on-surface-variant italic">"{dl.source_text}"</p>
              <p className="text-xs text-on-surface-variant/40 mt-2">{Math.round(dl.confidence_score * 100)}% confidence</p>
            </div>
          )}

          {/* AI Feedback */}
          {isAI && dl.status === "pending" && (
            <div className="flex items-center gap-3 p-3 bg-surface-container-high rounded-xl mb-4">
              <Sparkles className="w-4 h-4 text-primary shrink-0" />
              <p className="text-sm text-on-surface-variant flex-1">Was this deadline correctly detected?</p>
              <button onClick={() => feedbackMut.mutate(true)}
                className="px-3 py-1.5 rounded-lg bg-green-500/10 text-green-400 text-xs font-semibold hover:bg-green-500/20 transition-premium flex items-center gap-1">
                <Check className="w-3 h-3" />Yes
              </button>
              <button onClick={() => feedbackMut.mutate(false)}
                className="px-3 py-1.5 rounded-lg bg-error/10 text-error text-xs font-semibold hover:bg-error/20 transition-premium flex items-center gap-1">
                <X className="w-3 h-3" />No
              </button>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {isActionable && (
              <>
                <button onClick={() => patchMut.mutate("completed")}
                  disabled={patchMut.isPending}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-green-500/10 text-green-400 text-sm font-semibold hover:bg-green-500/20 transition-premium disabled:opacity-50">
                  <CheckCircle2 className="w-4 h-4" />Mark Complete
                </button>
                <button onClick={() => patchMut.mutate("dismissed")}
                  disabled={patchMut.isPending}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-surface-container-high text-on-surface-variant text-sm font-semibold hover:bg-surface-container-highest transition-premium disabled:opacity-50">
                  <X className="w-4 h-4" />Dismiss
                </button>
              </>
            )}
            {dl.status !== "pending" && (
              <button onClick={() => patchMut.mutate("pending")}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary/10 text-primary text-sm font-semibold hover:bg-primary/20 transition-premium">
                <CalendarClock className="w-4 h-4" />Reopen
              </button>
            )}
            <button onClick={() => setShowDelete(true)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-error/10 text-error text-sm font-semibold hover:bg-error/20 transition-premium ml-auto">
              <Trash2 className="w-4 h-4" />Delete
            </button>
          </div>
        </div>
      </div>

      {/* Reminders Section */}
      <div className="bg-surface-container rounded-2xl border border-white/5 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-title-md text-on-surface font-semibold flex items-center gap-2">
            <Bell className="w-4 h-4 text-primary" />
            Reminders ({dlReminders.length})
          </h2>
          <button onClick={() => setShowReminder(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/10 text-primary text-xs font-semibold hover:bg-primary/20 transition-premium">
            <Plus className="w-3.5 h-3.5" />Add
          </button>
        </div>
        {dlReminders.length === 0 ? (
          <div className="text-center py-6">
            <Bell className="w-8 h-8 text-on-surface-variant/30 mx-auto mb-2" />
            <p className="text-sm text-on-surface-variant">No reminders set.</p>
            <button onClick={() => setShowReminder(true)}
              className="text-xs text-primary hover:underline underline-offset-2 mt-2">
              Add a reminder
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {dlReminders.map(r => (
              <div key={r.id} className="flex items-center gap-3 p-3 rounded-xl bg-surface-container-high">
                <Clock className="w-3.5 h-3.5 text-on-surface-variant/60 shrink-0" />
                <div className="flex-1 text-sm">
                  <span className="text-on-surface font-medium">{format(parseISO(r.scheduled_at), "MMM d · h:mm a")}</span>
                  <span className="text-on-surface-variant/50 ml-2 text-xs">via {r.channel}</span>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                  r.status === "sent" ? "bg-green-500/10 text-green-400" :
                  r.status === "pending" ? "bg-amber-500/10 text-amber-400" :
                  r.status === "snoozed" ? "bg-primary/10 text-primary" :
                  "bg-error/10 text-error"
                }`}>{r.status}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Dialogs */}
      <ConfirmDialog
        isOpen={showDelete}
        onClose={() => setShowDelete(false)}
        onConfirm={() => deleteMut.mutate()}
        title="Delete Deadline"
        message="This will permanently delete the deadline and all its reminders. This cannot be undone."
        confirmLabel="Delete"
        danger
        loading={deleteMut.isPending}
      />

      {showReminder && (
        <CreateReminderModal deadlineId={id!} onClose={() => setShowReminder(false)} />
      )}
    </div>
  );
}
