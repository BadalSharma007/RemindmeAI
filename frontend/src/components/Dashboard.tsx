import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { format, parseISO, isPast, isToday, isTomorrow, isWithinInterval, addDays, startOfDay, endOfDay } from "date-fns";
import {
  CalendarClock, Clock, Bell, Mail, Link2, Plus,
  Sparkles, TrendingUp, ArrowRight, CheckCircle2, AlertTriangle,
  Calendar as CalendarIcon, HelpCircle
} from "lucide-react";
import { statsApi, authApi } from "../api";
import { deadlinesApi, type Deadline } from "../api/deadlines";
import { getDeadlineUrgency } from "../utils/urgency";
import { Onboarding } from "./Onboarding";

/* ── Helpers ────────────────────────────────────────────────────────── */
function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function formatRelativeDate(iso: string) {
  const d = parseISO(iso);
  if (isToday(d)) return `Today · ${format(d, "h:mm a")}`;
  if (isTomorrow(d)) return `Tomorrow · ${format(d, "h:mm a")}`;
  return format(d, "EEE, MMM d · h:mm a");
}

/* ── Stat Card ──────────────────────────────────────────────────────── */
function StatCard({ label, value, icon: Icon, accent = "text-primary" }: {
  label: string; value: number; icon: React.ElementType; accent?: string;
}) {
  return (
    <div className="bg-surface-container rounded-xl p-5 card-hover group animate-slide-up border border-white/5">
      <div className={`p-2 rounded-lg bg-surface-container-high w-fit mb-3 ${accent}`}>
        <Icon className="w-4 h-4" />
      </div>
      <p className="text-on-surface font-bold leading-none mb-1" style={{ fontSize: "1.75rem" }}>{value}</p>
      <p className="text-label-sm text-on-surface-variant">{label}</p>
    </div>
  );
}

