import tailwindcss from "@tailwindcss/vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// TanStack Start + Vite. Source: https://tanstack.com/start/latest/docs/framework/react/build-from-scratch
export default defineConfig({
  server: {
    port: 3000,
  },
  plugins: [tailwindcss(), tanstackStart({ srcDirectory: "src" }), viteReact()],
});
