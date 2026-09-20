import { test, expect } from "@playwright/test";

const mockCandidate = {
  id: "cand-uuid-12345",
  scheme_id: "scheme-uuid-pmkisan",
  scheme_code: "PM_KISAN",
  scheme_name: "PM-KISAN Samman Nidhi",
  title: "Mandatory Aadhaar Seeding and e-KYC Protocol",
  candidate_type: "PROCEDURAL_REQUIREMENT",
  candidate_text_en: "All eligible landholder farmer families must complete biometric or OTP-based e-KYC.",
  candidate_text_hi: "सभी पात्र भूमिधारक किसान परिवारों को बायोमेट्रिक या ओटीपी आधारित ई-केवाईसी पूरा करना होगा।",
  normalized_concept: "pm_kisan_mandatory_ekyc_seeding",
  source_url: "https://pmkisan.gov.in/Documents/OperationalGuidelines_2024_Update.pdf",
  source_title: "PM-KISAN Operational Guidelines",
  source_publisher: "Department of Agriculture & Farmers Welfare",
  source_document_identifier: "DOA/PMK/2024/CIR-08",
  source_publication_date: "2024-01-15T00:00:00Z",
  source_effective_date: "2024-02-01T00:00:00Z",
  effective_date_status: "VERIFIED_FUTURE_EFFECTIVE",
  provenance_status: "VERIFIED_OFFICIAL",
  extraction_confidence: 0.95,
  discovery_provider: "MOCK_DISCOVERY_PROVIDER",
  duplicate_status: "UNIQUE",
  conflict_detected: false,
  review_status: "PENDING_REVIEW",
  created_at: "2024-02-15T10:30:00Z",
  updated_at: "2024-02-15T10:30:00Z",
  review_events: [
    {
      id: "rev-evt-1",
      candidate_id: "cand-uuid-12345",
      action: "DISCOVERY_INGESTED",
      from_status: "PENDING_REVIEW",
      to_status: "PENDING_REVIEW",
      reviewer_id: "system",
      reviewer_role: "SYSTEM",
      reason: "Automated official ingestion from pmkisan.gov.in",
      created_at: "2024-02-15T10:30:00Z",
    },
  ],
};

const mockMetrics = {
  total_candidates: 1,
  pending_review: 1,
  in_review: 0,
  needs_clarification: 0,
  approved: 0,
  rejected: 0,
  archived: 0,
  conflict_detected: 0,
};

