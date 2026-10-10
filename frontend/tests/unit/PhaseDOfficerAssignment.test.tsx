import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import OfficerDashboardPage from "../../src/app/officer/page";
import OfficerQueuePage from "../../src/app/officer/queue/page";
import CaseOverviewPage from "../../src/app/officer/cases/[journeyId]/page";
import { OfficerAuthProvider } from "../../src/context/OfficerAuthContext";
import { CaseProvider } from "../../src/app/officer/cases/[journeyId]/CaseContext";
import { officerApi } from "../../src/api/officer";
import {
  OfficerCaseDetail,
  OfficerDashboardStats,
  OfficerQueueListResponse,
} from "../../src/types/officer";

// Mock next/navigation
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
  }),
  usePathname: () => "/officer",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ journeyId: "journey-test-123" }),
}));

// Mock officerApi
jest.mock("../../src/api/officer", () => ({
  officerApi: {
    login: jest.fn(),
    getProfile: jest.fn(),
    getDashboardStats: jest.fn(),
    getQueue: jest.fn(),
    getCaseDetail: jest.fn(),
    assignCase: jest.fn(),
    reassignCase: jest.fn(),
    autoAssignCase: jest.fn(),
    getAssignments: jest.fn(),
  },
}));

const mockStats: OfficerDashboardStats = {
  my_active_requests: 4,
  unassigned_requests: 6,
  due_soon: 2,
  overdue: 1,
  completed: 8,
  total_active_workload: 12,
  max_capacity_per_officer: 15,
  default_sla_duration_hours: 48,
};

const mockQueueResponse: OfficerQueueListResponse = {
  metrics: {
    total_cases: 3,
    pending_cases: 2,
    in_review_cases: 1,
    escalated_cases: 0,
    completed_cases: 0,
  },
  items: [
    {
      journey_id: "journey-1",
      citizen_ref: "SYN-CIT-100001",
      scheme_code: "PM_KISAN",
      scheme_name: "PM-KISAN Samman Nidhi",
      journey_state: "EVIDENCE_PENDING",
      submitted_at: "2026-09-29T10:00:00Z",
      review_status: "PENDING",
      review_decision: null,
      evidence_count: 2,
      verified_evidence_count: 0,
      automated_eligibility: "ELIGIBLE",
      assigned_officer: "officer@yogyatamitra.local",
      assigned_officer_name: "Senior Verification Officer (Demo)",
      assignment_status: "ASSIGNED",
      assigned_at: "2026-09-29T10:05:00Z",
      due_at: "2026-10-01T10:05:00Z",
      sla_status: "NOT_DUE",
    },
    {
      journey_id: "journey-2",
      citizen_ref: "SYN-CIT-100002",
      scheme_code: "SSY",
      scheme_name: "Sukanya Samriddhi Yojana",
      journey_state: "EVIDENCE_PENDING",
      submitted_at: "2026-09-29T11:00:00Z",
      review_status: "PENDING",
      review_decision: null,
      evidence_count: 1,
      verified_evidence_count: 0,
      automated_eligibility: null,
      assigned_officer: null,
      assigned_officer_name: null,
      assignment_status: "UNASSIGNED",
      assigned_at: null,
      due_at: null,
      sla_status: "NOT_DUE",
    },
  ],
};

const mockCaseDetail: OfficerCaseDetail = {
  journey_id: "journey-test-123",
  citizen_ref: "SYN-CIT-999999",
  scheme_code: "PM_KISAN",
  scheme_name: "PM-KISAN Samman Nidhi",
  journey_state: "EVIDENCE_PENDING",
  submitted_at: "2026-09-29T09:00:00Z",
  updated_at: "2026-09-29T09:30:00Z",
  review_status: "PENDING",
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
      source: "CITIZEN_DECLARATION",
      status: "CLAIMED",
      claimed_at: "2026-09-29T09:00:00Z",
    },
  ],
  evidence_items: [
    {
      id: "ev-1",
      claim_id: "claim-1",
      claim_type: "family.owns_cultivable_land",
      evidence_type: "LAND_RECORD",
      evidence_type_label: "Land Ownership Record / Record of Rights (RoR)",
      storage_reference: "evidence/ror_doc_123.pdf",
      metadata_json: { document_name: "RoR_Khatoni.pdf" },
      status: "PENDING",
      submitted_at: "2026-09-29T09:00:00Z",
      verification_records: [],
    },
  ],
  audit_history: [],
  active_assignment: {
    id: "assign-1",
    journey_id: "journey-test-123",
    officer_identity: "officer@yogyatamitra.local",
    officer_name: "Senior Verification Officer (Demo)",
    assigned_by: "SYSTEM_BALANCER",
    assigned_at: "2026-09-29T09:05:00Z",
    due_at: "2026-10-01T09:05:00Z",
    sla_duration_hours: 48,
    status: "ASSIGNED",
    is_active: true,
    reassigned_to_id: null,
    reassignment_reason: null,
    sla_status: "NOT_DUE",
    created_at: "2026-09-29T09:05:00Z",
    updated_at: "2026-09-29T09:05:00Z",
  },
  assignment_history: [
    {
      id: "assign-1",
      journey_id: "journey-test-123",
      officer_identity: "officer@yogyatamitra.local",
      officer_name: "Senior Verification Officer (Demo)",
      assigned_by: "SYSTEM_BALANCER",
      assigned_at: "2026-09-29T09:05:00Z",
      due_at: "2026-10-01T09:05:00Z",
      sla_duration_hours: 48,
      status: "ASSIGNED",
      is_active: true,
      reassigned_to_id: null,
      reassignment_reason: null,
      sla_status: "NOT_DUE",
      created_at: "2026-09-29T09:05:00Z",
      updated_at: "2026-09-29T09:05:00Z",
    },
  ],
};

