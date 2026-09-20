import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import PolicyAuthoringQueuePage from "../../src/app/officer/policy-authoring/page";
import NewPolicyDraftPage from "../../src/app/officer/policy-authoring/new/page";
import PolicyDraftDossierPage from "../../src/app/officer/policy-authoring/[draftId]/page";
import PolicyRuleBuilderPage from "../../src/app/officer/policy-authoring/[draftId]/rules/page";
import PolicyValidationPage from "../../src/app/officer/policy-authoring/[draftId]/validation/page";
import PolicyTestSuitePage from "../../src/app/officer/policy-authoring/[draftId]/tests/page";
import PolicyDiffViewerPage from "../../src/app/officer/policy-authoring/[draftId]/diff/page";
import PolicyReviewPage from "../../src/app/officer/policy-authoring/[draftId]/review/page";
import { OfficerAuthProvider } from "../../src/context/OfficerAuthContext";
import { policyAuthoringApi } from "../../src/api/policyAuthoring";
import {
  PolicyDraftDetail,
  PolicyDraftListResponse,
  ValidationReportResponse,
  PolicyDiffResponse,
  TestRunSummaryResponse,
} from "../../src/types/policyAuthoring";

// Mock router
const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: jest.fn(),
  }),
  usePathname: () => "/officer/policy-authoring/draft-uuid-12345",
  useParams: () => ({ draftId: "draft-uuid-12345" }),
}));

// Mock officerApi
jest.mock("../../src/api/officer", () => ({
  officerApi: {
    getProfile: jest.fn().mockResolvedValue({
      id: "usr-supervisor-01",
      email: "supervisor@yogyatamitra.gov.in",
      role: "SUPERVISOR",
      name: "Senior Supervisor Sharma",
    }),
  },
  getAuthHeaders: jest.fn().mockReturnValue({ Authorization: "Bearer mock-officer-jwt" }),
}));

// Mock policyAuthoringApi
jest.mock("../../src/api/policyAuthoring", () => ({
  policyAuthoringApi: {
    listDrafts: jest.fn(),
    getDraft: jest.fn(),
    createDraft: jest.fn(),
    updateDraft: jest.fn(),
    importCandidate: jest.fn(),
    validateDraft: jest.fn(),
    compileDraft: jest.fn(),
    generateTests: jest.fn(),
    listTests: jest.fn(),
    addTest: jest.fn(),
    runTests: jest.fn(),
    getDiff: jest.fn(),
    transitionDraft: jest.fn(),
    getHistory: jest.fn(),
  },
}));

