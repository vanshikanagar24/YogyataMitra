import { test, expect } from "@playwright/test";

const mockApprovedCandidate = {
  id: "cand-uuid-12345",
  scheme_id: "scheme-uuid-pmkisan",
  scheme_code: "PM_KISAN",
  scheme_name: "PM-KISAN Samman Nidhi",
  title: "Mandatory Aadhaar Seeding and e-KYC Protocol",
  candidate_type: "PROCEDURAL_REQUIREMENT",
  candidate_text_en: "All eligible landholder farmer families must complete biometric or OTP-based e-KYC.",
  candidate_text_hi: "सभी पात्र भूमिधारक किसान परिवारों को बायोमेट्रिक या ओटीपी आधारित ई-केवाईसी पूरा करना होगा।",
  source_url: "https://pmkisan.gov.in/Documents/OperationalGuidelines_2024_Update.pdf",
  source_publisher: "Department of Agriculture & Farmers Welfare",
  source_document_identifier: "DOA/PMK/2024/CIR-08",
  source_effective_date: "2024-02-01T00:00:00Z",
  source_excerpt: "Section 3.2: Mandatory biometric verification",
  review_status: "APPROVED",
};

let currentDraftState: any = {
  id: "draft-uuid-phase16",
  scheme_code: "PM_KISAN",
  policy_title: "PM-KISAN 2026 Enhanced Land Verification",
  description: "Statutory update derived from approved candidate.",
  source_candidate_id: "cand-uuid-12345",
  effective_from: "2026-08-01",
  effective_to: null,
  author_id: "officer.author@yogyatamitra.gov.in",
  author_role: "OFFICER",
  reviewer_id: null,
  reviewer_role: null,
  reviewer_reason: null,
  current_revision: 1,
  lifecycle_status: "DRAFT",
  validation_status: "NOT_VALIDATED",
  test_status: "NOT_TESTED",
  compiled_rule_hash: null,
  authored_rules_json: {
    schema_version: "2.0.0",
    root_rule_id: "land_ownership_check",
    rules: [
      {
        rule_id: "land_ownership_check",
        node_type: "comparison",
        field_path: "land_details.total_operational_holding_hectares",
        operator: "GREATER_THAN",
        expected_value: 0.0,
        description_en: "Farmer family must own cultivable agricultural land",
        description_hi: "किसान परिवार के पास कृषि योग्य भूमि होनी चाहिए",
      },
    ],
  },
  tests: [],
  revisions: [
    {
      id: "rev-1",
      revision_number: 1,
      author_id: "officer.author@yogyatamitra.gov.in",
      author_role: "OFFICER",
      change_summary: "Initial draft created from approved candidate.",
      new_rule_hash: null,
      created_at: "2026-09-20T10:00:00Z",
    },
  ],
  audit_events: [
    {
      id: "evt-1",
      actor_identity: "officer.author@yogyatamitra.gov.in",
      actor_role: "OFFICER",
      action: "CREATE_DRAFT",
      previous_status: null,
      new_status: "DRAFT",
      reason: "Initial draft created from approved candidate.",
      created_at: "2026-09-20T10:00:00Z",
    },
  ],
  created_at: "2026-09-20T10:00:00Z",
  updated_at: "2026-09-20T10:00:00Z",
};

