import React, { createContext, useContext, useState, useCallback } from "react";
import { CheckCircle2, AlertTriangle, Info, X } from "lucide-react";

export type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue>({
  showToast: () => {},
});

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback((message: string, type: ToastType = "info") => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);

    setTimeout(() => {
      removeToast(id);
    }, 4000);
  }, [removeToast]);

  const typeConfig: Record<ToastType, { icon: React.ElementType; border: string; bg: string; text: string }> = {
    success: { icon: CheckCircle2, border: "border-emerald-500/30", bg: "bg-surface-container-high", text: "text-emerald-400" },
    error: { icon: AlertTriangle, border: "border-red-500/30", bg: "bg-surface-container-high", text: "text-red-400" },
    warning: { icon: AlertTriangle, border: "border-amber-500/30", bg: "bg-surface-container-high", text: "text-amber-400" },
    info: { icon: Info, border: "border-primary/30", bg: "bg-surface-container-high", text: "text-primary" },
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {/* Toast container floating top-right */}
      <div className="fixed top-20 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
        {toasts.map((t) => {
          const cfg = typeConfig[t.type];
          const Icon = cfg.icon;
          return (
            <div
              key={t.id}
              className={`pointer-events-auto p-4 rounded-xl border ${cfg.border} ${cfg.bg} shadow-2xl backdrop-blur-md flex items-start gap-3 animate-slide-up`}
            >
              <Icon className={`w-5 h-5 ${cfg.text} shrink-0 mt-0.5`} />
              <p className="text-xs sm:text-sm text-on-surface font-medium flex-1">{t.message}</p>
              <button
                onClick={() => removeToast(t.id)}
                className="text-on-surface-variant/40 hover:text-on-surface p-0.5 rounded transition-premium"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
