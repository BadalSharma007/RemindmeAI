import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Settings as SettingsIcon, User, Bell, AlertTriangle,
  LogOut, Unplug, Save, Shield, Globe, Mail,
} from "lucide-react";
import { authApi, preferencesApi } from "../api";
import { ConfirmDialog } from "./shared/ConfirmDialog";
import { useToast } from "./ui/Toast";

const LEAD_OPTIONS = [
  { label: "15 minutes", value: 15 },
  { label: "30 minutes", value: 30 },
  { label: "1 hour", value: 60 },
  { label: "2 hours", value: 120 },
  { label: "4 hours", value: 240 },
];

const TIMEZONE_OPTIONS = [
  "Asia/Kolkata",
  "America/New_York",
  "America/Los_Angeles",
  "America/Chicago",
  "Europe/London",
  "Europe/Paris",
  "Europe/Berlin",
  "Asia/Dubai",
  "Asia/Singapore",
  "Asia/Tokyo",
  "Australia/Sydney",
  "UTC",
];

function SettingSection({ title, icon: Icon, accent = "text-primary", children }: {
  title: string; icon: React.ElementType; accent?: string; children: React.ReactNode;
}) {
  return (
    <div className="bg-surface-container rounded-2xl p-6 border border-white/5 animate-slide-up">
      <div className="flex items-center gap-3 mb-5">
        <div className={`p-2 rounded-lg bg-surface-container-high ${accent}`}>
          <Icon className="w-4 h-4" />
        </div>
        <h2 className="text-title-md text-on-surface font-semibold">{title}</h2>
      </div>
      {children}
    </div>
  );
}

function SettingRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-white/5 last:border-0">
      <span className="text-body-md text-on-surface-variant">{label}</span>
      <div className="text-body-md text-on-surface font-medium">{children}</div>
    </div>
  );
}

