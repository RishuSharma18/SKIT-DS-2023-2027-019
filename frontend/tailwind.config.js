/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#172338',
        canvas: '#f4f7fb',
        accent: '#2ba779',
      },
      boxShadow: {
        panel: '0 12px 32px rgba(24, 43, 69, 0.06)',
      },
    },
  },
  plugins: [],
};
