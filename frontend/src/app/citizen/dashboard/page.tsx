"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useAuth } from "@/context/AuthContext";
import { citizenApi } from "@/api/citizen";
import { CitizenApplicationSummary, CitizenDashboardStats } from "@/types/citizen";
import {
  User,
  ShieldCheck,
  ClipboardList,
  LayoutGrid,
  MapPin,
  ArrowRight,
  Clock,
  CheckCircle2,
  AlertTriangle,
  FileText,
  RefreshCw,
  ExternalLink,
} from "lucide-react";

function getStatusBadge(app: CitizenApplicationSummary) {
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

function CitizenDashboardContent() {
  const { citizen, citizenToken } = useAuth();
  const [stats, setStats] = useState<CitizenDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await citizenApi.getDashboardStats(citizenToken);
      setStats(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load dashboard metrics. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [citizenToken]);

  return (
    <div className="gov-container py-8 max-w-5xl mx-auto space-y-6">
      {/* Welcome Banner */}
      <div className="bg-white border border-gov-border rounded-xl p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-4">
            <div className="w-14 h-14 rounded-full bg-primary-50 border border-primary-200 flex items-center justify-center text-primary flex-shrink-0">
              <User className="w-7 h-7" />
            </div>
            <div>
              <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                <h1 className="text-2xl font-bold text-gov-text">
                  नमस्ते, {citizen?.citizen_name || "नागरिक"}
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                  सत्यापित नागरिक / Verified Citizen
                </span>
              </div>
              <p className="text-xs text-gov-secondary mt-1 flex items-center gap-3 flex-wrap">
                <span>
                  <strong>सिंथेटिक संदर्भ संख्या / Reference:</strong>{" "}
                  <code className="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-primary font-bold">
                    {citizen?.citizen_ref}
                  </code>
                </span>
                {citizen?.state && (
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-gov-secondary" />
                    {citizen?.district ? `${citizen.district}, ` : ""}
                    {citizen?.state}
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3 w-full sm:w-auto">
            <Link
              href="/citizen/profile"
              className="text-xs font-semibold px-3 py-2 rounded border border-gov-border hover:bg-gray-50 text-gov-text transition-colors"
            >
              प्रोफ़ाइल देखें / View Profile
            </Link>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Metric 1: Total */}
        <div className="bg-white border border-gov-border rounded-xl p-5 shadow-sm">
          <div className="text-xs font-semibold text-gov-secondary mb-1">
            कुल आवेदन / Total Applications
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-gov-text">
            {loading ? "..." : stats?.total_applications ?? 0}
          </div>
          <p className="text-[11px] text-gov-secondary mt-1">योजनाओं में सक्रिय दावे</p>
        </div>

        {/* Metric 2: Under Verification */}
        <div className="bg-white border border-gov-border rounded-xl p-5 shadow-sm">
          <div className="text-xs font-semibold text-blue-700 mb-1">
            प्रक्रियाधीन / Under Review
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-blue-800">
            {loading ? "..." : stats?.in_progress_count ?? 0}
          </div>
          <p className="text-[11px] text-gov-secondary mt-1">अधिकारी सत्यापन प्रगति पर</p>
        </div>

        {/* Metric 3: Evaluated / Available */}
        <div className="bg-white border border-gov-border rounded-xl p-5 shadow-sm">
          <div className="text-xs font-semibold text-emerald-700 mb-1">
            मूल्यांकन पूर्ण / Evaluated
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-emerald-800">
            {loading ? "..." : stats?.evaluated_count ?? 0}
          </div>
          <p className="text-[11px] text-gov-secondary mt-1">पात्रता निर्णय तैयार</p>
        </div>

        {/* Metric 4: Action Required */}
        <div className="bg-white border border-gov-border rounded-xl p-5 shadow-sm">
          <div className="text-xs font-semibold text-amber-700 mb-1">
            कार्रवाई आवश्यक / Action Req.
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-amber-800">
            {loading ? "..." : stats?.action_required_count ?? 0}
          </div>
          <p className="text-[11px] text-gov-secondary mt-1">दस्तावेज़ या स्पष्टीकरण लंबित</p>
        </div>
      </div>

      {/* Recent Applications Section */}
      <div className="bg-white border border-gov-border rounded-xl shadow-sm overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-gov-border bg-gray-50 flex items-center justify-between">
          <h2 className="text-sm font-bold text-gov-text flex items-center gap-2">
            <ClipboardList className="w-4 h-4 text-primary" />
            हाल के आवेदन एवं सत्यापन / Recent Applications & Status
          </h2>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchStats}
              title="Refresh status"
              className="text-gov-secondary hover:text-primary transition-colors p-1 rounded hover:bg-gray-200"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            </button>
            <Link
              href="/citizen/applications"
              className="text-xs font-semibold text-primary hover:underline flex items-center gap-1"
            >
              सभी देखें / View All
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        {loading ? (
          <div className="p-8 text-center text-xs text-gov-secondary">
            डेटा लोड हो रहा है... / Loading applications...
          </div>
        ) : error ? (
          <div className="p-6 text-center space-y-2">
            <p className="text-xs text-red-600 font-medium">{error}</p>
            <button
              onClick={fetchStats}
              className="text-xs font-semibold text-primary underline"
            >
              पुनः प्रयास करें / Retry
            </button>
          </div>
        ) : stats?.recent_applications && stats.recent_applications.length > 0 ? (
          <div className="divide-y divide-gov-border">
            {stats.recent_applications.map((app) => (
              <div
                key={app.id}
                className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs font-bold text-primary bg-primary-50 px-2 py-0.5 rounded border border-primary-200">
                      {app.application_ref}
                    </span>
                    <h3 className="text-sm font-bold text-gov-text">
                      {app.scheme_name}
                      {app.scheme_name_hi ? ` (${app.scheme_name_hi})` : ""}
                    </h3>
                  </div>
                  <div className="text-xs text-gov-secondary flex items-center gap-3 flex-wrap">
                    <span>
                      योजना कोड: <strong>{app.scheme_code}</strong>
                    </span>
                    {app.ministry && <span>• {app.ministry}</span>}
                    <span>
                      • अद्यतन:{" "}
                      {new Date(app.updated_at || app.created_at).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                    <span>• {app.claims_count} दावे / Claims</span>
                    <span>• {app.evidence_count} दस्तावेज़ / Evidence</span>
                  </div>
                </div>

                <div className="flex items-center gap-3 flex-shrink-0">
                  {getStatusBadge(app)}
                  <Link
                    href={`/citizen/applications/${app.id}`}
                    className="text-xs font-semibold px-3 py-1.5 rounded border border-gov-border bg-white hover:bg-gray-100 text-gov-text transition-colors flex items-center gap-1"
                  >
                    <span>विवरण / View Dossier</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center text-gov-secondary mx-auto">
              <Clock className="w-6 h-6" />
            </div>
            <div className="max-w-md mx-auto">
              <h3 className="text-sm font-bold text-gov-text">
                कोई सक्रिय आवेदन नहीं मिला / No Applications Filed Yet
              </h3>
              <p className="text-xs text-gov-secondary mt-1 leading-relaxed">
                आप समर्थित योजनाओं (PM-KISAN, SSY) के लिए अपनी पात्रता का परीक्षण कर सकते हैं और नया आवेदन प्रस्तुत कर सकते हैं।
              </p>
            </div>
            <div className="pt-2">
              <Link
                href="/schemes"
                className="gov-button-primary inline-flex items-center space-x-1.5 text-xs font-semibold px-4 py-2 rounded-md"
              >
                <span>उपलब्ध योजनाएं देखें / Browse Schemes</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* Quick Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Card 1: Check Eligibility */}
        <div className="bg-white border border-gov-border rounded-xl p-6 shadow-sm flex flex-col justify-between hover:border-primary-300 transition-colors">
          <div>
            <div className="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-primary mb-4">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h2 className="text-base font-bold text-gov-text">
              पात्रता जांचें / Check Scheme Eligibility
            </h2>
            <p className="text-xs text-gov-secondary mt-2 leading-relaxed">
              सत्यापनीय सरकारी नियमों के आधार पर पीएम-किसान और सुकन्या समृद्धि योजना के लिए अपनी पात्रता का तुरंत मूल्यांकन करें।
            </p>
          </div>
          <Link
            href="/eligibility"
            className="mt-5 inline-flex items-center justify-between text-xs font-semibold text-primary hover:text-primary-dark group"
          >
            <span>मूल्यांकन प्रारंभ करें / Start Evaluation</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>

        {/* Card 2: Browse Schemes */}
        <div className="bg-white border border-gov-border rounded-xl p-6 shadow-sm flex flex-col justify-between hover:border-primary-300 transition-colors">
          <div>
            <div className="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 mb-4">
              <LayoutGrid className="w-5 h-5" />
            </div>
            <h2 className="text-base font-bold text-gov-text">
              सरकारी योजनाएं / Welfare Schemes
            </h2>
            <p className="text-xs text-gov-secondary mt-2 leading-relaxed">
              वर्तमान में समर्थित योजनाओं (PM-KISAN, SSY) के नियम, लाभ, पात्रता मानदंड और आधिकारिक स्रोत विवरण देखें।
            </p>
          </div>
          <Link
            href="/schemes"
            className="mt-5 inline-flex items-center justify-between text-xs font-semibold text-emerald-700 hover:text-emerald-800 group"
          >
            <span>योजनाएं ब्राउज़ करें / Browse Schemes</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>

        {/* Card 3: My Applications */}
        <div className="bg-white border border-gov-border rounded-xl p-6 shadow-sm flex flex-col justify-between hover:border-primary-300 transition-colors">
          <div>
            <div className="w-10 h-10 rounded-lg bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-700 mb-4">
              <ClipboardList className="w-5 h-5" />
            </div>
            <h2 className="text-base font-bold text-gov-text">
              मेरे आवेदन / My Applications
            </h2>
            <p className="text-xs text-gov-secondary mt-2 leading-relaxed">
              अपने प्रस्तुत दावों, दस्तावेज़ साक्ष्यों, मूल्यांकन इतिहास और अधिकारी सत्यापन स्थिति की समीक्षा करें।
            </p>
          </div>
          <Link
            href="/citizen/applications"
            className="mt-5 inline-flex items-center justify-between text-xs font-semibold text-purple-700 hover:text-purple-800 group"
          >
            <span>आवेदन सूची / View Applications</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function CitizenDashboardPage() {
  return (
    <ProtectedRoute requiredRole="CITIZEN">
      <CitizenDashboardContent />
    </ProtectedRoute>
  );
}
