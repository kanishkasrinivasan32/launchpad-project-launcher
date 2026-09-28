import { defineConfig } from "@playwright/test";
import path from "node:path";

const root = path.resolve("..");
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  use: {
    extraHTTPHeaders: { "X-Launchpad-Request": "1" },
    baseURL: "http://127.0.0.1:5179",
    channel: "chrome",
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `"${root}/.venv/Scripts/python.exe" -m backend.main`,
      cwd: root,
      url: "http://127.0.0.1:8019/api/health",
      reuseExistingServer: false,
      timeout: 30000,
      env: {
        BACKEND_PORT: "8019",
        FRONTEND_URL: "http://localhost:5179",
        DATA_DIR: `${root}/test-results/e2e-data`,
        AUTO_OPEN_BROWSER: "false",
        MONITOR_INTERVAL: "0.5",
      },
    },
    {
      command: "npm run dev -- --port 5179",
      url: "http://127.0.0.1:5179",
      reuseExistingServer: false,
      timeout: 30000,
      env: { BACKEND_PORT: "8019", FRONTEND_URL: "http://localhost:5179" },
    },
  ],
});
