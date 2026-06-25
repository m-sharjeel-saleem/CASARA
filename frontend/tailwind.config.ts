import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Ground + surfaces — blue-biased near-black, chosen not defaulted.
        bg: "#090c14",
        surface: "#0e1320",
        panel: "#141b2b",
        border: "rgba(148,163,184,0.12)",
        // Brand signal — iris/periwinkle. Distinct from every status colour.
        accent: { DEFAULT: "#6d7bff", soft: "#a5b0ff", deep: "#4b4ee6" },
        // Semantic severity scale (separate from the accent).
        sev: {
          critical: "#ff4d6d",
          high: "#ff8a3d",
          medium: "#f5c043",
          low: "#7c8aa3",
          info: "#5b6678",
        },
        safe: "#3ee0a3",
        warn: "#f5c043",
        danger: "#ff4d6d",
      },
      fontFamily: {
        display: ["var(--font-display)", "var(--font-inter)", "system-ui", "sans-serif"],
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(109,123,255,0.25), 0 0 32px -8px rgba(109,123,255,0.45)",
        tile: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 12px 40px -24px rgba(0,0,0,0.9)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        sweep: { "0%": { transform: "rotate(0deg)" }, "100%": { transform: "rotate(360deg)" } },
        scan: {
          "0%": { transform: "translateY(-100%)", opacity: "0" },
          "50%": { opacity: "1" },
          "100%": { transform: "translateY(2400%)", opacity: "0" },
        },
        "pulse-glow": {
          "0%,100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "dash-draw": { "0%": { strokeDashoffset: "var(--dash)" }, "100%": { strokeDashoffset: "0" } },
      },
      animation: {
        "fade-up": "fade-up 0.45s cubic-bezier(0.22,1,0.36,1) both",
        sweep: "sweep 8s linear infinite",
        scan: "scan 7s ease-in-out infinite",
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        shimmer: "shimmer 1.8s linear infinite",
        "dash-draw": "dash-draw 1.1s cubic-bezier(0.22,1,0.36,1) both",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
export default config;
