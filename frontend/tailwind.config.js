/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0f1419",
        panel: "#1a2332",
        border: "#2d3a4f",
        accent: "#c9a227",
        muted: "#8b9cb3",
      },
      fontFamily: {
        sheet: ['"Bookman Old Style"', "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};
