/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          blue: "#2F6FF0",
          "blue-dark": "#1E4FD1",
          purple: "#8B5CF6",
          teal: "#14B8A6",
          cyan: "#22D3EE",
        },
      },
      fontFamily: {
        display: ["'Sora'", "system-ui", "sans-serif"],
        body: ["'Inter'", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 10px 30px -12px rgba(47, 111, 240, 0.25)",
        card: "0 4px 20px -4px rgba(76, 29, 149, 0.12)",
      },
      backgroundImage: {
        "brand-gradient":
          "linear-gradient(135deg, #2F6FF0 0%, #8B5CF6 60%, #22D3EE 100%)",
        "page-gradient":
          "radial-gradient(circle at 10% 0%, #EEF2FF 0%, transparent 45%), radial-gradient(circle at 90% 10%, #ECFEFF 0%, transparent 40%), radial-gradient(circle at 50% 100%, #F5F3FF 0%, transparent 50%)",
      },
    },
  },
  plugins: [],
};