/* ── Mini Deadline Card with Dynamic Urgency Colors ──────────────────── */
function MiniDeadlineCard({ dl }: { dl: Deadline }) {
  const navigate = useNavigate();
  const urgency = getDeadlineUrgency(dl.due_at, dl.status);
  const isAI = dl.source_text && dl.source_text !== "Manual entry" && dl.confidence_score < 1.0;

  return (
    <div
      onClick={() => navigate(`/deadlines/${dl.id}`)}
      className={`flex items-center gap-4 p-4 rounded-xl bg-surface-container card-hover cursor-pointer group border ${urgency.cardBorder} animate-slide-up relative overflow-hidden`}
    >
      {/* Left Urgency Color Stripe */}
      <div className={`w-1.5 self-stretch rounded-full shrink-0 ${urgency.stripeBg}`} />
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-body-md text-on-surface font-medium truncate group-hover:text-primary transition-premium">
            {dl.title}
          </p>
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${urgency.badgeBg} ${urgency.badgeText} ${urgency.badgeBorder}`}>
            {urgency.label}
          </span>
        </div>
        <p className="text-xs text-on-surface-variant mt-0.5">
          {formatRelativeDate(dl.due_at)}
        </p>
      </div>

      {isAI && (
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-primary/10 text-primary shrink-0 flex items-center gap-1">
          <Sparkles className="w-2.5 h-2.5" />AI
        </span>
      )}
      <ArrowRight className="w-4 h-4 text-on-surface-variant/40 group-hover:text-primary transition-premium shrink-0" />
    </div>
  );
}

/* ── Skeleton ───────────────────────────────────────────────────────── */
function DashboardSkeleton() {
  return (
    <div className="animate-fade-in space-y-8">
      <div className="skeleton h-10 w-64 rounded-xl" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1,2,3,4].map(i => <div key={i} className="skeleton h-28 rounded-xl" />)}
      </div>
      <div className="space-y-3">
        {[1,2,3].map(i => <div key={i} className="skeleton h-16 rounded-xl" />)}
      </div>
    </div>
  );
}

/* ── Dashboard Page ─────────────────────────────────────────────────── */
export function Dashboard() {
  const navigate = useNavigate();
  const token = localStorage.getItem("access_token");
  const [showOnboarding, setShowOnboarding] = useState(false);

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: statsApi.dashboard,
    enabled: !!token,
  });

  const { data: user } = useQuery({
    queryKey: ["me"],
    queryFn: authApi.me,
    enabled: !!token,
  });

  const { data: deadlines, isLoading: dlLoading } = useQuery({
    queryKey: ["deadlines", "all"],
    queryFn: () => deadlinesApi.list(),
    enabled: !!token,
  });

  const handleConnectGmail = () => {
    const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";
    const redirectUrl = `${window.location.origin}/auth/callback`;
    window.location.href = `${apiBase}/auth/start/gmail?redirect_url=${encodeURIComponent(redirectUrl)}`;
  };

  const isLoading = statsLoading || dlLoading;
  if (isLoading) return <DashboardSkeleton />;

  const now = new Date();
  const todayDeadlines = (deadlines ?? []).filter(dl =>
    dl.status === "pending" &&
    isWithinInterval(parseISO(dl.due_at), { start: now, end: endOfDay(addDays(now, 0)) })
  );
  const upcomingDeadlines = (deadlines ?? []).filter(dl =>
    dl.status === "pending" &&
    isWithinInterval(parseISO(dl.due_at), { start: startOfDay(addDays(now, 1)), end: endOfDay(addDays(now, 7)) })
  );
  const overdueDeadlines = (deadlines ?? []).filter(dl =>
    dl.status === "pending" && isPast(parseISO(dl.due_at))
  );

  const pendingReviewCount = (deadlines ?? []).filter(
    d => d.status === "pending" && d.source_text && d.source_text !== "Manual entry"
  ).length;

  const displayName = user?.display_name ?? user?.email?.split("@")[0] ?? "there";

  return (
    <div>
      {/* ── Greeting ─────────────────────────────────────────────── */}
      <div className="flex items-start justify-between mb-8 gap-4 flex-wrap">
        <div>
          <p className="text-label-sm text-on-surface-variant mb-1">{format(now, "EEEE, MMMM d")}</p>
          <h1 className="text-headline-md text-on-surface mb-1">
            {getGreeting()}, {displayName.charAt(0).toUpperCase() + displayName.slice(1)} 👋
          </h1>
          <p className="text-body-md text-on-surface-variant">Here's what needs your attention today.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowOnboarding(true)}
            className="p-2.5 rounded-xl bg-surface-container hover:bg-surface-container-high border border-white/5 text-on-surface-variant hover:text-on-surface text-xs font-semibold flex items-center gap-1.5 transition-premium"
            title="How it works"
          >
            <HelpCircle className="w-4 h-4 text-primary" />
            <span className="hidden sm:inline">Guide</span>
          </button>
          <button
            onClick={() => navigate("/calendar")}
            className="p-2.5 rounded-xl bg-surface-container hover:bg-surface-container-high border border-white/5 text-on-surface-variant hover:text-on-surface text-xs font-semibold flex items-center gap-1.5 transition-premium"
          >
            <CalendarIcon className="w-4 h-4 text-primary" />
            <span className="hidden sm:inline">Calendar</span>
          </button>
          <button
            onClick={() => navigate("/deadlines/create")}
            className="btn-primary-gradient px-4 py-2.5 rounded-xl text-sm flex items-center gap-2 group shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">New Deadline</span>
          </button>
        </div>
      </div>

      {/* ── Stats Grid ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Pending Deadlines" value={stats?.pending_deadlines ?? 0} icon={CalendarClock} accent="text-tertiary" />
        <StatCard label="Upcoming Reminders" value={stats?.upcoming_reminders ?? 0} icon={Bell} accent="text-primary" />
        <StatCard label="Emails Today" value={stats?.emails_processed_today ?? 0} icon={Mail} accent="text-primary" />
        <StatCard label="Connected Accounts" value={stats?.connected_accounts ?? 0} icon={Link2} accent="text-primary" />
      </div>

      {/* ── AI Detection Review Banner ────────────────────────────── */}
      {pendingReviewCount > 0 && (
        <div className="bg-primary/10 border border-primary/30 rounded-xl p-4 mb-6 flex items-center justify-between gap-3 animate-slide-up shadow-glow">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/20 text-primary">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm font-bold text-on-surface">
                {pendingReviewCount} AI-detected deadline{pendingReviewCount !== 1 ? "s" : ""} need verification
              </p>
              <p className="text-xs text-on-surface-variant/80 mt-0.5">
                Review extracted dates and confirm or adjust them in one click.
              </p>
            </div>
          </div>
          <button
            onClick={() => navigate("/review")}
            className="btn-primary-gradient px-4 py-2 rounded-xl text-xs font-bold shrink-0 flex items-center gap-1.5"
          >
            Review Now <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* ── Dynamic Urgency Critical Alert Banner ─────────────────── */}
      {overdueDeadlines.length > 0 && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 mb-6 flex items-center gap-3 animate-slide-up">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-red-400">
              🔴 {overdueDeadlines.length} critical / overdue deadline{overdueDeadlines.length !== 1 ? "s" : ""}
            </p>
            <p className="text-xs text-red-300/80 mt-0.5">These deadlines are due immediately or have expired.</p>
          </div>
          <button onClick={() => navigate("/deadlines")} className="text-xs font-semibold text-red-400 underline underline-offset-2 shrink-0">
            View urgent
          </button>
        </div>
      )}

      {/* ── Urgency Legend Bar ───────────────────────────────────── */}
      <div className="flex items-center gap-4 text-xs text-on-surface-variant/70 mb-4 px-1">
        <span className="font-semibold text-on-surface-variant">Urgency Guide:</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-red-500" /> &le;2 Days (Red)</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-blue-500" /> 3-7 Days (Blue)</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> &gt;7 Days (Green)</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-slate-500" /> &gt;14 Days (Gray)</span>
      </div>

      {/* ── Today Section ────────────────────────────────────────── */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-title-md text-on-surface font-semibold flex items-center gap-2">
            <Clock className="w-4 h-4 text-red-400" />
            Due Today &amp; Immediate
          </h2>
          {todayDeadlines.length > 0 && (
            <span className="text-xs text-red-400 font-medium">{todayDeadlines.length} immediate</span>
          )}
        </div>
        {todayDeadlines.length === 0 ? (
          <div className="bg-surface-container rounded-xl p-8 text-center border border-white/5">
            <CheckCircle2 className="w-8 h-8 text-green-400 mx-auto mb-3" />
            <p className="text-body-md text-on-surface font-medium">Free day</p>
            <p className="text-xs text-on-surface-variant mt-1">Nothing due today. Great work!</p>
          </div>
        ) : (
          <div className="space-y-2">
            {todayDeadlines.map(dl => <MiniDeadlineCard key={dl.id} dl={dl} />)}
          </div>
        )}
      </div>

      {/* ── Upcoming Section ─────────────────────────────────────── */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-title-md text-on-surface font-semibold flex items-center gap-2">
            <CalendarClock className="w-4 h-4 text-blue-400" />
            Upcoming (Next 7 Days)
          </h2>
          <button onClick={() => navigate("/deadlines")} className="text-xs text-primary hover:underline underline-offset-2">
            View all
          </button>
        </div>
        {upcomingDeadlines.length === 0 ? (
          <div className="bg-surface-container rounded-xl p-6 text-center border border-white/5">
            <p className="text-body-md text-on-surface-variant">Nothing scheduled for the next 7 days.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {upcomingDeadlines.slice(0, 5).map(dl => <MiniDeadlineCard key={dl.id} dl={dl} />)}
            {upcomingDeadlines.length > 5 && (
              <button onClick={() => navigate("/deadlines")} className="w-full text-center text-xs text-on-surface-variant hover:text-primary transition-premium py-2">
                +{upcomingDeadlines.length - 5} more deadlines →
              </button>
            )}
          </div>
        )}
      </div>

      {/* ── No connection state ──────────────────────────────────── */}
      {stats && stats.connected_accounts === 0 && (
        <div className="bg-surface-container rounded-2xl p-8 text-center border border-white/5 animate-slide-up">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/10 to-primary-container/10 flex items-center justify-center mx-auto mb-5">
            <TrendingUp className="w-7 h-7 text-primary" />
          </div>
          <h3 className="text-title-md text-on-surface mb-2">Get started with RemindmeAI</h3>
          <p className="text-body-md text-on-surface-variant max-w-sm mx-auto mb-6">
            Connect your Gmail account to start detecting deadlines automatically from your emails.
          </p>
          <button
            onClick={() => setShowOnboarding(true)}
            className="btn-primary-gradient px-6 py-3 rounded-xl text-sm inline-flex items-center gap-2 font-semibold"
          >
            <Sparkles className="w-4 h-4" /> Start Guided Setup
          </button>
        </div>
      )}

      {/* Onboarding Walkthrough */}
      <Onboarding
        isOpen={showOnboarding}
        onClose={() => setShowOnboarding(false)}
        onConnectGmail={handleConnectGmail}
      />
    </div>
  );
}
