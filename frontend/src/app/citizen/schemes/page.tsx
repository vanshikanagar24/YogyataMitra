"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useAuth } from "@/context/AuthContext";
import { citizenApi } from "@/api/citizen";
import { AvailableSchemeSummary } from "@/types/citizen";
import {
  FileText,
  Search,
  CheckCircle2,
  ArrowRight,
  ExternalLink,
  ShieldCheck,
  Building2,
  Calendar,
  Sparkles,
  Info,
} from "lucide-react";

function CitizenSchemesContent() {
  const { citizenToken } = useAuth();
  const [schemes, setSchemes] = useState<AvailableSchemeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    async function loadSchemes() {
      setLoading(true);
      setError(null);
      try {
        const data = await citizenApi.getAvailableSchemes(citizenToken);
        setSchemes(data);
      } catch (err: any) {
        setError(err?.message || "Failed to load available schemes.");
      } finally {
        setLoading(false);
      }
    }
    loadSchemes();
  }, [citizenToken]);

  const filteredSchemes = schemes.filter(
    (s) =>
      s.name_en.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.name_hi.includes(searchQuery) ||
      s.scheme_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (s.ministry && s.ministry.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="gov-container py-8 max-w-6xl mx-auto space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center space-x-2 text-gov-secondary text-xs mb-1">
        <Link href="/citizen/dashboard" className="hover:text-primary">
          नागरिक डैशबोर्ड / Dashboard
        </Link>
        <span>/</span>
        <span className="text-gov-text font-medium">उपलब्ध योजनाएं / Available Schemes</span>
      </div>

      <main className="w-full">
        {/* Header Banner */}
        <div className="bg-gradient-to-r from-blue-900 to-indigo-900 rounded-2xl p-6 sm:p-8 text-white shadow-md mb-8">
          <div className="max-w-3xl">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-800/80 text-blue-200 border border-blue-700/60 mb-4">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Statutory Government Schemes • अधिकृत सरकारी योजनाएं
            </span>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
              Available Welfare Schemes • उपलब्ध योजनाएं
            </h1>
            <p className="mt-2 text-blue-100 text-sm sm:text-base leading-relaxed">
              Explore welfare schemes with active statutory rules, inspect eligibility criteria, and
              initiate your official digital application directly with transparent tracking.
            </p>
          </div>
        </div>

        {/* Search & Filter Bar */}
        <div className="flex flex-col sm:flex-row gap-4 items-center justify-between mb-8">
          <div className="relative w-full sm:w-96">
            <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search scheme by name or ministry..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent shadow-sm"
            />
          </div>
          <div className="text-xs text-gray-500 font-medium self-end sm:self-center">
            Showing {filteredSchemes.length} active statutory scheme(s)
          </div>
        </div>

        {/* Loading / Error States */}
        {loading && (
          <div className="py-20 flex flex-col items-center justify-center text-gray-500">
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-3" />
            <p className="text-sm">Loading active statutory schemes...</p>
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-800 text-sm mb-6">
            {error}
          </div>
        )}

        {/* Scheme Cards Grid */}
        {!loading && !error && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {filteredSchemes.map((scheme) => (
              <div
                key={scheme.id}
                className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div>
                      <span className="inline-block px-2.5 py-0.5 rounded-md text-xs font-bold uppercase tracking-wider bg-blue-50 text-blue-800 border border-blue-200 mb-1.5">
                        {scheme.scheme_code}
                      </span>
                      <h2 className="text-xl font-bold text-gray-900 leading-snug">
                        {scheme.name_en}
                      </h2>
                      <p className="text-sm font-medium text-gray-600 mt-0.5">
                        {scheme.name_hi}
                      </p>
                    </div>
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Active Enactment
                    </span>
                  </div>

                  {scheme.ministry && (
                    <div className="flex items-center gap-2 text-xs text-gray-500 mb-4">
                      <Building2 className="w-3.5 h-3.5 text-gray-400" />
                      <span>{scheme.ministry}</span>
                    </div>
                  )}

                  <p className="text-sm text-gray-600 line-clamp-3 mb-4 leading-relaxed">
                    {scheme.description_en}
                  </p>

                  <div className="bg-slate-50 rounded-xl p-3.5 border border-slate-100 mb-6 text-xs text-slate-700 space-y-1.5">
                    <div className="font-semibold text-slate-900 flex items-center gap-1.5">
                      <Info className="w-3.5 h-3.5 text-blue-600" />
                      Statutory Requirements Highlights:
                    </div>
                    {scheme.scheme_code === "PM_KISAN" && (
                      <ul className="list-disc list-inside text-slate-600 space-y-0.5 pl-1">
                        <li>Cultivable landholding ownership recorded in revenue records (RoR)</li>
                        <li>Exclusion checks: Institutional, constitutional posts, tax payers</li>
                        <li>Supported Evidence: Land Record (7/12), Aadhaar, Bank Passbook</li>
                      </ul>
                    )}
                    {scheme.scheme_code === "SSY" && (
                      <ul className="list-disc list-inside text-slate-600 space-y-0.5 pl-1">
                        <li>Girl child up to 10 years of age (Indian resident citizen)</li>
                        <li>Natural or legal guardian application; max 2 accounts per family</li>
                        <li>Supported Evidence: Birth Certificate, Guardian ID, Bank Record</li>
                      </ul>
                    )}
                    {scheme.scheme_code === "PM_KMY" && (
                      <ul className="list-disc list-inside text-slate-600 space-y-0.5 pl-1">
                        <li>Small & Marginal Farmers (cultivable land up to 2.0 hectares)</li>
                        <li>Entry age 18 to 40 years; guaranteed monthly pension of ₹3,000 after 60</li>
                        <li>Supported Evidence: Aadhaar, Land Record (RoR), Bank Passbook</li>
                      </ul>
                    )}
                    {scheme.scheme_code === "PMUY" && (
                      <ul className="list-disc list-inside text-slate-600 space-y-0.5 pl-1">
                        <li>Adult woman member (18+) of eligible deprivation/BPL household</li>
                        <li>No existing LPG connection registered to any member of the household</li>
                        <li>Supported Evidence: Ration Card / Deprivation Proof, Aadhaar, Bank Passbook</li>
                      </ul>
                    )}
                    {scheme.scheme_code === "PM_VISHWAKARMA" && (
                      <ul className="list-disc list-inside text-slate-600 space-y-0.5 pl-1">
                        <li>Artisans & craftspeople working in 18 notified traditional family trades</li>
                        <li>Minimum age 18 years; one member per family; no recent credit default</li>
                        <li>Supported Evidence: Artisan ID / Trade Declaration, Aadhaar, Bank Passbook</li>
                      </ul>
                    )}
                    {scheme.scheme_code === "PMAY_G" && (
                      <ul className="list-disc list-inside text-slate-600 space-y-0.5 pl-1">
                        <li>Rural houseless families or living in kutcha/dilapidated house</li>
                        <li>SECC 2011 deprivation / Awaas+ list; no pucca house anywhere in India</li>
                        <li>Supported Evidence: Housing Verification Certificate, Job Card, Aadhaar</li>
                      </ul>
                    )}
                    {scheme.scheme_code === "PMAY_U_2_0" && (
                      <ul className="list-disc list-inside text-slate-600 space-y-0.5 pl-1">
                        <li>EWS / LIG / MIG families in statutory towns without pucca house</li>
                        <li>Income verified against statutory brackets (EWS ≤ ₹3L, LIG ≤ ₹6L, MIG ≤ ₹9L)</li>
                        <li>Supported Evidence: Income Certificate, Non-Pucca House Affidavit, Aadhaar</li>
                      </ul>
                    )}
                    {scheme.scheme_code === "PM_SVANIDHI" && (
                      <ul className="list-disc list-inside text-slate-600 space-y-0.5 pl-1">
                        <li>Urban street vendors engaged in vending before statutory cutoff date</li>
                        <li>Possession of Certificate of Vending (CoV) / ID card or ULB recommendation</li>
                        <li>Supported Evidence: Vending Proof / LOR, Aadhaar, Bank Passbook</li>
                      </ul>
                    )}
                    {scheme.scheme_code === "PMMVY" && (
                      <ul className="list-disc list-inside text-slate-600 space-y-0.5 pl-1">
                        <li>Pregnant Women & Lactating Mothers (PW&LM) under Mission Shakti</li>
                        <li>Applicable for first live birth, or second child if girl child</li>
                        <li>Supported Evidence: Mother and Child Protection (MCP) Card, Aadhaar</li>
                      </ul>
                    )}
                    {scheme.scheme_code === "IGNOAPS" && (
                      <ul className="list-disc list-inside text-slate-600 space-y-0.5 pl-1">
                        <li>Senior citizens aged 60 years or above living below poverty line</li>
                        <li>BPL status verified by competent State/UT civil supplies authority</li>
                        <li>Supported Evidence: Age Proof (Aadhaar / Voter ID), BPL Card / Certificate</li>
                      </ul>
                    )}
                  </div>
                </div>

                <div className="pt-4 border-t border-gray-100 flex items-center justify-between gap-4">
                  <a
                    href={scheme.official_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-blue-700 transition-colors font-medium"
                  >
                    <span>Official Portal</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>

                  <Link
                    href={`/citizen/applications/new?scheme=${scheme.scheme_code}`}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-700 text-white text-sm font-semibold hover:bg-blue-800 transition-colors shadow-sm"
                  >
                    <span>Start Application • आवेदन शुरू करें</span>
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Roadmap Schemes Preview (Future Expansion Notice) */}
        <div className="mt-12 bg-white rounded-2xl border border-dashed border-gray-300 p-6">
          <div className="flex items-center gap-2 text-sm font-bold text-gray-700 mb-2">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span>Future Welfare Schemes Roadmap • आगामी योजनाएं (Pipeline)</span>
          </div>
          <p className="text-xs text-gray-500 leading-relaxed mb-4">
            Ten core national statutory welfare schemes are fully operationalized with deterministic AST evaluation
            and generic forms. Additional statutory schemes are planned for subsequent expansions.
          </p>
          <div className="flex flex-wrap gap-2">
            {["PM-JAY", "MGNREGA", "PMJJBY", "PMSBY", "APY"].map((code) => (
              <span
                key={code}
                className="px-2.5 py-1 rounded-lg text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200"
              >
                {code} (Planned)
              </span>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

export default function CitizenSchemesPage() {
  return (
    <ProtectedRoute requiredRole="CITIZEN">
      <CitizenSchemesContent />
    </ProtectedRoute>
  );
}
