import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import OfficerLoginPage from "../../src/app/officer/login/page";
import OfficerQueuePage from "../../src/app/officer/queue/page";
import { OfficerAuthProvider } from "../../src/context/OfficerAuthContext";
import { CaseProvider } from "../../src/app/officer/cases/[journeyId]/CaseContext";
import CaseOverviewPage from "../../src/app/officer/cases/[journeyId]/page";
import CaseEvidencePage from "../../src/app/officer/cases/[journeyId]/evidence/page";
import CaseAssessmentPage from "../../src/app/officer/cases/[journeyId]/assessment/page";
import CasePolicyPage from "../../src/app/officer/cases/[journeyId]/policy/page";
import CaseReviewPage from "../../src/app/officer/cases/[journeyId]/review/page";
import CaseHistoryPage from "../../src/app/officer/cases/[journeyId]/history/page";
import { OfficerCaseDetail } from "../../src/types/officer";
import { officerApi } from "../../src/api/officer";

// Mock next/navigation
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
  }),
  usePathname: () => "/officer",
  useParams: () => ({ journeyId: "test-journey-uuid-12345" }),
}));

// Mock officerApi
jest.mock("../../src/api/officer", () => ({
  officerApi: {
    login: jest.fn(),
    getProfile: jest.fn(),
    getQueue: jest.fn(),
    getCaseDetail: jest.fn(),
    verifyEvidence: jest.fn(),
    reviewCase: jest.fn(),
    getAuditTrail: jest.fn(),
  },
}));

const mockCaseDetail: OfficerCaseDetail = {
  journey_id: "test-journey-uuid-12345",
  citizen_ref: "SYN-CIT-987654",
  scheme_code: "PM_KISAN",
  scheme_name: "PM-KISAN Samman Nidhi",
  journey_state: "EVIDENCE_PENDING",
  submitted_at: "2026-09-19T10:00:00Z",
  updated_at: "2026-09-19T10:30:00Z",
  review_status: "IN_REVIEW",
  review_decision: null,
  review_notes: null,
  reviewer_identity: "officer@yogyatamitra.local",
  reviewer_role: "OFFICER",
  claims: [
    {
      id: "claim-1",
      claim_type: "family.owns_cultivable_land",
      claim_label: "Agricultural Landholding",
      value_json: { value: true },
      value_display: "Yes (Confirmed)",
      source: "SELF_DECLARATION",
      status: "CLAIMED",
      claimed_at: "2026-09-19T10:00:00Z",
    },
    {
      id: "claim-2",
      claim_type: "family.land_size_hectares",
      claim_label: "Landholding Size",
      value_json: { value: 1.5 },
      value_display: "1.5 hectares",
      source: "SELF_DECLARATION",
      status: "CLAIMED",
      claimed_at: "2026-09-19T10:00:00Z",
    },
  ],
  evidence_items: [
    {
      id: "ev-1",
      claim_id: "claim-1",
      claim_type: "family.owns_cultivable_land",
      evidence_type: "LAND_RECORD",
      evidence_type_label: "Land Ownership Record / Record of Rights (RoR)",
      storage_reference: "vault://revenue/land/record-123.pdf",
      metadata_json: { khasra_no: "42/1", district: "Varanasi" },
      status: "PENDING",
      submitted_at: "2026-09-19T10:05:00Z",
      verified_at: null,
      rejected_at: null,
      rejection_reason: null,
      verification_records: [],
    },
  ],
  automated_assessment: {
    evaluation_id: "eval-trace-12345",
    determination: "INSUFFICIENT_INFORMATION",
    evaluated_at: "2026-09-19T10:10:00Z",
    ruleset_version: "v3.0-2023",
    ruleset_hash: "7ef27f5c071a8fa4fff2d95c6c34cda5211b76d16ddb0e610a312ea61cf669d6",
    rules_evaluated: [
      {
        rule_id: "PMKISAN-LAND-CULTIVABLE",
        rule_name: "Cultivable Landholding Criterion",
        description: "Farmer family must own cultivable landholding.",
        result: "PASS",
        details: "Ownership confirmed via self declaration",
      },
    ],
    missing_facts: ["family.is_institutional_landholder"],
    disqualifiers: [],
  },
  policy_provenance: {
    scheme_code: "PM_KISAN",
    scheme_name: "PM-KISAN Samman Nidhi",
    policy_version: "v3.0-2023",
    ruleset_version: "1.0",
    effective_from: "2023-01-01",
    effective_to: null,
    content_sha256: "7ef27f5c071a8fa4fff2d95c6c34cda5211b76d16ddb0e610a312ea61cf669d6",
    official_citation: "Operational Guidelines for PM-KISAN (Revised 2023)",
    gazette_reference: "Gazette Order Ref AGRI-2023/4412",
    issuing_authority: "Ministry of Agriculture & Farmers Welfare",
    rule_definitions_count: 5,
    is_statutory_source_verified: true,
  },
  audit_history: [
    {
      id: "audit-1",
      journey_id: "test-journey-uuid-12345",
      review_id: "review-12345",
      actor_identity: "officer@yogyatamitra.local",
      actor_role: "OFFICER",
      action: "EVIDENCE_VERIFY",
      previous_status: "PENDING",
      new_status: "VERIFIED",
      reason: "Document authentic and matched with state revenue registry",
      details_json: { notes: "Verified via API" },
      created_at: "2026-09-19T10:15:00Z",
    },
  ],
};

