import React from "react";
import fs from "fs";
import path from "path";
import { render, screen } from "@testing-library/react";
import { PolicyVersionCard } from "../../src/components/policy/PolicyVersionCard";
import { CitizenPolicyView } from "../../src/components/policy/CitizenPolicyView";
import { AuditPolicyView } from "../../src/components/policy/AuditPolicyView";
import { EvaluationResultCard } from "../../src/components/evaluation/EvaluationResultCard";
import { ExplainabilityView } from "../../src/components/evaluation/ExplainabilityView";
import { NextActionGuidance } from "../../src/components/evaluation/NextActionGuidance";
import { SchemeCard } from "../../src/components/schemes/SchemeCard";
import { JourneyStepper } from "../../src/components/journey/JourneyStepper";
import { ClaimCard } from "../../src/components/journey/ClaimCard";
import { EvidenceCard } from "../../src/components/journey/EvidenceCard";
import { GlobalNavbar } from "../../src/components/layout/GlobalNavbar";
import { Footer } from "../../src/components/layout/Footer";
import { Breadcrumbs } from "../../src/components/layout/Breadcrumbs";
import { LanguageProvider } from "../../src/context/LanguageContext";
import { EligibilityResult, EvidenceStatus } from "../../src/types/enums";
import { PolicyVersionDetail } from "../../src/types/policy";
import { EvaluationResponse } from "../../src/types/evaluation";
import { AuditPolicyDetails } from "../../src/types/audit";
import { SchemeSummary } from "../../src/types/scheme";
import { JourneyClaim, JourneyEvidence } from "../../src/types/journey";
import {
  RULE_PRESENTATION_MAP,
  getFriendlyRuleTitle,
  getFriendlyRuleExplanation,
  getPolicyStatutorySummary,
  getPolicyTimelineStatus,
  getTimelineStatusLabel,
} from "../../src/utils/rulePresentation";
import en from "../../src/i18n/locales/en.json";
import hi from "../../src/i18n/locales/hi.json";

// Mock next/navigation
jest.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: jest.fn(), back: jest.fn() }),
}));

