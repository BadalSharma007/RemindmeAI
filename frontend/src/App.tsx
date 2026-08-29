import { useEffect } from "react";
import { Routes, Route, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Layout } from "./components/shared/Layout";
import { ProtectedRoute } from "./components/shared/ProtectedRoute";
import { ErrorBoundary } from "./components/shared/ErrorBoundary";
import { Dashboard } from "./components/Dashboard";
import { Deadlines } from "./components/Deadlines";
import { DeadlineDetail } from "./components/DeadlineDetail";
import { CreateDeadline } from "./components/CreateDeadline";
import { Reminders } from "./components/Reminders";
import { Settings } from "./components/Settings";
import { Search } from "./components/Search";
import { Sparkles, ArrowRight, Shield, Zap, Brain } from "lucide-react";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: true,
    },
  },
});

/* ── Login Page ─────────────────────────────────────────────────────── */
function LoginPage() {
  const handleLogin = () => {
    const redirectUrl = `${window.location.origin}/auth/callback`;
    const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";
    window.location.href = `${apiBase}/auth/start/gmail?redirect_url=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen bg-background font-inter flex items-center justify-center px-6 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-tertiary/5 rounded-full blur-[100px] pointer-events-none" />

      <div className="relative z-10 w-full max-w-md animate-slide-up">
        {/* Brand */}
        <div className="flex items-center justify-center gap-3 mb-10">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-primary-container flex items-center justify-center shadow-glow">
            <Sparkles className="w-6 h-6 text-on-primary" />
          </div>
          <h1 className="text-headline-md text-on-surface">
            Remindme<span className="text-primary">AI</span>
          </h1>
        </div>

        {/* Card */}
        <div className="bg-surface-container rounded-2xl p-8 shadow-ambient border border-white/5">
          <div className="text-center mb-8">
            <p className="text-label-sm text-on-surface-variant mb-3">Welcome Back</p>
            <h2 className="text-title-md text-on-surface mb-2">Sign in to your workspace</h2>
            <p className="text-body-md text-on-surface-variant">
              Your intelligent email-based reminder system awaits.
            </p>
          </div>

          <div className="flex flex-wrap justify-center gap-2 mb-8">
            {[
              { icon: Brain, label: "AI-Powered" },
              { icon: Shield, label: "Secure" },
              { icon: Zap, label: "Real-time" },
            ].map((f) => (
              <span key={f.label} className="chip-unselected flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium">
                <f.icon className="w-3 h-3 text-primary" />
                {f.label}
              </span>
            ))}
          </div>

          <button
            id="login-btn-gmail"
            onClick={handleLogin}
            className="btn-primary-gradient w-full py-3.5 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 group"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Sign in with Gmail
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </button>

          <p className="text-center text-xs text-on-surface-variant/50 mt-5">
            RemindMeAI reads your Gmail to detect deadlines. No emails are stored — only subject &amp; snippet.
          </p>
        </div>

        <p className="text-center text-xs text-on-surface-variant/30 mt-6">
          By signing in, you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  );
}

/* ── Auth Callback ───────────────────────────────────────────────────── */
function AuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const token = searchParams.get("token");
    const email = searchParams.get("email");
    if (token) {
      localStorage.setItem("access_token", token);
      if (email) localStorage.setItem("user_email", email);
      navigate("/", { replace: true });
    } else {
      navigate("/login", { replace: true });
    }
  }, []);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-primary-container flex items-center justify-center shadow-glow animate-pulse">
          <Sparkles className="w-5 h-5 text-on-primary" />
        </div>
        <p className="text-on-surface-variant text-sm">Signing you in...</p>
      </div>
    </div>
  );
}

/* ── App Router ─────────────────────────────────────────────────────── */
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/auth/callback" element={<AuthCallbackPage />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <Layout>
                  <ErrorBoundary>
                    <Routes>
                      <Route path="/" element={<Dashboard />} />
                      <Route path="/deadlines" element={<Deadlines />} />
                      <Route path="/deadlines/create" element={<CreateDeadline />} />
                      <Route path="/deadlines/:id" element={<DeadlineDetail />} />
                      <Route path="/reminders" element={<Reminders />} />
                      <Route path="/settings" element={<Settings />} />
                      <Route path="/search" element={<Search />} />
                      <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                  </ErrorBoundary>
                </Layout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}
