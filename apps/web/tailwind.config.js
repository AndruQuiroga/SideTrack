/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        "slate-950": "#0b1221",
        "accent-cyan": "#38bdf8",
        "accent-violet": "#a78bfa",
        sidetrack: {
          bg: "#050816",
          surface: "#0f172a",
          soft: "#11192b",
          accent: "#a855f7",
          accentSoft: "#4c1d95",
        },
      },
      boxShadow: {
        soft: "0 18px 45px rgba(15,23,42,0.65)",
      },
      borderRadius: {
        "3xl": "1.75rem",
      },
    },
  },
  plugins: [],
};
