import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AuthProvider } from "../../src/context/AuthContext";
import { OfficerAuthProvider } from "../../src/context/OfficerAuthContext";
import { CaseProvider } from "../../src/app/officer/cases/[journeyId]/CaseContext";
import CitizenApplicationDetailPage from "../../src/app/citizen/applications/[applicationId]/page";
import CaseEvidencePage from "../../src/app/officer/cases/[journeyId]/evidence/page";
import { citizenApi } from "../../src/api/citizen";
import { officerApi } from "../../src/api/officer";
import { CitizenApplicationDetail } from "../../src/types/citizen";
import { OfficerCaseDetail } from "../../src/types/officer";

// Mock next/navigation
jest.mock("next/navigation", () => ({
  usePathname: () => "/citizen/applications/app-test-phase-e",
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({
    applicationId: "app-test-phase-e",
    journeyId: "journey-test-phase-e",
  }),
}));

// Mock citizenApi
jest.mock("../../src/api/citizen", () => ({
  citizenApi: {
    getApplicationDetail: jest.fn(),
    respondClarification: jest.fn(),
    getClarifications: jest.fn(),
    getVerificationStatus: jest.fn(),
  },
  getCitizenAuthHeaders: jest.fn(() => ({ Authorization: "Bearer mock_token" })),
}));

// Mock officerApi
jest.mock("../../src/api/officer", () => ({
  officerApi: {
    getProfile: jest.fn(),
    getCaseDetail: jest.fn(),
    verifyEvidence: jest.fn(),
    requestClarification: jest.fn(),
    getVerificationHistory: jest.fn(),
  },
  getAuthHeaders: jest.fn(() => ({ Authorization: "Bearer mock_token" })),
}));

const mockCitizenApplicationDetail: CitizenApplicationDetail = {
  id: "app-test-phase-e",
  application_ref: "APP-2026-PMKISAN-001",
  scheme_code: "PM_KISAN",
  scheme_name: "Pradhan Mantri Kisan Samman Nidhi",
  scheme_name_hi: "प्रधानमंत्री किसान सम्मान निधि",
  ministry: "Ministry of Agriculture & Farmers Welfare",
  state: "ACTION_REQUIRED",
  status_label_en: "Action Required",
  status_label_hi: "कार्रवाई आवश्यक",
  citizen_ref: "SYN-CIT-PHASE-E",
  citizen_name: "Radha Sharma",
  submitted_at: "2026-09-29T10:00:00Z",
  created_at: "2026-09-29T09:00:00Z",
  updated_at: "2026-09-29T10:30:00Z",
  claims: [
    {
      id: "claim-001",
      claim_type: "LAND_OWNERSHIP",
      value_json: { land_holding_hectares: 1.5, is_cultivable: true },
      source: "CITIZEN_DECLARATION",
      status: "PENDING",
      claimed_at: "2026-09-29T10:00:00Z",
      evidence_items: [
        {
          id: "ev-001",
          evidence_type: "LAND_RECORD",
          storage_reference: "docs/land_record_001.pdf",
          status: "CLARIFICATION_REQUIRED",
          submitted_at: "2026-09-29T10:00:00Z",
        },
      ],
    },
  ],
  transitions: [
    {
      id: "trans-001",
      from_state: "VERIFICATION_IN_PROGRESS",
      to_state: "ACTION_REQUIRED",
      actor: "OFFICER",
      reason: "Clarification required on Land Record",
      created_at: "2026-09-29T10:30:00Z",
    },
  ],
  allowed_actions: ["RESPOND_CLARIFICATION"],
  verification_status: "CLARIFICATION_REQUIRED",
  clarifications: [
    {
      id: "clarif-001",
      round: 1,
      evidence_id: "ev-001",
      request_reason: "Please upload current 2026 revenue record",
      status: "OPEN",
      requested_at: "2026-09-29T10:30:00Z",
      has_replacement_evidence: false,
    },
  ],
};