test.describe("Phase 16: Controlled Policy Authoring & Deterministic Compilation E2E", () => {
  test.beforeEach(async ({ page }) => {
    // Reset draft state for test runs
    currentDraftState.lifecycle_status = "DRAFT";
    currentDraftState.validation_status = "NOT_VALIDATED";
    currentDraftState.test_status = "NOT_TESTED";
    currentDraftState.compiled_rule_hash = null;
    currentDraftState.reviewer_id = null;
    currentDraftState.reviewer_role = null;
    currentDraftState.reviewer_reason = null;
    currentDraftState.tests = [];

    // Route authentication
    await page.route("**/api/v1/officer/auth/login", async (route) => {
      const postData = route.request().postDataJSON() || {};
      const isSupervisor = postData.email?.includes("supervisor");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: isSupervisor ? "mock-jwt-supervisor-token" : "mock-jwt-officer-token",
          token_type: "bearer",
          officer_name: isSupervisor ? "Supervisor Sharma" : "Officer Rajesh",
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
          email: isSupervisor ? "supervisor.reviewer@yogyatamitra.gov.in" : "officer.author@yogyatamitra.gov.in",
          role: isSupervisor ? "SUPERVISOR" : "OFFICER",
          name: isSupervisor ? "Supervisor Sharma" : "Officer Rajesh",
          designation: isSupervisor ? "Welfare Supervisor" : "Verification Officer",
          department: "Social Welfare Department",
        }),
      });
    });

    // Approved candidates for import
    await page.route("**/api/v1/officer/policy-discovery/candidates?*status=APPROVED*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          candidates: [mockApprovedCandidate],
          metrics: { total_candidates: 1, approved: 1 },
        }),
      });
    });

    // Drafts listing
    await page.route("**/api/v1/officer/policy-authoring/drafts?*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          drafts: [
            {
              id: currentDraftState.id,
              scheme_code: currentDraftState.scheme_code,
              policy_title: currentDraftState.policy_title,
              description: currentDraftState.description,
              lifecycle_status: currentDraftState.lifecycle_status,
              validation_status: currentDraftState.validation_status,
              test_status: currentDraftState.test_status,
              compiled_rule_hash: currentDraftState.compiled_rule_hash,
              author_id: currentDraftState.author_id,
              current_revision: currentDraftState.current_revision,
              created_at: currentDraftState.created_at,
              updated_at: currentDraftState.updated_at,
            },
          ],
          metrics: {
            total_drafts: 1,
            draft_status_count: currentDraftState.lifecycle_status === "DRAFT" ? 1 : 0,
            authoring: currentDraftState.lifecycle_status === "AUTHORING" ? 1 : 0,
            validating: currentDraftState.lifecycle_status === "VALIDATING" ? 1 : 0,
            testing: currentDraftState.lifecycle_status === "TESTING" ? 1 : 0,
            pending_review: currentDraftState.lifecycle_status === "PENDING_REVIEW" ? 1 : 0,
            in_review: currentDraftState.lifecycle_status === "IN_REVIEW" ? 1 : 0,
            needs_clarification: currentDraftState.lifecycle_status === "NEEDS_CLARIFICATION" ? 1 : 0,
            staged: currentDraftState.lifecycle_status === "STAGED" ? 1 : 0,
            archived: currentDraftState.lifecycle_status === "ARCHIVED" ? 1 : 0,
          },
        }),
      });
    });

    // Create draft
    await page.route("**/api/v1/officer/policy-authoring/drafts", async (route) => {
      if (route.request().method() === "POST") {
        const body = route.request().postDataJSON() || {};
        currentDraftState.policy_title = body.policy_title || currentDraftState.policy_title;
        currentDraftState.scheme_code = body.scheme_code || currentDraftState.scheme_code;
        currentDraftState.description = body.description || currentDraftState.description;
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(currentDraftState),
        });
      }
    });

    // Draft detail
    await page.route(`**/api/v1/officer/policy-authoring/drafts/${currentDraftState.id}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(currentDraftState),
      });
    });

    // Update rules
    await page.route(`**/api/v1/officer/policy-authoring/drafts/${currentDraftState.id}/rules`, async (route) => {
      const body = route.request().postDataJSON() || {};
      currentDraftState.authored_rules_json = body.rules_json || currentDraftState.authored_rules_json;
      currentDraftState.current_revision += 1;
      currentDraftState.validation_status = "NOT_VALIDATED";
      currentDraftState.test_status = "NOT_TESTED";
      currentDraftState.compiled_rule_hash = null;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(currentDraftState),
      });
    });

    // Validate
    await page.route(`**/api/v1/officer/policy-authoring/drafts/${currentDraftState.id}/validate`, async (route) => {
      currentDraftState.validation_status = "VALID";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          is_valid: true,
          errors: [],
          warnings: [],
          rule_count: 1,
          referenced_fields: ["land_details.total_operational_holding_hectares"],
          validated_at: "2026-09-20T10:05:00Z",
        }),
      });
    });

    // Compile
    await page.route(`**/api/v1/officer/policy-authoring/drafts/${currentDraftState.id}/compile`, async (route) => {
      currentDraftState.compiled_rule_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          is_compiled: true,
          rule_hash: currentDraftState.compiled_rule_hash,
          rule_count: 1,
          compiled_ruleset: currentDraftState.authored_rules_json,
          canonical_representation: JSON.stringify(currentDraftState.authored_rules_json),
          compiled_at: "2026-09-20T10:06:00Z",
        }),
      });
    });

    // Tests list and manual create
    await page.route(`**/api/v1/officer/policy-authoring/drafts/${currentDraftState.id}/tests`, async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(currentDraftState.tests || []),
        });
      } else if (route.request().method() === "POST") {
        const postData = route.request().postDataJSON() || {};
        const newTest = {
          id: `test-human-${Date.now()}`,
          name: postData.name || "Human Authored Test",
          description: postData.description || null,
          test_type: "MANUAL_HUMAN",
          facts_json: postData.facts_json || {},
          expected_result: postData.expected_result || "ELIGIBLE",
          status: "NOT_TESTED",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        currentDraftState.tests.push(newTest);
        currentDraftState.test_status = "NOT_TESTED";
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(newTest),
        });
      } else {
        await route.continue();
      }
    });

    // Auto-generate tests (support both /generate-tests and /tests/auto-generate)
    const handleAutoGen = async (route: any) => {
      const generatedTest = {
        id: "test-auto-1",
        name: "Boundary: land_details.total_operational_holding_hectares GT 0.0",
        description: "Auto-generated boundary value test",
        test_type: "BOUNDARY_VALUE",
        facts_json: { land_details: { total_operational_holding_hectares: 0.1 } },
        expected_result: "ELIGIBLE",
        status: "NOT_TESTED",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      currentDraftState.tests = [generatedTest];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([generatedTest]),
      });
    };
    await page.route(`**/api/v1/officer/policy-authoring/drafts/${currentDraftState.id}/generate-tests`, handleAutoGen);
    await page.route(`**/api/v1/officer/policy-authoring/drafts/${currentDraftState.id}/tests/auto-generate`, handleAutoGen);

    // Run tests
    await page.route(`**/api/v1/officer/policy-authoring/drafts/${currentDraftState.id}/test`, async (route) => {
      currentDraftState.test_status = "PASSED";
      if (currentDraftState.tests && currentDraftState.tests.length > 0) {
        currentDraftState.tests.forEach((t: any) => {
          t.status = "PASSED";
          t.actual_result = t.expected_result;
        });
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          total_tests: currentDraftState.tests.length || 1,
          passed_tests: currentDraftState.tests.length || 1,
          failed_tests: 0,
          pending_tests: 0,
          test_status: "PASSED",
          all_passed: true,
          executed_at: "2026-09-20T10:07:00Z",
          results: currentDraftState.tests,
        }),
      });
    });

    // Diff against baseline
    await page.route(`**/api/v1/officer/policy-authoring/drafts/${currentDraftState.id}/diff`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          parent_version_code: "v3.0-2023",
          parent_rule_hash: "7ef27f5c071a8fa4fff2d95c6c34cda5211b76d16ddb0e610a312ea61cf669d6",
          draft_rule_hash: currentDraftState.compiled_rule_hash || "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
          added_rules: [],
          removed_rules: [],
          modified_rules: [
            {
              rule_id: "land_ownership_check",
              diff_type: "MODIFIED",
              description_en: "Farmer family must own cultivable agricultural land",
              description_hi: "किसान परिवार के पास कृषि योग्य भूमि होनी चाहिए",
              old_value: "GREATER_THAN_OR_EQUAL",
              new_value: "GREATER_THAN",
              human_explanation: "Operational holding threshold changed from GREATER_THAN_OR_EQUAL to GREATER_THAN",
            },
          ],
          metadata_changes: [],
          human_summary: "1 rule modified, 0 added, 0 removed compared to v3.0-2023.",
        }),
      });
    });

    // Lifecycle transitions
    await page.route(`**/api/v1/officer/policy-authoring/drafts/${currentDraftState.id}/transitions`, async (route) => {
      const body = route.request().postDataJSON() || {};
      const action = body.action;
      const prevStatus = currentDraftState.lifecycle_status;

      if (action === "START_AUTHORING") currentDraftState.lifecycle_status = "AUTHORING";
      else if (action === "RUN_VALIDATION") currentDraftState.lifecycle_status = "VALIDATING";
      else if (action === "PROCEED_TO_TESTING") currentDraftState.lifecycle_status = "TESTING";
      else if (action === "SUBMIT_FOR_REVIEW") currentDraftState.lifecycle_status = "PENDING_REVIEW";
      else if (action === "START_REVIEW") currentDraftState.lifecycle_status = "IN_REVIEW";
      else if (action === "STAGE") {
        currentDraftState.lifecycle_status = "STAGED";
        currentDraftState.reviewer_id = "supervisor.reviewer@yogyatamitra.gov.in";
        currentDraftState.reviewer_role = "SUPERVISOR";
        currentDraftState.reviewer_reason = body.reason || "Approved and staged for official release cycle.";
      }

      currentDraftState.audit_events.push({
        id: `evt-${Date.now()}`,
        actor_identity: action === "STAGE" || action === "START_REVIEW" ? "supervisor.reviewer@yogyatamitra.gov.in" : "officer.author@yogyatamitra.gov.in",
        actor_role: action === "STAGE" || action === "START_REVIEW" ? "SUPERVISOR" : "OFFICER",
        action: action,
        previous_status: prevStatus,
        new_status: currentDraftState.lifecycle_status,
        reason: body.reason || `Transition via ${action}`,
        created_at: new Date().toISOString(),
      });

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(currentDraftState),
      });
    });

    // Verification queue fallback
    await page.route("**/api/v1/officer/queue*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0, metrics: {} }),
      });
    });
  });

  test("1. Citizen portal is strictly isolated: zero authoring or internal officer links", async ({
    page,
  }) => {
    await page.goto("/");
    const nav = page.getByRole("navigation", { name: /Main Navigation|मुख्य नेविगेशन/i });
    await expect(nav).toBeVisible();
    await expect(nav.getByText(/Policy Authoring/i)).toHaveCount(0);
    await expect(nav.getByText(/नीति निर्माण/i)).toHaveCount(0);
    await expect(nav.getByText(/Drafts/i)).toHaveCount(0);
  });

  test("2. Unauthenticated navigation to /officer/policy-authoring redirects to /officer/login", async ({
    page,
  }) => {
    await page.goto("/officer/login");
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    await page.goto("/officer/policy-authoring");
    await expect(page).toHaveURL(/.*officer\/login/, { timeout: 10000 });
    await expect(page.getByText(/DEVELOPMENT OFFICER LOGIN/i)).toBeVisible();
  });

  test("3. Complete 22-step Lifecycle: Create Draft -> Import Candidate -> Visual Rule Edit -> Validate -> Compile -> Auto-Test -> Run Tests -> Submit -> Supervisor Diff Review -> Stage -> Verify STAGED Isolation", async ({
    page,
  }) => {
    // -------------------------------------------------------------
    // Step 1: Login as Verification Officer
    // -------------------------------------------------------------
    await page.goto("/officer/login");
    await page.getByRole("button", { name: /Verification Officer/i }).click();
    await page.getByRole("button", { name: /Sign In to Verification Portal/i }).click();
    await expect(page).toHaveURL(/.*officer\/queue/, { timeout: 15000 });

    // -------------------------------------------------------------
    // Step 2: Navigate to Policy Authoring Workbench
    // -------------------------------------------------------------
    const authoringLink = page.getByRole("link", { name: /Policy Authoring/i }).first();
    await expect(authoringLink).toBeVisible();
    await authoringLink.click();
    await expect(page).toHaveURL(/.*officer\/policy-authoring/, { timeout: 10000 });

    // Verify STAGED IS NOT ACTIVE banner
    await expect(page.getByText(/CONTROLLED POLICY AUTHORING/i)).toBeVisible();
    await expect(page.getByText(/STAGED IS NOT ACTIVE/i).first()).toBeVisible();

    // -------------------------------------------------------------
    // Step 3 & 4: Create Draft via Candidate Import
    // -------------------------------------------------------------
    const newDraftBtn = page.getByRole("link", { name: /Create New Draft/i });
    await expect(newDraftBtn).toBeVisible();
    await newDraftBtn.click();
    await expect(page).toHaveURL(/.*officer\/policy-authoring\/new/, { timeout: 10000 });

    // Switch to Mode 2: Import from Approved Candidate
    const importModeBtn = page.getByRole("button", { name: /Derive From Approved Candidate/i });
    await expect(importModeBtn).toBeVisible();
    await importModeBtn.click();

    // Select candidate
    const candidateCard = page.getByText("Mandatory Aadhaar Seeding and e-KYC Protocol");
    await expect(candidateCard).toBeVisible();
    await candidateCard.click();

    // Verify candidate data imported into form
    const titleInput = page.getByPlaceholder(/PM-KISAN 2026 Revised Landholding/i);
    await expect(titleInput).toHaveValue("Mandatory Aadhaar Seeding and e-KYC Protocol");

    // Submit draft creation
    const submitBtn = page.getByRole("button", { name: /Create & Open Rule Builder/i });
    await expect(submitBtn).toBeVisible();
    await submitBtn.click();

    // -------------------------------------------------------------
    // Step 5: Draft Dossier Overview & Rule Builder
    // -------------------------------------------------------------
    await expect(page).toHaveURL(/.*officer\/policy-authoring\/draft-uuid-phase16/, { timeout: 15000 });
    await expect(page.getByText(/Mandatory Aadhaar Seeding and e-KYC Protocol/i).first()).toBeVisible();

    // Click "Rule Builder" tab
    const ruleBuilderTab = page.getByRole("link", { name: /Rule Builder/i }).first();
    await expect(ruleBuilderTab).toBeVisible();
    await ruleBuilderTab.click();
    await expect(page).toHaveURL(/.*draft-uuid-phase16\/rules/, { timeout: 10000 });

    // Verify Visual Rule Builder interface
    await expect(page.getByText(/Rule Builder/i).first()).toBeVisible();

    // Save authored rules
    const saveRulesBtn = page.getByRole("button", { name: /Save Rules/i });
    await expect(saveRulesBtn).toBeVisible();
    await saveRulesBtn.click();

    // Return to draft dossier
    await page.goto("/officer/policy-authoring/draft-uuid-phase16");

    // -------------------------------------------------------------
    // Step 6 & 7: Validate & Compile AST
    // -------------------------------------------------------------
    // Navigate to AST Validation tab
    const valNavBtn = page.getByRole("link", { name: /AST Validation/i }).first();
    await valNavBtn.click();
    await expect(page).toHaveURL(/.*draft-uuid-phase16\/validation/, { timeout: 10000 });

    // Trigger Static AST Validation
    const runValBtn = page.getByRole("button", { name: /Run Static Validation/i });
    await expect(runValBtn).toBeVisible();
    await runValBtn.click();
    await expect(page.getByText(/Zero Static Invariant Violations Detected/i)).toBeVisible();

    // Return to Dossier to Compile & Hash
    await page.goto("/officer/policy-authoring/draft-uuid-phase16");
    const compileBtn = page.getByRole("button", { name: /Compile & Hash/i });
    await expect(compileBtn).toBeVisible();
    await compileBtn.click();
    await expect(page.getByText(/Policy successfully compiled/i)).toBeVisible();

    // -------------------------------------------------------------
    // Step 8 & 9: Generate & Run Tests
    // -------------------------------------------------------------
    const testsNavBtn = page.getByRole("link", { name: /Test Suite & Regression/i }).first();
    await testsNavBtn.click();
    await expect(page).toHaveURL(/.*draft-uuid-phase16\/tests/, { timeout: 10000 });

    // Auto-generate test cases
    const autoGenBtn = page.getByRole("button", { name: /Auto-Generate Tests/i }).first();
    await expect(autoGenBtn).toBeVisible();
    await autoGenBtn.click();
    await expect(page.getByText(/Boundary: land_details.total_operational_holding_hectares/i)).toBeVisible();

    // Run test suite
    const runTestsBtn = page.getByRole("button", { name: /Run All Tests/i }).first();
    await expect(runTestsBtn).toBeVisible();
    await runTestsBtn.click();
    await expect(page.getByText(/Test run complete: 1 passed/i)).toBeVisible();
    await expect(page.getByText(/PASSED/i).first()).toBeVisible();

    // -------------------------------------------------------------
    // Step 10: Submit for Review
    // -------------------------------------------------------------
    await page.goto("/officer/policy-authoring/draft-uuid-phase16/review");
    await expect(page.getByText(/Select Lifecycle Transition Action/i)).toBeVisible();
    const submitReviewRadio = page.locator('input[value="SUBMIT_FOR_REVIEW"]');
    await submitReviewRadio.check();
    const reviewReasonInput = page.getByPlaceholder(/Enter detailed statutory, legislative, or technical rationale/i);
    await reviewReasonInput.fill("All AST static validations and unit tests passed cleanly.");
    await page.getByRole("button", { name: /Commit Lifecycle Determination/i }).click();
    await expect(page.getByText(/completed successfully/i)).toBeVisible();

    // -------------------------------------------------------------
    // Step 11: Switch Role -> Login as Supervisor
    // -------------------------------------------------------------
    await page.evaluate(() => {
      localStorage.clear();
    });
    await page.goto("/officer/login");
    await page.getByRole("button", { name: /Welfare Supervisor/i }).click();
    await page.getByRole("button", { name: /Sign In to Verification Portal/i }).click();
    await expect(page).toHaveURL(/.*officer\/queue/, { timeout: 15000 });

    // -------------------------------------------------------------
    // Step 12: Inspect Semantic Diff
    // -------------------------------------------------------------
    await page.goto("/officer/policy-authoring/draft-uuid-phase16/diff");
    await expect(page.getByText(/Visual Policy Differential/i).first()).toBeVisible();
    await expect(page.getByText(/v3.0-2023/i).first()).toBeVisible();
    await expect(page.getByText(/Rules Modified/i).first()).toBeVisible();

    // -------------------------------------------------------------
    // Step 13 & 14: Supervisor Stages Draft & Verifies STAGED status
    // -------------------------------------------------------------
    await page.goto("/officer/policy-authoring/draft-uuid-phase16/review");
    await expect(page.getByText(/Supervisory Review/i).first()).toBeVisible();

    // Select Stage decision
    const stageRadio = page.locator('input[value="STAGE"]');
    await stageRadio.check();

    // Fill mandatory statutory rationale
    const rationaleInput = page.getByPlaceholder(/Enter detailed statutory, legislative, or technical rationale/i);
    await rationaleInput.fill("Statutory requirements satisfied. Draft compiled and staged for upcoming release cycle.");

    // Submit staging determination
    const submitStageBtn = page.getByRole("button", { name: /Commit Lifecycle Determination/i });
    await expect(submitStageBtn).toBeVisible();
    await submitStageBtn.click();

    // Confirm STAGED status
    await page.goto("/officer/policy-authoring/draft-uuid-phase16");
    await expect(page.getByText(/STAGED/i).first()).toBeVisible();
    await expect(page.getByText(/STAGED IS NOT ACTIVE/i).first()).toBeVisible();

    // -------------------------------------------------------------
    // Step 15 to 18: Verify STAGED Quarantined Invariants
    // -------------------------------------------------------------
    // Check audit trail record exists
    await expect(page.getByText(/Application-level append-only audit trail protected by authorization/i).first()).toBeVisible();

    // Return to authoring queue and verify STAGED status badge
    await page.goto("/officer/policy-authoring");
    await expect(page.getByText(/STAGED/i).first()).toBeVisible();
  });
});
