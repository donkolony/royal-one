/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Royal Square brand palette — Navy Blue & Ruby Red
        brand: {
          50: "#f0f5fc",
          100: "#e3ebf8",
          200: "#c1d6ef",
          300: "#8bb6e2",
          400: "#4f91d1",
          500: "#002E6C", // Primary Navy Blue
          600: "#002459",
          700: "#001a43",
          800: "#00122f",
          900: "#000918",
        },
        accent: {
          50: "#fdf2f5",
          100: "#fae6ec",
          200: "#f4c0d1",
          300: "#ed99b6",
          400: "#de4d7e",
          500: "#B0234D", // Ruby Red
          600: "#9e1d43",
          700: "#841535",
          800: "#6a1029",
          900: "#590d22",
        },
        charcoal: {
          50: "#f5f5f6",
          100: "#e6e6e8",
          200: "#c8c9cc",
          300: "#a2a4a9",
          400: "#74777e",
          500: "#555961",
          600: "#3e4149",
          700: "#2d3038",
          800: "#1c1f26", // primary dark
          900: "#0f1117",
        },
        success: "#16a34a",
        warning: "#ca8a04",
        danger: "#dc2626",
      },
      fontFamily: {
        sans: [
          "DM Sans",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "sans-serif",
        ],
      },
      borderRadius: {
        DEFAULT: "0.5rem",
        lg: "0.75rem",
        xl: "1rem",
      },
    },
  },
  plugins: [
    // @ts-ignore
    require("@tailwindcss/forms"),
  ],
};
