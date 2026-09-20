import React from "react";
import { render, screen } from "@testing-library/react";
import { SchemeCard } from "../../src/components/schemes/SchemeCard";
import { SchemeStatus } from "../../src/types/enums";
import { LanguageProvider } from "../../src/context/LanguageContext";

const mockPmKisan = {
  id: "schem-001",
  scheme_code: "PM_KISAN",
  name_en: "Pradhan Mantri Kisan Samman Nidhi",
  name_hi: "प्रधानमंत्री किसान सम्मान निधि",
  description_en: "Income support for landholding farmer families.",
  description_hi: "भूमिधारक किसान परिवारों के लिए आय सहायता योजना।",
  ministry: "Ministry of Agriculture and Farmers Welfare",
  official_url: "https://pmkisan.gov.in",
  status: SchemeStatus.ACTIVE,
  created_at: "2024-01-01T00:00:00Z",
};

const mockSsy = {
  id: "schem-002",
  scheme_code: "SSY",
  name_en: "Sukanya Samriddhi Account",
  name_hi: "सुकन्या समृद्धि योजना",
  description_en: "Small deposit scheme for the girl child.",
  description_hi: "बालिकाओं के उज्ज्वल भविष्य के लिए विशेष बचत योजना।",
  ministry: "Ministry of Finance",
  official_url: "https://www.indiapost.gov.in",
  status: SchemeStatus.ACTIVE,
  created_at: "2024-01-01T00:00:00Z",
};

describe("SchemeCard Component", () => {
  it("renders PM-KISAN card with statutory benefit and CTA", () => {
    render(
      <LanguageProvider>
        <SchemeCard scheme={mockPmKisan} />
      </LanguageProvider>
    );

    expect(screen.getByText(/प्रधानमंत्री किसान सम्मान निधि/i)).toBeInTheDocument();
    expect(screen.getByText(/₹6,000/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /पात्रता जाँचें/i })).toHaveAttribute(
      "href",
      "/eligibility?scheme=PM_KISAN"
    );
  });

  it("renders SSY card with statutory interest benefit and CTA", () => {
    render(
      <LanguageProvider>
        <SchemeCard scheme={mockSsy} />
      </LanguageProvider>
    );

    expect(screen.getByText(/सुकन्या समृद्धि योजना/i)).toBeInTheDocument();
    expect(screen.getByText(/8.2%/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /पात्रता जाँचें/i })).toHaveAttribute(
      "href",
      "/eligibility?scheme=SSY"
    );
  });
});
