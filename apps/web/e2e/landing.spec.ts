import { expect, test } from "@playwright/test";

test("landing explains the desk", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Documents should move/i })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open the desk" })).toBeVisible();
  await expect(page.getByText("oren@gcs-tech.org")).toBeVisible();
});
