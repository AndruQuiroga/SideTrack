/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["system-ui", "ui-sans-serif", "sans-serif"],
      },
      colors: {
        sidetrack: {
          bg: "#050816",
          surface: "#0f172a",
          soft: "#1e293b",
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
