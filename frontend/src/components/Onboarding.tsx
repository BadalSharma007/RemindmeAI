import React, { useState } from "react";
import { Sparkles, Mail, CheckCircle2, ArrowRight, ShieldCheck, Zap } from "lucide-react";
import { Modal } from "./shared/Modal";

interface OnboardingProps {
  isOpen: boolean;
  onClose: () => void;
  onConnectGmail: () => void;
}

export function Onboarding({ isOpen, onClose, onConnectGmail }: OnboardingProps) {
  const [step, setStep] = useState(1);

  const steps = [
    {
      title: "Welcome to RemindmeAI",
      subtitle: "Never miss an important deadline from your emails again.",
      icon: Sparkles,
      iconColor: "text-primary",
      content: (
        <div className="space-y-4 text-center">
          <p className="text-sm text-on-surface-variant">
            RemindmeAI uses AI to extract deadlines, due dates, and actionable tasks directly from your Gmail inbox in real-time.
          </p>
          <div className="grid grid-cols-2 gap-3 text-left pt-2">
            <div className="p-3.5 rounded-xl bg-surface-container-high border border-white/5">
              <Zap className="w-4 h-4 text-amber-400 mb-1.5" />
              <p className="text-xs font-semibold text-on-surface">Auto-Detection</p>
              <p className="text-[11px] text-on-surface-variant/70 mt-0.5">Scans incoming emails for dates &amp; tasks automatically.</p>
            </div>
            <div className="p-3.5 rounded-xl bg-surface-container-high border border-white/5">
              <ShieldCheck className="w-4 h-4 text-emerald-400 mb-1.5" />
              <p className="text-xs font-semibold text-on-surface">Privacy First</p>
              <p className="text-[11px] text-on-surface-variant/70 mt-0.5">Only snippets are parsed. Full email bodies are never stored.</p>
            </div>
          </div>
        </div>
      ),
      button: "Next: Connect Gmail",
      action: () => setStep(2),
    },
    {
      title: "Connect Your Email",
      subtitle: "Grant readonly access to start detecting deadlines.",
      icon: Mail,
      iconColor: "text-primary",
      content: (
        <div className="space-y-4 text-center">
          <div className="p-4 rounded-xl bg-primary/10 border border-primary/20 text-xs text-on-surface-variant space-y-1.5 text-left">
            <p className="font-semibold text-primary">What happens when you connect:</p>
            <p>1. Google will ask for permission to read emails (readonly).</p>
            <p>2. Our background AI agent begins processing your recent emails.</p>
            <p>3. Detected deadlines will appear on your Dashboard.</p>
          </div>
        </div>
      ),
      button: "Connect Gmail Now",
      action: () => {
        onConnectGmail();
        onClose();
      },
    },
  ];

  const current = steps[step - 1];
  const Icon = current.icon;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md">
      <div className="text-center pt-2">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary to-primary-container flex items-center justify-center mx-auto mb-4 shadow-glow">
          <Icon className="w-6 h-6 text-on-primary" />
        </div>
        <h2 className="text-lg font-bold text-on-surface">{current.title}</h2>
        <p className="text-xs text-on-surface-variant mb-6">{current.subtitle}</p>

        {current.content}

        <div className="flex gap-3 pt-6">
          <button
            onClick={onClose}
            className="flex-1 py-3 rounded-xl bg-surface-container-high text-on-surface-variant text-sm font-semibold hover:bg-surface-container-highest transition-premium"
          >
            Skip for now
          </button>
          <button
            onClick={current.action}
            className="flex-1 btn-primary-gradient py-3 rounded-xl text-sm font-semibold flex items-center justify-center gap-2"
          >
            {current.button} <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </Modal>
  );
}
