import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { MailMinus, ShieldCheck, AlertTriangle, CheckCircle2, Search, ArrowLeft } from "lucide-react";
import { subscriptionsApi, type Subscription } from "../api";
import { ConfirmDialog } from "./shared/ConfirmDialog";
import { useToast } from "./ui/Toast";

export function Subscriptions() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [search, setSearch] = useState("");
  const [selectedSub, setSelectedSub] = useState<Subscription | null>(null);

  const { data: subs = [], isLoading, isError } = useQuery({
    queryKey: ["subscriptions"],
    queryFn: () => subscriptionsApi.list(),
  });

  const unsubMut = useMutation({
    mutationFn: (id: string) => subscriptionsApi.unsubscribe(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["subscriptions"] });
      showToast("Unsubscribe request initiated.", "success");
      setSelectedSub(null);
    },
    onError: () => {
      showToast("Could not process unsubscribe. Try again later.", "error");
      setSelectedSub(null);
    },
  });

  const filtered = subs.filter(
    (s) =>
      s.sender_email.toLowerCase().includes(search.toLowerCase()) ||
      (s.sender_name && s.sender_name.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-primary-container flex items-center justify-center shadow-glow">
            <MailMinus className="w-5 h-5 text-on-primary" />
          </div>
          <div>
            <h1 className="text-headline-md text-on-surface">Promotional Subscriptions</h1>
            <p className="text-xs text-on-surface-variant">
              Manage newsletter and promotional senders detected from your inbox.
            </p>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant/50" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter subscriptions..."
          className="w-full bg-surface-container text-on-surface rounded-xl pl-10 pr-4 py-2.5 text-sm ghost-border ghost-border-focus"
        />
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton h-20 rounded-xl" />
          ))}
        </div>
      ) : isError || filtered.length === 0 ? (
        <div className="bg-surface-container rounded-2xl p-12 text-center border border-white/5">
          <ShieldCheck className="w-10 h-10 text-emerald-400 mx-auto mb-3" />
          <h3 className="text-title-md text-on-surface mb-1">
            {search ? "No matches found" : "Clean Inbox!"}
          </h3>
          <p className="text-xs text-on-surface-variant max-w-sm mx-auto">
            {search
              ? `No senders matching "${search}".`
              : "No promotional newsletters detected from your inbox yet."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((s) => (
            <div
              key={s.id}
              className="bg-surface-container rounded-xl p-4 border border-white/5 flex items-center justify-between gap-4 card-hover"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-on-surface truncate">
                  {s.sender_name || s.sender_email}
                </p>
                <p className="text-xs text-on-surface-variant/70 truncate">{s.sender_email}</p>
              </div>
              <button
                onClick={() => setSelectedSub(s)}
                className="px-3.5 py-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 text-xs font-semibold transition-premium shrink-0"
              >
                Unsubscribe
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Unsubscribe Confirmation */}
      <ConfirmDialog
        isOpen={!!selectedSub}
        onClose={() => setSelectedSub(null)}
        onConfirm={() => selectedSub && unsubMut.mutate(selectedSub.id)}
        title="Confirm Unsubscribe"
        message={`Are you sure you want to trigger unsubscribe for ${selectedSub?.sender_email}?`}
        confirmLabel="Unsubscribe"
        danger
        loading={unsubMut.isPending}
      />
    </div>
  );
}
