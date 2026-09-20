import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  LoadingState,
  ErrorState,
  EmptyState,
  SchemeCardSkeleton,
  TableSkeleton,
} from "../../src/components/common/FeedbackStates";
import { LanguageProvider } from "../../src/context/LanguageContext";

describe("FeedbackStates Component Suite", () => {
  it("renders LoadingState with role='status' and accessible message", () => {
    render(
      <LanguageProvider>
        <LoadingState message="प्रमाणीकरण प्रगति पर है..." />
      </LanguageProvider>
    );

    const spinner = screen.getByRole("status");
    expect(spinner).toBeInTheDocument();
    expect(screen.getByText("प्रमाणीकरण प्रगति पर है...")).toBeInTheDocument();
  });

  it("renders ErrorState with role='alert' and supports retry callback", () => {
    const onRetry = jest.fn();
    render(
      <LanguageProvider>
        <ErrorState
          title="सर्वर त्रुटि"
          message="वैधानिक नीति सेवा से संपर्क नहीं हो सका।"
          onRetry={onRetry}
        />
      </LanguageProvider>
    );

    const alert = screen.getByRole("alert");
    expect(alert).toBeInTheDocument();
    expect(screen.getByText("सर्वर त्रुटि")).toBeInTheDocument();
    expect(
      screen.getByText("वैधानिक नीति सेवा से संपर्क नहीं हो सका।")
    ).toBeInTheDocument();

    const retryBtn = screen.getByRole("button", { name: /पुनः प्रयास करें|retry/i });
    expect(retryBtn).toBeInTheDocument();
    fireEvent.click(retryBtn);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("renders EmptyState with custom title, description, and action", () => {
    const onAction = jest.fn();
    render(
      <LanguageProvider>
        <EmptyState
          title="कोई परिणाम नहीं मिला"
          description="चयनित मापदंडों के अनुसार कोई योजना उपलब्ध नहीं है।"
          action={
            <button type="button" onClick={onAction}>
              फ़िल्टर साफ़ करें
            </button>
          }
        />
      </LanguageProvider>
    );

    expect(screen.getByText("कोई परिणाम नहीं मिला")).toBeInTheDocument();
    expect(
      screen.getByText("चयनित मापदंडों के अनुसार कोई योजना उपलब्ध नहीं है।")
    ).toBeInTheDocument();

    const actionBtn = screen.getByRole("button", { name: /फ़िल्टर साफ़ करें/i });
    fireEvent.click(actionBtn);
    expect(onAction).toHaveBeenCalledTimes(1);
  });

  it("renders SchemeCardSkeleton and TableSkeleton with aria-hidden for screen reader cleanliness", () => {
    const { container } = render(
      <LanguageProvider>
        <SchemeCardSkeleton />
        <TableSkeleton rows={3} />
      </LanguageProvider>
    );

    const hiddenSkeletons = container.querySelectorAll('[aria-hidden="true"]');
    expect(hiddenSkeletons.length).toBeGreaterThanOrEqual(2);
  });
});
