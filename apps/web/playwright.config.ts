import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173";
const remote = /^(https?:\/\/)(?!127\.0\.0\.1|localhost)/i.test(baseURL);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : [["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    launchOptions: {
      args: [
        "--disable-features=PasswordManager,PasswordManagerOnboarding,PasswordCheck,AutofillServerCommunication",
        "--password-store=basic",
      ],
    },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: remote
    ? undefined
    : [
        {
          command: "PYTHONPATH=. python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
          cwd: "../api",
          url: "http://127.0.0.1:8000/health",
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
        {
          command: "npm run dev",
          url: "http://127.0.0.1:5173",
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
      ],
});
