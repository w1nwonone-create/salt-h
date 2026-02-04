/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // 살짝 따뜻한 바이올렛 & 앰버 톤
        "salt-primary": "#8B7CFF",
        "salt-secondary": "#F6AD55"
      }
    }
  },
  plugins: []
};

