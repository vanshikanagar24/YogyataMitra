import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AuthProvider } from "../../src/context/AuthContext";
import { citizenApi } from "../../src/api/citizen";
import CitizenSchemesPage from "../../src/app/citizen/schemes/page";
import CitizenApplicationWizardPage from "../../src/app/citizen/applications/new/page";
import CitizenApplicationsPage from "../../src/app/citizen/applications/page";
import CitizenApplicationDetailPage from "../../src/app/citizen/applications/[applicationId]/page";
import {
  AvailableSchemeSummary,
  SchemeRequirementsResponse,
  CitizenApplicationDetail,
  CitizenApplicationSummary,
} from "../../src/types/citizen";

// Mock next/navigation
const mockPush = jest.fn();
let mockSearchParams = new URLSearchParams();

jest.mock("next/navigation", () => ({
  usePathname: () => "/citizen/applications/new",
  useRouter: () => ({
    push: mockPush,
    replace: jest.fn(),
  }),
  useSearchParams: () => mockSearchParams,
  useParams: () => ({
    applicationId: "draft-app-001",
  }),
}));

// Mock citizenApi
jest.mock("../../src/api/citizen", () => ({
  citizenApi: {
    getAvailableSchemes: jest.fn(),
    getSchemeRequirements: jest.fn(),
    createApplication: jest.fn(),
    updateDraft: jest.fn(),
    submitApplication: jest.fn(),
    getApplications: jest.fn(),
    getApplicationDetail: jest.fn(),
    getDashboardStats: jest.fn(),
    getProfile: jest.fn(),
  },
  getCitizenAuthHeaders: jest.fn(() => ({ Authorization: "Bearer mock_token" })),
}));

const mockAvailableSchemes: AvailableSchemeSummary[] = [
  {
    id: "scheme-pmkisan",
    scheme_code: "PM_KISAN",
    name_en: "Pradhan Mantri Kisan Samman Nidhi",
    name_hi: "प्रधानमंत्री किसान सम्मान निधि",
    description_en: "Income support of Rs. 6,000 per year for landholding farmer families.",
    description_hi: "भूमिधारक किसान परिवारों के लिए प्रति वर्ष 6,000 रुपये की आय सहायता।",
    ministry: "Ministry of Agriculture & Farmers Welfare",
    official_url: "https://pmkisan.gov.in",
    status: "ACTIVE",
    created_at: "2026-09-29T00:00:00Z",
  },
  {
    id: "scheme-ssy",
    scheme_code: "SSY",
    name_en: "Sukanya Samriddhi Account Scheme",
    name_hi: "सुकन्या समृद्धि खाता योजना",
    description_en: "Small deposit savings scheme for girl children with preferential interest rates.",
    description_hi: "बालिकाओं के लिए अधिमान्य ब्याज दरों वाली छोटी जमा बचत योजना।",
    ministry: "Ministry of Finance",
    official_url: "https://financialservices.gov.in",
    status: "ACTIVE",
    created_at: "2026-09-29T00:00:00Z",
  },
];

const mockPmkisanRequirements: SchemeRequirementsResponse = {
  scheme_code: "PM_KISAN",
  scheme_name_en: "Pradhan Mantri Kisan Samman Nidhi",
  scheme_name_hi: "प्रधानमंत्री किसान सम्मान निधि",
  ministry: "Ministry of Agriculture & Farmers Welfare",
  official_url: "https://pmkisan.gov.in",
  policy_version_id: "4947bf8e-9cb5-43f2-bb69-fc22e5aa58da",
  policy_version_code: "v3.0-2023",
  effective_from: "2023-01-01",
  rule_definition_hash: "hash1234567890abcdef",
  fields: [
    {
      field_key: "has_cultivable_land",
      field_type: "boolean",
      label_en: "Do you own cultivable agricultural land?",
      label_hi: "क्या आपके पास कृषि योग्य भूमि है?",
      help_text_en: "Must own cultivable agricultural land registered in land revenue records.",
      required: true,
      default_value: false,
    },
    {
      field_key: "land_area_hectares",
      field_type: "number",
      label_en: "Total Cultivable Land Area (in Hectares)",
      label_hi: "कुल कृषि योग्य भूमि क्षेत्रफल (हेक्टेयर में)",
      help_text_en: "Land area in hectares as per land records.",
      required: false,
      default_value: 0.0,
    },
  ],
  evidence_types: [
    {
      evidence_type: "LAND_OWNERSHIP_RECORD",
      label_en: "Land Ownership Record (RoR / 7/12 / Khatoni / Khasra)",
      label_hi: "भू-अभिलेख / खतौनी / 7/12 नकल",
      description_en: "Updated Land Revenue Record confirming cultivable land ownership.",
      description_hi: "कृषि योग्य भूमि स्वामित्व की पुष्टि करने वाला भू-राजस्व रिकॉर्ड।",
      mandatory: true,
    },
    {
      evidence_type: "AADHAAR_CARD",
      label_en: "Aadhaar Card",
      label_hi: "आधार कार्ड",
      description_en: "UIDAI Aadhaar Card for statutory beneficiary identification.",
      description_hi: "लाभार्थी पहचान हेतु यूआईडीएआई आधार कार्ड।",
      mandatory: true,
    },
  ],
};

