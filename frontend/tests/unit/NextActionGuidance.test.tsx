import React from "react";
import { render, screen } from "@testing-library/react";
import { NextActionGuidance } from "../../src/components/evaluation/NextActionGuidance";
import { EligibilityResult } from "../../src/types/enums";
import { LanguageProvider } from "../../src/context/LanguageContext";

import { useLanguage } from "../../src/context/LanguageContext";
import en from "../../src/i18n/locales/en.json";
import hi from "../../src/i18n/locales/hi.json";

describe("NextActionGuidance Component & Statutory Correctness", () => {
  // Test A: PM-KISAN description does not say "small/marginal farmers" as a current universal category
  test("Test A: PM-KISAN statutory description does not state small/marginal farmers as universal restriction", () => {
    expect(en.scheme_detail.pm_kisan_who_for).not.toMatch(/small and marginal/i);
    expect(en.scheme_detail.pm_kisan_who_for).not.toMatch(/small\/marginal/i);
    expect(hi.scheme_detail.pm_kisan_who_for).not.toMatch(/लघु एवं सीमांत/i);
    expect(en.scheme_detail.pm_kisan_who_for).toBe(
      "Eligible landholding farmer families with cultivable land, subject to the applicable scheme exclusions."
    );
    expect(hi.scheme_detail.pm_kisan_who_for).toBe(
      "पात्र भूमिधारक किसान परिवार जिनके पास खेती योग्य भूमि हो, योजना में लागू बहिष्करण शर्तों के अधीन।"
    );
  });

  // Test B: PM-KISAN description does not expose <=2 hectare as a universal requirement
  test("Test B: PM-KISAN description does not expose <=2 hectare as universal restriction", () => {
    expect(en.scheme_detail.pm_kisan_who_for).not.toMatch(/2\s*hectare/i);
    expect(en.scheme_detail.pm_kisan_key_criteria).not.toMatch(/2\s*hectare/i);
    expect(hi.scheme_detail.pm_kisan_who_for).not.toMatch(/२ हेक्टेयर|2 हेक्टेयर/);
    expect(hi.scheme_detail.pm_kisan_key_criteria).not.toMatch(/२ हेक्टेयर|2 हेक्टेयर/);
  });

  // Test C: ELIGIBLE guidance does not contain hardcoded universal document checklist
  test("Test C: ELIGIBLE guidance renders statutory document guidance and does not contain hardcoded checklist", () => {
    const { container } = render(
      <LanguageProvider>
        <NextActionGuidance
          overall_result={EligibilityResult.ELIGIBLE}
          scheme_code="PM_KISAN"
        />
      </LanguageProvider>
    );

    // Displays neutral statutory document guidance
    expect(screen.getByText(hi.next_actions.document_guidance)).toBeInTheDocument();

    // Does NOT render hardcoded specific document checklists
    expect(container.textContent).not.toMatch(/आधार कार्ड \(मोबाइल से जुड़ा हुआ\)/);
    expect(container.textContent).not.toMatch(/Aadhaar Card \(linked to mobile\)/);
    expect(container.textContent).not.toMatch(/खतौनी/);
    expect(container.textContent).not.toMatch(/Khatauni/);
    expect(container.textContent).not.toMatch(/सक्रिय बैंक खाता पासबुक/);
  });

  // Test D: SSY destination is official India Post info and accurately labelled
  test("Test D: SSY destination links to official India Post information and displays offline opening note", () => {
    render(
      <LanguageProvider>
        <NextActionGuidance
          overall_result={EligibilityResult.ELIGIBLE}
          scheme_code="SSY"
        />
      </LanguageProvider>
    );

    const ssyLink = screen.getByRole("link", { name: /आधिकारिक योजना जानकारी देखें \(इंडिया पोस्ट\)/i });
    expect(ssyLink).toBeInTheDocument();
    expect(ssyLink).toHaveAttribute(
      "href",
      "https://www.indiapost.gov.in/Financial/Pages/Content/Sukanya-Samriddhi-Account.aspx"
    );
    expect(screen.getByText(hi.next_actions.ssy_offline_note)).toBeInTheDocument();
  });

  // Test E: CSC destination is official locator and accurately labelled
  test("Test E: CSC destination links to official locator and is accurately labelled", () => {
    render(
      <LanguageProvider>
        <NextActionGuidance
          overall_result={EligibilityResult.MANUAL_REVIEW_REQUIRED}
          scheme_code="PM_KISAN"
        />
      </LanguageProvider>
    );

    const cscLink = screen.getByRole("link", { name: /निकटतम कॉमन सर्विस सेंटर \(CSC\) खोजें/i });
    expect(cscLink).toBeInTheDocument();
    expect(cscLink).toHaveAttribute("href", "https://locator.csccloud.in/");
  });

  // Test F: INELIGIBLE CTA says "View supported schemes" / "उपलब्ध योजनाएं देखें" and does not claim broader catalogue
  test("Test F: INELIGIBLE CTA links to /schemes with accurate wording", () => {
    render(
      <LanguageProvider>
        <NextActionGuidance
          overall_result={EligibilityResult.INELIGIBLE}
          scheme_code="PM_KISAN"
        />
      </LanguageProvider>
    );

    const link = screen.getByRole("link", { name: /उपलब्ध योजनाएं देखें/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/schemes");
    expect(screen.getByText(hi.next_actions.ineligible_desc)).toBeInTheDocument();
  });

  // Test G: All 5 Next Action outcomes render correctly
  test("Test G: All 5 Next Action outcomes render correctly", () => {
    const handleComplete = jest.fn();
    const handleReview = jest.fn();

    // 1. ELIGIBLE
    const { unmount: unmount1 } = render(
      <LanguageProvider>
        <NextActionGuidance
          overall_result={EligibilityResult.ELIGIBLE}
          scheme_code="PM_KISAN"
        />
      </LanguageProvider>
    );
    expect(screen.getByText(hi.next_actions.eligible_heading)).toBeInTheDocument();
    unmount1();

    // 2. INELIGIBLE
    const { unmount: unmount2 } = render(
      <LanguageProvider>
        <NextActionGuidance
          overall_result={EligibilityResult.INELIGIBLE}
          scheme_code="PM_KISAN"
        />
      </LanguageProvider>
    );
    expect(screen.getByText(hi.next_actions.ineligible_heading)).toBeInTheDocument();
    unmount2();

    // 3. INSUFFICIENT_INFORMATION
    const { unmount: unmount3 } = render(
      <LanguageProvider>
        <NextActionGuidance
          overall_result={EligibilityResult.INSUFFICIENT_INFORMATION}
          scheme_code="SSY"
          missing_fields={["beneficiary.date_of_birth"]}
          onCompleteInformation={handleComplete}
        />
      </LanguageProvider>
    );
    expect(screen.getByText(hi.next_actions.insufficient_heading)).toBeInTheDocument();
    const completeBtn = screen.getByRole("button", { name: /छूटी हुई जानकारी दर्ज करें/i });
    completeBtn.click();
    expect(handleComplete).toHaveBeenCalledTimes(1);
    unmount3();

    // 4. VERIFICATION_REQUIRED
    const { unmount: unmount4 } = render(
      <LanguageProvider>
        <NextActionGuidance
          overall_result={EligibilityResult.VERIFICATION_REQUIRED}
          scheme_code="PM_KISAN"
          onReviewDocuments={handleReview}
        />
      </LanguageProvider>
    );
    expect(screen.getByText(hi.next_actions.verification_heading)).toBeInTheDocument();
    expect(screen.getByText(hi.next_actions.verification_disclaimer)).toBeInTheDocument();
    const reviewBtn = screen.getByRole("button", { name: /सहायक दस्तावेज़ों की समीक्षा करें/i });
    reviewBtn.click();
    expect(handleReview).toHaveBeenCalledTimes(1);
    unmount4();

    // 5. MANUAL_REVIEW_REQUIRED
    const { unmount: unmount5 } = render(
      <LanguageProvider>
        <NextActionGuidance
          overall_result={EligibilityResult.MANUAL_REVIEW_REQUIRED}
          scheme_code="PM_KISAN"
        />
      </LanguageProvider>
    );
    expect(screen.getByText(hi.next_actions.manual_heading)).toBeInTheDocument();
    expect(screen.getByText(hi.next_actions.manual_desc)).toBeInTheDocument();
    unmount5();
  });

  // Test H: Technical leak scan passes
  test("Test H: Technical leak scan passes in NextActionGuidance", () => {
    const { container } = render(
      <LanguageProvider>
        <NextActionGuidance
          overall_result={EligibilityResult.ELIGIBLE}
          scheme_code="PM_KISAN"
        />
        <NextActionGuidance
          overall_result={EligibilityResult.MANUAL_REVIEW_REQUIRED}
          scheme_code="SSY"
        />
      </LanguageProvider>
    );

    expect(container.textContent).not.toMatch(/SHA-256/i);
    expect(container.textContent).not.toMatch(/UUID/i);
    expect(container.textContent).not.toMatch(/doc-ref:\/\//i);
    expect(container.textContent).not.toMatch(/SYN-CIT/i);
    expect(container.textContent).not.toMatch(/Deterministic Engine/i);
    expect(container.textContent).not.toMatch(/AST/i);
  });

  // Test I: Both English and Hindi render accurately
  test("Test I: English mode renders English text accurately", () => {
    const EnglishWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
      const { setLanguage } = useLanguage();
      React.useEffect(() => {
        setLanguage("en");
      }, [setLanguage]);
      return <>{children}</>;
    };

    render(
      <LanguageProvider>
        <EnglishWrapper>
          <NextActionGuidance
            overall_result={EligibilityResult.ELIGIBLE}
            scheme_code="SSY"
          />
        </EnglishWrapper>
      </LanguageProvider>
    );

    expect(screen.getByText(en.next_actions.eligible_heading)).toBeInTheDocument();
    expect(screen.getByText(en.next_actions.document_guidance)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /View Official Scheme Information \(India Post\)/i })).toBeInTheDocument();
    expect(screen.getByText(en.next_actions.ssy_offline_note)).toBeInTheDocument();
  });
});
