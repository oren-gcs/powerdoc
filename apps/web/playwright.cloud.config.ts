import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL;
if (!baseURL) {
  throw new Error("Cloud Playwright needs PLAYWRIGHT_BASE_URL (the deployed desk, e.g. https://desk.example.com)");
}

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  retries: 2,
  workers: 2,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    launchOptions: {
      args: [
        "--disable-features=PasswordManager,PasswordManagerOnboarding,PasswordCheck",
        "--password-store=basic",
      ],
    },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
