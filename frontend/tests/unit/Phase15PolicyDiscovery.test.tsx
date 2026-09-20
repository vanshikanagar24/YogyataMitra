import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import PolicyDiscoveryQueuePage from "../../src/app/officer/policy-discovery/page";
import PolicyDiscoveryCandidatePage from "../../src/app/officer/policy-discovery/[candidateId]/page";
import { OfficerAuthProvider } from "../../src/context/OfficerAuthContext";

// Mock next/navigation
const mockRouter = {
  push: jest.fn(),
  replace: jest.fn(),
  back: jest.fn(),
  forward: jest.fn(),
  prefetch: jest.fn(),
  refresh: jest.fn(),
};

jest.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  usePathname: () => "/officer/policy-discovery",
  useParams: () => ({ candidateId: "cand-uuid-12345" }),
}));

// Mock officerApi
jest.mock("../../src/api/officer", () => ({
  officerApi: {
    getProfile: jest.fn().mockResolvedValue({
      id: "usr-officer-01",
      email: "officer@yogyatamitra.gov.in",
      role: "OFFICER",
      name: "Inspector Rajesh",
    }),
  },
}));

// Mock localStorage with the exact keys used in OfficerAuthContext
const mockLocalStorage = (() => {
  let store: Record<string, string> = {
    yogyatamitra_officer_token: "mock-officer-jwt-token",
    yogyatamitra_officer_profile: JSON.stringify({
      id: "usr-officer-01",
      email: "officer@yogyatamitra.gov.in",
      role: "OFFICER",
      name: "Inspector Rajesh",
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
  source_excerpt: "Bank accounts receiving the financial benefit of Rs. 6000 per annum must be strictly Aadhaar-seeded.",
  discovered_at: "2026-09-19T10:00:00Z",
  discovered_by: "system",
  ai_provider: "MOCK_GOV_DISCOVERY_AGENT",
  ai_model: "mock-statutory-agent-v1",
  ai_run_id: "run-mock-12345",
  extraction_confidence: 0.95,
  confidence_explanation: "Directly referenced from official operational circular.",
  uncertainty_notes: null,
  questions_for_reviewer: ["Should non-seeded accounts be subject to immediate temporary pause?"],
  provenance_status: "OFFICIAL_PORTAL",
  effective_date_status: "CONFIRMED",
  conflict_detected: false,
  conflict_details_json: null,
  duplicate_status: "UNIQUE",
  duplicate_of_id: null,
  review_status: "PENDING_REVIEW",
  reviewer_id: null,
  reviewer_role: null,
  reviewed_at: null,
  reviewer_reason: null,
  created_at: "2026-09-19T10:00:00Z",
  updated_at: "2026-09-19T10:00:00Z",
  review_events: [
    {
      id: "ev-1",
      candidate_id: "cand-uuid-12345",
      actor_identity: "system",
      actor_role: "SYSTEM",
      previous_status: null,
      new_status: "PENDING_REVIEW",
      action: "DISCOVER",
      reason: "Extracted from official circular DOA/PMK/2024/CIR-08.",
      details_json: null,
      created_at: "2026-09-19T10:00:00Z",
    },
  ],
};

const mockQueueResponse = {
  candidates: [mockCandidate],
  total: 1,
  metrics: {
    total_candidates: 1,
    pending_review: 1,
    in_review: 0,
    needs_clarification: 0,
    approved: 0,
    rejected: 0,
    archived: 0,
    conflict_detected: 0,
  },
};

describe("Phase 15: AI-Assisted Policy Discovery & Review Frontend", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn((url: string | Request | URL) => {
      const urlStr = url.toString();
      if (urlStr.includes("/api/v1/officer/policy-discovery/candidates?")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockQueueResponse),
        } as Response);
      }
      if (urlStr.includes("/api/v1/officer/policy-discovery/candidates/cand-uuid-12345/history")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockCandidate.review_events),
        } as Response);
      }
      if (urlStr.includes("/api/v1/officer/policy-discovery/candidates/cand-uuid-12345")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockCandidate),
        } as Response);
      }
      if (urlStr.includes("/api/v1/officer/policy-discovery/discover")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([mockCandidate]),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      } as Response);
    }) as jest.Mock;
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test("renders policy discovery queue dashboard with non-executable advisory banner and metrics", async () => {
    render(
      <OfficerAuthProvider>
        <PolicyDiscoveryQueuePage />
      </OfficerAuthProvider>
    );

    // Advisory banner check
    await waitFor(
      () => {
        expect(screen.getByText(/ADVISORY INTELLIGENCE/i)).toBeInTheDocument();
      },
      { timeout: 4000 }
    );

    // Metrics cards check
    expect(screen.getByText(/Total Candidates/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Pending Review/i).length).toBeGreaterThan(0);

    // Candidate card check
    await waitFor(
      () => {
        expect(
          screen.getByText("Mandatory Aadhaar Seeding and e-KYC Protocol")
        ).toBeInTheDocument();
      },
      { timeout: 4000 }
    );

    expect(screen.getAllByText(/PM_KISAN|PM-KISAN/i).length).toBeGreaterThan(0);
  });

  test("renders candidate dossier page with 3-way visual separation and statutory advisory", async () => {
    render(
      <OfficerAuthProvider>
        <PolicyDiscoveryCandidatePage />
      </OfficerAuthProvider>
    );

    // Wait for full candidate dossier to render
    await waitFor(
      () => {
        expect(
          screen.getByText(/AI ADVISORY DISCOVERY • HUMAN APPROVAL REQUIRED/i)
        ).toBeInTheDocument();
        expect(
          screen.getByText(/AI Suggestion \(Advisory Extraction\)/i)
        ).toBeInTheDocument();
      },
      { timeout: 4000 }
    );

    expect(screen.getByText(/Official Government Source & Provenance/i)).toBeInTheDocument();

    // English text content
    expect(
      screen.getByText(
        /All eligible landholder farmer families must complete biometric or OTP-based e-KYC/i
      )
    ).toBeInTheDocument();

    // Provenance details
    expect(screen.getByText("PM-KISAN Operational Guidelines")).toBeInTheDocument();
    expect(screen.getAllByText(/DOA\/PMK\/2024\/CIR-08/i).length).toBeGreaterThan(0);
  });

  test("restricts PENDING_REVIEW candidate to START_REVIEW action only", async () => {
    render(
      <OfficerAuthProvider>
        <PolicyDiscoveryCandidatePage />
      </OfficerAuthProvider>
    );

    await waitFor(
      () => {
        expect(screen.getByText(/Authorized Review Determination/i)).toBeInTheDocument();
      },
      { timeout: 4000 }
    );

    // In PENDING_REVIEW, only START_REVIEW action should be available
    expect(screen.getByDisplayValue("START_REVIEW")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("APPROVE")).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue("REJECT")).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue("ARCHIVE")).not.toBeInTheDocument();
  });

  test("enforces mandatory reason for approval and displays non-statutory disclaimer", async () => {
    (global.fetch as jest.Mock).mockImplementation((url: string | Request | URL) => {
      const urlStr = url.toString();
      if (urlStr.includes("/api/v1/officer/policy-discovery/candidates/cand-uuid-12345/history")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockCandidate.review_events),
        } as Response);
      }
      if (urlStr.includes("/api/v1/officer/policy-discovery/candidates/cand-uuid-12345")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...mockCandidate, review_status: "IN_REVIEW" }),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      } as Response);
    });

    render(
      <OfficerAuthProvider>
        <PolicyDiscoveryCandidatePage />
      </OfficerAuthProvider>
    );

    await waitFor(
      () => {
        expect(
          screen.getByText(/AI ADVISORY DISCOVERY • HUMAN APPROVAL REQUIRED/i)
        ).toBeInTheDocument();
        expect(
          screen.getByText(/Authorized Review Determination/i)
        ).toBeInTheDocument();
      },
      { timeout: 4000 }
    );

    // Non-statutory approval disclaimer presence
    expect(screen.getByText(/AI is not a statutory authority/i)).toBeInTheDocument();

    // Select APPROVE radio (available in IN_REVIEW state)
    const approveRadio = screen.getByDisplayValue("APPROVE");
    fireEvent.click(approveRadio);

    // Enter short reason (< 5 characters) to test client-side enforcement
    const reasonTextarea = screen.getByPlaceholderText(
      /Explain the evidentiary basis for approving/i
    );
    fireEvent.change(reasonTextarea, { target: { value: "ok" } });

    // Submit determination
    const submitBtn = screen.getByRole("button", { name: /Commit Determination to Audit Trail/i });
    const form = submitBtn.closest("form");
    if (form) {
      fireEvent.submit(form);
    } else {
      fireEvent.click(submitBtn);
    }

    // Should indicate reason is required
    await waitFor(
      () => {
        expect(
          screen.getByText(/Mandatory.*justification reason.*5 characters/i)
        ).toBeInTheDocument();
      },
      { timeout: 4000 }
    );
  });

  test("renders audit history events in chronological sequence", async () => {
    render(
      <OfficerAuthProvider>
        <PolicyDiscoveryCandidatePage />
      </OfficerAuthProvider>
    );

    await waitFor(
      () => {
        expect(screen.getByText(/Append-Only Review Audit Trail/i)).toBeInTheDocument();
      },
      { timeout: 4000 }
    );

    // Initial discover event in audit history
    await waitFor(
      () => {
        expect(
          screen.getByText(/Extracted from official circular DOA\/PMK\/2024\/CIR-08/i)
        ).toBeInTheDocument();
      },
      { timeout: 4000 }
    );
  });
});