describe("Phase D — Officer Assignment, Workload & SLA Portal", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    localStorage.setItem("yogyatamitra_officer_token", "fake-officer-token");
    localStorage.setItem(
      "yogyatamitra_officer_profile",
      JSON.stringify({
        email: "officer@yogyatamitra.local",
        name: "Senior Verification Officer (Demo)",
        role: "OFFICER",
        designation: "Verification Officer Grade II",
        department: "Welfare Verification Cell",
      })
    );
    (officerApi.getProfile as jest.Mock).mockResolvedValue({
      email: "officer@yogyatamitra.local",
      role: "OFFICER",
      name: "Senior Verification Officer (Demo)",
      designation: "Verification Officer Grade II",
      department: "Welfare Verification Cell",
    });
    (officerApi.getDashboardStats as jest.Mock).mockResolvedValue(mockStats);
    (officerApi.getQueue as jest.Mock).mockResolvedValue(mockQueueResponse);
    (officerApi.getCaseDetail as jest.Mock).mockResolvedValue(mockCaseDetail);
  });

  afterEach(() => {
    localStorage.clear();
  });

  test("Officer Dashboard renders database-driven workload and SLA counters", async () => {
    render(
      <OfficerAuthProvider>
        <OfficerDashboardPage />
      </OfficerAuthProvider>
    );

    // Verify title and statutory notice
    await waitFor(() => {
      expect(screen.getByText(/Officer Verification Dashboard/i)).toBeInTheDocument();
      expect(screen.getByText(/Statutory Notice:/i)).toBeInTheDocument();
    });

    // Verify database-backed counters
    expect(screen.getByText("My Active")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument(); // my_active_requests

    expect(screen.getByText("Unassigned")).toBeInTheDocument();
    expect(screen.getByText("6")).toBeInTheDocument(); // unassigned_requests

    expect(screen.getByText("Due Soon")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument(); // due_soon

    expect(screen.getByText("Overdue SLA")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument(); // overdue

    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument(); // completed

    expect(screen.getByText("Total Active")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument(); // total_active_workload

    // Verify capacity and SLA cards
    expect(screen.getByText(/Workload Capacity Governance/i)).toBeInTheDocument();
    expect(screen.getByText(/15 active cases/i)).toBeInTheDocument();
    expect(screen.getByText(/48 hours \(2 days\)/i)).toBeInTheDocument();
  });

  test("Officer Queue displays assigned officers, SLA badges, and scope filter", async () => {
    render(
      <OfficerAuthProvider>
        <OfficerQueuePage />
      </OfficerAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Verification Queue/i)).toBeInTheDocument();
      expect(screen.getByText(/Scope:/i)).toBeInTheDocument();
      expect(screen.getByText(/All Applications/i)).toBeInTheDocument();
    });

    // Verify table renders items
    await waitFor(() => {
      expect(screen.getByText("SYN-CIT-100001")).toBeInTheDocument();
      expect(screen.getByText("Senior Verification Officer (Demo)")).toBeInTheDocument();
      expect(screen.getAllByText("On Track").length).toBeGreaterThan(0);

      expect(screen.getByText("SYN-CIT-100002")).toBeInTheDocument();
      expect(screen.getAllByText("Unassigned").length).toBeGreaterThan(0);
      expect(screen.getByText("Auto-Assign")).toBeInTheDocument();
    });
  });

  test("Officer Case Detail renders operational assignment card, due date, and reassignment controls", async () => {
    render(
      <OfficerAuthProvider>
        <CaseProvider journeyId="journey-test-123">
          <CaseOverviewPage />
        </CaseProvider>
      </OfficerAuthProvider>
    );

    // Verify case overview title
    await waitFor(() => {
      expect(screen.getByText(/Operational Officer Assignment & SLA Tracking/i)).toBeInTheDocument();
      expect(screen.getByText(/Assigned Officer:/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Senior Verification Officer \(Demo\) \(officer@yogyatamitra\.local\)/i)).toBeInTheDocument();
    expect(screen.getByText(/SLA Target Due Date:/i)).toBeInTheDocument();

    // Verify evidence is displayed as read-only references without verification controls
    expect(screen.getByText(/Submitted Evidence References \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Land Ownership Record \/ Record of Rights \(RoR\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Storage Ref: evidence\/ror_doc_123\.pdf/i)).toBeInTheDocument();

    // Open reassignment form
    const reassignButton = screen.getByRole("button", { name: /Reassign Case/i });
    fireEvent.click(reassignButton);

    expect(screen.getByText(/Reassign Case to New Officer/i)).toBeInTheDocument();
    expect(screen.getByText(/Justification \/ Reason \(Mandatory\):/i)).toBeInTheDocument();
  });
});
