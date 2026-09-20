import React from "react";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "../../src/components/common/StatusBadge";
import { EligibilityResult, EvidenceStatus } from "../../src/types/enums";
import { LanguageProvider } from "../../src/context/LanguageContext";

const renderWithLang = (ui: React.ReactElement) => {
  return render(<LanguageProvider>{ui}</LanguageProvider>);
};

describe("StatusBadge Component", () => {
  it("renders ELIGIBLE status with green success treatment", () => {
    renderWithLang(<StatusBadge status={EligibilityResult.ELIGIBLE} />);
    expect(screen.getByText(/पात्र/i)).toBeInTheDocument();
  });

  it("renders INELIGIBLE status with danger treatment", () => {
    renderWithLang(<StatusBadge status={EligibilityResult.INELIGIBLE} />);
    expect(screen.getByText(/अपात्र/i)).toBeInTheDocument();
  });

  it("renders INSUFFICIENT_INFORMATION status with warning treatment", () => {
    renderWithLang(<StatusBadge status={EligibilityResult.INSUFFICIENT_INFORMATION} />);
    expect(screen.getByText(/अतिरिक्त जानकारी/i)).toBeInTheDocument();
  });

  it("renders VERIFICATION_REQUIRED status with info treatment", () => {
    renderWithLang(<StatusBadge status={EligibilityResult.VERIFICATION_REQUIRED} />);
    expect(screen.getByText(/सत्यापन आवश्यक/i)).toBeInTheDocument();
  });

  it("renders MANUAL_REVIEW_REQUIRED status with purple treatment", () => {
    renderWithLang(<StatusBadge status={EligibilityResult.MANUAL_REVIEW_REQUIRED} />);
    expect(screen.getByText(/समीक्षा आवश्यक/i)).toBeInTheDocument();
  });

  it("renders Evidence VERIFIED status distinctly", () => {
    renderWithLang(<StatusBadge status={EvidenceStatus.VERIFIED} />);
    expect(screen.getByText(/दस्तावेज़ सत्यापित/i)).toBeInTheDocument();
  });

  it("renders Evidence REJECTED status distinctly", () => {
    renderWithLang(<StatusBadge status={EvidenceStatus.REJECTED} />);
    expect(screen.getByText(/दस्तावेज़ अस्वीकृत/i)).toBeInTheDocument();
  });
});
