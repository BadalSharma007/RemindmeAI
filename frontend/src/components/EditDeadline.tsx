import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { ArrowLeft, Edit3, CalendarClock, Clock, Check, AlertTriangle } from "lucide-react";
import { deadlinesApi } from "../api/deadlines";
import { useToast } from "./ui/Toast";
import { friendlyError } from "../utils/errors";

export function EditDeadline() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { showToast } = useToast();

  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const { data: dl, isLoading, isError } = useQuery({
    queryKey: ["deadline", id],
    queryFn: () => deadlinesApi.get(id!),
    enabled: !!id,
  });

  useEffect(() => {
    if (dl) {
      setTitle(dl.title);
      try {
        const d = parseISO(dl.due_at);
        setDate(format(d, "yyyy-MM-dd"));
        setTime(format(d, "HH:mm"));
      } catch {
        setDate(format(new Date(), "yyyy-MM-dd"));
        setTime("09:00");
      }
    }
  }, [dl]);

  const patchMut = useMutation({
    mutationFn: (body: { title: string; due_at?: string }) => deadlinesApi.patch(id!, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["deadlines"] });
      qc.invalidateQueries({ queryKey: ["deadline", id] });
      showToast("Deadline updated successfully!", "success");
      navigate(`/deadlines/${id}`);
    },
    onError: (err) => {
      showToast(friendlyError(err), "error");
    },
  });

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!title.trim() || title.trim().length < 2) errs.title = "Title must be at least 2 characters.";
    const due = new Date(`${date}T${time}`);
    if (isNaN(due.getTime())) errs.date = "Please enter a valid date and time.";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSave = () => {
    if (validate()) {
      const isoDue = new Date(`${date}T${time}`).toISOString();
      patchMut.mutate({
        title: title.trim(),
        due_at: isoDue,
      });
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-xl mx-auto space-y-4 animate-fade-in">
        <div className="skeleton h-8 w-40 rounded-xl" />
        <div className="skeleton h-64 rounded-2xl" />
      </div>
    );
  }

  if (isError || !dl) {
    return (
      <div className="text-center py-20">
        <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-4" />
        <p className="text-on-surface-variant mb-4">Could not load deadline details.</p>
        <button onClick={() => navigate("/deadlines")} className="btn-primary-gradient px-5 py-2.5 rounded-xl text-sm">
          Back to Deadlines
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto">
      {/* Back */}
      <button onClick={() => navigate(`/deadlines/${id}`)} className="flex items-center gap-2 text-on-surface-variant hover:text-on-surface transition-premium mb-6 text-sm">
        <ArrowLeft className="w-4 h-4" />Back to Details
      </button>

      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-primary-container flex items-center justify-center">
          <Edit3 className="w-5 h-5 text-on-primary" />
        </div>
        <div>
          <h1 className="text-headline-md text-on-surface">Edit Deadline</h1>
          <p className="text-body-md text-on-surface-variant">Update the deadline title or schedule.</p>
        </div>
      </div>

      {/* Form */}
      <div className="bg-surface-container rounded-2xl p-6 border border-white/5 space-y-5">
        {/* Title */}
        <div>
          <label className="text-xs font-semibold text-on-surface-variant mb-2 block uppercase tracking-wide">
            Title <span className="text-red-400">*</span>
          </label>
          <input
            id="edit-deadline-title"
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            className={`w-full bg-surface-container-high text-on-surface rounded-xl px-4 py-3 text-sm ghost-border ghost-border-focus transition-premium ${errors.title ? "border border-red-500/50" : ""}`}
          />
          {errors.title && <p className="text-xs text-red-400 mt-1.5">{errors.title}</p>}
        </div>

        {/* Date & Time */}
        <div>
          <label className="text-xs font-semibold text-on-surface-variant mb-2 block uppercase tracking-wide">
            Due Date &amp; Time <span className="text-red-400">*</span>
          </label>
          <div className="flex gap-3">
            <div className="flex-1">
              <div className="relative">
                <CalendarClock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant/50" />
                <input
                  id="edit-deadline-date"
                  type="date"
                  value={date}
                  onChange={e => setDate(e.target.value)}
                  className={`w-full bg-surface-container-high text-on-surface rounded-xl pl-10 pr-4 py-3 text-sm ghost-border ghost-border-focus transition-premium ${errors.date ? "border border-red-500/50" : ""}`}
                />
              </div>
            </div>
            <div className="w-36">
              <div className="relative">
                <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant/50" />
                <input
                  id="edit-deadline-time"
                  type="time"
                  value={time}
                  onChange={e => setTime(e.target.value)}
                  className="w-full bg-surface-container-high text-on-surface rounded-xl pl-10 pr-4 py-3 text-sm ghost-border ghost-border-focus transition-premium"
                />
              </div>
            </div>
          </div>
          {errors.date && <p className="text-xs text-red-400 mt-1.5">{errors.date}</p>}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-2">
          <button
            onClick={() => navigate(`/deadlines/${id}`)}
            className="flex-1 py-3 rounded-xl bg-surface-container-high text-on-surface-variant text-sm font-semibold hover:bg-surface-container-highest transition-premium"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={patchMut.isPending}
            className="flex-1 btn-primary-gradient py-3 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {patchMut.isPending ? "Saving changes..." : <><Check className="w-4 h-4" />Save Changes</>}
          </button>
        </div>
      </div>
    </div>
  );
}
