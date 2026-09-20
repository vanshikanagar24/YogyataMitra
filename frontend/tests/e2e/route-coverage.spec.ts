import { test, expect } from "@playwright/test";

test.describe("Portal Route Coverage and Responsiveness", () => {
  test("Navigates across all 5 statutory portal routes", async ({ page }) => {
    // 1. Home
    await page.goto("/");
    await expect(page).toHaveTitle(/YogyataMitra|योग्यता मित्र/i);
    await expect(page.locator("#main-content")).toBeVisible();

    // 2. Schemes Directory
    await page.goto("/schemes");
    await expect(page).toHaveURL(/.*schemes/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // 3. Eligibility Journey
    await page.goto("/eligibility");
    await expect(page).toHaveURL(/.*eligibility/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // 4. Policy Verification
    await page.goto("/policy-verification");
    await expect(page).toHaveURL(/.*policy-verification/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // 5. Audit History
    await page.goto("/audit-history");
    await expect(page).toHaveURL(/.*audit-history/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("Adapts responsive layout at mobile 375px and desktop 1280px viewports", async ({ page }) => {
    // Desktop Viewport (1280x800)
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/");
    const desktopNav = page.getByRole("navigation", { name: /Main Navigation|मुख्य नेविगेशन/i });
    await expect(desktopNav).toBeVisible();

    // Mobile Viewport (375x667 - iPhone SE)
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(desktopNav).toBeHidden();

    // Mobile menu toggle button
    const menuToggle = page.getByRole("button", { name: /नेविगेशन मेनू टॉगल करें|toggle navigation menu/i });
    await expect(menuToggle).toBeVisible();
    await expect(menuToggle).toHaveAttribute("aria-expanded", "false");

    // Open mobile drawer
    await menuToggle.click();
    await expect(menuToggle).toHaveAttribute("aria-expanded", "true");
    const mobileDrawer = page.locator("#mobile-navigation");
    await expect(mobileDrawer).toBeVisible();

    // Close via Escape key
    await page.keyboard.press("Escape");
    await expect(menuToggle).toHaveAttribute("aria-expanded", "false");
  });

  test("Provides accessible skip-to-content link targeting #main-content", async ({ page }) => {
    await page.goto("/");
    const skipLink = page.locator("a.skip-to-content");
    await expect(skipLink).toHaveAttribute("href", "#main-content");

    const mainTarget = page.locator("#main-content");
    await expect(mainTarget).toBeAttached();
    await expect(mainTarget).toHaveAttribute("tabindex", "-1");
  });

  test("Verifies zero horizontal overflow across all standard responsive breakpoints (320px to 1440px)", async ({ page }) => {
    const viewports = [
      { width: 320, height: 568 },   // Small mobile
      { width: 375, height: 667 },   // Standard mobile (iPhone SE)
      { width: 390, height: 844 },   // Modern mobile (iPhone 14)
      { width: 768, height: 1024 },  // Tablet portrait
      { width: 1024, height: 768 },  // Tablet landscape / small desktop
      { width: 1280, height: 800 },  // Standard desktop
      { width: 1440, height: 900 },  // Large desktop
    ];

    for (const vp of viewports) {
      await page.setViewportSize(vp);
      await page.goto("/");
      
      // Verify body does not horizontally overflow viewport
      const hasOverflow = await page.evaluate(() => {
        return document.documentElement.scrollWidth > window.innerWidth;
      });
      expect(hasOverflow, `Horizontal overflow detected at ${vp.width}px`).toBeFalsy();
    }
  });
});
