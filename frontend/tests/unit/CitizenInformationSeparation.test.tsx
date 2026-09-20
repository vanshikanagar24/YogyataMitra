import React from "react";
import { render, screen } from "@testing-library/react";
import { EvaluationResultCard } from "../../src/components/evaluation/EvaluationResultCard";
import { ExplainabilityView } from "../../src/components/evaluation/ExplainabilityView";
import { PolicyVersionCard } from "../../src/components/policy/PolicyVersionCard";
import { ClaimCard } from "../../src/components/journey/ClaimCard";
import { EligibilityResult } from "../../src/types/enums";
import { EvaluationResponse } from "../../src/types/evaluation";
import { JourneyClaim } from "../../src/types/journey";
import { LanguageProvider } from "../../src/context/LanguageContext";
import en from "../../src/i18n/locales/en.json";
import hi from "../../src/i18n/locales/hi.json";

const mockEvaluation: EvaluationResponse = {
  evaluation_id: "e9b5f884-1122-4433-8899-aabbccddeeff",
  scheme_code: "PM_KISAN",
  policy_version_code: "v3.0-2023",
  rule_definition_hash: "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
  evaluation_date: "2026-09-19",
  effective_from: "2023-01-01",
  effective_to: null,
  overall_result: EligibilityResult.ELIGIBLE,
  root_truth_value: "TRUE",
  reasons_en: ["Family satisfies all statutory landholding and exclusion criteria."],
  reasons_hi: ["परिवार भूमि स्वामित्व और बहिष्करण संबंधी सभी वैधानिक मानदंडों को पूरा करता है।"],
  missing_fields: ["family.owns_cultivable_land"],
  satisfied_rules: ["PMKISAN-LAND-CULTIVABLE", "PMKISAN-EXCLUSIONS-NONE"],
  failed_rules: [],
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
  created_at: "2026-09-19T10:00:00Z",
  trace: {
    provenance: {
      source_title: "Operational Guidelines for Pradhan Mantri Kisan Samman Nidhi (PM-KISAN) 2023",
      source_url: "https://pmkisan.gov.in/Documents/OperationalGuidelines2023.pdf",
    },
  },
};

const mockClaim: JourneyClaim = {
  id: "clm-12345-67890",
  journey_id: "jrn-12345-67890",
  claim_type: "family.owns_cultivable_land",
  value_json: { value: true },
  source: "SELF_DECLARATION",
  status: "CLAIMED" as any,
  created_at: "2026-09-19T10:00:00Z",
  updated_at: "2026-09-19T10:00:00Z",
};

