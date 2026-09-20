import { test, expect } from "@playwright/test";

test.describe("Phase 12 Citizen Journey QA Pass — End-to-End Automated Testing", () => {
  test.describe.configure({ mode: "serial" });

  // ---------------------------------------------------------------------------
  // JOURNEY 1: PM-KISAN in Hindi (Default Portal Language)
  // ---------------------------------------------------------------------------
  test("Journey 1: PM-KISAN in Hindi (Full Citizen Entitlement Flow)", async ({ page }) => {
    // 1. HOME: What is YogyataMitra? What can I do here? Which schemes? Next step?
    await page.goto("/");
    await expect(page).toHaveTitle(/योग्यता मित्र/);

    const heading = page.locator("h1");
    await expect(heading).toBeVisible();

    // Check Schemes displayed on Home
    const pmKisanChip = page.locator("a[href='/schemes/PM_KISAN']").first();
    const ssyChip = page.locator("a[href='/schemes/SSY']").first();
    await expect(pmKisanChip).toBeVisible();
    await expect(ssyChip).toBeVisible();

    // 2. UNDERSTAND YOGYATAMITRA
    const howItWorks = page.locator("#how-it-works-heading");
    await expect(howItWorks).toBeVisible();

    // 3. BROWSE SCHEMES
    await page.goto("/schemes");
    await expect(page).toHaveURL(/.*schemes/);

    // Exactly 2 schemes
    const schemeHeadings = page.locator("main").getByRole("heading", { level: 3 });
    await expect(schemeHeadings).toHaveCount(2);

    // 4. SELECT SCHEME
    const pmKisanDetailLink = page.locator("a[href='/schemes/PM_KISAN']").first();
    await pmKisanDetailLink.click();
    await expect(page).toHaveURL(/.*schemes\/PM_KISAN/);

    // 5. UNDERSTAND SCHEME
    await expect(page.locator("h1")).toContainText(/किसान/);
    const checkEligibilityCTA = page.locator("main").getByRole("link", { name: /पात्रता जाँचें/i }).first();
    await expect(checkEligibilityCTA).toBeVisible();

    // 6. CHECK ELIGIBILITY
    await checkEligibilityCTA.click();
    await expect(page).toHaveURL(/.*eligibility.*scheme=PM_KISAN/);

    // 7. PROVIDE FACTS
    // Verify citizen-readable question labels
    await expect(page.getByText(/कृषि योग्य भूमि/i)).toBeVisible();
    await expect(page.getByText(/भूमि का कुल क्षेत्रफल/i)).toBeVisible();

    // 8. REVIEW CLAIMS
    const proceedToClaimsBtn = page.getByRole("button", { name: /दावे पंजीकृत करें/i });
    await expect(proceedToClaimsBtn).toBeVisible();
    await proceedToClaimsBtn.click();

    // Verify claims view
    await expect(page.locator("[data-claim-type='family.owns_cultivable_land']")).toBeVisible();

    // 9. ADD SUPPORTING EVIDENCE
    const addEvidenceBtn = page.getByRole("button", { name: /साक्ष्य जोड़ें/i }).first();
    await expect(addEvidenceBtn).toBeVisible();
    await addEvidenceBtn.click();

    // Evidence modal
    const modalTitle = page.locator("#evidence-modal-title");
    await expect(modalTitle).toBeVisible();
    const attachBtn = page.getByRole("button", { name: /दस्तावेज़ जोड़ें|साक्ष्य संलग्न करें/i });
    await attachBtn.click();

    // 10. UNDERSTAND VERIFICATION STATUS
    await expect(page.locator("#evidence-modal-title")).toBeHidden();

    // 11. EVALUATE
    const evaluateBtn = page.getByRole("button", { name: /वैधानिक मूल्यांकन चलाएं/i });
    await expect(evaluateBtn).toBeVisible();
    await evaluateBtn.click();

    // 12. VIEW RESULT
    await expect(page.getByText(/वैधानिक पात्रता निर्णय/i)).toBeVisible();

    // 13. UNDERSTAND WHY
    const explainSection = page.locator("#explainability-section");
    await expect(explainSection).toBeVisible();
    await expect(explainSection.getByText(/यह परिणाम क्यों मिला/i)).toBeVisible();

    // 14. VIEW POLICY / SOURCE
    const viewPolicyLink = page.getByRole("link", { name: /नीति विवरण देखें/i }).first();
    await expect(viewPolicyLink).toBeVisible();

    // 15. OPTIONALLY VIEW ASSESSMENT HISTORY
    await page.goto("/audit-history");
    await expect(page).toHaveURL(/.*audit-history/);
    await expect(page.locator("h1")).toBeVisible();
  });

  // ---------------------------------------------------------------------------
  // JOURNEY 2: PM-KISAN in English
  // ---------------------------------------------------------------------------
  test("Journey 2: PM-KISAN in English (Full Citizen Entitlement Flow)", async ({ page }) => {
    // 1. HOME in English
    await page.goto("/");
    const langBtn = page.getByRole("button", { name: /Switch to English/i });
    if (await langBtn.isVisible()) {
      await langBtn.click();
    }
    await expect(page.locator("h1")).toContainText(/The Right Scheme for You/i);

    // 2. UNDERSTAND YOGYATAMITRA
    await expect(page.locator("#how-it-works-heading")).toContainText(/How YogyataMitra Works/i);

    // 3. BROWSE SCHEMES
    await page.goto("/schemes");
    const schemeHeadings = page.locator("main").getByRole("heading", { level: 3 });
    await expect(schemeHeadings).toHaveCount(2);

    // 4. SELECT SCHEME
    const pmKisanDetailLink = page.locator("a[href='/schemes/PM_KISAN']").first();
    await pmKisanDetailLink.click();
    await expect(page).toHaveURL(/.*schemes\/PM_KISAN/);

    // 5. UNDERSTAND SCHEME
    await expect(page.locator("h1")).toContainText(/Pradhan Mantri Kisan Samman Nidhi/i);
    const checkEligibilityCTA = page.locator("main").getByRole("link", { name: /Check.*eligibility/i }).first();
    await expect(checkEligibilityCTA).toBeVisible();

    // 6. CHECK ELIGIBILITY
    await checkEligibilityCTA.click();
    await expect(page).toHaveURL(/.*eligibility.*scheme=PM_KISAN/);

    // 7. PROVIDE FACTS
    await expect(page.getByText(/Does the farmer family own cultivable land/i)).toBeVisible();

    // 8. REVIEW CLAIMS
    const proceedToClaimsBtn = page.getByRole("button", { name: /Register Claims & Proceed/i });
    await expect(proceedToClaimsBtn).toBeVisible();
    await proceedToClaimsBtn.click();

    await expect(page.locator("[data-claim-type='family.owns_cultivable_land']")).toBeVisible();

    // 9. ADD SUPPORTING EVIDENCE
    const addEvidenceBtn = page.getByRole("button", { name: /Add Supporting Evidence/i }).first();
    await expect(addEvidenceBtn).toBeVisible();
    await addEvidenceBtn.click();

    const attachBtn = page.getByRole("button", { name: /Attach Document|Attach Artifact/i });
    await attachBtn.click();

    // 10. EVALUATE
    const evaluateBtn = page.getByRole("button", { name: /Execute Statutory Evaluation/i });
    await expect(evaluateBtn).toBeVisible();
    await evaluateBtn.click();

    // 11. VIEW RESULT & WHY
    await expect(page.getByText(/Statutory Entitlement Decision/i)).toBeVisible();
    const explainSection = page.locator("#explainability-section");
    await expect(explainSection).toBeVisible();

    // 12. OPTIONALLY VIEW ASSESSMENT HISTORY
    await page.goto("/audit-history");
    await expect(page).toHaveURL(/.*audit-history/);
  });

  // ---------------------------------------------------------------------------
  // JOURNEY 3: SSY in Hindi
  // ---------------------------------------------------------------------------
  test("Journey 3: SSY in Hindi (Sukanya Samriddhi Full Flow)", async ({ page }) => {
    // 1. HOME in Hindi
    await page.goto("/");
    const langBtn = page.getByRole("button", { name: /Switch to Hindi/i });
    if (await langBtn.isVisible()) {
      await langBtn.click();
    }

    // 2. BROWSE SCHEMES
    await page.goto("/schemes");
    await expect(page.getByText(/सुकन्या समृद्धि/i)).toBeVisible();

    // 3. SELECT SCHEME
    const ssyDetailLink = page.locator("a[href='/schemes/SSY']").first();
    await ssyDetailLink.click();
    await expect(page).toHaveURL(/.*schemes\/SSY/);

    // 4. UNDERSTAND SCHEME
    await expect(page.locator("h1")).toContainText(/सुकन्या समृद्धि/i);
    const checkEligibilityCTA = page.locator("main").getByRole("link", { name: /पात्रता जाँचें/i }).first();
    await expect(checkEligibilityCTA).toBeVisible();

    // 5. CHECK ELIGIBILITY
    await checkEligibilityCTA.click();
    await expect(page).toHaveURL(/.*eligibility.*scheme=SSY/);

    // 6. PROVIDE FACTS
    await expect(page.getByText(/बालिका की जन्म तिथि/i)).toBeVisible();
    await expect(page.getByText(/सक्रिय SSY खातों की संख्या/i)).toBeVisible();

    // 7. REVIEW CLAIMS
    const proceedBtn = page.getByRole("button", { name: /दावे पंजीकृत करें/i });
    await proceedBtn.click();

    // 8. EVALUATE
    const evaluateBtn = page.getByRole("button", { name: /वैधानिक मूल्यांकन चलाएं/i });
    await expect(evaluateBtn).toBeVisible();
    await evaluateBtn.click();

    // 9. RESULT & EXPLAINABILITY
    await expect(page.getByText(/वैधानिक पात्रता निर्णय/i)).toBeVisible();
    await expect(page.locator("#explainability-section")).toBeVisible();
  });

  // ---------------------------------------------------------------------------
  // JOURNEY 4: SSY in English
  // ---------------------------------------------------------------------------
  test("Journey 4: SSY in English (Sukanya Samriddhi Full Flow)", async ({ page }) => {
    // 1. HOME in English
    await page.goto("/");
    const langBtn = page.getByRole("button", { name: /Switch to English/i });
    if (await langBtn.isVisible()) {
      await langBtn.click();
    }

    // 2. BROWSE SCHEMES
    await page.goto("/schemes");
    await expect(page.getByText(/Sukanya Samriddhi/i)).toBeVisible();

    // 3. SELECT SCHEME
    const ssyDetailLink = page.locator("a[href='/schemes/SSY']").first();
    await ssyDetailLink.click();
    await expect(page).toHaveURL(/.*schemes\/SSY/);

    // 4. UNDERSTAND SCHEME
    await expect(page.locator("h1")).toContainText(/Sukanya Samriddhi/i);
    const checkEligibilityCTA = page.locator("main").getByRole("link", { name: /Check.*eligibility/i }).first();
    await expect(checkEligibilityCTA).toBeVisible();

    // 5. CHECK ELIGIBILITY
    await checkEligibilityCTA.click();
    await expect(page).toHaveURL(/.*eligibility.*scheme=SSY/);

    // 6. PROVIDE FACTS
    await expect(page.getByText(/Beneficiary Date of Birth/i)).toBeVisible();

    // 7. REVIEW CLAIMS
    const proceedBtn = page.getByRole("button", { name: /Register Claims & Proceed/i });
    await proceedBtn.click();

    // 8. EVALUATE
    const evaluateBtn = page.getByRole("button", { name: /Execute Statutory Evaluation/i });
    await expect(evaluateBtn).toBeVisible();
    await evaluateBtn.click();

    // 9. RESULT & EXPLAINABILITY
    await expect(page.getByText(/Statutory Entitlement Decision/i)).toBeVisible();
    await expect(page.locator("#explainability-section")).toBeVisible();
  });
});
