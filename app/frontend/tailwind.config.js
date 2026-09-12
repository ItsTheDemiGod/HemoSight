/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#16161a",
        muted: "#5d5a54",
        faint: "#8a857c",
        paper: "#faf9f7",
        panel: "#f3f1ec",
        rule: "#ddd9d1",
        fail: "#9e2b1e",
        insufficient: "#8a6410",
        pass: "#2c6248",
      },
      fontFamily: {
        serif: ["Iowan Old Style", "Palatino Linotype", "Georgia", "serif"],
        sans: ["Inter", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Consolas", "monospace"],
      },
      maxWidth: { measure: "68ch" },
    },
  },
  plugins: [],
};
