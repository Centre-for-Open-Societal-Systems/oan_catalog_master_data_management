/**
 * Tailwind is here only for the dashboard under src/app/dashboard — see
 * src/app/dashboard/dashboard.css, which imports the theme and utility layers
 * but not Preflight, so the console's own stylesheet (src/app/globals.css) is
 * left exactly as it was.
 */
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
