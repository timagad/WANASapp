import type { Config } from "tailwindcss";

// Palette and type scale come straight from the WANAS proof-of-concept
// prototypes so the built product and the pitch deck stay the same object.
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: "#12463A", dark: "#0B2E25", light: "#1B5A48" },
        secondary: "#C97D4B",
        accent: "#E8B33D",
        cream: "#F7F3EC",
        ink: "#1F2A24",
        muted: "#6E7D76",
        line: "#E7E2D6",
      },
      fontFamily: {
        display: ["var(--font-display)", "Fraunces", "Georgia", "serif"],
        body: ["var(--font-body)", "Manrope", "system-ui", "sans-serif"],
      },
      boxShadow: {
        phone: "0 40px 80px -20px rgba(0,0,0,.65), inset 0 0 0 1px rgba(255,255,255,.04)",
        card: "0 8px 20px -12px rgba(18,70,58,.25)",
      },
      keyframes: {
        rise: { "0%": { opacity: "0", transform: "translateY(6px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        blink: { "0%,100%": { opacity: ".25" }, "50%": { opacity: "1" } },
      },
      animation: {
        rise: "rise .35s ease",
        blink: "blink 1.2s infinite",
      },
    },
  },
  plugins: [],
};

export default config;
