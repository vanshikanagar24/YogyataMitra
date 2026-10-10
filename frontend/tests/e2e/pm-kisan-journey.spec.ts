import { test, expect } from "@playwright/test";

test.describe("PM-KISAN Complete Citizen Entitlement Flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/v1/schemes", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "pmk-01",
            scheme_code: "PM_KISAN",
            name_en: "Pradhan Mantri Kisan Samman Nidhi",
            name_hi: "प्रधानमंत्री किसान सम्मान निधि",
            description_en: "Income support scheme for farmers.",
            description_hi: "भूमिधारक किसान परिवारों के लिए आय सहायता।",
            ministry: "Ministry of Agriculture and Farmers Welfare",
            official_url: "https://pmkisan.gov.in",
            status: "ACTIVE",
            created_at: "2024-01-01T00:00:00Z",
          },
          {
            id: "ssy-01",
            scheme_code: "SSY",
            name_en: "Sukanya Samriddhi Account",
            name_hi: "सुकन्या समृद्धि योजना",
            description_en: "Deposit scheme for girl child.",
            description_hi: "बालिकाओं के लिए बचत योजना।",
            ministry: "Ministry of Finance",
            official_url: "https://www.indiapost.gov.in",
            status: "ACTIVE",
            created_at: "2024-01-01T00:00:00Z",
          },
        ]),
      });
    });

    await page.route("**/api/v1/schemes/PM_KISAN", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "pmk-01",
          scheme_code: "PM_KISAN",
          name_en: "Pradhan Mantri Kisan Samman Nidhi",
          name_hi: "प्रधानमंत्री किसान सम्मान निधि",
          description_en: "Income support scheme for farmers.",
          description_hi: "भूमिधारक किसान परिवारों के लिए आय सहायता।",
          ministry: "Ministry of Agriculture and Farmers Welfare",
          official_url: "https://pmkisan.gov.in",
          status: "ACTIVE",
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
          policy_versions: [
            {
              version_code: "v3.0-2023",
              effective_from: "2023-07-01",
              effective_to: null,
              rule_definition_hash: "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
            },
          ],
        }),
      });
    });

    await page.route("**/api/v1/schemes/PM_KISAN/policies", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "pol-01",
            scheme_code: "PM_KISAN",
            version_code: "v3.0-2023",
            effective_from: "2023-07-01",
            effective_to: null,
            source_url: "https://pmkisan.gov.in",
            source_title: "Operational Guidelines 2023",
            source_document_identifier: "GUIDELINE-2023",
            rule_definition_hash: "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
            ruleset_schema_version: "1.0",
            ruleset_version: "3.0",
            created_at: "2024-01-01T00:00:00Z",
          },
        ]),
      });
    });

    await page.route("**/api/v1/journeys", async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            id: "jrn-pmk-101",
            citizen_id: "cit-101",
            citizen_ref: "SYN-CIT-2026-001",
            scheme_id: "pmk-01",
            scheme_code: "PM_KISAN",
            state: "DRAFT",
            created_at: "2024-01-15T00:00:00Z",
            updated_at: "2024-01-15T00:00:00Z",
          }),
        });
      }
    });

    await page.route("**/api/v1/journeys/*/claims", async (route) => {
      if (route.request().method() === "POST") {
        const payload = route.request().postDataJSON();
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            id: `clm-${Math.random().toString(36).slice(2, 7)}`,
            citizen_id: "cit-101",
            claim_type: payload.claim_type,
            value_json: payload.value_json,
            source: payload.source || "SELF_DECLARATION",
            status: "ASSERTED",
            claimed_at: "2024-01-15T00:00:00Z",
            updated_at: "2024-01-15T00:00:00Z",
            evidence_items: [],
          }),
        });
      }
    });

    await page.route("**/api/v1/evaluations", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          evaluation_id: "eval-101",
          scheme_code: "PM_KISAN",
          policy_version_code: "v3.0-2023",
          rule_definition_hash: "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
          evaluation_date: "2024-01-15",
          effective_from: "2023-07-01",
          effective_to: null,
          overall_result: "ELIGIBLE",
          root_truth_value: "TRUE",
          reasons_en: ["Family satisfies all statutory landholding criteria."],
          reasons_hi: ["परिवार सभी वैधानिक भूमि स्वामित्व मानदंडों को पूरा करता है।"],
          missing_fields: [],
          satisfied_rules: ["R_CULTIVABLE_LAND"],
          failed_rules: [],
          unknown_rules: [],
          blockers: [],
          audit_persisted: true,
          created_at: "2024-01-15T10:00:00Z",
        }),
      });
    });
  });

  test("Navigates from Homepage to PM-KISAN scheme details and completes eligibility journey", async ({
    page,
  }) => {
    // Authenticate as demo citizen
    await page.goto("/citizen/login");
    await page.getByRole("button", { name: /Auto Fill|स्वतः भरें/i }).click();
    await expect(page.locator("#citizen-identifier")).toHaveValue("citizen.test@yogyatamitra.local");
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*citizen\/dashboard/, { timeout: 15000 });

    await page.goto("/");
    await expect(page).toHaveTitle(/योग्यता मित्र/);
    await expect(page.locator("h1")).toContainText(/आपके लिए/);

    // Click PM-KISAN chip in Hero
    const pmKisanChip = page.locator("a[href='/schemes/PM_KISAN']").first();
    await pmKisanChip.click();
    await expect(page).toHaveURL(/.*schemes\/PM_KISAN/);

    // On Scheme Detail page, click Check Eligibility CTA inside main content
    const checkBtn = page.locator("main").getByRole("link", { name: /पात्रता जाँचें/i }).first();
    await checkBtn.click();
    await expect(page).toHaveURL(/.*eligibility.*scheme=PM_KISAN/);

    // In Step 1 (Facts)
    await expect(page.getByText(/कृषि योग्य भूमि/i)).toBeVisible();

    // Register Claims
    const registerBtn = page.getByRole("button", { name: /दावे पंजीकृत करें/i });
    await registerBtn.click();

    // Step 2-4: Claims review
    await expect(page.locator("[data-claim-type='family.owns_cultivable_land']")).toBeVisible();
    await expect(page.getByRole("heading", { name: /कृषि योग्य भूमि का स्वामित्व/i })).toBeVisible();

    // Execute Evaluation
    const evalBtn = page.getByRole("button", { name: /वैधानिक मूल्यांकन चलाएं/i });
    await evalBtn.click();

    // Step 5: Result & Explainability
    await expect(page.getByText(/वैधानिक पात्रता निर्णय/i)).toBeVisible();
    await expect(page.locator("#explainability-section").getByText(/यह परिणाम क्यों मिला/i)).toBeVisible();
  });
});
