import type { Config } from "tailwindcss";

/**
 * Tailwind ссылается на CSS-переменные из design-tokens.css (§4).
 * Цвета НЕ хардкодятся в компонентах — только через эти токены.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    // Брейкпоинты строго по §5.1 (mobile-first, база = 320px)
    screens: {
      xs: "320px",
      sm: "425px",
      md: "768px",
      lg: "1024px",
      xl: "1280px",
    },
    extend: {
      colors: {
        brand: "var(--arkand-crimson)",
        "deep-maroon": "var(--deep-maroon)",
        ink: "var(--warm-ink)",
        paper: "var(--paper)",
        crimson: {
          50: "var(--crimson-50)",
          100: "var(--crimson-100)",
          200: "var(--crimson-200)",
          300: "var(--crimson-300)",
          400: "var(--crimson-400)",
          500: "var(--crimson-500)",
          600: "var(--crimson-600)",
          700: "var(--crimson-700)",
          800: "var(--crimson-800)",
          900: "var(--crimson-900)",
          950: "var(--crimson-950)",
        },
        neutral: {
          50: "var(--neutral-50)",
          100: "var(--neutral-100)",
          200: "var(--neutral-200)",
          300: "var(--neutral-300)",
          400: "var(--neutral-400)",
          500: "var(--neutral-500)",
          600: "var(--neutral-600)",
          700: "var(--neutral-700)",
          800: "var(--neutral-800)",
          900: "var(--neutral-900)",
        },
        status: {
          success: "var(--status-success)",
          warning: "var(--status-warning)",
          error: "var(--status-error)",
          info: "var(--status-info)",
        },
        // Бренд ≠ Деньги (§4.2)
        money: {
          income: "var(--money-income)",
          expense: "var(--money-expense)",
          balance: "var(--money-balance)",
        },
      },
      fontFamily: {
        sans: "var(--font-sans)",
        num: "var(--font-num)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        pill: "var(--radius-pill)",
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
      },
    },
  },
  plugins: [],
} satisfies Config;
