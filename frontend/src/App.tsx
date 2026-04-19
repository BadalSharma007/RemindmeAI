import { useEffect } from "react";
import { Routes, Route, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { Layout } from "./components/shared/Layout";
import { ProtectedRoute } from "./components/shared/ProtectedRoute";
import { Dashboard } from "./components/Dashboard";
import { Deadlines } from "./components/Deadlines";
import { Reminders } from "./components/Reminders";
import { Settings } from "./components/Settings";
import { authApi } from "./api/auth";

function LoginPage() {
  const handleLogin = () => {
    // Direct redirect to backend — avoids CORS preflight on POST
    window.location.href = "https://proactive-unadorned-gout.ngrok-free.dev/auth/start/gmail";
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-10 w-full max-w-md text-center">
        <h1 className="text-2xl font-semibold text-gray-900 mb-2">RemindmeAI</h1>
        <p className="text-gray-500 mb-8 text-sm">
          Intelligent email-based reminder system
        </p>
        <button
          onClick={handleLogin}
          className="w-full bg-indigo-600 text-white py-3 rounded-xl font-medium hover:bg-indigo-700 transition-colors"
        >
          Sign in with Gmail
        </button>
      </div>
    </div>
  );
}

function AuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const token = searchParams.get("token");
    if (token) {
      localStorage.setItem("access_token", token);
      navigate("/", { replace: true });
    } else {
      navigate("/login", { replace: true });
    }
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <p className="text-gray-500">Signing you in...</p>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/deadlines" element={<Deadlines />} />
                <Route path="/reminders" element={<Reminders />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
