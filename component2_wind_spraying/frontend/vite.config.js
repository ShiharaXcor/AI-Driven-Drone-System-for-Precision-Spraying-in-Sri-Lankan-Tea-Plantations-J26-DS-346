import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// React dev server on http://localhost:5173
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
