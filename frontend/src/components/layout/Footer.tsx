"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLanguage } from "../../context/LanguageContext";
import { Shield, FileCheck, CheckCircle2, Scale } from "lucide-react";

export const Footer: React.FC = () => {
  const { t, isHindi } = useLanguage();
  const pathname = usePathname();

  if (pathname?.startsWith("/officer")) {
    return (
      <footer className="bg-slate-950 text-slate-400 border-t border-slate-800 py-4 text-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-2">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-300">YogyataMitra Officer Portal</span>
            <span className="text-slate-600">|</span>
            <span>Authorized Internal Use Only</span>
          </div>
          <div className="text-amber-400 font-medium">
            DEVELOPMENT DEMO ENVIRONMENT &bull; NO REAL SSO OR AADHAAR
          </div>
          <div>Audit Logging: Append-Only Active</div>
        </div>
      </footer>
    );
  }

  return (
    <footer className="bg-primary-dark text-white border-t border-navy-700 mt-16 pt-12 pb-8">
      <div className="gov-container">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 pb-10 border-b border-navy-700">
          {/* Col 1: Platform identity */}
          <div className="md:col-span-2 space-y-4">
            <div className="flex items-center space-x-3">
              <div className="relative w-9 h-9 flex items-center justify-center flex-shrink-0">
                <img
                  src="/images/logo.png"
                  alt="YogyataMitra Emblem"
                  className="w-9 h-9 object-contain"
                />
                <span className="sr-only">YM</span>
              </div>
              <span className="text-xl font-bold tracking-tight">
                {isHindi ? "योग्यता मित्र" : "YogyataMitra"}
              </span>
            </div>
            <p className="text-sm text-gray-300 max-w-lg leading-relaxed">
              {t("footer.description")}
            </p>
            <div className="flex flex-wrap gap-4 pt-2 text-xs text-gray-300">
              <div className="flex items-center space-x-1.5">
                <Shield className="w-4 h-4 text-blue-400" />
                <span>{isHindi ? "100% वैधानिक नियम" : "Deterministic Policy Rules"}</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <FileCheck className="w-4 h-4 text-blue-400" />
                <span>{isHindi ? "राजपत्र आधारित स्रोत" : "Statutory Gazette Provenance"}</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <Scale className="w-4 h-4 text-blue-400" />
                <span>{isHindi ? "प्रमाणित नीति अखंडता" : "Certified Policy Integrity"}</span>
              </div>
            </div>
          </div>

          {/* Col 2: Navigation Links */}
          <div className="space-y-3">
            <h4 className="text-sm font-bold uppercase tracking-wider text-blue-300">
              {t("footer.quick_links")}
            </h4>
            <ul className="space-y-2 text-sm text-gray-300">
              <li>
                <Link href="/" className="hover:text-white transition-colors">
                  {t("nav.home")}
                </Link>
              </li>
              <li>
                <Link href="/schemes" className="hover:text-white transition-colors">
                  {t("nav.schemes")}
                </Link>
              </li>
              <li>
                <Link href="/eligibility" className="hover:text-white transition-colors">
                  {t("nav.eligibility")}
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 3: Policy & Audit */}
          <div className="space-y-3">
            <h4 className="text-sm font-bold uppercase tracking-wider text-blue-300">
              {t("footer.policies")}
            </h4>
            <ul className="space-y-2 text-sm text-gray-300">
              <li>
                <Link href="/policy-verification" className="hover:text-white transition-colors">
                  {t("nav.policy_verification")}
                </Link>
              </li>
              <li>
                <Link href="/audit-history" className="hover:text-white transition-colors">
                  {t("nav.audit_history")}
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Disclaimer & Copyright */}
        <div className="pt-8 flex flex-col md:flex-row items-center justify-between text-xs text-gray-400 space-y-4 md:space-y-0">
          <p className="max-w-2xl text-center md:text-left">
            {t("footer.disclaimer")}
          </p>
          <p className="text-center md:text-right font-medium text-gray-300">
            {t("footer.copyright")}
          </p>
        </div>
      </div>
    </footer>
  );
};
