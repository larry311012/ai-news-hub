/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./*.html",
    "./*.js",
    "./components/**/*.{vue,js}",
    "./utils/**/*.js",
    "!./node_modules/**",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#FF6B35',      // Orange from your design
        secondary: '#4ECDC4',    // Teal
        accent: '#FFE66D',       // Yellow
      }
    },
  },
  plugins: [],
}
