import React from "react";
import { render, screen } from "@testing-library/react";
import { ExplainabilityView } from "../../src/components/evaluation/ExplainabilityView";
import { EligibilityResult } from "../../src/types/enums";
import { EvaluationResponse } from "../../src/types/evaluation";
import { LanguageProvider } from "../../src/context/LanguageContext";

const mockIneligibleEvaluation: EvaluationResponse = {
  evaluation_id: "e9b5f884-1122-4433-8899-aabbccddeeff",
  scheme_code: "PM_KISAN",
  policy_version_code: "v3.0-2023",
  rule_definition_hash: "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
  evaluation_date: "2024-01-15",
  effective_from: "2023-07-01",
  effective_to: null,
  overall_result: EligibilityResult.INELIGIBLE,
  root_truth_value: "FALSE",
  reasons_en: ["Disqualified due to income tax payment."],
  reasons_hi: ["आयकर दाता होने के कारण योजना से बहिष्कृत।"],
  missing_fields: ["family.owns_cultivable_land"],
  satisfied_rules: ["R_LAND"],
  failed_rules: ["R_EXCLUSION_INCOME_TAX"],
  unknown_rules: [],
  blockers: [
    {
      code: "DISQUALIFIED_INCOME_TAX",
      category: "DISQUALIFYING_CONDITION",
      field_path: "family.has_income_tax_payer",
      rule_id: "R_EXCLUSION_INCOME_TAX",
      message_en: "Family paid income tax in last assessment year.",
      message_hi: "परिवार के सदस्य द्वारा पिछले निर्धारण वर्ष में आयकर का भुगतान किया गया है।",
    },
  ],
  audit_persisted: true,
  created_at: "2024-01-15T10:00:00Z",
};

describe("ExplainabilityView Component — Citizen Presentation", () => {
  it("renders blockers with friendly localized title and citizen explanation message", () => {
    render(
      <LanguageProvider>
        <ExplainabilityView evaluation={mockIneligibleEvaluation} />
      </LanguageProvider>
    );

    expect(screen.getByText(/आयकर निर्धारण स्थिति/i)).toBeInTheDocument();
    expect(screen.getByText(/आयकर का भुगतान किया गया है/i)).toBeInTheDocument();
    expect(screen.getByText(/कृषि योग्य भूमि का स्वामित्व/i)).toBeInTheDocument();
  });

  it("does NOT render technical blocker codes, raw field paths, rule IDs, or SHA-256 hashes", () => {
    render(
      <LanguageProvider>
        <ExplainabilityView evaluation={mockIneligibleEvaluation} />
      </LanguageProvider>
    );

    // No raw internal codes
    expect(screen.queryByText("DISQUALIFIED_INCOME_TAX")).not.toBeInTheDocument();
    expect(screen.queryByText("R_EXCLUSION_INCOME_TAX")).not.toBeInTheDocument();
    expect(screen.queryByText("R_LAND")).not.toBeInTheDocument();

    // No raw fact dot paths
    expect(screen.queryByText(/family\.has_income_tax_payer/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/family\.owns_cultivable_land/i)).not.toBeInTheDocument();

    // No SHA-256 hashes
    expect(screen.queryByText(/SHA-256/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/a1b2c3d4e5f6/i)).not.toBeInTheDocument();
  });
});