describe("Phase 14: Officer / Human Verification Portal", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    localStorage.setItem("yogyatamitra_officer_token", "fake-token");
    localStorage.setItem(
      "yogyatamitra_officer_profile",
      JSON.stringify({
        email: "officer@yogyatamitra.local",
        name: "Senior Verification Officer (Demo)",
        role: "OFFICER",
        designation: "Officer Grade II",
        department: "Welfare Verification Cell",
      })
    );
    (officerApi.getProfile as jest.Mock).mockResolvedValue({
      email: "officer@yogyatamitra.local",
      name: "Senior Verification Officer (Demo)",
      role: "OFFICER",
      designation: "Officer Grade II",
      department: "Welfare Verification Cell",
    });
  });

  test("1. Officer login page renders demo warning and quick-fill buttons", () => {
    render(
      <OfficerAuthProvider>
        <OfficerLoginPage />
      </OfficerAuthProvider>
    );

    expect(screen.getByText("DEVELOPMENT OFFICER LOGIN")).toBeInTheDocument();
    expect(
      screen.getByText(/DEMO ENVIRONMENT ONLY • BACK-OFFICE VERIFICATION/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Production deployments integrate with official Government Single Sign-On/i)
    ).toBeInTheDocument();

    // Quick-fill buttons
    expect(screen.getByText("Verification Officer")).toBeInTheDocument();
    expect(screen.getByText("Welfare Supervisor")).toBeInTheDocument();

    // Click quick fill
    fireEvent.click(screen.getByText("Verification Officer"));
    const emailInput = screen.getByPlaceholderText("officer@yogyatamitra.local") as HTMLInputElement;
    expect(emailInput.value).toBe("officer@yogyatamitra.local");
  });

  test("2. Verification Queue renders metrics and case items", async () => {
    (officerApi.getQueue as jest.Mock).mockResolvedValueOnce({
      metrics: {
        total_cases: 12,
        pending_cases: 5,
        in_review_cases: 4,
        escalated_cases: 2,
        completed_cases: 1,
      },
      items: [
        {
          journey_id: "test-journey-uuid-12345",
          citizen_ref: "SYN-CIT-987654",
          scheme_code: "PM_KISAN",
          scheme_name: "PM-KISAN Samman Nidhi",
          journey_state: "EVIDENCE_PENDING",
          submitted_at: "2026-09-19T10:00:00Z",
          review_status: "IN_REVIEW",
          review_decision: null,
          evidence_count: 2,
          verified_evidence_count: 1,
          automated_eligibility: "INSUFFICIENT_INFORMATION",
        },
      ],
    });

    render(
      <OfficerAuthProvider>
        <OfficerQueuePage />
      </OfficerAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Total in Queue")).toBeInTheDocument();
      expect(screen.getByText("12")).toBeInTheDocument();
      expect(screen.getByText("SYN-CIT-987654")).toBeInTheDocument();
      expect(screen.getByText("Inspect Case")).toBeInTheDocument();
    });
  });

  test("3. Case Overview renders plain-language claims", async () => {
    (officerApi.getCaseDetail as jest.Mock).mockResolvedValue(mockCaseDetail);

    render(
      <OfficerAuthProvider>
        <CaseProvider journeyId="test-journey-uuid-12345">
          <CaseOverviewPage />
        </CaseProvider>
      </OfficerAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Citizen Asserted Claims (2)")).toBeInTheDocument();
      expect(screen.getByText("Agricultural Landholding")).toBeInTheDocument();
      expect(screen.getByText("Yes (Confirmed)")).toBeInTheDocument();
      expect(screen.getByText("Landholding Size")).toBeInTheDocument();
      expect(screen.getByText("1.5 hectares")).toBeInTheDocument();
    });
  });

  test("4. Supporting Evidence displays documents and action button", async () => {
    (officerApi.getCaseDetail as jest.Mock).mockResolvedValue(mockCaseDetail);

    render(
      <OfficerAuthProvider>
        <CaseProvider journeyId="test-journey-uuid-12345">
          <CaseEvidencePage />
        </CaseProvider>
      </OfficerAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Supporting Documentary Evidence (1 items)")).toBeInTheDocument();
      expect(
        screen.getByText("Land Ownership Record / Record of Rights (RoR)")
      ).toBeInTheDocument();
      expect(screen.getByText("vault://revenue/land/record-123.pdf")).toBeInTheDocument();
      expect(screen.getByText("Take Action")).toBeInTheDocument();
      expect(
        screen.getByText(/Documentary verification does not alter citizen claims/i)
      ).toBeInTheDocument();
    });
  });

  test("5. Automated Assessment displays deterministic engine output & rule breakdowns", async () => {
    (officerApi.getCaseDetail as jest.Mock).mockResolvedValue(mockCaseDetail);

    render(
      <OfficerAuthProvider>
        <CaseProvider journeyId="test-journey-uuid-12345">
          <CaseAssessmentPage />
        </CaseProvider>
      </OfficerAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Deterministic Statutory Evaluation")).toBeInTheDocument();
      expect(screen.getByText("DETERMINATION: INSUFFICIENT INFO")).toBeInTheDocument();
      expect(screen.getByText("Cultivable Landholding Criterion")).toBeInTheDocument();
      expect(screen.getByText("PASS")).toBeInTheDocument();
      expect(screen.getByText("family.is_institutional_landholder")).toBeInTheDocument();
    });
  });

  test("6. Policy Provenance displays canonical SHA-256 rule hash and gazette citations", async () => {
    (officerApi.getCaseDetail as jest.Mock).mockResolvedValue(mockCaseDetail);

    render(
      <OfficerAuthProvider>
        <CaseProvider journeyId="test-journey-uuid-12345">
          <CasePolicyPage />
        </CaseProvider>
      </OfficerAuthProvider>
    );

    await waitFor(() => {
      expect(
        screen.getByText("Statutory Policy Provenance & Gazette Authority")
      ).toBeInTheDocument();
      expect(screen.getByText("STATUTORY SOURCE VERIFIED")).toBeInTheDocument();
      expect(
        screen.getByText("7ef27f5c071a8fa4fff2d95c6c34cda5211b76d16ddb0e610a312ea61cf669d6")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Operational Guidelines for PM-KISAN (Revised 2023)")
      ).toBeInTheDocument();
    });
  });

  test("7. Officer Determination enforces mandatory reason on adverse or escalated decision", async () => {
    (officerApi.getCaseDetail as jest.Mock).mockResolvedValue(mockCaseDetail);

    render(
      <OfficerAuthProvider>
        <CaseProvider journeyId="test-journey-uuid-12345">
          <CaseReviewPage />
        </CaseProvider>
      </OfficerAuthProvider>
    );

    await waitFor(() => {
      expect(
        screen.getByText("Record Official Verification Determination")
      ).toBeInTheDocument();
    });

    // Select REJECTED
    const rejectRadio = screen.getByLabelText(/REJECTED — Verification Failed/i);
    fireEvent.click(rejectRadio);

    // Try submitting without reason
    const submitBtn = screen.getByText("Commit Official Determination");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/A mandatory justification reason is required for this determination/i)
      ).toBeInTheDocument();
    });
  });

  test("8. Audit History displays chronological append-only events", async () => {
    (officerApi.getCaseDetail as jest.Mock).mockResolvedValue(mockCaseDetail);

    render(
      <OfficerAuthProvider>
        <CaseProvider journeyId="test-journey-uuid-12345">
          <CaseHistoryPage />
        </CaseProvider>
      </OfficerAuthProvider>
    );

    await waitFor(() => {
      expect(
        screen.getByText("Immutable Verification Audit Trail (1 events)")
      ).toBeInTheDocument();
      expect(screen.getByText("EVIDENCE_VERIFY")).toBeInTheDocument();
      expect(screen.getByText("officer@yogyatamitra.local")).toBeInTheDocument();
      expect(
        screen.getByText("Document authentic and matched with state revenue registry")
      ).toBeInTheDocument();
    });
  });
});
