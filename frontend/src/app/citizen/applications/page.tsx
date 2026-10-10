"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useAuth } from "@/context/AuthContext";
import { citizenApi } from "@/api/citizen";
import { CitizenApplicationSummary } from "@/types/citizen";
import {
  ClipboardList,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Shield,
  RefreshCw,
  Search,
  Filter,
  FileCheck2,
  PlusCircle,
} from "lucide-react";

function getStatusBadge(app: CitizenApplicationSummary) {
  if (app.state === "DRAFT") {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-300">
        <Clock className="w-3.5 h-3.5 text-amber-600" />
        प्रारूप / Draft
      </span>
    );
  }

  if (app.state === "EVALUATED") {
    if (app.evaluation_outcome === "ELIGIBLE") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          पात्र / Eligible ({app.policy_version_code || "Evaluated"})
        </span>
      );
    }
    if (app.evaluation_outcome === "INELIGIBLE") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-red-800 border border-red-200">
          <AlertTriangle className="w-3.5 h-3.5 text-red-600" />
          अपात्र / Ineligible
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-800 border border-blue-200">
        <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
        मूल्यांकित / Evaluated
      </span>
    );
  }

  if (app.state === "ACTION_REQUIRED") {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-900 border border-amber-300">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
        कार्रवाई आवश्यक / Action Required
      </span>
    );
  }

  if (app.state === "VERIFICATION_IN_PROGRESS") {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-800 border border-blue-200">
        <Clock className="w-3.5 h-3.5 text-blue-600" />
        सत्यापन प्रगति पर / Under Verification
      </span>
    );
  }

  if (app.state === "EVIDENCE_PENDING") {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-800 border border-indigo-200">
        <Clock className="w-3.5 h-3.5 text-indigo-600" />
        साक्ष्य लंबित / Evidence Pending
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-700 border border-gray-300">
      {app.status_label_hi} / {app.status_label_en}
    </span>
  );
}

