import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--ui-bg-matte)",
        foreground: "var(--ui-foreground)",
        accent: "var(--ui-accent-red)",
        card: "var(--ui-surface-1)",
      },
    },
  },
  plugins: [],
};

export default config;
