import { useState, useEffect } from "react";
import {
  CalendarClock, Clock, Bell, Mail, Link2, Plus, ArrowUpRight,
  Sparkles, TrendingUp, Inbox, ShieldCheck,
} from "lucide-react";

/* ── Types ────────────────────────────────────────────────────────────── */
interface DashboardStats {
  total_deadlines: number;
  pending_deadlines: number;
  upcoming_reminders: number;
  emails_processed_today: number;
  connected_accounts: number;
  total_emails_read: number;
  important_emails_today: number;
}

/* ── Mock Stats ───────────────────────────────────────────────────────── */
const MOCK_STATS: DashboardStats = {
  total_deadlines: 12,
  pending_deadlines: 5,
  upcoming_reminders: 8,
  emails_processed_today: 23,
  connected_accounts: 2,
  total_emails_read: 142,
  important_emails_today: 18,
};

/* ── Stat Card ────────────────────────────────────────────────────────── */
function StatCard({ label, value, icon: Icon, accent = "text-primary" }: {
  label: string; value: number; icon: React.ElementType; accent?: string;
}) {
  return (
    <div className="bg-surface-container rounded-xl p-5 card-hover group animate-slide-up">
      <div className="flex items-start justify-between mb-4">
        <div className={`p-2 rounded-lg bg-surface-container-high transition-premium group-hover:shadow-glow ${accent}`}>
          <Icon className="w-4 h-4" />
        </div>
        <ArrowUpRight className="w-3.5 h-3.5 text-on-surface-variant/40 group-hover:text-primary transition-premium" />
      </div>
      <p className="text-on-surface leading-none mb-1 font-bold" style={{ fontSize: "2rem" }}>{value}</p>
      <p className="text-label-sm text-on-surface-variant">{label}</p>
    </div>
  );
}

/* ── Loading Skeleton ─────────────────────────────────────────────────── */
function DashboardSkeleton() {
  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div className="skeleton h-8 w-48" />
        <div className="skeleton h-10 w-36 rounded-xl" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-8">
        {[1, 2, 3, 4, 5, 6, 7].map((i) => <div key={i} className="skeleton h-32 rounded-xl" />)}
      </div>
    </div>
  );
}

/* ── Dashboard Page ───────────────────────────────────────────────────── */
export function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>(MOCK_STATS);
  const [isLoading, setIsLoading] = useState(true);
  const [isDemoMode, setIsDemoMode] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setIsDemoMode(true);
      setIsLoading(false);
      return;
    }

    const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
    fetch(`${baseUrl}/stats/dashboard`, {
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    })
      .then(res => {
        if (!res.ok) throw new Error("API error");
        return res.json();
      })
      .then(data => {
        if (data && typeof data.total_deadlines === "number") {
          setStats(data);
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

  const handleConnectGmail = () => {
    if (isDemoMode) {
      alert("Demo mode: Gmail connection would redirect to OAuth flow.");
      return;
    }
    const token = localStorage.getItem("access_token");
    const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
    fetch(`${baseUrl}/auth/connect/gmail`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token ?? ""}`, "Content-Type": "application/json" },
    })
      .then(res => res.json())
      .then(data => { if (data.redirect_url) window.location.href = data.redirect_url; })
      .catch(() => alert("Could not connect to Gmail. Please try again."));
  };

  if (isLoading) return <DashboardSkeleton />;

  return (
    <div>
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-headline-md text-on-surface mb-1">Dashboard</h1>
            {isDemoMode && <span className="text-label-sm bg-tertiary/10 text-tertiary px-2.5 py-1 rounded-full">Demo</span>}
          </div>
          <p className="text-body-md text-on-surface-variant">Your command center at a glance.</p>
        </div>
        <button id="connect-gmail-btn" onClick={handleConnectGmail}
          className="btn-primary-gradient px-5 py-2.5 rounded-xl text-sm flex items-center gap-2 group">
          <Plus className="w-4 h-4" />Connect Gmail
          <ArrowUpRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
        </button>
      </div>

      {/* ── Stats Grid ──────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-8">
        <StatCard label="Total Deadlines" value={stats.total_deadlines} icon={CalendarClock} />
        <StatCard label="Pending" value={stats.pending_deadlines} icon={Clock} accent="text-tertiary" />
        <StatCard label="Upcoming Reminders" value={stats.upcoming_reminders} icon={Bell} accent="text-tertiary" />
        <StatCard label="Total Read" value={stats.total_emails_read} icon={Inbox} accent="text-primary" />
        <StatCard label="Emails Today" value={stats.emails_processed_today} icon={Mail} accent="text-primary" />
        <StatCard label="Important Today" value={stats.important_emails_today} icon={ShieldCheck} accent="text-secondary" />
        <StatCard label="Connected" value={stats.connected_accounts} icon={Link2} accent="text-primary" />
      </div>

      {/* ── AI Command Input ────────────────────────────────────── */}
      <div className="bg-surface-container-high rounded-xl p-6 mb-8 animate-pulse-glow">
        <div className="flex items-center gap-3 mb-3">
          <Sparkles className="w-4 h-4 text-primary" />
          <span className="text-label-sm text-primary">AI Assistant</span>
        </div>
        <div className="bg-surface-container rounded-xl px-5 py-4 ghost-border ghost-border-focus cursor-text">
          <p className="text-title-md text-on-surface-variant/50">Ask AI to manage your reminders...</p>
        </div>
      </div>

      {/* ── Empty State ─────────────────────────────────────────── */}
      {stats.connected_accounts === 0 && (
        <div className="bg-surface-container rounded-2xl p-8 text-center animate-slide-up">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/10 to-primary-container/10 flex items-center justify-center mx-auto mb-5">
            <TrendingUp className="w-7 h-7 text-primary" />
          </div>
          <h3 className="text-title-md text-on-surface mb-2">Get started with RemindmeAI</h3>
          <p className="text-body-md text-on-surface-variant max-w-sm mx-auto mb-6">
            Connect your Gmail account to start detecting deadlines automatically from your emails.
          </p>
          <button onClick={handleConnectGmail} className="btn-primary-gradient px-6 py-3 rounded-xl text-sm inline-flex items-center gap-2">
            <Mail className="w-4 h-4" />Connect Gmail
          </button>
        </div>
      )}
    </div>
  );
}
