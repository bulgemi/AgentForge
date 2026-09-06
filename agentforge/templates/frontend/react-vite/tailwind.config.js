/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./admin.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        skred: "#E1002A",
        skorange: "#F58220",
      },
    },
  },
  plugins: [],
}
