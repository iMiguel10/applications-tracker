/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    // Los bind mounts de Docker en Windows no propagan eventos de fichero:
    // sin polling no hay HMR dentro del contenedor.
    watch: {
      usePolling: true,
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
});
