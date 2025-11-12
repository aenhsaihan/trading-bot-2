/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'dark-bg': '#1e1e2e',
        'dark-card': '#2a2a3e',
        'critical': '#FF4444',
        'high': '#FF8800',
        'medium': '#FFBB00',
        'low': '#4488FF',
        'info': '#888888',
      },
    },
  },
  plugins: [],
}