test.describe("Phase 15: AI-Assisted Policy Discovery & Human Approval E2E", () => {
  test.beforeEach(async ({ page }) => {
    // Intercept officer authentication and policy discovery API endpoints ONLY
    await page.route("**/api/v1/officer/auth/login", async (route) => {
      const postData = route.request().postDataJSON() || {};
      const isSupervisor = postData.email?.includes("supervisor");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: isSupervisor ? "mock-jwt-supervisor-token" : "mock-jwt-officer-token",
          token_type: "bearer",
          officer_name: isSupervisor ? "Supervisor Verma" : "Inspector Rajesh",
          officer_role: isSupervisor ? "SUPERVISOR" : "OFFICER",
          designation: isSupervisor ? "Welfare Supervisor" : "Verification Officer",
          department: "Social Welfare Department",
          demo_environment: true,
          environment_notice: "Local Demonstration Mode",
        }),
      });
    });

    await page.route("**/api/v1/officer/auth/me", async (route) => {
      const authHeader = route.request().headers()["authorization"] || "";
      const isSupervisor = authHeader.includes("supervisor");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          email: isSupervisor ? "supervisor@yogyatamitra.local" : "officer@yogyatamitra.local",
          role: isSupervisor ? "SUPERVISOR" : "OFFICER",
          name: isSupervisor ? "Supervisor Verma" : "Inspector Rajesh",
          designation: isSupervisor ? "Welfare Supervisor" : "Verification Officer",
          department: "Social Welfare Department",
        }),
      });
    });

    await page.route("**/api/v1/officer/policy-discovery/candidates?*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          candidates: [mockCandidate],
          metrics: mockMetrics,
        }),
      });
    });

    await page.route("**/api/v1/officer/policy-discovery/candidates/cand-uuid-12345/history", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockCandidate.review_events),
      });
    });

    await page.route("**/api/v1/officer/policy-discovery/candidates/cand-uuid-12345", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockCandidate),
      });
    });

    await page.route("**/api/v1/officer/queue*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [],
          total: 0,
          metrics: {
            total_cases: 0,
            pending_cases: 0,
            in_review_cases: 0,
            escalated_cases: 0,
            completed_cases: 0,
          },
        }),
      });
    });
  });

  test("1. Citizen portal navigation is strictly isolated and contains zero policy discovery links", async ({
    page,
  }) => {
    await page.goto("/");

    // Main navigation check
    const nav = page.getByRole("navigation", { name: /Main Navigation|मुख्य नेविगेशन/i });
    await expect(nav).toBeVisible();

    // Verify zero officer or policy discovery exposure to citizens
    await expect(nav.getByText(/Policy Discovery/i)).toHaveCount(0);
    await expect(nav.getByText(/नीति खोज/i)).toHaveCount(0);
    await expect(nav.getByText(/Officer/i)).toHaveCount(0);
  });

  test("2. Unauthenticated navigation to /officer/policy-discovery redirects to /officer/login", async ({
    page,
  }) => {
    // Clear any existing session
    await page.goto("/officer/login");
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    // Attempt direct deep link
    await page.goto("/officer/policy-discovery");

    // Must be redirected to officer login
    await expect(page).toHaveURL(/.*officer\/login/, { timeout: 10000 });
    await expect(page.getByText(/DEVELOPMENT OFFICER LOGIN/i)).toBeVisible();
  });

  test("3. Officer can login and access Policy Discovery queue with AI advisory banner and metrics", async ({
    page,
  }) => {
    await page.goto("/officer/login");

    // Quick fill for Officer
    await page.getByRole("button", { name: /Verification Officer/i }).click();
    await page.getByRole("button", { name: /Sign In to Verification Portal/i }).click();

    // Redirected to officer queue
    await expect(page).toHaveURL(/.*officer\/queue/, { timeout: 15000 });

    // Click Policy Discovery navigation link in officer topbar
    const discoveryLink = page.getByRole("link", { name: /Policy Discovery/i }).first();
    await expect(discoveryLink).toBeVisible();
    await discoveryLink.click();

    // Confirm navigation to /officer/policy-discovery
    await expect(page).toHaveURL(/.*officer\/policy-discovery/, { timeout: 10000 });

    // Header & Advisory Warning Banner Check
    await expect(page.getByRole("heading", { name: /AI POLICY DISCOVERY & HUMAN APPROVAL/i })).toBeVisible();
    await expect(
      page.getByText(/ADVISORY INTELLIGENCE/i).first()
    ).toBeVisible();
    await expect(
      page.getByText(/All candidates are strictly non-executable data objects awaiting human verification/i)
    ).toBeVisible();

    // Metrics Cards Check
    await expect(page.getByText("Total Candidates")).toBeVisible();
    await expect(page.getByText("Pending Review").first()).toBeVisible();

    // Search and filters
    await expect(page.getByPlaceholder("Search by candidate title, concept, or source document...")).toBeVisible();
  });

  test("4. Candidate dossier renders 3-way separation and non-statutory legal disclaimer", async ({
    page,
  }) => {
    await page.goto("/officer/login");
    await page.getByRole("button", { name: /Verification Officer/i }).click();
    await page.getByRole("button", { name: /Sign In to Verification Portal/i }).click();
    await expect(page).toHaveURL(/.*officer\/queue/, { timeout: 15000 });

    // Navigate to Policy Discovery via top link
    const discoveryLink = page.getByRole("link", { name: /Policy Discovery/i }).first();
    await expect(discoveryLink).toBeVisible();
    await discoveryLink.click();
    await expect(page).toHaveURL(/.*officer\/policy-discovery/, { timeout: 10000 });

    // Check candidate card title
    await expect(page.getByText("Mandatory Aadhaar Seeding and e-KYC Protocol")).toBeVisible({ timeout: 10000 });

    // Click Inspect & Review button
    const viewButton = page.getByRole("link", { name: /Inspect & Review/i }).first();
    await expect(viewButton).toBeVisible();
    await viewButton.click();

    // Check Candidate Dossier Page URL
    await expect(page).toHaveURL(/.*officer\/policy-discovery\/cand-uuid-12345/, { timeout: 10000 });

    // Non-negotiable Advisory Warning Banner
    await expect(
      page.getByText(/AI ADVISORY DISCOVERY • HUMAN APPROVAL REQUIRED/i)
    ).toBeVisible();
    await expect(
      page.getByText(/It does NOT enact law, activate a statutory rule, or alter existing deterministic policies/i)
    ).toBeVisible();

    // Section A: Source Text & Provenance
    await expect(page.getByText(/Official Government Source & Provenance/i)).toBeVisible();

    // Section B: AI Proposed Entitlement Concept
    await expect(page.getByText(/AI Suggestion \(Advisory Extraction\)/i)).toBeVisible();

    // Section D: Authorized Review Determination Panel
    await expect(page.getByRole("heading", { name: /Authorized Review Determination/i })).toBeVisible();
    await expect(page.getByText(/Start Review & Transition to IN_REVIEW/i)).toBeVisible();
    await expect(page.getByText(/Mandatory Justification Reason/i)).toBeVisible();

    // Section E: Append-Only Review Audit Trail
    await expect(page.getByText(/Append-Only Review Audit Trail/i)).toBeVisible();
  });

  test("5. Supervisor can view policy discovery with supervisor badge", async ({
    page,
  }) => {
    await page.goto("/officer/login");
    await page.getByRole("button", { name: /Welfare Supervisor/i }).click();
    await page.getByRole("button", { name: /Sign In to Verification Portal/i }).click();
    await expect(page).toHaveURL(/.*officer\/queue/, { timeout: 15000 });

    // Navigate to Policy Discovery via top link
    const discoveryLink = page.getByRole("link", { name: /Policy Discovery/i }).first();
    await expect(discoveryLink).toBeVisible();
    await discoveryLink.click();
    await expect(page).toHaveURL(/.*officer\/policy-discovery/, { timeout: 10000 });

    // Verify Supervisor badge
    await expect(page.getByText("SUPERVISOR", { exact: true })).toBeVisible();
  });
});