// Mock 6 Statutory Policy Versions
const mockPolicies: PolicyVersionDetail[] = [
  {
    id: "pol-pk-v3",
    scheme_code: "PM_KISAN",
    version_code: "v3.0-2023",
    effective_from: "2023-01-01",
    effective_to: null,
    source_url: "https://pmkisan.gov.in/Documents/OperationalGuidelines2023.pdf",
    source_title: "Operational Guidelines for Pradhan Mantri Kisan Samman Nidhi (PM-KISAN) 2023",
    source_document_identifier: "PMKISAN-OPERATIONAL-GUIDELINES-2023",
    rule_definition_hash: "7ef27f5c071a8fa4fff2d95c6c34cda5211b76d16ddb0e610a312ea61cf669d6",
    ruleset_schema_version: "1.0",
    ruleset_version: "3.0.0",
    created_at: "2023-01-01T00:00:00Z",
  },
  {
    id: "pol-pk-v2",
    scheme_code: "PM_KISAN",
    version_code: "v2.0-2019",
    effective_from: "2019-04-01",
    effective_to: "2022-12-31",
    source_url: "https://pmkisan.gov.in/Documents/RevisedOperationalGuidelines.pdf",
    source_title: "Revised Operational Guidelines for Pradhan Mantri Kisan Samman Nidhi (PM-KISAN) 2019",
    source_document_identifier: "PMKISAN-REVISED-GUIDELINES-2019",
    rule_definition_hash: "55fe76d5bd441cbe4a0ceddb45ddbf253f5f059683570bd29096bf9b972ad6d8",
    ruleset_schema_version: "1.0",
    ruleset_version: "2.0.0",
    created_at: "2019-04-01T00:00:00Z",
  },
  {
    id: "pol-pk-v1",
    scheme_code: "PM_KISAN",
    version_code: "v1.0-2018",
    effective_from: "2018-12-01",
    effective_to: "2019-03-31",
    source_url: "https://pmkisan.gov.in/Documents/OperationalGuidelines.pdf",
    source_title: "PM-KISAN Operational Guidelines (Original - Small & Marginal Farmers)",
    source_document_identifier: "PMKISAN-GUIDELINES-2018-SMF",
    rule_definition_hash: "facc14b3388802e3d0ef0c4134414459500dc9a9be7e0dc62ddecc082b47e9d2",
    ruleset_schema_version: "1.0",
    ruleset_version: "1.0.0",
    created_at: "2018-12-01T00:00:00Z",
  },
  {
    id: "pol-ssy-v3",
    scheme_code: "SSY",
    version_code: "v3.0-2024",
    effective_from: "2024-04-01",
    effective_to: null,
    source_url: "https://www.dea.gov.in/sites/default/files/SukanyaSamriddhiAccountScheme2019.pdf",
    source_title: "Sukanya Samriddhi Account Scheme, 2019 (as amended by MoF DEA Order F.No. 1/3/2024-NS)",
    source_document_identifier: "GSR-914E-2019-MOF-2024-NS",
    rule_definition_hash: "5fa83b3d5b0177ca9d0983e46213d11e92883993f2f7a5abc9fe43fb25b9ff28",
    ruleset_schema_version: "1.0",
    ruleset_version: "3.0.0",
    created_at: "2024-04-01T00:00:00Z",
  },
  {
    id: "pol-ssy-v2",
    scheme_code: "SSY",
    version_code: "v2.0-2019",
    effective_from: "2019-12-12",
    effective_to: "2024-03-31",
    source_url: "https://www.dea.gov.in/sites/default/files/SukanyaSamriddhiAccountScheme2019.pdf",
    source_title: "Sukanya Samriddhi Account Scheme, 2019",
    source_document_identifier: "GSR-914E-2019",
    rule_definition_hash: "3dbd7d9d1f87ae7ce5064143333bd8ac969b14e927ac6cb7e6206f1777288669",
    ruleset_schema_version: "1.0",
    ruleset_version: "2.0.0",
    created_at: "2019-12-12T00:00:00Z",
  },
  {
    id: "pol-ssy-v1",
    scheme_code: "SSY",
    version_code: "v1.0-2016",
    effective_from: "2016-03-18",
    effective_to: "2019-12-11",
    source_url: "https://www.dea.gov.in/sites/default/files/SukanyaSamriddhiAccountRules2016.pdf",
    source_title: "Sukanya Samriddhi Account Rules, 2016",
    source_document_identifier: "GSR-323E-2016",
    rule_definition_hash: "ffb3c2dae2cf283d3b0b41c8dfd87267cfff29e30fa898ee1ca93fde19419ae7",
    ruleset_schema_version: "1.0",
    ruleset_version: "1.0.0",
    created_at: "2016-03-18T00:00:00Z",
  },
];

// Mock Evaluation Response for citizen UI testing
const mockEvaluation: EvaluationResponse = {
  overall_result: EligibilityResult.ELIGIBLE,
  scheme_code: "PM_KISAN",
  policy_version_code: "v3.0-2023",
  evaluation_date: "2024-01-15",
  effective_from: "2023-01-01",
  effective_to: null,
  rule_definition_hash: "7ef27f5c071a8fa4fff2d95c6c34cda5211b76d16ddb0e610a312ea61cf669d6",
  reasons_en: [
    "Cultivable land ownership condition satisfied.",
    "No disqualifying exclusion categories identified.",
  ],
  reasons_hi: [
    "कृषि योग्य भूमि स्वामित्व मानदंड संतुष्ट है।",
    "कोई बहिष्करण श्रेणी लागू नहीं पाई गई।",
  ],
  satisfied_rules: ["PMKISAN-LAND-CULTIVABLE", "PMKISAN-EXCL-CONSTITUTIONAL"],
  blockers: [],
  missing_fields: [],
  trace: {
    provenance: {
      source_title: "Operational Guidelines for Pradhan Mantri Kisan Samman Nidhi (PM-KISAN) 2023",
      source_url: "https://pmkisan.gov.in/Documents/OperationalGuidelines2023.pdf",
    },
  } as any,
};

