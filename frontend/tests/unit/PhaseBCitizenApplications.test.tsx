import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AuthProvider } from "../../src/context/AuthContext";
import { citizenApi } from "../../src/api/citizen";
import CitizenDashboardPage from "../../src/app/citizen/dashboard/page";
import CitizenApplicationsPage from "../../src/app/citizen/applications/page";
import CitizenApplicationDetailPage from "../../src/app/citizen/applications/[applicationId]/page";
import { CitizenApplicationDetail, CitizenApplicationSummary, CitizenDashboardStats } from "../../src/types/citizen";

// Mock next/navigation
const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  usePathname: () => "/citizen/dashboard",
  useRouter: () => ({
    push: mockPush,
    replace: jest.fn(),
  }),
  useParams: () => ({
    applicationId: "bb830ba4-04fb-45f8-a36f-7a360f696173",
  }),
}));

// Mock citizenApi
jest.mock("../../src/api/citizen", () => ({
  citizenApi: {
    getDashboardStats: jest.fn(),
    getApplications: jest.fn(),
    getApplicationDetail: jest.fn(),
    createApplication: jest.fn(),
    getProfile: jest.fn(),
  },
  getCitizenAuthHeaders: jest.fn(() => ({ Authorization: "Bearer mock_token" })),
}));

const mockApplications: CitizenApplicationSummary[] = [
  {
    id: "bb830ba4-04fb-45f8-a36f-7a360f696173",
    application_ref: "APP-2026-BB830BA4",
    scheme_id: "a35ba76b-11c9-46f7-b317-b0d2044b4ce1",
    scheme_code: "PM_KISAN",
    scheme_name: "Pradhan Mantri Kisan Samman Nidhi",
    scheme_name_hi: "प्रधानमंत्री किसान सम्मान निधि",
    ministry: "Ministry of Agriculture & Farmers Welfare",
    state: "EVALUATED",
    status_label_en: "Evaluated",
    status_label_hi: "मूल्यांकित",
    created_at: "2026-09-28T10:00:00Z",
    updated_at: "2026-09-28T12:00:00Z",
    policy_version_id: "4947bf8e-9cb5-43f2-bb69-fc22e5aa58da",
    policy_version_code: "v3.0-2023",
    evaluation_outcome: "ELIGIBLE",
    claims_count: 3,
    evidence_count: 1,
  },
  {
    id: "f413260a-0572-40d2-ab77-a674eaf0c699",
    application_ref: "APP-2026-F413260A",
    scheme_id: "a2e47e1b-36d8-4323-8619-13930acecb7e",
    scheme_code: "SSY",
    scheme_name: "Sukanya Samriddhi Account Scheme",
    scheme_name_hi: "सुकन्या समृद्धि खाता योजना",
    ministry: "Ministry of Finance",
    state: "VERIFICATION_IN_PROGRESS",
    status_label_en: "Under Verification",
    status_label_hi: "सत्यापन प्रगति पर",
    created_at: "2026-09-28T11:00:00Z",
    updated_at: "2026-09-28T11:30:00Z",
    policy_version_id: null,
    policy_version_code: null,
    evaluation_outcome: null,
    claims_count: 3,
    evidence_count: 1,
  },
];

const mockStats: CitizenDashboardStats = {
  total_applications: 2,
  in_progress_count: 1,
  evaluated_count: 1,
  action_required_count: 0,
  recent_applications: mockApplications,
};

const mockDetail: CitizenApplicationDetail = {
  ...mockApplications[0],
  citizen_ref: "SYN-CIT-DEMO0001",
  citizen_name: "Test Citizen (Demo)",
  official_url: "https://pmkisan.gov.in",
  claims: [
    {
      id: "claim-1",
      claim_type: "agricultural_landholding",
      value_json: { has_cultivable_land: true, land_area_hectares: 1.8 },
      source: "CITIZEN_DECLARATION",
      status: "VERIFIED",
      claimed_at: "2026-09-28T10:00:00Z",
      evidence_items: [
        {
          id: "ev-1",
          claim_id: "claim-1",
          evidence_type: "land_record_7_12",
          storage_reference: "uploads/pmkisan_ror_712.pdf",
          status: "VERIFIED",
          submitted_at: "2026-09-28T10:05:00Z",
          verified_at: "2026-09-28T11:45:00Z",
        },
      ],
    },
  ],
  transitions: [
    {
      id: "trans-1",
      journey_id: "bb830ba4-04fb-45f8-a36f-7a360f696173",
      from_state: "DRAFT",
      to_state: "FACTS_COLLECTED",
      actor: "CITIZEN",
      reason: "Application self-declaration submitted by citizen",
      created_at: "2026-09-28T10:00:00Z",
    },
    {
      id: "trans-2",
      journey_id: "bb830ba4-04fb-45f8-a36f-7a360f696173",
      from_state: "FACTS_COLLECTED",
      to_state: "VERIFICATION_IN_PROGRESS",
      actor: "CITIZEN",
      reason: "Evidence attached and queued for verification",
      created_at: "2026-09-28T10:05:00Z",
    },
  ],
  latest_evaluation: {
    evaluation_id: "eval-1",
    result_state: "ELIGIBLE",
    evaluation_date: "2026-09-28",
    policy_version_code: "v3.0-2023",
    rule_definition_hash: "7ef27f5c071a8fa4fff2d95c6c34cda5211b76d16ddb0e610a312ea61cf669d6",
    reasons_en: ["Applicant holds cultivable agricultural land of 1.8 hectares."],
    reasons_hi: ["आवेदक के पास 1.8 हेक्टेयर कृषि योग्य भूमि की पुष्टि हुई।"],
  },
  allowed_actions: ["VIEW_SCHEME", "CHECK_ELIGIBILITY"],
};