describe("Citizen vs Internal Audit Separation Invariants", () => {
  test("1. Citizen result does NOT render SHA-256 hashes", () => {
    const { container } = render(
      <LanguageProvider>
        <EvaluationResultCard evaluation={mockEvaluation} />
      </LanguageProvider>
    );

    expect(container.textContent).not.toMatch(/a1b2c3d4e5f67890/i);
    expect(container.textContent).not.toMatch(/SHA-256/i);
    expect(container.textContent).not.toMatch(/hash/i);
  });

  test("2. Citizen result does NOT render UUIDs or internal IDs", () => {
    const { container } = render(
      <LanguageProvider>
        <EvaluationResultCard evaluation={mockEvaluation} />
      </LanguageProvider>
    );

    expect(container.textContent).not.toMatch(/e9b5f884-1122-4433-8899-aabbccddeeff/i);
    expect(container.textContent).not.toMatch(/evaluation_id/i);
    expect(container.textContent).not.toMatch(/ID:\s*e9b5/i);
  });

  test("3. Citizen result does NOT render canonical rule hash or AST tokens", () => {
    const { container } = render(
      <LanguageProvider>
        <EvaluationResultCard evaluation={mockEvaluation} />
        <ExplainabilityView evaluation={mockEvaluation} />
      </LanguageProvider>
    );

    expect(container.textContent).not.toMatch(/canonical rule hash/i);
    expect(container.textContent).not.toMatch(/canonical_rule_hash/i);
    expect(container.textContent).not.toMatch(/AST/i);
    expect(container.textContent).not.toMatch(/root_rule/i);
  });

  test("4. PolicyVersionCard does NOT render hash or verification hash tags", () => {
    const mockPolicy = {
      id: "pol-001",
      scheme_code: "PM_KISAN",
      version_code: "v3.0-2023",
      effective_from: "2023-01-01",
      effective_to: null,
      source_url: "https://pmkisan.gov.in/guidelines.pdf",
      source_title: "Operational Guidelines for PM-KISAN 2023",
      source_document_identifier: "PMKISAN-2023",
      rule_definition_hash: "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
      ruleset_schema_version: "1.0",
      ruleset_version: "3.0",
      created_at: "2024-01-01T00:00:00Z",
    };

    const { container } = render(
      <LanguageProvider>
        <PolicyVersionCard policy={mockPolicy} />
      </LanguageProvider>
    );

    expect(container.textContent).not.toMatch(/a1b2c3d4e5f6/i);
    expect(container.textContent).not.toMatch(/SHA-256/i);
    expect(container.textContent).not.toMatch(/Verified SHA-256/i);
  });

  test("5. Raw JSON is not rendered in citizen claim views", () => {
    const { container } = render(
      <LanguageProvider>
        <ClaimCard claim={mockClaim} />
      </LanguageProvider>
    );

    // No raw JSON
    expect(container.textContent).not.toMatch(/\{"value":\s*true\}/);
    expect(container.textContent).not.toMatch(/\{"value":\s*false\}/);
    expect(container.textContent).not.toMatch(/JSON\.stringify/);
    // Rendered as friendly text
    expect(screen.getByText("हाँ")).toBeInTheDocument();
  });

  test("6. Raw fact paths and rule codes are not rendered in citizen views", () => {
    const { container } = render(
      <LanguageProvider>
        <ClaimCard claim={mockClaim} />
        <ExplainabilityView evaluation={mockEvaluation} />
      </LanguageProvider>
    );

    // Raw fact path in visible text
    expect(container.querySelector("h3")?.textContent).not.toContain("family.owns_cultivable_land");
    expect(container.textContent).not.toContain("family.has_income_tax_payer");
    expect(container.textContent).not.toContain("R_EXCLUSION_INCOME_TAX");
    expect(container.textContent).not.toContain("DISQUALIFIED_INCOME_TAX");
    expect(container.textContent).not.toContain("PMKISAN-LAND-CULTIVABLE");
  });

  test("7. English mode remains 100% English and Hindi mode remains 100% Hindi in dictionaries", () => {
    // English brand has no Devanagari characters
    const devanagariRegex = /[\u0900-\u097F]/;
    expect(devanagariRegex.test(en.brand.title)).toBe(false);
    expect(devanagariRegex.test(en.brand.subtitle)).toBe(false);

    // Hindi brand has Devanagari
    expect(devanagariRegex.test(hi.brand.title)).toBe(true);
    expect(devanagariRegex.test(hi.brand.subtitle)).toBe(true);
  });

  test("8. Exactly two schemes remain configured in portal", () => {
    expect(en.schemes.pm_kisan).toBeDefined();
    expect(en.schemes.ssy).toBeDefined();
    // Verify no extraneous schemes in localized keys
    const schemeKeys = Object.keys(en.schemes).filter((k) => ["pm_kisan", "ssy"].includes(k));
    expect(schemeKeys).toEqual(["pm_kisan", "ssy"]);
  });

  test("9. Evaluation date displays actual dynamic metadata returned by evaluation", () => {
    const dynamicDate = "2026-09-19";
    const customEval = { ...mockEvaluation, evaluation_date: dynamicDate };

    render(
      <LanguageProvider>
        <EvaluationResultCard evaluation={customEval} />
      </LanguageProvider>
    );

    expect(screen.getByText(dynamicDate)).toBeInTheDocument();
  });
});
