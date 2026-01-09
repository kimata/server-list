/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#667eea',
          light: '#7c91ed',
          dark: '#5a70d6',
        },
        secondary: {
          DEFAULT: '#764ba2',
          light: '#8a5fb6',
          dark: '#6a428f',
        },
      },
    },
  },
  plugins: [],
}