const mockDraftDetail: CitizenApplicationDetail = {
  id: "draft-app-001",
  application_ref: "APP-2026-DRAFT001",
  scheme_id: "scheme-pmkisan",
  scheme_code: "PM_KISAN",
  scheme_name: "Pradhan Mantri Kisan Samman Nidhi",
  scheme_name_hi: "प्रधानमंत्री किसान सम्मान निधि",
  ministry: "Ministry of Agriculture & Farmers Welfare",
  state: "DRAFT",
  status_label_en: "Draft",
  status_label_hi: "प्रारूप",
  created_at: "2026-09-29T10:00:00Z",
  updated_at: "2026-09-29T10:00:00Z",
  submitted_at: null,
  policy_version_id: "4947bf8e-9cb5-43f2-bb69-fc22e5aa58da",
  policy_version_code: "v3.0-2023",
  evaluation_outcome: null,
  citizen_ref: "SYN-CIT-DEMO0001",
  citizen_name: "Test Citizen (Demo)",
  claims_count: 0,
  evidence_count: 0,
  claims: [],
  allowed_actions: ["UPDATE_DRAFT", "SUBMIT"],
  transitions: [
    {
      id: "tr-1",
      journey_id: "draft-app-001",
      from_state: "DRAFT",
      to_state: "DRAFT",
      actor: "CITIZEN",
      reason: "Initial draft initialized",
      created_at: "2026-09-29T10:00:00Z",
    },
  ],
};

