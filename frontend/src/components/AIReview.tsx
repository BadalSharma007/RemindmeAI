import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { format, parseISO, formatDistanceToNow } from "date-fns";
import {
  Sparkles, Check, X, Clock, ArrowLeft, ArrowRight,
  CheckCircle2, AlertTriangle, Edit3
} from "lucide-react";
import { deadlinesApi, type Deadline } from "../api/deadlines";
import { getDeadlineUrgency } from "../utils/urgency";
import { useToast } from "./ui/Toast";

export function AIReview() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [currentIndex, setCurrentIndex] = useState(0);

  const { data: deadlines = [], isLoading, isError } = useQuery({
    queryKey: ["deadlines", "all"],
    queryFn: () => deadlinesApi.list(),
  });

  // Unconfirmed or AI detected pending items
  const aiDeadlines = deadlines.filter(
    (d) => d.status === "pending" && d.source_text && d.source_text !== "Manual entry"
  );

  const feedbackMut = useMutation({
    mutationFn: ({ id, helpful }: { id: string; helpful: boolean }) =>
      deadlinesApi.feedback(id, helpful),
    onSuccess: (_, { helpful }) => {
      qc.invalidateQueries({ queryKey: ["deadlines"] });
      showToast(helpful ? "Deadline confirmed! 👍" : "Feedback recorded. Dismissed.", "info");
      if (currentIndex >= aiDeadlines.length - 1) {
        setCurrentIndex(Math.max(0, aiDeadlines.length - 2));
      }
    },
  });

  if (isLoading) {
    return (
      <div className="max-w-xl mx-auto space-y-4 animate-fade-in">
        <div className="skeleton h-8 w-48 rounded-xl" />
        <div className="skeleton h-72 rounded-2xl" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-20">
        <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-4" />
        <p className="text-on-surface-variant mb-4">Could not load AI review items.</p>
        <button onClick={() => navigate("/")} className="btn-primary-gradient px-5 py-2.5 rounded-xl text-sm">
          Return to Dashboard
        </button>
      </div>
    );
  }

  if (aiDeadlines.length === 0) {
    return (
      <div className="max-w-xl mx-auto text-center py-16">
        <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-5 shadow-glow">
          <CheckCircle2 className="w-8 h-8 text-emerald-400" />
        </div>
        <h2 className="text-xl font-bold text-on-surface mb-2">All Caught Up!</h2>
        <p className="text-sm text-on-surface-variant max-w-sm mx-auto mb-6">
          No pending AI-detected deadlines require your review right now.
        </p>
        <button onClick={() => navigate("/deadlines")} className="btn-primary-gradient px-6 py-3 rounded-xl text-sm inline-flex items-center gap-2">
          View All Deadlines <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    );
  }

  const currentDl = aiDeadlines[currentIndex] || aiDeadlines[0];
  const urgency = getDeadlineUrgency(currentDl.due_at, currentDl.status);

  return (
    <div className="max-w-xl mx-auto">
      {/* Back */}
      <button onClick={() => navigate("/")} className="flex items-center gap-2 text-on-surface-variant hover:text-on-surface transition-premium mb-6 text-sm">
        <ArrowLeft className="w-4 h-4" />Back to Dashboard
      </button>

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-primary-container flex items-center justify-center shadow-glow">
            <Sparkles className="w-5 h-5 text-on-primary" />
          </div>
          <div>
            <h1 className="text-headline-md text-on-surface">AI Detection Review</h1>
            <p className="text-xs text-on-surface-variant">
              Item {currentIndex + 1} of {aiDeadlines.length} pending review
            </p>
          </div>
        </div>
      </div>

      {/* Main Review Card */}
      <div className={`bg-surface-container rounded-2xl border ${urgency.cardBorder} overflow-hidden shadow-ambient mb-6`}>
        <div className={`h-1.5 ${urgency.stripeBg} w-full`} />

        <div className="p-6 space-y-4">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${urgency.badgeBg} ${urgency.badgeText} ${urgency.badgeBorder}`}>
              {urgency.label}
            </span>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-primary/10 text-primary flex items-center gap-1">
              <Sparkles className="w-3 h-3" />{Math.round(currentDl.confidence_score * 100)}% Confidence
            </span>
          </div>

          <div>
            <h2 className="text-lg font-bold text-on-surface mb-1">{currentDl.title}</h2>
            <div className="flex items-center gap-1.5 text-xs text-on-surface-variant">
              <Clock className={`w-3.5 h-3.5 ${urgency.iconColor}`} />
              <span>{format(parseISO(currentDl.due_at), "EEEE, MMMM d, yyyy · h:mm a")}</span>
              <span className="opacity-60">({formatDistanceToNow(parseISO(currentDl.due_at), { addSuffix: true })})</span>
            </div>
          </div>

          {/* Email Snippet */}
          {currentDl.source_text && (
            <div className="p-4 rounded-xl bg-primary/5 border border-primary/10">
              <p className="text-xs font-semibold text-primary mb-1 flex items-center gap-1">
                <Sparkles className="w-3 h-3" />Extracted from email:
              </p>
              <p className="text-xs text-on-surface-variant/90 italic leading-relaxed">
                "{currentDl.source_text}"
              </p>
            </div>
          )}

          {/* Decision Buttons */}
          <div className="pt-4 border-t border-white/5 space-y-3">
            <p className="text-xs font-semibold text-center text-on-surface">Is this date &amp; deadline accurate?</p>
            <div className="grid grid-cols-3 gap-2.5">
              <button
                onClick={() => feedbackMut.mutate({ id: currentDl.id, helpful: false })}
                disabled={feedbackMut.isPending}
                className="py-3 rounded-xl bg-red-500/10 text-red-400 text-xs font-bold hover:bg-red-500/20 transition-premium flex items-center justify-center gap-1.5"
              >
                <X className="w-4 h-4" /> Dismiss
              </button>
              <button
                onClick={() => navigate(`/deadlines/${currentDl.id}/edit`)}
                className="py-3 rounded-xl bg-surface-container-high text-on-surface text-xs font-bold hover:bg-surface-container-highest transition-premium flex items-center justify-center gap-1.5"
              >
                <Edit3 className="w-4 h-4 text-primary" /> Edit
              </button>
              <button
                onClick={() => feedbackMut.mutate({ id: currentDl.id, helpful: true })}
                disabled={feedbackMut.isPending}
                className="py-3 rounded-xl bg-emerald-500/10 text-emerald-400 text-xs font-bold hover:bg-emerald-500/20 transition-premium flex items-center justify-center gap-1.5"
              >
                <Check className="w-4 h-4" /> Confirm
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Pagination controls */}
      {aiDeadlines.length > 1 && (
        <div className="flex items-center justify-between text-xs text-on-surface-variant px-2">
          <button
            onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
            disabled={currentIndex === 0}
            className="flex items-center gap-1 disabled:opacity-30 hover:text-on-surface transition-premium"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Previous
          </button>
          <span>{currentIndex + 1} of {aiDeadlines.length}</span>
          <button
            onClick={() => setCurrentIndex((prev) => Math.min(aiDeadlines.length - 1, prev + 1))}
            disabled={currentIndex === aiDeadlines.length - 1}
            className="flex items-center gap-1 disabled:opacity-30 hover:text-on-surface transition-premium"
          >
            Next <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
