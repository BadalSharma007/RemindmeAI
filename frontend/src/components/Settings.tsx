import { useState, useEffect } from "react";
import { Settings as SettingsIcon, User, Bell, AlertTriangle, LogOut, Unplug, Save, CheckCircle2 } from "lucide-react";

/* ── Types ────────────────────────────────────────────────────────────── */
interface UserProfile {
  id: string;
  email: string;
  display_name: string | null;
  timezone: string;
}

export function Settings() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [leadMinutes, setLeadMinutes] = useState(60);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState(false);

  const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";
  const token = localStorage.getItem("access_token");
  const storedEmail = localStorage.getItem("user_email");

  // Fetch user profile
  useEffect(() => {
    if (!token) return;
    fetch(`${apiBase}/auth/me`, {
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    })
      .then(res => { if (!res.ok) throw new Error(); return res.json(); })
      .then(data => setUser(data))
      .catch(() => {
        // Use stored email as fallback
        if (storedEmail) {
          setUser({ id: "", email: storedEmail, display_name: null, timezone: "UTC" });
        }
      });
  }, []);

  const handleSave = async () => {
    setSaveError(false);
    try {
      const res = await fetch(`${apiBase}/preferences`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token ?? ""}`, "Content-Type": "application/json" },
        body: JSON.stringify({ reminder_lead_minutes: leadMinutes }),
      });
      if (!res.ok) throw new Error();
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setSaveError(true);
      setTimeout(() => setSaveError(false), 3000);
    }
  };

  const handleDisconnect = async () => {
    try {
      await fetch(`${apiBase}/auth/disconnect/gmail`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token ?? ""}`, "Content-Type": "application/json" },
      });
      window.location.reload();
    } catch {
      alert("Failed to disconnect. Please try again.");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_email");
    window.location.href = "/login";
  };

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

      {/* Account Card */}
      <div className="bg-surface-container rounded-xl p-6 mb-4 animate-slide-up">
        <div className="flex items-center gap-3 mb-5">
          <div className="p-2 rounded-lg bg-surface-container-high">
            <User className="w-4 h-4 text-primary" />
          </div>
          <h2 className="text-title-md text-on-surface">Account</h2>
        </div>
        <div className="space-y-3 mb-5">
          <div className="flex items-center justify-between py-2">
            <span className="text-body-md text-on-surface-variant">Email</span>
            <span className="text-body-md text-on-surface font-medium">{user?.email ?? storedEmail ?? "—"}</span>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-body-md text-on-surface-variant">Timezone</span>
            <span className="text-body-md text-on-surface font-medium">{user?.timezone ?? "UTC"}</span>
          </div>
        </div>
        <button id="logout-btn" onClick={handleLogout} className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-surface-container-high text-on-surface-variant text-sm font-medium hover:bg-surface-container-highest hover:text-on-surface transition-premium">
          <LogOut className="w-4 h-4" />Log out
        </button>
      </div>

      {/* Preferences Card */}
      <div className="bg-surface-container rounded-xl p-6 mb-4 animate-slide-up" style={{ animationDelay: "60ms" }}>
        <div className="flex items-center gap-3 mb-5">
          <div className="p-2 rounded-lg bg-surface-container-high">
            <Bell className="w-4 h-4 text-tertiary" />
          </div>
          <h2 className="text-title-md text-on-surface">Reminder Preferences</h2>
        </div>
        <label className="block text-body-md text-on-surface-variant mb-3">Remind me this many minutes before a deadline:</label>
        <div className="flex items-center gap-3">
          <input
            id="lead-minutes-input"
            type="number"
            min={5}
            max={10080}
            value={leadMinutes}
            onChange={(e) => setLeadMinutes(Number(e.target.value))}
            className="bg-surface-container-high text-on-surface rounded-lg px-4 py-2.5 text-sm w-32 ghost-border ghost-border-focus transition-premium"
          />
          <button id="save-prefs-btn" onClick={handleSave} className={`px-5 py-2.5 rounded-lg text-sm flex items-center gap-2 ${
            saveError ? "bg-error/10 text-error" : "btn-primary-gradient"
          }`}>
            {saveError ? <>Error</> : saved ? <><CheckCircle2 className="w-4 h-4" />Saved!</> : <><Save className="w-4 h-4" />Save</>}
          </button>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="bg-surface-container rounded-xl p-6 animate-slide-up" style={{ animationDelay: "120ms" }}>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-error/10">
            <AlertTriangle className="w-4 h-4 text-error" />
          </div>
          <h2 className="text-title-md text-error">Danger Zone</h2>
        </div>
        <p className="text-body-md text-on-surface-variant mb-4">Disconnecting Gmail will revoke access and stop processing your emails.</p>
        <button id="disconnect-gmail-btn" onClick={handleDisconnect} className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-error/10 text-error text-sm font-semibold hover:bg-error/20 transition-premium">
          <Unplug className="w-4 h-4" />Disconnect Gmail
        </button>
      </div>
    </div>
  );
}
