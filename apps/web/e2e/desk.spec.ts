import { expect, test } from "@playwright/test";
import { openTab, signIn } from "./helpers";

test.describe("desk", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page);
  });

  test("side panel opens work tabs", async ({ page }) => {
    await expect(page.locator("aside.rail")).toBeVisible();
    await expect(page.getByRole("heading", { name: /the desk is live/i })).toBeVisible();
    await openTab(page, "/app/documents");
    await expect(page.getByRole("heading", { name: /documents/i })).toBeVisible();
    await openTab(page, "/app/forms");
    await expect(page.getByRole("heading", { name: "Forms" })).toBeVisible();
  });

  test("creates a live form from chat", async ({ page }) => {
    await openTab(page, "/app/forms/new");
    await expect(page.locator("[data-demo=form-exit]")).toBeVisible();
    await expect(page.locator("[data-demo=form-exit-back]")).toBeVisible();
    await expect(page.locator("[data-demo=form-exit-cancel]")).toBeVisible();
    await page.locator("[data-demo=compose]").click();
    await expect(page.locator("[data-demo=chat-reply]")).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("[data-demo=chat-reply] .bubble.assistant")).toContainText(/I drafted|understood|Connectors/i);
    await expect(page.locator(".paper-row").first()).toBeVisible({ timeout: 15_000 });
    await page.locator("[data-demo=publish]").click();
    await expect(page.getByText(/In the automation folder — form is alive|Alive:/i)).toBeVisible({ timeout: 15_000 });
  });

  test("form builder cancel returns to forms list", async ({ page }) => {
    await openTab(page, "/app/forms/new");
    await page.locator("[data-demo=form-exit-cancel]").click();
    await expect(page).toHaveURL(/\/app\/forms\/?$/);
    await expect(page.getByRole("heading", { name: "Forms" })).toBeVisible();
  });

  test("answered folder route renders for a form id", async ({ page }) => {
    await openTab(page, "/app/forms");
    await expect(page.getByRole("heading", { name: "Forms" })).toBeVisible();
    // Locked forms expose Answered; draft forms still list Edit.
    const answered = page.locator("[data-demo=open-answered]").first();
    const edit = page.getByRole("link", { name: "Edit" }).first();
    if (await answered.count()) {
      await answered.click();
      await expect(page).toHaveURL(/\/app\/forms\/\d+\/answered/);
      await expect(page.locator("[data-demo=answered-title]")).toBeVisible();
      await expect(page.locator("[data-demo=answered-list]")).toBeVisible();
      await expect(page.locator("[data-demo=copy-form]")).toBeVisible();
      await expect(page.locator("[data-demo=archive-form]")).toBeVisible();
    } else {
      await expect(edit).toBeVisible();
      await expect(page.locator("[data-demo=copy-form]").first()).toBeVisible();
    }
  });

  test("syncs Google Drive, Microsoft 365, and local DB", async ({ page }) => {
    await openTab(page, "/app/connectors");
    await expect(page.getByRole("heading", { name: "Connectors" })).toBeVisible();
    await expect(page.locator("[data-demo=connector-google_drive]")).toBeVisible();
    await expect(page.locator("[data-demo=connector-microsoft]")).toBeVisible();
    await expect(page.locator("[data-demo=connector-local_db]")).toBeVisible();
    await expect(page.locator("[data-demo=connector-ollama]")).toBeVisible();
    await expect(page.locator("[data-demo=connector-ollama]")).toContainText(/Ollama|offline|connected/i);
    await page.locator("[data-demo=sync-google_drive]").click();
    await expect(page.getByText(/Synced/i)).toBeVisible({ timeout: 15_000 });
    await page.locator("[data-demo=sync-microsoft]").click();
    await page.locator("[data-demo=sync-local_db]").click();
    await expect(page.locator("[data-demo=connector-google_drive]")).toContainText(/Drive \//);
    await expect(page.locator("[data-demo=connector-microsoft]")).toContainText(/SharePoint|OneDrive/);
    await expect(page.locator("[data-demo=connector-local_db]")).toContainText(/document:|local_db/);
  });

  test("shows n8n flow canvas and JSON", async ({ page }) => {
    await openTab(page, "/app/workflows");
    await expect(page.getByRole("heading", { name: /n8n flows/i })).toBeVisible();
    await expect(page.locator("[data-demo=n8n-board]")).toBeVisible();
    await expect(page.locator(".n8n-node").first()).toBeVisible();
    await page.getByRole("button", { name: /Invoice Intake/ }).click();
    await page.locator("[data-demo=n8n-json]").click();
    await expect(page.locator("[data-demo=n8n-json-view]")).toContainText("Webhook");
  });
});
