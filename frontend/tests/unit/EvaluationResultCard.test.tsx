import React from "react";
import { render, screen } from "@testing-library/react";
import { EvaluationResultCard } from "../../src/components/evaluation/EvaluationResultCard";
import { EligibilityResult } from "../../src/types/enums";
import { EvaluationResponse } from "../../src/types/evaluation";
import { LanguageProvider } from "../../src/context/LanguageContext";

const mockEvaluation: EvaluationResponse = {
  evaluation_id: "e9b5f884-1122-4433-8899-aabbccddeeff",
  scheme_code: "PM_KISAN",
  policy_version_code: "v3.0-2023",
  rule_definition_hash: "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
  evaluation_date: "2024-01-15",
  effective_from: "2023-07-01",
  effective_to: null,
  overall_result: EligibilityResult.ELIGIBLE,
  root_truth_value: "TRUE",
  reasons_en: ["Family satisfies all statutory landholding and exclusion criteria."],
  reasons_hi: ["परिवार भूमि स्वामित्व और बहिष्करण संबंधी सभी वैधानिक मानदंडों को पूरा करता है।"],
  missing_fields: [],
  satisfied_rules: ["R_CULTIVABLE_LAND", "R_EXCLUSIONS_NONE"],
  failed_rules: [],
  unknown_rules: [],
  blockers: [],
  audit_persisted: true,
  created_at: "2024-01-15T10:00:00Z",
};

describe("EvaluationResultCard Component — Citizen Presentation", () => {
  it("renders citizen policy details, dates, official source and view link", () => {
    render(
      <LanguageProvider>
        <EvaluationResultCard evaluation={mockEvaluation} />
      </LanguageProvider>
    );

    expect(screen.getByRole("heading", { name: /योजना के लिए पूर्णतः पात्र/i })).toBeInTheDocument();
    expect(screen.getByText("PM-KISAN")).toBeInTheDocument();
    expect(screen.getByText("v3.0-2023")).toBeInTheDocument();
    expect(screen.getByText("2023-07-01")).toBeInTheDocument();
    expect(screen.getByText("2024-01-15")).toBeInTheDocument();
    expect(screen.getByText(/नीति विवरण देखें/i)).toBeInTheDocument();
  });

  it("does NOT render technical SHA-256 hashes, UUIDs, or internal IDs into the citizen DOM", () => {
    render(
      <LanguageProvider>
        <EvaluationResultCard evaluation={mockEvaluation} />
      </LanguageProvider>
    );

    // Assert absence of SHA-256 rule hash
    expect(screen.queryByText(/a1b2c3d4e5f6/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/SHA-256/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/canonical rule hash/i)).not.toBeInTheDocument();

    // Assert absence of evaluation UUID and internal IDs
    expect(screen.queryByText(/e9b5f884/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/aabbccddeeff/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/evaluation_id/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^ID:/i)).not.toBeInTheDocument();

    // Assert absence of technical details disclosure
    expect(screen.queryByText(/तकनीकी ऑडिट विवरण/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Technical Audit Details/i)).not.toBeInTheDocument();
  });
});
