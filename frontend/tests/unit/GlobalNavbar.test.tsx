import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { GlobalNavbar } from "../../src/components/layout/GlobalNavbar";
import { LanguageProvider } from "../../src/context/LanguageContext";

jest.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

describe("GlobalNavbar Component", () => {
  it("renders institutional branding and logo", () => {
    render(
      <LanguageProvider>
        <GlobalNavbar />
      </LanguageProvider>
    );

    expect(screen.getByText("YM")).toBeInTheDocument();
    expect(screen.getByText("योग्यता मित्र")).toBeInTheDocument();
  });

  it("renders all statutory navigation links", () => {
    render(
      <LanguageProvider>
        <GlobalNavbar />
      </LanguageProvider>
    );

    expect(screen.getByText("मुख्य पृष्ठ")).toBeInTheDocument();
    expect(screen.getByText("योजनाएं")).toBeInTheDocument();
    expect(screen.getByText("पात्रता जाँचें")).toBeInTheDocument();
    expect(screen.getByText("नीति सत्यापन")).toBeInTheDocument();
    expect(screen.getByText("ऑडिट और इतिहास")).toBeInTheDocument();
  });

  it("supports language toggle between EN and HI", () => {
    render(
      <LanguageProvider>
        <GlobalNavbar />
      </LanguageProvider>
    );

    const enBtn = screen.getByRole("button", { name: /switch to english/i });
    fireEvent.click(enBtn);
    expect(screen.getByText("YogyataMitra")).toBeInTheDocument();
    expect(screen.getByText("Check Eligibility")).toBeInTheDocument();

    const hiBtn = screen.getByRole("button", { name: /switch to hindi/i });
    fireEvent.click(hiBtn);
    expect(screen.getByText("योग्यता मित्र")).toBeInTheDocument();
  });
});
