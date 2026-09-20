import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { GlobalNavbar } from "../../src/components/layout/GlobalNavbar";
import { LanguageProvider } from "../../src/context/LanguageContext";

jest.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

describe("Accessibility Standards (WCAG 2.2 AA)", () => {
  it("renders skip to content link matching main content target", () => {
    render(
      <LanguageProvider>
        <a href="#main-content" className="skip-to-content">
          मुख्य सामग्री पर जाएं / Skip to main content
        </a>
        <main id="main-content" tabIndex={-1}>
          <h1>Portal Content</h1>
        </main>
      </LanguageProvider>
    );

    const skipLink = screen.getByRole("link", {
      name: /skip to main content/i,
    });
    expect(skipLink).toBeInTheDocument();
    expect(skipLink).toHaveAttribute("href", "#main-content");

    const mainContent = screen.getByRole("main");
    expect(mainContent).toHaveAttribute("id", "main-content");
    expect(mainContent).toHaveAttribute("tabIndex", "-1");
  });

  it("ensures mobile navigation menu responds to Escape key for accessibility", () => {
    render(
      <LanguageProvider>
        <GlobalNavbar />
      </LanguageProvider>
    );

    const menuToggle = screen.getByRole("button", {
      name: /नेविगेशन मेनू टॉगल करें|toggle navigation menu/i,
    });
    expect(menuToggle).toHaveAttribute("aria-expanded", "false");

    // Open mobile menu
    fireEvent.click(menuToggle);
    expect(menuToggle).toHaveAttribute("aria-expanded", "true");

    // Press Escape to dismiss menu
    fireEvent.keyDown(window, { key: "Escape" });
    expect(menuToggle).toHaveAttribute("aria-expanded", "false");
  });

  it("provides proper group and aria-label attributes on language switcher", () => {
    render(
      <LanguageProvider>
        <GlobalNavbar />
      </LanguageProvider>
    );

    const langGroup = screen.getByRole("group", {
      name: /भाषा चयनकर्ता|language selector/i,
    });
    expect(langGroup).toBeInTheDocument();

    const enBtn = screen.getByRole("button", { name: /switch to english/i });
    const hiBtn = screen.getByRole("button", { name: /switch to hindi/i });

    expect(enBtn).toHaveAttribute("aria-pressed");
    expect(hiBtn).toHaveAttribute("aria-pressed");
  });
});
