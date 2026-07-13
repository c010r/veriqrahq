/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17211b",
        muted: "#5b6b61",
        line: "#cbd8ce",
        accent: "#0f766e"
      }
    }
  },
  plugins: []
};
