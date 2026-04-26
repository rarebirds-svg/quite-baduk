import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        paper: "rgb(var(--paper) / <alpha-value>)",
        "paper-deep": "rgb(var(--paper-deep) / <alpha-value>)",
        ink: "rgb(var(--ink) / <alpha-value>)",
        "ink-mute": "rgb(var(--ink-mute) / <alpha-value>)",
        "ink-faint": "rgb(var(--ink-faint) / <alpha-value>)",
        oxblood: "rgb(var(--oxblood) / <alpha-value>)",
        gold: "rgb(var(--gold) / <alpha-value>)",
        moss: "rgb(var(--moss) / <alpha-value>)",
        "stone-black": "rgb(var(--stone-black) / <alpha-value>)",
        "stone-white": "rgb(var(--stone-white) / <alpha-value>)",
        /* board.bg and board.dark kept for legacy Board.tsx until Phase 2 rewrite */
        board: { bg: "#E8C572", dark: "#C49A54" },
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "serif"],
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      letterSpacing: { label: "0.16em" },
      transitionTimingFunction: { stone: "cubic-bezier(.2,.7,.2,1)" },
      transitionDuration: { stone: "300ms", page: "200ms" },
      borderRadius: { DEFAULT: "2px", sm: "2px" },
    },
  },
  plugins: [],
};

export default config;