export function Settings() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const storedEmail = localStorage.getItem("user_email");

  const [leadMinutes, setLeadMinutes] = useState(60);
  const [selectedTz, setSelectedTz] = useState("Asia/Kolkata");
  const [showDisconnect, setShowDisconnect] = useState(false);
  const [showLogout, setShowLogout] = useState(false);

  const { data: user } = useQuery({
    queryKey: ["me"],
    queryFn: authApi.me,
  });

  const { data: prefs } = useQuery({
    queryKey: ["preferences"],
    queryFn: preferencesApi.get,
  });

  useEffect(() => {
    if (prefs?.reminder_lead_minutes) {
      setLeadMinutes(prefs.reminder_lead_minutes);
    }
    if (prefs?.timezone) {
      setSelectedTz(prefs.timezone);
    } else if (user?.timezone) {
      setSelectedTz(user.timezone);
    }
  }, [prefs, user]);

  const savePrefsMut = useMutation({
    mutationFn: () =>
      preferencesApi.update({
        reminder_lead_minutes: leadMinutes,
        timezone: selectedTz,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["preferences"] });
      qc.invalidateQueries({ queryKey: ["me"] });
      showToast("Preferences saved successfully!", "success");
    },
    onError: () => {
      showToast("Could not update preferences.", "error");
    },
  });

  const disconnectMut = useMutation({
    mutationFn: () => authApi.disconnect("gmail"),
    onSuccess: () => {
      showToast("Gmail disconnected.", "info");
      window.location.reload();
    },
    onError: () => {
      showToast("Failed to disconnect Gmail.", "error");
    },
  });

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_email");
    window.location.href = "/login";
  };

  const initials = (user?.display_name ?? user?.email ?? storedEmail ?? "?")
    .split(" ")
    .map((n: string) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <SettingsIcon className="w-5 h-5 text-primary" />
          <h1 className="text-headline-md text-on-surface">Settings</h1>
        </div>
        <p className="text-body-md text-on-surface-variant ml-8">Manage your account and preferences.</p>
      </div>

      <div className="space-y-4">
        {/* Profile */}
        <SettingSection title="Profile" icon={User}>
          <div className="flex items-center gap-4 mb-5 p-4 bg-surface-container-high rounded-xl">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary to-primary-container flex items-center justify-center text-on-primary font-bold text-sm shrink-0">
              {initials}
            </div>
            <div className="min-w-0">
              <p className="text-on-surface font-semibold truncate">
                {user?.display_name ?? storedEmail?.split("@")[0] ?? "User"}
              </p>
              <p className="text-xs text-on-surface-variant truncate">{user?.email ?? storedEmail ?? "—"}</p>
            </div>
          </div>
          <div className="space-y-0">
            <SettingRow label="Email">{user?.email ?? storedEmail ?? "—"}</SettingRow>
            <SettingRow label="Configured Timezone">
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-primary shrink-0" />
                <select
                  value={selectedTz}
                  onChange={(e) => setSelectedTz(e.target.value)}
                  className="bg-surface-container-high text-on-surface text-xs rounded-lg px-2.5 py-1.5 border border-white/5 font-medium"
                >
                  {TIMEZONE_OPTIONS.map((tz) => (
                    <option key={tz} value={tz}>
                      {tz}
                    </option>
                  ))}
                </select>
              </div>
            </SettingRow>
          </div>
        </SettingSection>

        {/* Connected Accounts */}
        <SettingSection title="Connected Accounts" icon={Mail} accent="text-primary">
          <div className="flex items-center gap-4 p-4 bg-surface-container-high rounded-xl">
            <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center shrink-0">
              <svg viewBox="0 0 24 24" className="w-5 h-5">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-on-surface">Gmail</p>
              <p className="text-xs text-on-surface-variant truncate">{user?.email ?? storedEmail ?? "Connected"}</p>
            </div>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-green-500/10 text-green-400">Active</span>
          </div>
        </SettingSection>

        {/* Preferences */}
        <SettingSection title="Reminder Preferences" icon={Bell} accent="text-amber-400">
          <div>
            <label className="text-xs font-semibold text-on-surface-variant mb-3 block uppercase tracking-wide">
              Remind me before deadline
            </label>
            <div className="flex flex-wrap gap-2 mb-4">
              {LEAD_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setLeadMinutes(opt.value)}
                  className={`px-4 py-2 rounded-xl text-sm font-semibold transition-premium ${
                    leadMinutes === opt.value
                      ? "chip-selected"
                      : "chip-unselected hover:bg-surface-container-high"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <button
              onClick={() => savePrefsMut.mutate()}
              disabled={savePrefsMut.isPending}
              className="btn-primary-gradient px-5 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              {savePrefsMut.isPending ? "Saving..." : "Save Preferences"}
            </button>
          </div>
        </SettingSection>

        {/* Privacy */}
        <SettingSection title="Privacy & Data" icon={Shield} accent="text-primary">
          <div className="space-y-3 text-sm text-on-surface-variant">
            <div className="p-4 bg-surface-container-high rounded-xl space-y-2">
              <p className="font-semibold text-on-surface">What RemindmeAI accesses:</p>
              <ul className="space-y-1 text-xs">
                <li>✅ Gmail readonly (subject + snippet)</li>
                <li>✅ Your email address and name</li>
                <li>❌ Full email body (never stored)</li>
                <li>❌ Attachments (never accessed)</li>
                <li>❌ Sent emails or drafts</li>
              </ul>
            </div>
            <p className="text-xs">
              Emails are processed in the background. Only the subject and snippet are stored for deadline detection.
              You can disconnect at any time.
            </p>
          </div>
        </SettingSection>

        {/* Danger Zone */}
        <SettingSection title="Account" icon={AlertTriangle} accent="text-error">
          <div className="space-y-3">
            <button
              id="logout-btn"
              onClick={() => setShowLogout(true)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-surface-container-high text-on-surface-variant text-sm font-semibold hover:bg-surface-container-highest hover:text-on-surface transition-premium w-full"
            >
              <LogOut className="w-4 h-4" />Log out
            </button>
            <div className="pt-1 border-t border-white/5">
              <p className="text-xs text-on-surface-variant mb-3">
                Disconnecting Gmail will revoke access and stop processing your emails. Your existing deadlines will
                remain.
              </p>
              <button
                id="disconnect-gmail-btn"
                onClick={() => setShowDisconnect(true)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-error/10 text-error text-sm font-semibold hover:bg-error/20 transition-premium"
              >
                <Unplug className="w-4 h-4" />Disconnect Gmail
              </button>
            </div>
          </div>
        </SettingSection>
      </div>

      {/* Confirmation dialogs */}
      <ConfirmDialog
        isOpen={showDisconnect}
        onClose={() => setShowDisconnect(false)}
        onConfirm={() => disconnectMut.mutate()}
        title="Disconnect Gmail"
        message="Disconnecting Gmail will stop email monitoring. Your existing deadlines will remain. Continue?"
        confirmLabel="Disconnect"
        danger
        loading={disconnectMut.isPending}
      />
      <ConfirmDialog
        isOpen={showLogout}
        onClose={() => setShowLogout(false)}
        onConfirm={handleLogout}
        title="Log Out"
        message="You'll need to sign in again with Gmail to access your deadlines."
        confirmLabel="Log Out"
      />
    </div>
  );
}
