import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ArrowLeft, CalendarClock, Clock, Check } from "lucide-react";
import { deadlinesApi } from "../api/deadlines";

export function CreateDeadline() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [title, setTitle] = useState("");
  const [date, setDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [time, setTime] = useState("09:00");
  const [notes, setNotes] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const mut = useMutation({
    mutationFn: () => deadlinesApi.create({
      title: title.trim(),
      due_at: new Date(`${date}T${time}`).toISOString(),
      source_text: notes.trim() || undefined,
    }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["deadlines"] });
      navigate(`/deadlines/${data.id}`);
    },
  });

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!title.trim() || title.trim().length < 2) errs.title = "Title must be at least 2 characters.";
    const due = new Date(`${date}T${time}`);
    if (isNaN(due.getTime()) || due <= new Date()) errs.date = "Due date must be in the future.";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSave = () => {
    if (validate()) mut.mutate();
  };

  return (
    <div className="max-w-xl mx-auto">
      {/* Back */}
      <button onClick={() => navigate("/deadlines")} className="flex items-center gap-2 text-on-surface-variant hover:text-on-surface transition-premium mb-6 text-sm">
        <ArrowLeft className="w-4 h-4" />Back to Deadlines
      </button>

      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-primary-container flex items-center justify-center">
          <CalendarClock className="w-5 h-5 text-on-primary" />
        </div>
        <div>
          <h1 className="text-headline-md text-on-surface">New Deadline</h1>
          <p className="text-body-md text-on-surface-variant">Create a deadline manually.</p>
        </div>
      </div>

      {/* Form */}
      <div className="bg-surface-container rounded-2xl p-6 border border-white/5 space-y-5">
        {/* Title */}
        <div>
          <label className="text-xs font-semibold text-on-surface-variant mb-2 block uppercase tracking-wide">
            Title <span className="text-error">*</span>
          </label>
          <input
            id="deadline-title"
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="e.g. Submit project proposal"
            className={`w-full bg-surface-container-high text-on-surface rounded-xl px-4 py-3 text-sm ghost-border ghost-border-focus transition-premium placeholder:text-on-surface-variant/40 ${errors.title ? "border border-error/50" : ""}`}
            onKeyDown={e => e.key === "Enter" && handleSave()}
          />
          {errors.title && <p className="text-xs text-error mt-1.5">{errors.title}</p>}
        </div>

        {/* Date */}
        <div>
          <label className="text-xs font-semibold text-on-surface-variant mb-2 block uppercase tracking-wide">
            Due Date <span className="text-error">*</span>
          </label>
          <div className="flex gap-3">
            <div className="flex-1">
              <div className="relative">
                <CalendarClock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant/50" />
                <input
                  id="deadline-date"
                  type="date"
                  value={date}
                  onChange={e => setDate(e.target.value)}
                  className={`w-full bg-surface-container-high text-on-surface rounded-xl pl-10 pr-4 py-3 text-sm ghost-border ghost-border-focus transition-premium ${errors.date ? "border border-error/50" : ""}`}
                />
              </div>
            </div>
            <div className="w-36">
              <div className="relative">
                <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant/50" />
                <input
                  id="deadline-time"
                  type="time"
                  value={time}
                  onChange={e => setTime(e.target.value)}
                  className="w-full bg-surface-container-high text-on-surface rounded-xl pl-10 pr-4 py-3 text-sm ghost-border ghost-border-focus transition-premium"
                />
              </div>
            </div>
          </div>
          {errors.date && <p className="text-xs text-error mt-1.5">{errors.date}</p>}
        </div>

        {/* Notes */}
        <div>
          <label className="text-xs font-semibold text-on-surface-variant mb-2 block uppercase tracking-wide">
            Notes <span className="text-on-surface-variant/30 font-normal normal-case">(optional)</span>
          </label>
          <textarea
            id="deadline-notes"
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Add context or notes..."
            rows={3}
            className="w-full bg-surface-container-high text-on-surface rounded-xl px-4 py-3 text-sm ghost-border ghost-border-focus transition-premium placeholder:text-on-surface-variant/40 resize-none"
          />
        </div>

        {/* Save */}
        <div className="flex gap-3 pt-2">
          <button onClick={() => navigate("/deadlines")}
            className="flex-1 py-3 rounded-xl bg-surface-container-high text-on-surface-variant text-sm font-semibold hover:bg-surface-container-highest transition-premium">
            Cancel
          </button>
          <button
            id="save-deadline-btn"
            onClick={handleSave}
            disabled={mut.isPending}
            className="flex-1 btn-primary-gradient py-3 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {mut.isPending ? (
              <span className="flex items-center gap-2"><span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />Saving...</span>
            ) : (
              <><Check className="w-4 h-4" />Save Deadline</>
            )}
          </button>
        </div>

        {mut.isError && (
          <p className="text-xs text-error text-center pt-1">Failed to create deadline. Please try again.</p>
        )}
      </div>
    </div>
  );
}
