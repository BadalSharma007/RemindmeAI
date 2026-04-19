import { format, parseISO } from "date-fns";
import { useDeadlines, usePatchDeadline } from "../hooks/useDeadlines";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800",
  reminded: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  dismissed: "bg-gray-100 text-gray-500",
};

export function Deadlines() {
  const { data: deadlines, isLoading } = useDeadlines("pending");
  const { mutate: patchDeadline } = usePatchDeadline();

  if (isLoading) return <div className="text-gray-400 py-12 text-center">Loading deadlines...</div>;

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Deadlines</h1>
      {!deadlines?.length ? (
        <div className="text-gray-400 text-center py-16">
          No pending deadlines. Check back after your emails are processed.
        </div>
      ) : (
        <div className="space-y-3">
          {deadlines.map((dl) => (
            <div
              key={dl.id}
              className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex items-start justify-between gap-4"
            >
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">{dl.title}</p>
                {dl.source_text && (
                  <p className="text-xs text-gray-400 mt-1 truncate">{dl.source_text}</p>
                )}
                <p className="text-sm text-gray-500 mt-2">
                  Due: <span className="font-medium">{format(parseISO(dl.due_at), "PPPp")}</span>
                </p>
                <span className={`inline-block mt-2 text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[dl.status]}`}>
                  {dl.status}
                </span>
              </div>
              <div className="flex gap-2 shrink-0">
                <button
                  onClick={() => patchDeadline({ id: dl.id, patch: { status: "completed" } })}
                  className="text-xs bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-700"
                >
                  Done
                </button>
                <button
                  onClick={() => patchDeadline({ id: dl.id, patch: { status: "dismissed" } })}
                  className="text-xs bg-gray-200 text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-300"
                >
                  Dismiss
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
