import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#070b12",
        surface: "#0d131e",
        border: "rgba(255,255,255,0.08)",
        accent: { DEFAULT: "#22d3ee", soft: "#67e8f9", deep: "#0891b2" },
        safe: "#34d399",
        warn: "#fbbf24",
        danger: "#f87171",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        radar: { "0%": { transform: "rotate(0deg)" }, "100%": { transform: "rotate(360deg)" } },
      },
      animation: { "fade-up": "fade-up 0.4s ease-out both", radar: "radar 4s linear infinite" },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
export default config;