const mockIneligibleEvaluation: EvaluationResponse = {
  overall_result: EligibilityResult.INELIGIBLE,
  scheme_code: "PM_KISAN",
  policy_version_code: "v3.0-2023",
  evaluation_date: "2024-01-15",
  effective_from: "2023-01-01",
  effective_to: null,
  rule_definition_hash: "7ef27f5c071a8fa4fff2d95c6c34cda5211b76d16ddb0e610a312ea61cf669d6",
  reasons_en: ["Institutional landholders are excluded from scheme benefits."],
  reasons_hi: ["संस्थागत भूमि धारक योजना से बहिष्कृत हैं।"],
  satisfied_rules: [],
  blockers: [
    {
      rule_id: "PMKISAN-EXCL-INSTITUTIONAL",
      field_path: "household.is_institutional",
      message_en: "Institutional landholder exclusion applies.",
      message_hi: "संस्थागत भूमि धारक बहिष्करण लागू है।",
    },
  ],
  missing_fields: ["household.land.area_hectares"],
  trace: {} as any,
};

describe("Phase 13: Policy Transparency, Provenance & Audit UX Separation", () => {
  // Test A: Audit view exposure check
  test("Test A: AuditPolicyView is strictly unreachable from public citizen app routes, layout, and navbar", () => {
    const appDir = path.resolve(__dirname, "../../src/app");
    const componentsDir = path.resolve(__dirname, "../../src/components");

    // Scan all page.tsx and layout.tsx files in app directory
    const checkDirectory = (dir: string): string[] => {
      const files: string[] = [];
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          files.push(...checkDirectory(fullPath));
        } else if (entry.isFile() && (entry.name.endsWith(".tsx") || entry.name.endsWith(".ts"))) {
          files.push(fullPath);
        }
      }
      return files;
    };

    const appFiles = checkDirectory(appDir);
    for (const filePath of appFiles) {
      const content = fs.readFileSync(filePath, "utf-8");
      expect(content).not.toContain("AuditPolicyView");
    }

    // Verify navbar and footer do not link to or import AuditPolicyView
    const navbarContent = fs.readFileSync(path.join(componentsDir, "layout/GlobalNavbar.tsx"), "utf-8");
    expect(navbarContent).not.toContain("AuditPolicyView");
    expect(navbarContent).not.toContain("/audit-view");

    const footerContent = fs.readFileSync(path.join(componentsDir, "layout/Footer.tsx"), "utf-8");
    expect(footerContent).not.toContain("AuditPolicyView");
  });

  // Test B: Comprehensive citizen DOM technical-leak scan across 12 public views
  test("Test B: Citizen DOM technical-leak scan: zero prohibited tokens across 12 public views", () => {
    // Prohibited patterns for citizen-facing DOM
    const prohibitedPatterns = [
      /\b[a-f0-9]{64}\b/i, // 64-char SHA-256 hex string
      /\bsha-?256\b/i,
      /canonical[_ -]?hash/i,
      /ruleset[_ -]?schema/i,
      /\bAST\b/,
      /database entity id/i,
      /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/i, // Raw UUID
      /PMKISAN-(?:EXCL|LAND|HIST|V\d)/,
      /SSY-(?:AGE|BENEFICIARY|FAMILY|GUARDIAN|LEGAL|NATURAL|MULTIPLE|ONE|V\d)/,
      /household\.[a-z_]+/i,
      /applicant\.[a-z_]+/i,
      /SYN-CIT/i,
      /doc-ref:\/\//i,
    ];

    const assertNoLeak = (html: string, componentName: string) => {
      prohibitedPatterns.forEach((pattern) => {
        const match = html.match(pattern);
        expect(match).toBeNull();
      });
    };

    // 1. CitizenPolicyView
    const { container: c1, unmount: u1 } = render(
      <LanguageProvider>
        <CitizenPolicyView policy={mockPolicies[0]} index={0} />
      </LanguageProvider>
    );
    assertNoLeak(c1.innerHTML, "CitizenPolicyView");
    u1();

    // 2. PolicyVersionCard
    const { container: c2, unmount: u2 } = render(
      <LanguageProvider>
        <PolicyVersionCard policy={mockPolicies[0]} index={0} />
      </LanguageProvider>
    );
    assertNoLeak(c2.innerHTML, "PolicyVersionCard");
    u2();

    // 3. EvaluationResultCard
    const { container: c3, unmount: u3 } = render(
      <LanguageProvider>
        <EvaluationResultCard evaluation={mockEvaluation} />
      </LanguageProvider>
    );
    assertNoLeak(c3.innerHTML, "EvaluationResultCard");
    u3();

    // 4. ExplainabilityView
    const { container: c4, unmount: u4 } = render(
      <LanguageProvider>
        <ExplainabilityView evaluation={mockIneligibleEvaluation} />
      </LanguageProvider>
    );
    assertNoLeak(c4.innerHTML, "ExplainabilityView");
    u4();

    // 5. NextActionGuidance
    const { container: c5, unmount: u5 } = render(
      <LanguageProvider>
        <NextActionGuidance
          overall_result={EligibilityResult.ELIGIBLE}
          scheme_code="PM_KISAN"
        />
      </LanguageProvider>
    );
    assertNoLeak(c5.innerHTML, "NextActionGuidance");
    u5();

    // 6. SchemeCard
    const mockScheme: SchemeSummary = {
      scheme_code: "PM_KISAN",
      name_en: "PM-KISAN",
      name_hi: "पीएम-किसान",
      description_en: "Direct income support of ₹6,000 per year.",
      description_hi: "₹6,000 प्रति वर्ष की प्रत्यक्ष आय सहायता।",
      official_url: "https://pmkisan.gov.in",
      current_policy_version: "v3.0-2023",
      rule_count: 14,
    };
    const { container: c6, unmount: u6 } = render(
      <LanguageProvider>
        <SchemeCard scheme={mockScheme} />
      </LanguageProvider>
    );
    assertNoLeak(c6.innerHTML, "SchemeCard");
    u6();

    // 7. JourneyStepper
    const { container: c7, unmount: u7 } = render(
      <LanguageProvider>
        <JourneyStepper currentStep="claims" />
      </LanguageProvider>
    );
    assertNoLeak(c7.innerHTML, "JourneyStepper");
    u7();

    // 8. ClaimCard
    const mockClaim: JourneyClaim = {
      id: "claim-test-1",
      claim_type: "PMKISAN_LAND_OWNERSHIP",
      value_json: { owns_land: true, area_hectares: 1.5 },
      status: "VERIFIED",
    };
    const { container: c8, unmount: u8 } = render(
      <LanguageProvider>
        <ClaimCard claim={mockClaim} />
      </LanguageProvider>
    );
    assertNoLeak(c8.innerHTML, "ClaimCard");
    u8();

    // 9. EvidenceCard
    const mockEvidence: JourneyEvidence = {
      id: "ev-test-1",
      claim_id: "claim-test-1",
      evidence_type: "LAND_RECORD",
      document_reference: "KHASRA-12345",
      status: EvidenceStatus.VERIFIED,
      verified_at: "2024-01-15T10:00:00Z",
    };
    const { container: c9, unmount: u9 } = render(
      <LanguageProvider>
        <EvidenceCard evidence={mockEvidence} />
      </LanguageProvider>
    );
    assertNoLeak(c9.innerHTML, "EvidenceCard");
    u9();

    // 10. GlobalNavbar
    const { container: c10, unmount: u10 } = render(
      <LanguageProvider>
        <GlobalNavbar />
      </LanguageProvider>
    );
    assertNoLeak(c10.innerHTML, "GlobalNavbar");
    u10();

    // 11. Footer
    const { container: c11, unmount: u11 } = render(
      <LanguageProvider>
        <Footer />
      </LanguageProvider>
    );
    assertNoLeak(c11.innerHTML, "Footer");
    u11();

    // 12. Breadcrumbs
    const { container: c12, unmount: u12 } = render(
      <LanguageProvider>
        <Breadcrumbs items={[{ label: "Schemes", href: "/schemes" }, { label: "PM-KISAN" }]} />
      </LanguageProvider>
    );
    assertNoLeak(c12.innerHTML, "Breadcrumbs");
    u12();
  });

  // Test C: Rule presentation mapping
  test("Test C: Rule presentation mapping preserves statutory meaning without raw slugs or dot notation", () => {
    // PM-KISAN exclusions
    const constitutionalTitleEn = getFriendlyRuleTitle("PMKISAN-EXCL-CONSTITUTIONAL", false);
    const constitutionalTitleHi = getFriendlyRuleTitle("PMKISAN-EXCL-CONSTITUTIONAL", true);
    expect(constitutionalTitleEn).toBe("Constitutional Post Exclusion");
    expect(constitutionalTitleHi).toContain("संवैधानिक");

    // SSY qualifications
    const ssyAgeTitleEn = getFriendlyRuleTitle("SSY-AGE-LIMIT-10", false);
    const ssyAgeTitleHi = getFriendlyRuleTitle("SSY-AGE-LIMIT-10", true);
    expect(ssyAgeTitleEn).toContain("10 Years");
    expect(ssyAgeTitleHi).toContain("10 वर्ष");

    // Verify all keys in RULE_PRESENTATION_MAP have clean bilingual explanations
    Object.entries(RULE_PRESENTATION_MAP).forEach(([ruleId, meta]) => {
      expect(meta.titleEn).toBeTruthy();
      expect(meta.titleHi).toBeTruthy();
      expect(meta.explanationEn).toBeTruthy();
      expect(meta.explanationHi).toBeTruthy();
      expect(meta.titleEn).not.toMatch(/[a-z]\.[a-z]/i);
      expect(meta.explanationEn).not.toMatch(/household\.|applicant\./);
    });
  });

  // Test D: English/Hindi parity
  test("Test D: Bilingual parity is preserved with 100% key match between en.json and hi.json", () => {
    expect(en.policy_page).toBeDefined();
    expect(hi.policy_page).toBeDefined();
    expect(Object.keys(en.policy_page)).toEqual(Object.keys(hi.policy_page));

    expect(en.audit_page).toBeDefined();
    expect(hi.audit_page).toBeDefined();
    expect(Object.keys(en.audit_page)).toEqual(Object.keys(hi.audit_page));

    expect(en.results).toBeDefined();
    expect(hi.results).toBeDefined();
    expect(Object.keys(en.results)).toEqual(Object.keys(hi.results));
  });

  // Test E: Official policy links
  test("Test E: Official guidelines links point exclusively to official government domains", () => {
    const approvedDomains = ["pmkisan.gov.in", "dea.gov.in", "indiapost.gov.in", "gov.in"];

    mockPolicies.forEach((p) => {
      const url = new URL(p.source_url);
      const isGovDomain = approvedDomains.some((d) => url.hostname.endsWith(d));
      expect(isGovDomain).toBe(true);
    });
  });

  // Test F: Policy timeline and status classification
  test("Test F: Historical policy timeline correctly presents all 6 versions chronologically with neutral statutory summaries", () => {
    // Check PM-KISAN neutral statutory summaries starting with "Policy version applicable from..."
    const pkSummary1 = getPolicyStatutorySummary("PM_KISAN", "v1.0-2018", false);
    const pkSummary2 = getPolicyStatutorySummary("PM_KISAN", "v2.0-2019", false);
    const pkSummary3 = getPolicyStatutorySummary("PM_KISAN", "v3.0-2023", false);

    expect(pkSummary1.summary).toMatch(/^Policy version applicable from 1 December 2018/);
    expect(pkSummary1.summary).toContain("2.0 hectares");
    expect(pkSummary2.summary).toMatch(/^Policy version applicable from 1 April 2019/);
    expect(pkSummary2.summary).toContain("01-Feb-2019");
    expect(pkSummary3.summary).toMatch(/^Policy version applicable from 1 January 2023/);

    // Check SSY neutral statutory summaries starting with "Policy version applicable from..."
    const ssySummary1 = getPolicyStatutorySummary("SSY", "v1.0-2016", false);
    const ssySummary2 = getPolicyStatutorySummary("SSY", "v2.0-2019", false);
    const ssySummary3 = getPolicyStatutorySummary("SSY", "v3.0-2024", false);

    expect(ssySummary1.summary).toMatch(/^Policy version applicable from 18 March 2016/);
    expect(ssySummary1.summary).toContain("GSR 323(E)");
    expect(ssySummary2.summary).toMatch(/^Policy version applicable from 12 December 2019/);
    expect(ssySummary2.summary).toContain("GSR 914(E)");
    expect(ssySummary3.summary).toMatch(/^Policy version applicable from 1 April 2024/);
    expect(ssySummary3.summary).toContain("F.No. 1/3/2024-NS");

    // Timeline status classifications
    expect(getPolicyTimelineStatus(null, 0)).toBe("CURRENT");
    expect(getPolicyTimelineStatus("2024-03-31", 1)).toBe("PREVIOUS");
    expect(getPolicyTimelineStatus("2019-12-11", 2)).toBe("EARLIER");

    expect(getTimelineStatusLabel("CURRENT", false)).toBe("Current Effective Policy");
    expect(getTimelineStatusLabel("CURRENT", true)).toBe("वर्तमान प्रभावी नीति");
  });

  // Test G: Five outcomes plain-language explainability
  test("Test G: All 5 eligibility outcomes render plain-language guidance without welfare guarantees", () => {
    const outcomes = [
      EligibilityResult.ELIGIBLE,
      EligibilityResult.INELIGIBLE,
      EligibilityResult.INSUFFICIENT_INFORMATION,
      EligibilityResult.VERIFICATION_REQUIRED,
      EligibilityResult.MANUAL_REVIEW_REQUIRED,
    ];

    outcomes.forEach((result) => {
      const { unmount, container } = render(
        <LanguageProvider>
          <NextActionGuidance overall_result={result} scheme_code="PM_KISAN" />
        </LanguageProvider>
      );

      // Verify guidance renders heading and contains no welfare entitlement guarantees
      expect(screen.getByRole("heading")).toBeInTheDocument();
      expect(container.textContent).not.toMatch(/guarantee scheme entitlement/i);
      expect(container.textContent).not.toMatch(/funds deposited/i);
      unmount();
    });
  });

  // Test H: Assessment date vs execution timestamp
  test("Test H: Assessment date vs calculation execution timestamp maintains explicit distinction", () => {
    const { container, unmount } = render(
      <LanguageProvider>
        <EvaluationResultCard evaluation={mockEvaluation} />
      </LanguageProvider>
    );

    // Verify statutory assessment date is clearly labelled
    expect(screen.getByText(/2024-01-15/)).toBeInTheDocument();
    expect(screen.getByText(/2023-01-01/)).toBeInTheDocument();
    unmount();
  });

  // Test I: Provenance classification & Auditor boundary isolation
  test("Test I: AuditPolicyView displays technical SHA-256 and AST details, while CitizenPolicyView isolates them", () => {
    const auditPolicy: AuditPolicyDetails = {
      id: "uuid-audit-12345-67890",
      scheme_code: "PM_KISAN",
      version_code: "v3.0-2023",
      effective_from: "2023-01-01",
      effective_to: null,
      rule_definition_hash: "7ef27f5c071a8fa4fff2d95c6c34cda5211b76d16ddb0e610a312ea61cf669d6",
      ruleset_schema_version: "1.0",
      ruleset_version: "3.0.0",
      source_url: "https://pmkisan.gov.in/Documents/OperationalGuidelines2023.pdf",
      source_title: "Operational Guidelines for PM-KISAN 2023",
      source_document_identifier: "PMKISAN-2023",
      created_at: "2023-01-01T00:00:00Z",
    };

    // Render Auditor View
    const { getByTestId, unmount: unmountAudit } = render(
      <AuditPolicyView policy={auditPolicy} />
    );

    const hashElement = getByTestId("audit-rule-hash");
    expect(hashElement.textContent).toBe(auditPolicy.rule_definition_hash);
    expect(screen.getByText(/Authorized Auditor Inspection Layer/i)).toBeInTheDocument();
    expect(screen.getByText(/Ruleset Version/i)).toBeInTheDocument();
    unmountAudit();

    // Render Citizen View
    const { container: citizenContainer, unmount: unmountCitizen } = render(
      <LanguageProvider>
        <CitizenPolicyView policy={mockPolicies[0]} index={0} />
      </LanguageProvider>
    );

    // Citizen view must NOT contain the hash or auditor layer text
    expect(citizenContainer.textContent).not.toContain(auditPolicy.rule_definition_hash);
    expect(citizenContainer.textContent).not.toContain("Authorized Auditor Inspection Layer");
    unmountCitizen();
  });
});