// Mock officer profile in localStorage
const mockLocalStorage = (() => {
  let store: Record<string, string> = {
    yogyatamitra_officer_token: "mock-officer-jwt",
    yogyatamitra_officer_profile: JSON.stringify({
      id: "usr-supervisor-01",
      email: "supervisor@yogyatamitra.gov.in",
      role: "SUPERVISOR",
      name: "Senior Supervisor Sharma",
    }),
  };
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();
Object.defineProperty(window, "localStorage", { value: mockLocalStorage });

// Sample Mock Data
const mockDraftDetail: PolicyDraftDetail = {
  id: "draft-uuid-12345",
  scheme_id: "scheme-uuid-pmkisan",
  scheme_code: "PM_KISAN",
  scheme_name: "PM-KISAN Samman Nidhi",
  policy_title: "PM-KISAN 2026 Enhanced Mandatory Guidelines",
  description: "Statutory amendments requiring mandatory e-KYC and 2-hectare land validation.",
  lifecycle_status: "REVIEW_PENDING",
  source_candidate_id: "cand-uuid-999",
  source_title: "Gazette Notification No. 102/2026",
  source_publisher: "Ministry of Agriculture",
  source_url: "https://agricoop.gov.in/gazette/2026-102.pdf",
  source_excerpt: "All beneficiaries must complete biometric Aadhaar e-KYC verification.",
  authored_rules_json: {
    schema_version: "2.0",
    rules: [
      {
        rule_id: "pmkisan_land_limit",
        name_en: "Cultivable Land Limit",
        name_hi: "कृषि योग्य भूमि सीमा",
        field_path: "land_size_hectares",
        operator: "LESS_THAN_OR_EQUAL",
        target_value: 2,
        is_disqualification: false,
      },
      {
        rule_id: "pmkisan_mandatory_ekyc",
        name_en: "Mandatory Aadhaar e-KYC",
        name_hi: "अनिवार्य आधार ई-केवाईसी",
        field_path: "aadhaar_seeded",
        operator: "EQUALS",
        target_value: true,
        is_disqualification: false,
      },
    ],
  },
  canonical_rules_json: null,
  rule_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  schema_version: "2.0",
  compiler_version: "1.0",
  validation_status: "VALID",
  validation_details_json: {
    is_valid: true,
    errors: [],
    warnings: [],
    info: [],
    rule_count: 2,
    validated_at: "2026-09-20T10:00:00Z",
  },
  test_status: "PASSED",
  test_summary_json: {
    total_tests: 2,
    passed_tests: 2,
    failed_tests: 0,
  },
  author_id: "usr-author-99", // Different from usr-supervisor-01 to satisfy separation of duties
  author_role: "OFFICER",
  created_at: "2026-09-20T08:00:00Z",
  updated_at: "2026-09-20T09:00:00Z",
  audit_events: [
    {
      id: "aud-1",
      draft_id: "draft-uuid-12345",
      actor_identity: "usr-author-99",
      actor_role: "OFFICER",
      previous_status: "REGRESSION_VALIDATED",
      new_status: "REVIEW_PENDING",
      action: "SUBMIT_FOR_REVIEW",
      reason: "Completed all boundary and regression tests.",
      created_at: "2026-09-20T09:00:00Z",
    },
  ],
  revisions: [
    {
      id: "rev-1",
      draft_id: "draft-uuid-12345",
      revision_number: 1,
      author_id: "usr-author-99",
      author_role: "OFFICER",
      change_summary: "Initial draft rule setup",
      created_at: "2026-09-20T08:00:00Z",
    },
  ],
  tests: [
    {
      id: "tst-1",
      draft_id: "draft-uuid-12345",
      name: "Eligible Farmer with 1.5 Ha",
      test_type: "BOUNDARY",
      facts_json: { land_size_hectares: 1.5, aadhaar_seeded: true },
      expected_result: "ELIGIBLE",
      actual_result: "ELIGIBLE",
      status: "PASSED",
      created_at: "2026-09-20T08:30:00Z",
      updated_at: "2026-09-20T08:30:00Z",
    },
  ],
};

const mockListResponse: PolicyDraftListResponse = {
  drafts: [mockDraftDetail],
  total: 1,
  metrics: {
    total_drafts: 1,
    draft_status_count: 0,
    authoring: 0,
    validating: 0,
    testing: 0,
    pending_review: 1,
    in_review: 0,
    needs_clarification: 0,
    staged: 0,
    archived: 0,
  },
};

const mockValidationReport: ValidationReportResponse = {
  is_valid: true,
  errors: [],
  warnings: [],
  info: [],
  rule_count: 2,
  validated_at: "2026-09-20T10:00:00Z",
};

const mockDiffResponse: PolicyDiffResponse = {
  parent_version_code: "PM_KISAN_2020_REVISED",
  parent_rule_hash: "a1b2c3d4e5f6...",
  draft_rule_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  added_rules: [
    {
      rule_id: "pmkisan_mandatory_ekyc",
      diff_type: "ADDED",
      description_en: "Mandatory Aadhaar e-KYC Verification",
      human_explanation: "Introduced mandatory e-KYC requirement.",
    },
  ],
  removed_rules: [],
  modified_rules: [],
  metadata_changes: [],
  human_summary: "Introduced 1 new mandatory e-KYC requirement.",
};

describe("Phase 16: Controlled Policy Authoring & Compilation Frontend", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.setItem("yogyatamitra_officer_token", "mock-officer-jwt");
    mockLocalStorage.setItem(
      "yogyatamitra_officer_profile",
      JSON.stringify({
        id: "usr-supervisor-01",
        email: "supervisor@yogyatamitra.gov.in",
        role: "SUPERVISOR",
        name: "Senior Supervisor Sharma",
      })
    );
    (policyAuthoringApi.listDrafts as jest.Mock).mockResolvedValue(mockListResponse);
    (policyAuthoringApi.getDraft as jest.Mock).mockResolvedValue(mockDraftDetail);
    (policyAuthoringApi.validateDraft as jest.Mock).mockResolvedValue(mockValidationReport);
    (policyAuthoringApi.getDiff as jest.Mock).mockResolvedValue(mockDiffResponse);
    (policyAuthoringApi.listTests as jest.Mock).mockResolvedValue(mockDraftDetail.tests);
  });

  test("1. Queue Dashboard renders with non-active quarantine warning, metric cards, and drafts table", async () => {
    render(
      <OfficerAuthProvider>
        <PolicyAuthoringQueuePage />
      </OfficerAuthProvider>
    );

    // Warning banner check
    await waitFor(() => {
      expect(screen.getByText(/STAGED IS NOT ACTIVE/i)).toBeInTheDocument();
    });

    // Metrics check
    expect(screen.getByText(/Total Drafts/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Review Pending/i).length).toBeGreaterThan(0);

    // Draft item check
    await waitFor(() => {
      expect(
        screen.getByText("PM-KISAN 2026 Enhanced Mandatory Guidelines")
      ).toBeInTheDocument();
      expect(screen.getByText("PM_KISAN")).toBeInTheDocument();
    });
  });

  test("2. New Draft page renders mode switcher and supports scratch authoring and candidate derivation", async () => {
    render(
      <OfficerAuthProvider>
        <NewPolicyDraftPage />
      </OfficerAuthProvider>
    );

    expect(screen.getByText(/1. Author From Scratch/i)).toBeInTheDocument();
    expect(screen.getByText(/2. Derive From Approved Candidate/i)).toBeInTheDocument();
    expect(screen.getByText(/Statutory Target Scheme \*/i)).toBeInTheDocument();
    expect(screen.getByText(/Create & Open Rule Builder/i)).toBeInTheDocument();
  });

  test("3. Draft Dossier renders 10-state lifecycle stepper, metadata cards, and sub-nav tabs", async () => {
    render(
      <OfficerAuthProvider>
        <PolicyDraftDossierPage />
      </OfficerAuthProvider>
    );

    await waitFor(() => {
      expect(
        screen.getByText("PM-KISAN 2026 Enhanced Mandatory Guidelines")
      ).toBeInTheDocument();
      expect(screen.getByText(/Statutory Policy Authoring Lifecycle/i)).toBeInTheDocument();
    });

    // SubNav tabs check
    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getAllByText("Rule Builder").length).toBeGreaterThan(0);
    expect(screen.getAllByText("AST Validation").length).toBeGreaterThan(0);
    expect(screen.getByText("Test Suite & Regression")).toBeInTheDocument();
    expect(screen.getByText("Policy Diff")).toBeInTheDocument();
    expect(screen.getAllByText("Supervisory Review").length).toBeGreaterThan(0);

    // Provenance check
    expect(screen.getByText(/Gazette Notification No. 102\/2026/i)).toBeInTheDocument();
  });

  test("4. Interactive Rule Builder displays configured rules and JSON AST preview", async () => {
    render(
      <OfficerAuthProvider>
        <PolicyRuleBuilderPage />
      </OfficerAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Interactive Statutory Rule Builder/i)).toBeInTheDocument();
      expect(screen.getByText("pmkisan_land_limit")).toBeInTheDocument();
      expect(screen.getByText("pmkisan_mandatory_ekyc")).toBeInTheDocument();
    });

    // AST JSON schema check
    expect(screen.getByText(/Canonical AST Schema v2.0/i)).toBeInTheDocument();
  });

  test("5. Static AST Validation page displays invariant check categories and findings", async () => {
    render(
      <OfficerAuthProvider>
        <PolicyValidationPage />
      </OfficerAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Deterministic Static AST Validation/i)).toBeInTheDocument();
      expect(screen.getByText(/Statutory Verification Invariants/i)).toBeInTheDocument();
      expect(screen.getByText(/AST Syntax/i)).toBeInTheDocument();
      expect(screen.getByText(/Temporality/i)).toBeInTheDocument();
      expect(screen.getByText(/Code Safety/i)).toBeInTheDocument();
    });
  });

  test("6. Deterministic Test Suite displays boundary test cases and 6 frozen hashes regression assurance", async () => {
    render(
      <OfficerAuthProvider>
        <PolicyTestSuitePage />
      </OfficerAuthProvider>
    );

    await waitFor(() => {
      expect(
        screen.getByText(/Deterministic Test Suite & Statutory Regression/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Statutory Baseline Invariance & Regression Safety \(6 Frozen Hashes\)/i)
      ).toBeInTheDocument();
      expect(screen.getByText("Eligible Farmer with 1.5 Ha")).toBeInTheDocument();
    });
  });

  test("7. Visual Policy Diff page shows rule additions and hash comparisons", async () => {
    render(
      <OfficerAuthProvider>
        <PolicyDiffViewerPage />
      </OfficerAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Visual Policy Differential/i)).toBeInTheDocument();
      expect(screen.getByText(/Rules Added/i)).toBeInTheDocument();
      expect(screen.getByText("+ ADDED")).toBeInTheDocument();
      expect(screen.getByText("pmkisan_mandatory_ekyc")).toBeInTheDocument();
    });
  });

  test("8. Supervisory Review panel verifies separation of duties and requires >= 5 character justification", async () => {
    render(
      <OfficerAuthProvider>
        <PolicyReviewPage />
      </OfficerAuthProvider>
    );

    await waitFor(() => {
      expect(
        screen.getByText(/Supervisory Review & Lifecycle Determination/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/Separation of Duties Satisfied/i)).toBeInTheDocument();
      expect(screen.getByText(/Approve & Stage Policy \(STAGE\)/i)).toBeInTheDocument();
      expect(screen.getByText(/5 chars minimum/i)).toBeInTheDocument();
    });
  });

  test("9. Supervisory Review panel blocks staging and enforces Separation of Duties when officer is author", async () => {
    (policyAuthoringApi.getDraft as jest.Mock).mockResolvedValue({
      ...mockDraftDetail,
      author_id: "usr-supervisor-01", // Matches current logged in officer ID!
    });

    render(
      <OfficerAuthProvider>
        <PolicyReviewPage />
      </OfficerAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Separation of Duties Restriction Active/i)).toBeInTheDocument();
      expect(screen.getByText(/You authored this draft/i)).toBeInTheDocument();
    });
  });
});
