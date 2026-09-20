import React from "react";
import { render, screen } from "@testing-library/react";
import { JourneyStepper } from "../../src/components/journey/JourneyStepper";
import { LanguageProvider } from "../../src/context/LanguageContext";

describe("JourneyStepper Component", () => {
  it("renders all 4 honest statutory stages and indicates current step", () => {
    render(
      <LanguageProvider>
        <JourneyStepper currentStep="facts" />
      </LanguageProvider>
    );

    expect(screen.getAllByText("तथ्य संकलन").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("दावे पंजीकरण")).toBeInTheDocument();
    expect(screen.getByText("पात्रता मूल्यांकन")).toBeInTheDocument();
    expect(screen.getByText("मूल्यांकन परिणाम")).toBeInTheDocument();

    // Verify misleading 6-step stages are removed
    expect(screen.queryByText("प्रमाण दस्तावेज़")).not.toBeInTheDocument();
    expect(screen.queryByText("दस्तावेज़ सत्यापन")).not.toBeInTheDocument();

    // Verify step counter indicator
    expect(screen.getByText(/चरण 1 \/ 4/)).toBeInTheDocument();
  });
});
