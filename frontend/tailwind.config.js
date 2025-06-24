/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./*.{vue,js,ts,jsx,tsx}",
    "./**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // You can add custom colors here if needed
      },
    },
  },
  plugins: [],
}