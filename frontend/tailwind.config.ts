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
        primary: {
          DEFAULT: "#1E3A8A",
          dark: "#14265C",
          light: "#3B5BDB",
          50: "#EFF4FE",
          100: "#DBE6FD",
          800: "#1E3A8A",
          900: "#14265C",
        },
        navy: {
          900: "#14265C",
          800: "#1E3A8A",
          700: "#2A439E",
        },
        gov: {
          bg: "#F4F6FB",
          surface: "#FFFFFF",
          text: "#101828",
          secondary: "#5B6472",
          border: "#E2E5EC",
        },
        success: {
          DEFAULT: "#15803D",
          50: "#F0FDF4",
          100: "#DCFCE7",
          700: "#15803D",
        },
        warning: {
          DEFAULT: "#B45309",
          50: "#FFFBEB",
          100: "#FEF3C7",
          700: "#B45309",
        },
        danger: {
          DEFAULT: "#B91C1C",
          50: "#FEF2F2",
          100: "#FEE2E2",
          700: "#B91C1C",
        },
        info: {
          DEFAULT: "#2563A8",
          50: "#EFF6FF",
          100: "#DBEAFE",
          700: "#2563A8",
        },
      },
      boxShadow: {
        'gov-card': '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px 0 rgba(0, 0, 0, 0.03)',
        'gov-elevated': '0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -1px rgba(0, 0, 0, 0.04)',
        'gov-modal': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
      },
      borderRadius: {
        'gov': '6px',
        'gov-lg': '10px',
      }
    },
  },
  plugins: [],
};
export default config;
