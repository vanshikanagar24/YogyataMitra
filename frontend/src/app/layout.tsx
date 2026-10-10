import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "../context/QueryProvider";
import { AuthProvider } from "../context/AuthContext";
import { LanguageProvider } from "../context/LanguageContext";
import { GlobalNavbar } from "../components/layout/GlobalNavbar";
import { Footer } from "../components/layout/Footer";

export const metadata: Metadata = {
  title: "योग्यता मित्र | YogyataMitra — Government Scheme Eligibility & Verification Portal",
  description:
    "Deterministic welfare scheme eligibility evaluation, policy provenance, and cryptographic ruleset verification for Indian citizens.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="hi" suppressHydrationWarning>
      <body className="flex flex-col min-h-screen bg-gov-bg text-gov-text antialiased">
        <QueryProvider>
          <AuthProvider>
            <LanguageProvider>
              <a href="#main-content" className="skip-to-content">
                मुख्य सामग्री पर जाएं / Skip to main content
              </a>
              <GlobalNavbar />
              <main id="main-content" tabIndex={-1} className="flex-grow focus:outline-none">
                {children}
              </main>
              <Footer />
            </LanguageProvider>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
