import { useState } from "react";
import { useCurrentUser } from "../hooks/useAuth";
import { authApi } from "../api/auth";
import { apiClient } from "../api/client";

export function Settings() {
  const { data: user } = useCurrentUser();
  const [leadMinutes, setLeadMinutes] = useState(60);
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    await apiClient.put("/preferences", { reminder_lead_minutes: leadMinutes });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleDisconnect = async () => {
    await authApi.disconnect("gmail");
    window.location.reload();
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    window.location.href = "/login";
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-8">Settings</h1>

      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Account</h2>
        <p className="text-sm text-gray-600">Email: <span className="font-medium">{user?.email ?? "—"}</span></p>
        <p className="text-sm text-gray-600 mt-1">Timezone: <span className="font-medium">{user?.timezone ?? "UTC"}</span></p>
        <button
          onClick={handleLogout}
          className="mt-4 bg-gray-100 text-gray-700 border border-gray-300 px-4 py-2 rounded-lg text-sm hover:bg-gray-200"
        >
          Log out
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Reminder Preferences</h2>
        <label className="block text-sm text-gray-600 mb-2">
          Remind me this many minutes before a deadline:
        </label>
        <input
          type="number"
          min={5}
          max={10080}
          value={leadMinutes}
          onChange={(e) => setLeadMinutes(Number(e.target.value))}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-32 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          onClick={handleSave}
          className="ml-3 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700"
        >
          {saved ? "Saved!" : "Save"}
        </button>
      </div>

      <div className="bg-white rounded-xl border border-red-200 p-6 shadow-sm">
        <h2 className="text-lg font-medium text-red-700 mb-2">Danger Zone</h2>
        <p className="text-sm text-gray-500 mb-4">
          Disconnecting Gmail will revoke access and stop processing your emails.
        </p>
        <button
          onClick={handleDisconnect}
          className="bg-red-50 text-red-700 border border-red-300 px-4 py-2 rounded-lg text-sm hover:bg-red-100"
        >
          Disconnect Gmail
        </button>
      </div>
    </div>
  );
}
