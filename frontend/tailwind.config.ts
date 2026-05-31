import type { Config } from "tailwindcss";

// MedFlow design tokens (see ./app/globals.css :root for the source-of-truth
// CSS custom properties). Tailwind utilities reference the tokens via
// `var(--token)` so theme changes flow through the CSS layer, not Tailwind's
// build artifact.
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        "bg-surface": "var(--bg-surface)",
        "bg-subtle": "var(--bg-subtle)",
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-foreground)",
          soft: "var(--mf-accent-soft)",
          hover: "var(--accent-hover)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
          foreground: "var(--destructive-foreground)",
        },
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
        "mf-paper": "var(--mf-paper)",
        "mf-paper-2": "var(--mf-paper-2)",
        "mf-ink": "var(--mf-ink)",
        "mf-ink-soft": "var(--mf-ink-soft)",
        "mf-clinician": "var(--mf-clinician)",
        "mf-patient": "var(--mf-patient)",
      },
      borderRadius: {
        sm: "calc(var(--radius) * 0.6)",
        md: "calc(var(--radius) * 0.8)",
        lg: "var(--radius)",
        xl: "calc(var(--radius) * 1.4)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Georgia", "serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        "mf-sm": "var(--shadow-sm)",
        "mf-md": "var(--shadow-md)",
      },
    },
  },
  plugins: [],
};

export default config;
