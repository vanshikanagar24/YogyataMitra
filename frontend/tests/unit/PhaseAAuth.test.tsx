import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { AuthProvider, useAuth } from "../../src/context/AuthContext";
import { ProtectedRoute } from "../../src/components/auth/ProtectedRoute";
import { LanguageProvider } from "../../src/context/LanguageContext";
import { GlobalNavbar } from "../../src/components/layout/GlobalNavbar";
import { isSafeInternalRedirect, getSafeRedirectUrl } from "../../src/utils/redirects";

const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({
    push: mockPush,
    replace: jest.fn(),
  }),
  useSearchParams: () => ({
    get: (param: string) => (param === "redirect" ? "/citizen/dashboard" : null),
  }),
}));

describe("Phase A: Authentication, Role Routing & Access Control", () => {
  beforeEach(() => {
    localStorage.clear();
    mockPush.mockClear();
  });

  it("renders GlobalNavbar with profile entry point and role selection popover", () => {
    render(
      <AuthProvider>
        <LanguageProvider>
          <GlobalNavbar />
        </LanguageProvider>
      </AuthProvider>
    );

    // Profile trigger button is present
    const profileBtn = screen.getByRole("button", {
      name: /उपयोगकर्ता प्रोफ़ाइल और पोर्टल भूमिका/i,
    });
    expect(profileBtn).toBeInTheDocument();

    // Open dropdown
    fireEvent.click(profileBtn);

    // Both Citizen and Officer role options are rendered
    expect(screen.getByText(/Citizen \/ नागरिक/i)).toBeInTheDocument();
    expect(screen.getByText(/Officer \/ अधिकारी/i)).toBeInTheDocument();
    expect(screen.getByText(/Apply for schemes, track applications/i)).toBeInTheDocument();
    expect(screen.getByText(/Verification queue, review evidence/i)).toBeInTheDocument();
  });

  it("ProtectedRoute redirects unauthenticated citizen to citizen login with redirect query", () => {
    render(
      <AuthProvider>
        <ProtectedRoute requiredRole="CITIZEN">
          <div data-testid="protected-content">Secret Citizen Area</div>
        </ProtectedRoute>
      </AuthProvider>
    );

    // Content should not be rendered
    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
    expect(mockPush).toHaveBeenCalledWith(expect.stringContaining("/citizen/login"));
  });

  it("ProtectedRoute redirects unauthenticated officer to officer login with redirect query", () => {
    render(
      <AuthProvider>
        <ProtectedRoute requiredRole="OFFICER">
          <div data-testid="protected-content">Secret Officer Area</div>
        </ProtectedRoute>
      </AuthProvider>
    );

    // Content should not be rendered
    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
    expect(mockPush).toHaveBeenCalledWith(expect.stringContaining("/officer/login"));
  });

  it("useAuth provides safe defaults when accessed outside AuthProvider", () => {
    function TestConsumer() {
      const auth = useAuth();
      return (
        <div>
          <span data-testid="auth-role">{auth.role || "NONE"}</span>
          <span data-testid="auth-status">{auth.isAuthenticated ? "YES" : "NO"}</span>
        </div>
      );
    }

    render(<TestConsumer />);
    expect(screen.getByTestId("auth-role")).toHaveTextContent("NONE");
    expect(screen.getByTestId("auth-status")).toHaveTextContent("NO");
  });

  describe("Open-Redirect Defense-in-Depth", () => {
    it("1. no redirect falls back to /citizen/dashboard", () => {
      expect(isSafeInternalRedirect(null)).toBe(false);
      expect(isSafeInternalRedirect(undefined)).toBe(false);
      expect(isSafeInternalRedirect("")).toBe(false);
      expect(getSafeRedirectUrl(null)).toBe("/citizen/dashboard");
      expect(getSafeRedirectUrl(undefined)).toBe("/citizen/dashboard");
      expect(getSafeRedirectUrl("")).toBe("/citizen/dashboard");
    });

    it("2. valid /citizen/dashboard is accepted", () => {
      expect(isSafeInternalRedirect("/citizen/dashboard")).toBe(true);
      expect(getSafeRedirectUrl("/citizen/dashboard")).toBe("/citizen/dashboard");
    });

    it("3. valid /eligibility?scheme=PM_KISAN is accepted", () => {
      expect(isSafeInternalRedirect("/eligibility?scheme=PM_KISAN")).toBe(true);
      expect(getSafeRedirectUrl("/eligibility?scheme=PM_KISAN")).toBe("/eligibility?scheme=PM_KISAN");
    });

    it("4. valid /schemes/PM_KISAN is accepted", () => {
      expect(isSafeInternalRedirect("/schemes/PM_KISAN")).toBe(true);
      expect(getSafeRedirectUrl("/schemes/PM_KISAN")).toBe("/schemes/PM_KISAN");
    });

    it("5. https://example.com is rejected and falls back to /citizen/dashboard", () => {
      expect(isSafeInternalRedirect("https://example.com")).toBe(false);
      expect(isSafeInternalRedirect("https://malicious.gov.in/phish")).toBe(false);
      expect(getSafeRedirectUrl("https://example.com")).toBe("/citizen/dashboard");
    });

    it("6. //example.com is rejected and falls back to /citizen/dashboard", () => {
      expect(isSafeInternalRedirect("//example.com")).toBe(false);
      expect(isSafeInternalRedirect("//")).toBe(false);
      expect(isSafeInternalRedirect("/\\example.com")).toBe(false);
      expect(getSafeRedirectUrl("//example.com")).toBe("/citizen/dashboard");
    });

    it("7. javascript:... is rejected and falls back to /citizen/dashboard", () => {
      expect(isSafeInternalRedirect("javascript:alert(1)")).toBe(false);
      expect(isSafeInternalRedirect("javascript:void(0)")).toBe(false);
      expect(getSafeRedirectUrl("javascript:alert(1)")).toBe("/citizen/dashboard");
    });

    it("8. data:... is rejected and falls back to /citizen/dashboard", () => {
      expect(isSafeInternalRedirect("data:text/html,<script>alert(1)</script>")).toBe(false);
      expect(getSafeRedirectUrl("data:text/html,...")).toBe("/citizen/dashboard");
    });
  });
});