function CitizenApplicationsContent() {
  const { citizen, citizenToken } = useAuth();
  const [applications, setApplications] = useState<CitizenApplicationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterTab, setFilterTab] = useState<"ALL" | "IN_PROGRESS" | "EVALUATED">("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  const fetchApplications = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await citizenApi.getApplications(citizenToken);
      setApplications(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load applications. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, [citizenToken]);

  const filteredApps = applications.filter((app) => {
    if (filterTab === "IN_PROGRESS") {
      if (app.state === "EVALUATED" || app.state === "COMPLETED") return false;
    } else if (filterTab === "EVALUATED") {
      if (app.state !== "EVALUATED" && app.state !== "COMPLETED") return false;
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchRef = app.application_ref.toLowerCase().includes(q);
      const matchScheme = app.scheme_name.toLowerCase().includes(q);
      const matchCode = app.scheme_code.toLowerCase().includes(q);
      return matchRef || matchScheme || matchCode;
    }
    return true;
  });

  const inProgressCount = applications.filter(
    (a) => a.state !== "EVALUATED" && a.state !== "COMPLETED"
  ).length;
  const evaluatedCount = applications.filter(
    (a) => a.state === "EVALUATED" || a.state === "COMPLETED"
  ).length;

  return (
    <div className="gov-container py-8 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gov-border">
        <div>
          <div className="flex items-center space-x-2 text-gov-secondary text-xs mb-1">
            <Link href="/citizen/dashboard" className="hover:text-primary">
              नागरिक डैशबोर्ड / Dashboard
            </Link>
            <span>/</span>
            <span className="text-gov-text font-medium">मेरे आवेदन / Applications</span>
          </div>
          <h1 className="text-2xl font-bold text-gov-text">
            मेरे आवेदन एवं पात्रता दावे / My Scheme Applications & Claims
          </h1>
          <p className="text-xs text-gov-secondary mt-1">
            सिंथेटिक संदर्भ संख्या / Beneficiary Reference:{" "}
            <code className="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-primary font-bold">
              {citizen?.citizen_ref}
            </code>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchApplications}
            title="Refresh applications"
            className="p-2 rounded border border-gov-border bg-white hover:bg-gray-50 text-gov-text transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>

          <Link
            href="/citizen/schemes"
            className="gov-button-primary inline-flex items-center space-x-2 text-xs font-semibold px-4 py-2.5 rounded-md shadow-sm"
          >
            <PlusCircle className="w-4 h-4" />
            <span>नया आवेदन / Apply for Scheme</span>
          </Link>

          <Link
            href="/eligibility"
            className="hidden sm:inline-flex items-center space-x-2 text-xs font-semibold px-4 py-2.5 rounded-md border border-gov-border bg-white hover:bg-gray-50 text-gov-text transition-colors"
          >
            <span>पात्रता जांच / Eligibility Check</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Filter Tabs and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        {/* Tabs */}
        <div className="flex border-b border-gov-border sm:border-b-0 space-x-2">
          <button
            onClick={() => setFilterTab("ALL")}
            className={`text-xs font-semibold px-3.5 py-2 rounded-md transition-colors ${
              filterTab === "ALL"
                ? "bg-primary text-white"
                : "bg-white text-gov-secondary hover:text-gov-text border border-gov-border"
            }`}
          >
            सभी आवेदन / All ({applications.length})
          </button>
          <button
            onClick={() => setFilterTab("IN_PROGRESS")}
            className={`text-xs font-semibold px-3.5 py-2 rounded-md transition-colors ${
              filterTab === "IN_PROGRESS"
                ? "bg-primary text-white"
                : "bg-white text-gov-secondary hover:text-gov-text border border-gov-border"
            }`}
          >
            सत्यापन प्रक्रिया में / Under Review ({inProgressCount})
          </button>
          <button
            onClick={() => setFilterTab("EVALUATED")}
            className={`text-xs font-semibold px-3.5 py-2 rounded-md transition-colors ${
              filterTab === "EVALUATED"
                ? "bg-primary text-white"
                : "bg-white text-gov-secondary hover:text-gov-text border border-gov-border"
            }`}
          >
            मूल्यांकन पूर्ण / Evaluated ({evaluatedCount})
          </button>
        </div>

        {/* Search */}
        <div className="relative max-w-xs w-full">
          <Search className="w-4 h-4 text-gov-secondary absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="खोजें / Search reference, scheme..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="gov-input pl-9 text-xs w-full py-1.5"
          />
        </div>
      </div>

      {/* Applications List */}
      <div className="bg-white border border-gov-border rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs text-gov-secondary space-y-2">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-primary" />
            <p>आवेदन विवरण लोड हो रहा है... / Loading application records...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center space-y-3">
            <p className="text-xs text-red-600 font-semibold">{error}</p>
            <button
              onClick={fetchApplications}
              className="text-xs font-semibold text-primary underline"
            >
              पुनः प्रयास करें / Retry
            </button>
          </div>
        ) : filteredApps.length > 0 ? (
          <div className="divide-y divide-gov-border">
            {filteredApps.map((app) => (
              <div
                key={app.id}
                className="p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-5 hover:bg-slate-50 transition-colors"
              >
                <div className="space-y-2 max-w-2xl">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs font-bold text-primary bg-primary-50 px-2.5 py-0.5 rounded border border-primary-200">
                      {app.application_ref}
                    </span>
                    <h2 className="text-base font-bold text-gov-text">
                      {app.scheme_name}
                      {app.scheme_name_hi ? ` (${app.scheme_name_hi})` : ""}
                    </h2>
                  </div>

                  <p className="text-xs text-gov-secondary">
                    {app.ministry ? `${app.ministry} • ` : ""}
                    योजना कोड: <strong className="text-gov-text">{app.scheme_code}</strong>
                  </p>

                  <div className="text-xs text-gov-secondary flex items-center gap-4 flex-wrap pt-1">
                    {app.submitted_at ? (
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-gov-secondary" />
                        प्रस्तुत / Submitted:{" "}
                        {new Date(app.submitted_at).toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </span>
                    ) : app.state === "DRAFT" ? (
                      <span className="flex items-center gap-1 text-amber-700 font-medium">
                        <Clock className="w-3.5 h-3.5 text-amber-600" />
                        प्रारूप बनाया / Draft:{" "}
                        {new Date(app.created_at).toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </span>
                    ) : (
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-gov-secondary" />
                        सृजित / Created:{" "}
                        {new Date(app.created_at).toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </span>
                    )}
                    <span>
                      • अद्यतन / Updated:{" "}
                      {new Date(app.updated_at).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                    <span className="bg-gray-100 text-gov-text px-2 py-0.5 rounded text-[11px]">
                      {app.claims_count} दावे / Claims
                    </span>
                    <span className="bg-gray-100 text-gov-text px-2 py-0.5 rounded text-[11px]">
                      {app.evidence_count} दस्तावेज़ / Evidence
                    </span>
                  </div>
                </div>

                <div className="flex flex-col sm:items-end gap-3 flex-shrink-0">
                  <div>{getStatusBadge(app)}</div>
                  {app.state === "DRAFT" ? (
                    <div className="flex items-center gap-2 flex-wrap sm:justify-end">
                      <Link
                        href={`/citizen/applications/new?scheme=${app.scheme_code}&applicationId=${app.id}`}
                        className="gov-button-primary inline-flex items-center space-x-1.5 text-xs font-semibold px-3 py-1.5 rounded-md"
                      >
                        <span>आवेदन पूरा करें / Resume</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                      <Link
                        href={`/citizen/applications/${app.id}`}
                        className="px-3 py-1.5 rounded-md border border-gov-border bg-white hover:bg-gray-50 text-xs font-semibold text-gov-text transition-colors"
                      >
                        डोज़ियर / Dossier
                      </Link>
                    </div>
                  ) : (
                    <Link
                      href={`/citizen/applications/${app.id}`}
                      className="gov-button-primary inline-flex items-center space-x-1.5 text-xs font-semibold px-4 py-2 rounded-md"
                    >
                      <span>डोज़ियर देखें / View Dossier</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-12 text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center text-gov-secondary mx-auto">
              <ClipboardList className="w-6 h-6" />
            </div>
            <div className="max-w-md mx-auto">
              <h3 className="text-sm font-bold text-gov-text">
                कोई मेल खाने वाले आवेदन नहीं मिले / No Matching Applications Found
              </h3>
              <p className="text-xs text-gov-secondary mt-1 leading-relaxed">
                {searchQuery
                  ? "आपकी खोज से कोई आवेदन मेल नहीं खाता। कृपया दूसरा कीवर्ड आज़माएं।"
                  : "आप समर्थित योजनाओं के लिए अपनी पात्रता का तुरंत परीक्षण कर सकते हैं और नया आवेदन प्रारंभ कर सकते हैं।"}
              </p>
            </div>
            <div className="pt-2">
              <Link
                href="/citizen/schemes"
                className="gov-button-primary inline-flex items-center space-x-1.5 text-xs font-semibold px-4 py-2 rounded-md"
              >
                <span>उपलब्ध योजनाएं देखें / View Available Schemes</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function CitizenApplicationsPage() {
  return (
    <ProtectedRoute requiredRole="CITIZEN">
      <CitizenApplicationsContent />
    </ProtectedRoute>
  );
}
