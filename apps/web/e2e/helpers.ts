import { expect, type Page } from "@playwright/test";

export const demoEmail = process.env.PLAYWRIGHT_DEMO_EMAIL?.trim() || "oren@gcs-tech.org";
export const demoPassword = process.env.PLAYWRIGHT_DEMO_PASSWORD?.trim() || "DocFlow!2026";

export async function signIn(page: Page) {
  await page.goto("/login");
  await page.locator("#login-email").fill(demoEmail);
  await page.locator("#login-password").fill(demoPassword);
  await page.getByRole("button", { name: "Enter" }).click();
  await page.waitForURL("**/app**");
  await expect(page.locator("aside.rail")).toBeVisible();
}

export async function openTab(page: Page, href: string) {
  await page.locator(`aside.rail a[href="${href}"]`).click();
  await expect(page.locator(`aside.rail a[href="${href}"]`)).toHaveClass(/active/);
}
