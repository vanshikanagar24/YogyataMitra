import { test, expect } from "@playwright/test";

test.describe("Bilingual Navigation and Consistency", () => {
  test("Switches between English and Hindi across the portal", async ({ page }) => {
    await page.goto("/");

    // Default Hindi navigation
    await expect(page.locator("header")).toContainText("मुख्य पृष्ठ");

    // Switch to English
    await page.getByRole("button", { name: /Switch to English/i }).click();
    await expect(page.locator("header")).toContainText("Home");
    await expect(page.locator("header")).toContainText("Schemes");
    await expect(page.locator("h1")).toContainText(/The Right Scheme for You/);

    // Navigate to Schemes in English using main navigation link
    await page.getByRole("navigation", { name: "Main Navigation" }).getByRole("link", { name: "Schemes" }).click();
    await expect(page).toHaveURL(/.*schemes/);
    await expect(page.locator("h1")).toContainText("Statutory Welfare Schemes");

    // Switch back to Hindi
    await page.getByRole("button", { name: /Switch to Hindi/i }).click();
    await expect(page.locator("h1")).toContainText("सरकारी कल्याणकारी योजनाएं");
  });
});
