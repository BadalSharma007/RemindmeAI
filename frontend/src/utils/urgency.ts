import { parseISO, differenceInHours, differenceInCalendarDays, isPast } from "date-fns";

export type UrgencyTier = "red" | "blue" | "green" | "gray";

export interface UrgencyInfo {
  tier: UrgencyTier;
  label: string;
  badgeBg: string;
  badgeText: string;
  badgeBorder: string;
  cardBorder: string;
  stripeBg: string;
  iconColor: string;
  bannerBg: string;
}

/**
 * Calculates deadline urgency tier and dynamic color scheme:
 * - <= 2 days (or overdue): RED
 * - 3 to 7 days: BLUE
 * - 8 to 14 days (> 7 days): GREEN
 * - > 14 days (or completed/dismissed): GRAY
 */
export function getDeadlineUrgency(dueAt: string, status?: string): UrgencyInfo {
  if (status === "completed" || status === "dismissed") {
    return {
      tier: "gray",
      label: status === "completed" ? "Completed" : "Dismissed",
      badgeBg: "bg-slate-500/10",
      badgeText: "text-slate-400",
      badgeBorder: "border-slate-500/20",
      cardBorder: "border-slate-800/40",
      stripeBg: "bg-slate-500",
      iconColor: "text-slate-400",
      bannerBg: "bg-slate-500/5",
    };
  }

  const now = new Date();
  const dueDate = parseISO(dueAt);
  const isPastDue = isPast(dueDate);
  const hoursLeft = differenceInHours(dueDate, now);
  const daysLeft = differenceInCalendarDays(dueDate, now);

  // RED: Overdue or due within 2 days (<= 48 hours / <= 2 days)
  if (isPastDue || hoursLeft <= 48 || daysLeft <= 2) {
    return {
      tier: "red",
      label: isPastDue ? "Overdue" : daysLeft <= 0 ? "Due Today" : daysLeft === 1 ? "Due Tomorrow" : "Due in 2 days",
      badgeBg: "bg-red-500/15",
      badgeText: "text-red-400",
      badgeBorder: "border-red-500/30",
      cardBorder: "border-red-500/30",
      stripeBg: "bg-red-500",
      iconColor: "text-red-400",
      bannerBg: "bg-red-500/10",
    };
  }

  // BLUE: 3 to 7 days
  if (daysLeft >= 3 && daysLeft <= 7) {
    return {
      tier: "blue",
      label: `Due in ${daysLeft} days`,
      badgeBg: "bg-blue-500/15",
      badgeText: "text-blue-400",
      badgeBorder: "border-blue-500/30",
      cardBorder: "border-blue-500/20",
      stripeBg: "bg-blue-500",
      iconColor: "text-blue-400",
      bannerBg: "bg-blue-500/10",
    };
  }

  // GREEN: > 7 days up to 14 days
  if (daysLeft > 7 && daysLeft <= 14) {
    return {
      tier: "green",
      label: `Due in ${daysLeft} days`,
      badgeBg: "bg-emerald-500/15",
      badgeText: "text-emerald-400",
      badgeBorder: "border-emerald-500/30",
      cardBorder: "border-emerald-500/20",
      stripeBg: "bg-emerald-500",
      iconColor: "text-emerald-400",
      bannerBg: "bg-emerald-500/10",
    };
  }

  // GRAY: More than 14 days
  return {
    tier: "gray",
    label: `Due in ${daysLeft} days`,
    badgeBg: "bg-slate-500/15",
    badgeText: "text-slate-400",
    badgeBorder: "border-slate-500/30",
    cardBorder: "border-slate-700/40",
    stripeBg: "bg-slate-500",
    iconColor: "text-slate-400",
    bannerBg: "bg-slate-500/10",
  };
}
