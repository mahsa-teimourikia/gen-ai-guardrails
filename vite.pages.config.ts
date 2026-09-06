import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  root: "github-pages",
  base: "/gen-ai-guardrails/",
  plugins: [react()],
  build: {
    outDir: "../out",
    emptyOutDir: true,
  },
});
