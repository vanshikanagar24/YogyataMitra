import { test, expect } from "@playwright/test";

test.describe("Phase 14: Officer / Human Verification Portal E2E", () => {
  test("1. Citizen portal does not display internal officer links in header or navigation", async ({
    page,
  }) => {
    await page.goto("/");
    // Header navigation should only have public items
    const nav = page.getByRole("navigation", { name: /Main Navigation|मुख्य नेविगेशन/i });
    await expect(nav).toBeVisible();
    await expect(nav.getByText(/Officer/i)).toHaveCount(0);
    await expect(nav.getByText(/Verification Portal/i)).toHaveCount(0);
  });

  test("2. Officer login page renders official banner, demo warnings, and pre-seeded accounts", async ({
    page,
  }) => {
    await page.goto("/officer/login");

    // Title / Header
    await expect(page.getByText("DEVELOPMENT OFFICER LOGIN")).toBeVisible();
    await expect(page.getByText(/BACK-OFFICE VERIFICATION/i)).toBeVisible();

    // Demo warning notice
    await expect(
      page.getByText(/Demonstration & Local Testing Notice/i)
    ).toBeVisible();
    await expect(
      page.getByText(/Do not enter real citizen Aadhaar numbers/i)
    ).toBeVisible();

    // Quick-fill buttons
    const officerBtn = page.getByRole("button", { name: /Verification Officer/i });
    const supervisorBtn = page.getByRole("button", { name: /Welfare Supervisor/i });
    await expect(officerBtn).toBeVisible();
    await expect(supervisorBtn).toBeVisible();
  });

  test("3. Officer can login using demo credentials and view Verification Queue", async ({
    page,
  }) => {
    await page.goto("/officer/login");

    // Click quick fill for Verification Officer
    await page.getByRole("button", { name: /Verification Officer/i }).click();

    // Verify email field auto-filled
    const emailInput = page.getByPlaceholder("officer@yogyatamitra.local");
    await expect(emailInput).toHaveValue("officer@yogyatamitra.local");

    // Submit form
    await page.getByRole("button", { name: /Sign In to Verification Portal/i }).click();

    // Should redirect to queue
    await expect(page).toHaveURL(/.*officer\/queue/, { timeout: 15000 });

    // Queue header & metrics cards should be present
    await expect(page.getByRole("heading", { name: /^Verification Queue$/i })).toBeVisible();
    await expect(page.getByText("Total in Queue")).toBeVisible();
    await expect(page.locator("div").filter({ hasText: /^Pending Review$/ }).first()).toBeVisible();
    await expect(page.locator("div").filter({ hasText: /^Escalated$/ }).first()).toBeVisible();
    await expect(page.locator("div").filter({ hasText: /^Completed$/ }).first()).toBeVisible();

    // Role badge
    await expect(page.getByText("OFFICER", { exact: true })).toBeVisible();
  });

  test("4. Supervisor login displays elevated SUPERVISOR role badge", async ({
    page,
  }) => {
    await page.goto("/officer/login");

    // Click quick fill for Welfare Supervisor
    await page.getByRole("button", { name: /Welfare Supervisor/i }).click();

    // Submit form
    await page.getByRole("button", { name: /Sign In to Verification Portal/i }).click();

    // Should redirect to queue
    await expect(page).toHaveURL(/.*officer\/queue/, { timeout: 15000 });

    // Role badge
    await expect(page.getByText("SUPERVISOR", { exact: true })).toBeVisible();
  });
});
