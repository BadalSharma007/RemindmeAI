import { AlertTriangle } from "lucide-react";
import { Modal } from "./Modal";

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  loading?: boolean;
}

export function ConfirmDialog({
  isOpen, onClose, onConfirm, title, message,
  confirmLabel = "Confirm", danger = false, loading = false,
}: ConfirmDialogProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} size="sm">
      <div className="text-center">
        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4 ${danger ? "bg-error/10" : "bg-primary/10"}`}>
          <AlertTriangle className={`w-5 h-5 ${danger ? "text-error" : "text-primary"}`} />
        </div>
        <h3 className="text-title-md text-on-surface font-semibold mb-2">{title}</h3>
        <p className="text-body-md text-on-surface-variant mb-6">{message}</p>
        <div className="flex gap-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="flex-1 py-2.5 rounded-xl bg-surface-container-high text-on-surface-variant text-sm font-semibold hover:bg-surface-container-highest transition-premium disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={`flex-1 py-2.5 rounded-xl text-sm font-semibold transition-premium disabled:opacity-50 ${
              danger
                ? "bg-error/10 text-error hover:bg-error/20"
                : "btn-primary-gradient"
            }`}
          >
            {loading ? "..." : confirmLabel}
          </button>
        </div>
      </div>
    </Modal>
  );
}
