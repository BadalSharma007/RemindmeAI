import React from "react";
import { Modal } from "./Modal";
import { Command } from "lucide-react";

interface ShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ShortcutsModal({ isOpen, onClose }: ShortcutsModalProps) {
  const shortcuts = [
    { key: "N", desc: "Create a new deadline" },
    { key: "D", desc: "Navigate to Deadlines list" },
    { key: "R", desc: "Navigate to Reminders list" },
    { key: "C", desc: "Navigate to Calendar view" },
    { key: "S", desc: "Navigate to Settings" },
    { key: "/", desc: "Open Search" },
    { key: "?", desc: "Show this keyboard shortcuts guide" },
    { key: "Esc", desc: "Close any open dialog or modal" },
  ];

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="sm" title="Keyboard Shortcuts">
      <div className="space-y-3 pt-2">
        {shortcuts.map((s) => (
          <div key={s.key} className="flex items-center justify-between py-1.5 border-b border-white/5 last:border-0">
            <span className="text-xs text-on-surface-variant">{s.desc}</span>
            <kbd className="px-2 py-1 rounded bg-surface-container-high border border-white/10 text-primary font-mono text-xs font-bold">
              {s.key}
            </kbd>
          </div>
        ))}
      </div>
    </Modal>
  );
}