const mockOfficerCaseDetail: OfficerCaseDetail = {
  journey_id: "journey-test-phase-e",
  citizen_ref: "SYN-CIT-PHASE-E",
  scheme_code: "PM_KISAN",
  scheme_name: "Pradhan Mantri Kisan Samman Nidhi",
  journey_state: "ACTION_REQUIRED",
  submitted_at: "2026-09-29T10:00:00Z",
  updated_at: "2026-09-29T10:30:00Z",
  review_status: "CLARIFICATION_REQUIRED",
  claims: [
    {
      id: "claim-001",
      claim_type: "LAND_OWNERSHIP",
      value_json: { land_holding_hectares: 1.5 },
      source: "CITIZEN_DECLARATION",
      status: "PENDING",
      claimed_at: "2026-09-29T10:00:00Z",
      evidence_items: [],
    },
  ],
  evidence_items: [
    {
      id: "ev-001",
      claim_id: "claim-001",
      claim_type: "LAND_OWNERSHIP",
      evidence_type: "LAND_RECORD",
      evidence_type_label: "Land Revenue Record",
      storage_reference: "docs/land_record_001.pdf",
      metadata_json: { doc_name: "Land Record.pdf" },
      status: "CLARIFICATION_REQUIRED",
      submitted_at: "2026-09-29T10:00:00Z",
      verification_records: [],
    },
  ],
  audit_history: [],
  clarifications: [
    {
      id: "clarif-001",
      journey_id: "journey-test-phase-e",
      evidence_id: "ev-001",
      round: 1,
      requesting_officer: "officer@test.local",
      requesting_officer_role: "OFFICER",
      request_reason: "Please upload current 2026 revenue record",
      status: "OPEN",
      requested_at: "2026-09-29T10:30:00Z",
      created_at: "2026-09-29T10:30:00Z",
    },
  ],
  verification_status: "CLARIFICATION_REQUIRED",
};

describe("Phase E: Operational Evidence Verification & Clarification Workflow", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    localStorage.setItem("yogyatamitra_active_role", "CITIZEN");
    localStorage.setItem("yogyatamitra_role", "CITIZEN");
    localStorage.setItem("yogyatamitra_citizen_token", "mock_citizen_jwt");
    localStorage.setItem(
      "yogyatamitra_citizen_profile",
      JSON.stringify({
        id: "cit-123",
        synthetic_reference: "SYN-CIT-PHASE-E",
        display_name: "Radha Sharma",
        citizen_name: "Radha Sharma",
        role: "CITIZEN",
      })
    );
    localStorage.setItem("yogyatamitra_officer_token", "fake-officer-token");
    localStorage.setItem(
      "yogyatamitra_officer_profile",
      JSON.stringify({
        email: "officer@test.local",
        name: "Test Officer",
        role: "OFFICER",
      })
    );
    (officerApi.getProfile as jest.Mock).mockResolvedValue({
      email: "officer@test.local",
      role: "OFFICER",
      name: "Test Officer",
    });
    (citizenApi.getApplicationDetail as jest.Mock).mockResolvedValue(mockCitizenApplicationDetail);
    (officerApi.getCaseDetail as jest.Mock).mockResolvedValue(mockOfficerCaseDetail);
  });

  afterEach(() => {
    localStorage.clear();
  });

  test("Citizen dossier renders Action Required banner and clarification section", async () => {
    render(
      <AuthProvider>
        <CitizenApplicationDetailPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Action Required: Clarification Requested/i)).toBeInTheDocument();
    });

    // Check clarification reason displayed
    expect(screen.getByText("Please upload current 2026 revenue record")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Please explain details clearly/i)).toBeInTheDocument();
  });

  test("Citizen can respond to open clarification", async () => {
    (citizenApi.respondClarification as jest.Mock).mockResolvedValue({
      id: "clarif-001",
      status: "RESPONDED",
      response_text: "Here is the updated 2026 document",
    });

    render(
      <AuthProvider>
        <CitizenApplicationDetailPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Please explain details clearly/i)).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/Please explain details clearly/i);
    fireEvent.change(textarea, { target: { value: "Here is the updated 2026 document" } });

    const submitBtn = screen.getByRole("button", { name: /Submit Clarification Response/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(citizenApi.respondClarification).toHaveBeenCalledWith(
        "app-test-phase-e",
        "clarif-001",
        expect.objectContaining({
          response_text: "Here is the updated 2026 document",
        }),
        expect.anything()
      );
    });
  });

  test("Officer evidence page renders CLARIFICATION_REQUIRED badge and clarification details", async () => {
    render(
      <OfficerAuthProvider>
        <CaseProvider journeyId="journey-test-phase-e">
          <CaseEvidencePage />
        </CaseProvider>
      </OfficerAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("CLARIFICATION REQUIRED")).toBeInTheDocument();
    });

    expect(screen.getByText(/Round 1: Clarification OPEN/i)).toBeInTheDocument();
    expect(screen.getByText(/Awaiting citizen response/i)).toBeInTheDocument();
  });
});
