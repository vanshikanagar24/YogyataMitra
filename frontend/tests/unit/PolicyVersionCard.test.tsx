import React from "react";
import { render, screen } from "@testing-library/react";
import { PolicyVersionCard } from "../../src/components/policy/PolicyVersionCard";
import { LanguageProvider } from "../../src/context/LanguageContext";

const mockPolicy = {
  id: "pol-001",
  scheme_code: "PM_KISAN",
  version_code: "v2.0-2019",
  effective_from: "2019-04-01",
  effective_to: "2023-06-30",
  source_url: "https://pmkisan.gov.in/revised-guidelines-2019.pdf",
  source_title: "Cabinet Decision on Universal Coverage - PM-KISAN 2019",
  source_document_identifier: "F.No. 1-1/2019-Credit-II",
  rule_definition_hash: "7f9e8d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e",
  ruleset_schema_version: "1.0",
  ruleset_version: "2.0",
  created_at: "2024-01-01T00:00:00Z",
};

describe("PolicyVersionCard Component — Citizen Presentation", () => {
  it("renders version code, title, validity period, and citizen action links", () => {
    render(
      <LanguageProvider>
        <PolicyVersionCard policy={mockPolicy} />
      </LanguageProvider>
    );

    expect(screen.getByText("v2.0-2019")).toBeInTheDocument();
    expect(screen.getByText(/Universal Coverage/i)).toBeInTheDocument();
    expect(screen.getByText(/2019-04-01/i)).toBeInTheDocument();
    expect(screen.getByText(/नीति विवरण देखें/i)).toBeInTheDocument();
    expect(screen.getByText(/आधिकारिक स्रोत देखें/i)).toBeInTheDocument();
  });

  it("does NOT render raw SHA-256 cryptographic hashes or verified hash tags to citizens", () => {
    render(
      <LanguageProvider>
        <PolicyVersionCard policy={mockPolicy} />
      </LanguageProvider>
    );

    expect(screen.queryByText(/7f9e8d6c5b4a/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/SHA-256/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/प्रमाणित हैश/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Verified SHA-256/i)).not.toBeInTheDocument();
  });
});