describe("Phase C: Citizen Generic Application Creation & Submission", () => {
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
    mockSearchParams = new URLSearchParams();
  });

  it("1. Available Schemes Catalog renders flagship schemes and links to application wizard", async () => {
    (citizenApi.getAvailableSchemes as jest.Mock).mockResolvedValue(mockAvailableSchemes);

    render(
      <AuthProvider>
        <CitizenSchemesPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Pradhan Mantri Kisan Samman Nidhi")).toBeInTheDocument();
      expect(screen.getByText("Sukanya Samriddhi Account Scheme")).toBeInTheDocument();
    });

    expect(screen.getByText("प्रधानमंत्री किसान सम्मान निधि")).toBeInTheDocument();
    expect(screen.getByText("सुकन्या समृद्धि खाता योजना")).toBeInTheDocument();

    // Verify scheme code tags
    expect(screen.getByText("PM_KISAN")).toBeInTheDocument();
    expect(screen.getByText("SSY")).toBeInTheDocument();

    // Search filter test
    const searchInput = screen.getByPlaceholderText(/Search scheme by name or ministry.../i);
    fireEvent.change(searchInput, { target: { value: "Sukanya" } });

    expect(screen.getByText("Sukanya Samriddhi Account Scheme")).toBeInTheDocument();
    expect(screen.queryByText("Pradhan Mantri Kisan Samman Nidhi")).not.toBeInTheDocument();
  });

  it("2. Application Wizard initializes draft, navigates steps, and submits with statutory disclaimer", async () => {
    mockSearchParams = new URLSearchParams("scheme=PM_KISAN");

    (citizenApi.getSchemeRequirements as jest.Mock).mockResolvedValue(mockPmkisanRequirements);
    (citizenApi.createApplication as jest.Mock).mockResolvedValue({
      id: "draft-app-001",
      application_ref: "APP-2026-DRAFT001",
      scheme_code: "PM_KISAN",
      scheme_name: "Pradhan Mantri Kisan Samman Nidhi",
      state: "DRAFT",
      policy_version_id: "4947bf8e-9cb5-43f2-bb69-fc22e5aa58da",
      policy_version_code: "v3.0-2023",
      created_at: "2026-09-29T10:00:00Z",
    });
    (citizenApi.updateDraft as jest.Mock).mockResolvedValue({
      id: "draft-app-001",
      message: "Draft saved",
    });
    (citizenApi.submitApplication as jest.Mock).mockResolvedValue({
      id: "draft-app-001",
      application_ref: "APP-2026-DRAFT001",
      scheme_code: "PM_KISAN",
      scheme_name: "Pradhan Mantri Kisan Samman Nidhi",
      state: "FACTS_COLLECTED",
      status_label_en: "Facts Collected",
      status_label_hi: "तथ्य संगृहीत",
      submitted_at: "2026-09-29T10:15:00Z",
      policy_version_code: "v3.0-2023",
    });

    render(
      <AuthProvider>
        <CitizenApplicationWizardPage />
      </AuthProvider>
    );

    // Step 1: Policy Context
    await waitFor(() => {
      expect(screen.getByText("Step 1 of 4 • Policy Binding")).toBeInTheDocument();
      expect(screen.getAllByText("v3.0-2023").length).toBeGreaterThan(0);
    });

    expect(citizenApi.createApplication).toHaveBeenCalledWith(
      expect.objectContaining({
        scheme_code: "PM_KISAN",
      }),
      expect.anything()
    );

    // Click Proceed to Step 2
    const proceedToStep2 = screen.getByRole("button", { name: /Continue to Declarations/i });
    fireEvent.click(proceedToStep2);

    // Step 2: Factual Declarations
    await waitFor(() => {
      expect(screen.getByText(/Do you own cultivable agricultural land\?/i)).toBeInTheDocument();
    });

    // Enter Land Area
    const landAreaInput = screen.getByPlaceholderText("0.0");
    fireEvent.change(landAreaInput, { target: { value: "2.5" } });

    // Click Proceed to Step 3
    const proceedToStep3 = screen.getByRole("button", { name: /Next: Supporting Evidence/i });
    fireEvent.click(proceedToStep3);

    // Step 3: Evidence Attachments
    await waitFor(() => {
      expect(screen.getByText(/Land Ownership Record \(RoR \/ 7\/12 \/ Khatoni \/ Khasra\)/i)).toBeInTheDocument();
    });

    // Click Proceed to Step 4
    const proceedToStep4 = screen.getByRole("button", { name: /Next: Review Application/i });
    fireEvent.click(proceedToStep4);

    // Step 4: Review and Statutory Declaration
    await waitFor(() => {
      expect(screen.getByText(/Review Application & Submit/i)).toBeInTheDocument();
    });

    // Submit button should be disabled before checking disclaimer
    const submitBtn = screen.getByRole("button", { name: /Submit Application • आवेदन जमा करें/i });
    expect(submitBtn).toBeDisabled();

    // Check disclaimer checkbox
    const disclaimerCheckbox = screen.getByRole("checkbox");
    fireEvent.click(disclaimerCheckbox);
    expect(submitBtn).not.toBeDisabled();

    // Submit application
    fireEvent.click(submitBtn);

    // Step 5: Submitted Confirmation
    await waitFor(() => {
      expect(screen.getByText(/Application Successfully Submitted • आवेदन सफलतापूर्वक जमा हुआ/i)).toBeInTheDocument();
      expect(screen.getByText("APP-2026-DRAFT001")).toBeInTheDocument();
    });

    expect(citizenApi.submitApplication).toHaveBeenCalledWith(
      "draft-app-001",
      expect.objectContaining({
        declaration_confirmed: true,
      }),
      expect.anything()
    );
  });

  it("3. Applications List page shows Draft badge and Resume Application button for unsubmitted drafts", async () => {
    const mockAppsWithDraft: CitizenApplicationSummary[] = [
      {
        id: "draft-app-001",
        application_ref: "APP-2026-DRAFT001",
        scheme_id: "scheme-pmkisan",
        scheme_code: "PM_KISAN",
        scheme_name: "Pradhan Mantri Kisan Samman Nidhi",
        scheme_name_hi: "प्रधानमंत्री किसान सम्मान निधि",
        ministry: "Ministry of Agriculture & Farmers Welfare",
        state: "DRAFT",
        status_label_en: "Draft",
        status_label_hi: "प्रारूप",
        created_at: "2026-09-29T10:00:00Z",
        updated_at: "2026-09-29T10:00:00Z",
        submitted_at: null,
        policy_version_id: "4947bf8e-9cb5-43f2-bb69-fc22e5aa58da",
        policy_version_code: "v3.0-2023",
        evaluation_outcome: null,
        claims_count: 0,
        evidence_count: 0,
      },
    ];

    (citizenApi.getApplications as jest.Mock).mockResolvedValue(mockAppsWithDraft);

    render(
      <AuthProvider>
        <CitizenApplicationsPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("APP-2026-DRAFT001")).toBeInTheDocument();
    });

    expect(screen.getByText(/प्रारूप \/ Draft/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /आवेदन पूरा करें \/ Resume/i })).toBeInTheDocument();
  });

  it("4. Application Dossier displays unsubmitted draft notice banner with direct resume button", async () => {
    (citizenApi.getApplicationDetail as jest.Mock).mockResolvedValue(mockDraftDetail);

    render(
      <AuthProvider>
        <CitizenApplicationDetailPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("APP-2026-DRAFT001")).toBeInTheDocument();
    });

    expect(screen.getByText(/यह आवेदन अभी प्रारूप में है \/ Application is in Draft State/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /आवेदन पूरा करें एवं जमा करें \/ Complete & Submit/i })).toBeInTheDocument();
    expect(screen.getByText(/असमर्पित प्रारूप \/ Draft \(Not Yet Submitted\)/i)).toBeInTheDocument();
  });
});
