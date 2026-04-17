import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        board: { bg: "#DCB35C", dark: "#2B1E0E" }
      }
    }
  },
  plugins: []
};
export default config;
