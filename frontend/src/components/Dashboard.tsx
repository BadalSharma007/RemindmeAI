import { useQuery } from "@tanstack/react-query";
import { statsApi } from "../api/stats";
import { authApi } from "../api/auth";

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className={`bg-white rounded-xl border border-gray-200 p-6 shadow-sm`}>
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
    </div>
  );
}

export function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: statsApi.getDashboard,
    refetchInterval: 60_000,
  });

  const handleConnectGmail = async () => {
    const response = await authApi.connectGmail();
    window.location.href = response.redirect_url;
  };

  if (isLoading) {
    return <div className="text-gray-400 text-center py-12">Loading dashboard...</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <button
          onClick={handleConnectGmail}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          + Connect Gmail
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        <StatCard label="Total Deadlines" value={stats?.total_deadlines ?? 0} color="text-gray-900" />
        <StatCard label="Pending" value={stats?.pending_deadlines ?? 0} color="text-indigo-600" />
        <StatCard label="Upcoming Reminders" value={stats?.upcoming_reminders ?? 0} color="text-amber-600" />
        <StatCard label="Emails Today" value={stats?.emails_processed_today ?? 0} color="text-green-600" />
        <StatCard label="Connected Accounts" value={stats?.connected_accounts ?? 0} color="text-blue-600" />
      </div>

      {stats?.connected_accounts === 0 && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-6 text-center">
          <p className="text-indigo-800 font-medium">No email accounts connected yet.</p>
          <p className="text-indigo-600 text-sm mt-1">
            Connect your Gmail account to start detecting deadlines.
          </p>
          <button
            onClick={handleConnectGmail}
            className="mt-4 bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700"
          >
            Connect Gmail
          </button>
        </div>
      )}
    </div>
  );
}