describe("Phase B: Citizen Dashboard & Applications Workspace", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yogyatamitra_role", "CITIZEN");
    localStorage.setItem("yogyatamitra_citizen_token", "mock_citizen_jwt");
    localStorage.setItem(
      "yogyatamitra_citizen_profile",
      JSON.stringify({
        email: "citizen.test@yogyatamitra.local",
        citizen_name: "Test Citizen (Demo)",
        citizen_ref: "SYN-CIT-DEMO0001",
        role: "CITIZEN",
        state: "Maharashtra",
        district: "Pune",
      })
    );
    jest.clearAllMocks();
  });

  it("Dashboard renders application statistics and recent applications", async () => {
    (citizenApi.getDashboardStats as jest.Mock).mockResolvedValue(mockStats);

    render(
      <AuthProvider>
        <CitizenDashboardPage />
      </AuthProvider>
    );

    // Initial greeting
    expect(screen.getByText(/नमस्ते, Test Citizen \(Demo\)/i)).toBeInTheDocument();
    expect(screen.getByText("SYN-CIT-DEMO0001")).toBeInTheDocument();

    // Await stats load
    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument(); // Total applications
    });

    // Recent applications rendered
    expect(screen.getByText(/Pradhan Mantri Kisan Samman Nidhi/i)).toBeInTheDocument();
    expect(screen.getByText("APP-2026-BB830BA4")).toBeInTheDocument();
    expect(screen.getByText(/पात्र \/ Eligible \(v3.0-2023\)/i)).toBeInTheDocument();
  });

  it("Dashboard renders clean empty state when citizen has zero applications", async () => {
    (citizenApi.getDashboardStats as jest.Mock).mockResolvedValue({
      total_applications: 0,
      in_progress_count: 0,
      evaluated_count: 0,
      action_required_count: 0,
      recent_applications: [],
    });

    render(
      <AuthProvider>
        <CitizenDashboardPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/कोई सक्रिय आवेदन नहीं मिला/i)).toBeInTheDocument();
      expect(screen.getByText(/No Applications Filed Yet/i)).toBeInTheDocument();
    });
  });

  it("Applications List page renders multiple applications across schemes with status filters", async () => {
    (citizenApi.getApplications as jest.Mock).mockResolvedValue(mockApplications);

    render(
      <AuthProvider>
        <CitizenApplicationsPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("APP-2026-BB830BA4")).toBeInTheDocument();
      expect(screen.getByText("APP-2026-F413260A")).toBeInTheDocument();
    });

    expect(screen.getByText(/Pradhan Mantri Kisan Samman Nidhi/i)).toBeInTheDocument();
    expect(screen.getByText(/Sukanya Samriddhi Account Scheme/i)).toBeInTheDocument();

    // Filter to Evaluated
    const evaluatedTab = screen.getByRole("button", { name: /मूल्यांकन पूर्ण \/ Evaluated/i });
    fireEvent.click(evaluatedTab);

    expect(screen.getByText("APP-2026-BB830BA4")).toBeInTheDocument();
    expect(screen.queryByText("APP-2026-F413260A")).not.toBeInTheDocument();
  });

  it("Application Detail page renders full dossier with claims, evidence and bilingual evaluation", async () => {
    (citizenApi.getApplicationDetail as jest.Mock).mockResolvedValue(mockDetail);

    render(
      <AuthProvider>
        <CitizenApplicationDetailPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("APP-2026-BB830BA4")).toBeInTheDocument();
    });

    // Scheme & Evaluation
    expect(screen.getByText(/Pradhan Mantri Kisan Samman Nidhi/i)).toBeInTheDocument();
    expect(screen.getByText(/Statutory Eligibility Determination:/i)).toBeInTheDocument();
    expect(screen.getByText(/Applicant holds cultivable agricultural land of 1.8 hectares./i)).toBeInTheDocument();
    expect(screen.getByText(/आवेदक के पास 1.8 हेक्टेयर कृषि योग्य भूमि की पुष्टि हुई।/i)).toBeInTheDocument();

    // Claims and Evidence
    expect(screen.getByText(/AGRICULTURAL LANDHOLDING/i)).toBeInTheDocument();
    expect(screen.getByText(/uploads\/pmkisan_ror_712.pdf/i)).toBeInTheDocument();

    // Lifecycle Timeline
    expect(screen.getByText(/DRAFT → FACTS_COLLECTED/i)).toBeInTheDocument();
    expect(screen.getByText(/FACTS_COLLECTED → VERIFICATION_IN_PROGRESS/i)).toBeInTheDocument();
  });
});
