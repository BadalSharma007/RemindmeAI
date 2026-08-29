import { format, parseISO, isToday, isTomorrow, formatDistanceToNow } from "date-fns";

/**
 * Format an ISO UTC string in the user's configured IANA timezone using Intl.DateTimeFormat
 */
export function formatInUserTz(
  isoUtc: string,
  userTz = "Asia/Kolkata",
  formatStyle: "full" | "date" | "time" | "datetime" | "relative" = "datetime"
): string {
  try {
    const date = parseISO(isoUtc);
    if (isNaN(date.getTime())) return isoUtc;

    if (formatStyle === "relative") {
      return formatDistanceToNow(date, { addSuffix: true });
    }

    const optionsMap: Record<string, Intl.DateTimeFormatOptions> = {
      full: {
        weekday: "long",
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        timeZone: userTz,
      },
      date: {
        year: "numeric",
        month: "short",
        day: "numeric",
        timeZone: userTz,
      },
      time: {
        hour: "numeric",
        minute: "2-digit",
        timeZone: userTz,
      },
      datetime: {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
        timeZone: userTz,
      },
    };

    const formatter = new Intl.DateTimeFormat("en-US", optionsMap[formatStyle] || optionsMap.datetime);
    return formatter.format(date);
  } catch {
    // Fallback to local browser formatting if timezone string is invalid
    const d = parseISO(isoUtc);
    return format(d, "MMM d, yyyy · h:mm a");
  }
}

/**
 * Get timezone short abbreviation (e.g., "IST", "EST", "UTC")
 */
export function getUserTzAbbr(userTz = "Asia/Kolkata"): string {
  try {
    const formatter = new Intl.DateTimeFormat("en-US", {
      timeZone: userTz,
      timeZoneName: "short",
    });
    const parts = formatter.formatToParts(new Date());
    const tzPart = parts.find((p) => p.type === "timeZoneName");
    return tzPart ? tzPart.value : userTz;
  } catch {
    return userTz;
  }
}
