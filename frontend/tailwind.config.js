/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: "#0B2A4A",
          maroon: "#7A003C",
          gold: "#E39A18",
          green: "#1C9C5A",

          light: "#F6F8FB",
          dark: "#16212B",
        },
      },

      fontFamily: {
        display: ["'Sora'", "system-ui", "sans-serif"],
        body: ["'Inter'", "system-ui", "sans-serif"],
      },

      boxShadow: {
        soft: "0 12px 28px rgba(11,42,74,.12)",
        card: "0 8px 24px rgba(11,42,74,.08)",
      },

      backgroundImage: {
        "brand-gradient":
          "linear-gradient(135deg,#0B2A4A 0%,#7A003C 55%,#E39A18 100%)",

        "page-gradient":
          "radial-gradient(circle at top left,#eef4ff 0%,transparent 40%),radial-gradient(circle at top right,#fff3e2 0%,transparent 35%),linear-gradient(180deg,#ffffff,#f6f8fb)",
      },
    },
  },

  plugins: [],
};