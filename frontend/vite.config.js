import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(() => {
  const env = { ...loadEnv("", "..", ""), ...process.env };
  const frontend = new URL(env.FRONTEND_URL || "http://localhost:5173");
  return {
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      strictPort: true,
      allowedHosts: ["localhost", "127.0.0.1"],
      headers: {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
      },
      fs: {
        strict: true,
        deny: [
          ".env",
          ".env.*",
          "*.{pem,key,p12,pfx,db,sqlite,sqlite3}",
          "**/.git/**",
          "**/data/**",
        ],
      },
      port: Number(frontend.port || 5173),
      proxy: {
        "/api": { target: `http://127.0.0.1:${env.BACKEND_PORT || 8000}` },
      },
    },
  };
});
