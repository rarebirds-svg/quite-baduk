import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        board: { bg: "#E8C572", dark: "#C49A54" }
      }
    }
  },
  plugins: []
};
export default config;
