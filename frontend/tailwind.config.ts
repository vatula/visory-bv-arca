import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        arcra: {
          pending: "#6366f1",
          processing: "#f59e0b",
          policy_check: "#8b5cf6",
          evidence_gathering: "#3b82f6",
          awaiting_slack: "#f97316",
          complete: "#22c55e",
          escalated: "#ef4444",
        },
      },
    },
  },
  plugins: [],
};

export default config;
