import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        inter: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        // Core surfaces
        background: "#131313",
        surface: {
          DEFAULT: "#131313",
          dim: "#131313",
          bright: "#3a3939",
          container: {
            DEFAULT: "#201f1f",
            low: "#1c1b1b",
            high: "#2a2a2a",
            highest: "#353534",
            lowest: "#0e0e0e",
          },
          variant: "#353534",
          tint: "#c0c1ff",
        },
        // Primary
        primary: {
          DEFAULT: "#c0c1ff",
          container: "#8083ff",
          fixed: "#e1e0ff",
          "fixed-dim": "#c0c1ff",
        },
        "on-primary": "#1000a9",
        "on-primary-container": "#0d0096",
        // Secondary
        secondary: {
          DEFAULT: "#c0c1ff",
          container: "#42447b",
          fixed: "#e1e0ff",
          "fixed-dim": "#c0c1ff",
        },
        "on-secondary": "#292a60",
        // Tertiary
        tertiary: {
          DEFAULT: "#ffb783",
          container: "#d97721",
          fixed: "#ffdcc5",
          "fixed-dim": "#ffb783",
        },
        "on-tertiary": "#4f2500",
        // Text / on-surface
        "on-surface": "#e5e2e1",
        "on-surface-variant": "#c7c4d7",
        "on-background": "#e5e2e1",
        // Outline
        outline: {
          DEFAULT: "#908fa0",
          variant: "#464554",
        },
        // Error
        error: {
          DEFAULT: "#ffb4ab",
          container: "#93000a",
        },
        "on-error": "#690005",
        "on-error-container": "#ffdad6",
        // Inverse
        "inverse-surface": "#e5e2e1",
        "inverse-on-surface": "#313030",
        "inverse-primary": "#494bd6",
      },
      borderRadius: {
        lg: "0.5rem",
        xl: "0.75rem",
        "2xl": "1rem",
      },
      boxShadow: {
        ambient: "0 20px 40px rgba(0, 0, 0, 0.4)",
        glow: "0 0 20px rgba(192, 193, 255, 0.15)",
        "glow-lg": "0 0 40px rgba(192, 193, 255, 0.2)",
      },
      backdropBlur: {
        "24": "24px",
      },
      animation: {
        "fade-in": "fadeIn 0.5s ease-out",
        "slide-up": "slideUp 0.4s ease-out",
        "pulse-glow": "pulseGlow 3s ease-in-out infinite",
        "shimmer": "shimmer 2s linear infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 15px rgba(192, 193, 255, 0.1)" },
          "50%": { boxShadow: "0 0 30px rgba(192, 193, 255, 0.25)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
