import { format, parseISO, addHours } from "date-fns";
import { useReminders, useSnoozeReminder } from "../hooks/useReminders";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800",
  sent: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  snoozed: "bg-blue-100 text-blue-800",
};

export function Reminders() {
  const { data: reminders, isLoading } = useReminders();
  const { mutate: snooze } = useSnoozeReminder();

  if (isLoading) return <div className="text-gray-400 py-12 text-center">Loading reminders...</div>;

  const handleSnooze1h = (id: string) => {
    const snoozeUntil = addHours(new Date(), 1).toISOString();
    snooze({ id, snoozeUntil });
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Reminders</h1>
      {!reminders?.length ? (
        <div className="text-gray-400 text-center py-16">No reminders scheduled.</div>
      ) : (
        <div className="space-y-3">
          {reminders.map((r) => (
            <div
              key={r.id}
              className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex items-center justify-between gap-4"
            >
              <div>
                <p className="text-sm text-gray-500">
                  Scheduled: <span className="font-medium text-gray-900">{format(parseISO(r.scheduled_at), "PPPp")}</span>
                </p>
                <p className="text-xs text-gray-400 mt-1">Channel: {r.channel}</p>
                <span className={`inline-block mt-2 text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[r.status]}`}>
                  {r.status}
                </span>
              </div>
              {r.status === "pending" && (
                <button
                  onClick={() => handleSnooze1h(r.id)}
                  className="text-xs bg-indigo-50 text-indigo-700 px-3 py-1.5 rounded-lg hover:bg-indigo-100 border border-indigo-200"
                >
                  Snooze 1h
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
