import { test, expect } from "@playwright/test";

test.describe("SSY Complete Citizen Entitlement Flow", () => {
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
            description_hi: "बालिकाओं के लिए विशेष बचत योजना।",
            ministry: "Ministry of Finance",
            official_url: "https://www.indiapost.gov.in",
            status: "ACTIVE",
            created_at: "2024-01-01T00:00:00Z",
          },
        ]),
      });
    });

    await page.route("**/api/v1/schemes/SSY", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "ssy-01",
          scheme_code: "SSY",
          name_en: "Sukanya Samriddhi Account",
          name_hi: "सुकन्या समृद्धि योजना",
          description_en: "Deposit scheme for girl child.",
          description_hi: "बालिकाओं के लिए विशेष बचत योजना।",
          ministry: "Ministry of Finance",
          official_url: "https://www.indiapost.gov.in",
          status: "ACTIVE",
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
          policy_versions: [],
        }),
      });
    });

    await page.route("**/api/v1/schemes/SSY/policies", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.route("**/api/v1/journeys", async (route) => {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          id: "jrn-ssy-202",
          citizen_id: "cit-202",
          citizen_ref: "SYN-CIT-2026-001",
          scheme_id: "ssy-01",
          scheme_code: "SSY",
          state: "DRAFT",
          created_at: "2024-01-15T00:00:00Z",
          updated_at: "2024-01-15T00:00:00Z",
        }),
      });
    });

    await page.route("**/api/v1/journeys/*/claims", async (route) => {
      const payload = route.request().postDataJSON();
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          id: `clm-${Math.random().toString(36).slice(2, 7)}`,
          citizen_id: "cit-202",
          claim_type: payload.claim_type,
          value_json: payload.value_json,
          source: payload.source || "SELF_DECLARATION",
          status: "ASSERTED",
          claimed_at: "2024-01-15T00:00:00Z",
          updated_at: "2024-01-15T00:00:00Z",
          evidence_items: [],
        }),
      });
    });

    await page.route("**/api/v1/evaluations", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          evaluation_id: "eval-202",
          scheme_code: "SSY",
          policy_version_code: "v2.0-2019",
          rule_definition_hash: "b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef01",
          evaluation_date: "2024-01-15",
          effective_from: "2019-12-12",
          effective_to: null,
          overall_result: "ELIGIBLE",
          root_truth_value: "TRUE",
          reasons_en: ["Beneficiary satisfies statutory age and residency criteria."],
          reasons_hi: ["बालिका आयु एवं निवास संबंधी सभी वैधानिक शर्तों को पूरा करती है।"],
          missing_fields: [],
          satisfied_rules: ["R_GENDER_FEMALE", "R_AGE_UNDER_TEN"],
          failed_rules: [],
          unknown_rules: [],
          blockers: [],
          audit_persisted: true,
          created_at: "2024-01-15T10:00:00Z",
        }),
      });
    });
  });

  test("Navigates to Sukanya Samriddhi Yojana and tests eligibility journey", async ({
    page,
  }) => {
    // Authenticate as demo citizen
    await page.goto("/citizen/login");
    await page.getByRole("button", { name: /Auto Fill|स्वतः भरें/i }).click();
    await expect(page.locator("#citizen-identifier")).toHaveValue("citizen.test@yogyatamitra.local");
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*citizen\/dashboard/, { timeout: 15000 });

    await page.goto("/");

    // Click SSY chip in Hero
    const ssyChip = page.locator("a[href='/schemes/SSY']").first();
    await ssyChip.click();
    await expect(page).toHaveURL(/.*schemes\/SSY/);

    // On Scheme Detail page, click Check Eligibility CTA inside main content
    const checkBtn = page.locator("main").getByRole("link", { name: /पात्रता जाँचें/i }).first();
    await checkBtn.click();
    await expect(page).toHaveURL(/.*eligibility.*scheme=SSY/);

    // In Step 1 (Facts), verify SSY question
    await expect(page.getByText(/बालिका की जन्म तिथि/i)).toBeVisible();

    // Register claims
    const registerBtn = page.getByRole("button", { name: /दावे पंजीकृत करें/i });
    await registerBtn.click();

    // Verify claims
    await expect(page.locator("[data-claim-type='beneficiary.gender']")).toBeVisible();
    await expect(page.getByRole("heading", { name: /बालिका का लिंग/i })).toBeVisible();

    // Evaluate
    const evalBtn = page.getByRole("button", { name: /वैधानिक मूल्यांकन चलाएं/i });
    await evalBtn.click();

    // Verify Result
    await expect(page.getByText(/वैधानिक पात्रता निर्णय/i)).toBeVisible();
  });
});
