"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Sparkles,
  Search,
  Filter,
  AlertTriangle,
  FileCheck2,
  Clock,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ExternalLink,
  ChevronRight,
  RefreshCw,
  Layers,
  BookOpen,
  Calendar,
} from "lucide-react";
import { useOfficerAuth } from "@/context/OfficerAuthContext";

interface CandidateItem {
  id: string;
  scheme_id: string;
  scheme_code: string | null;
  scheme_name: string | null;
  title: string;
  candidate_type: string;
  candidate_text_en: string;
  candidate_text_hi: string;
  normalized_concept: string;
  source_url: string;
  source_title: string;
  source_publisher: string;
  source_document_identifier: string | null;
  source_publication_date: string | null;
  source_effective_date: string | null;
  source_excerpt: string;
  discovered_at: string;
  discovered_by: string;
  ai_provider: string;
  ai_model: string;
  extraction_confidence: number;
  confidence_explanation: string | null;
  provenance_status: string;
  effective_date_status: string;
  conflict_detected: boolean;
  duplicate_status: string;
  review_status: string;
  reviewer_id: string | null;
  reviewed_at: string | null;
  reviewer_reason: string | null;
  retrieved_at?: string | null;
  adversarial_flag_detected?: boolean;
}

interface DiscoveryMetrics {
  total_candidates: number;
  pending_review: number;
  in_review: number;
  needs_clarification: number;
  approved: number;
  rejected: number;
  archived: number;
  conflict_detected: number;
}

export default function OfficerPolicyDiscoveryPage() {
  const { isAuthenticated, isLoading: authLoading, token } = useOfficerAuth();
  const router = useRouter();

  const [candidates, setCandidates] = useState<CandidateItem[]>([]);
  const [metrics, setMetrics] = useState<DiscoveryMetrics>({
    total_candidates: 0,
    pending_review: 0,
    in_review: 0,
    needs_clarification: 0,
    approved: 0,
    rejected: 0,
    archived: 0,
    conflict_detected: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState("ALL");
  const [schemeFilter, setSchemeFilter] = useState("ALL");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  const [isDiscovering, setIsDiscovering] = useState(false);
  const [discoverScheme, setDiscoverScheme] = useState("PM_KISAN");
  const [discoverySuccess, setDiscoverySuccess] = useState<string | null>(null);

  // Authentication guard
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/officer/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const fetchCandidates = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (statusFilter !== "ALL") params.set("status", statusFilter);
      if (schemeFilter !== "ALL") params.set("scheme", schemeFilter);
      if (typeFilter !== "ALL") params.set("type", typeFilter);

      const res = await fetch(`/api/v1/officer/policy-discovery/candidates?${params.toString()}`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          router.push("/officer/login");
          return;
        }
        throw new Error(`Failed to load policy discovery candidates (HTTP ${res.status})`);
      }

      const data = await res.json();
      setCandidates(data.candidates || []);
      if (data.metrics) {
        setMetrics(data.metrics);
      }
    } catch (err: any) {
      setError(err?.message || "An unexpected error occurred while fetching discovery candidates.");
    } finally {
      setLoading(false);
    }
  }, [token, statusFilter, schemeFilter, typeFilter, router]);

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchCandidates();
    }
  }, [isAuthenticated, token, fetchCandidates]);

  const handleRunDiscovery = async () => {
    if (!token) return;
    setIsDiscovering(true);
    setError(null);
    setDiscoverySuccess(null);

    try {
      const res = await fetch("/api/v1/officer/policy-discovery/discover", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ scheme_code: discoverScheme }),
      });

      if (!res.ok) {
        throw new Error(`Discovery run failed (HTTP ${res.status})`);
      }

      const newCandidates = await res.json();
      setDiscoverySuccess(
        `Discovery completed for ${discoverScheme}: ${newCandidates.length} candidate statement(s) extracted and queued for human review.`
      );
      await fetchCandidates();
    } catch (err: any) {
      setError(err?.message || "Failed to trigger AI policy discovery.");
    } finally {
      setIsDiscovering(false);
    }
  };

  const filteredCandidates = candidates.filter((c) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      c.title.toLowerCase().includes(q) ||
      c.normalized_concept.toLowerCase().includes(q) ||
      c.candidate_text_en.toLowerCase().includes(q) ||
      c.source_title.toLowerCase().includes(q)
    );
  });

  const getStatusBadge = (st: string) => {
    switch (st) {
      case "APPROVED":
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-bold bg-green-100 text-green-800 border border-green-200">
            <CheckCircle2 className="w-3 h-3" />
            <span>APPROVED</span>
          </span>
        );
      case "REJECTED":
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-bold bg-red-100 text-red-800 border border-red-200">
            <XCircle className="w-3 h-3" />
            <span>REJECTED</span>
          </span>
        );
      case "NEEDS_CLARIFICATION":
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-bold bg-orange-100 text-orange-800 border border-orange-200">
            <HelpCircle className="w-3 h-3" />
            <span>NEEDS CLARIFICATION</span>
          </span>
        );
      case "IN_REVIEW":
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-bold bg-purple-100 text-purple-800 border border-purple-200">
            <Clock className="w-3 h-3" />
            <span>IN REVIEW</span>
          </span>
        );
      case "ARCHIVED":
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
            <span>ARCHIVED</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-bold bg-blue-100 text-blue-800 border border-blue-200">
            <Clock className="w-3 h-3" />
            <span>PENDING REVIEW</span>
          </span>
        );
    }
  };

  const getProvenanceBadge = (prov: string) => {
    switch (prov) {
      case "OFFICIAL_DOMAIN_MATCH":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
            OFFICIAL DOMAIN MATCH (.GOV.IN / .NIC.IN)
          </span>
        );
      case "SOURCE_RETRIEVED":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-200">
            SOURCE RETRIEVED
          </span>
        );
      case "PROVENANCE_REVIEW_REQUIRED":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
            PROVENANCE REVIEW REQUIRED
          </span>
        );
      case "REVIEWED_BY_AUTHORIZED_REVIEWER":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-300">
            REVIEWED BY OFFICER
          </span>
        );
      case "UNVERIFIED":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300">
            UNVERIFIED SOURCE
          </span>
        );
      case "OFFICIAL_GAZETTE":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-800 border border-indigo-200">
            OFFICIAL GAZETTE
          </span>
        );
      case "OFFICIAL_PORTAL":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-100 text-cyan-800 border border-cyan-200">
            OFFICIAL PORTAL
          </span>
        );
      case "OFFICIAL_CIRCULAR":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
            OFFICIAL CIRCULAR
          </span>
        );
      case "CONFLICT_DETECTED":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
            CONFLICT DETECTED
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
            UNVERIFIED / UNKNOWN
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Advisory Nature & Statutory Separation */}
      <div className="bg-gradient-to-r from-blue-900 to-indigo-950 text-white p-6 rounded-xl shadow-sm border border-blue-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2.5 mb-1.5">
              <Sparkles className="w-5 h-5 text-blue-300" />
              <h1 className="text-xl font-bold tracking-tight">
                AI POLICY DISCOVERY & HUMAN APPROVAL
              </h1>
              <span className="px-2.5 py-0.5 text-[11px] font-bold bg-blue-500/30 text-blue-200 rounded border border-blue-400/40">
                ADVISORY INTELLIGENCE
              </span>
            </div>
            <p className="text-xs text-blue-200 max-w-3xl leading-relaxed">
              Discovers candidate eligibility conditions, exclusions, and amendments from official government sources.
              All candidates are strictly non-executable data objects awaiting human verification.
              Approval accepts candidates for future policy-authoring consideration and does not modify active statutory rules.
            </p>
          </div>

          <div className="flex items-center space-x-2 bg-slate-800/80 p-2.5 rounded-lg border border-slate-700">
            <select
              value={discoverScheme}
              onChange={(e) => setDiscoverScheme(e.target.value)}
              className="bg-slate-900 text-white text-xs border border-slate-700 rounded px-2.5 py-1.5 focus:ring-blue-500"
            >
              <option value="PM_KISAN">PM-KISAN</option>
              <option value="SSY">Sukanya Samriddhi (SSY)</option>
            </select>

            <button
              type="button"
              onClick={handleRunDiscovery}
              disabled={isDiscovering}
              className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white text-xs font-semibold rounded flex items-center space-x-1.5 transition-colors shadow-sm"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isDiscovering ? "animate-spin" : ""}`} />
              <span>{isDiscovering ? "Discovering..." : "Run Discovery"}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Success Notification */}
      {discoverySuccess && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-900 flex items-center justify-between">
          <span>{discoverySuccess}</span>
          <button
            onClick={() => setDiscoverySuccess(null)}
            className="text-emerald-700 hover:text-emerald-900 font-bold ml-4"
          >
            &times;
          </button>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-xs text-red-900 flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Metric Cards Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Total Candidates
          </div>
          <div className="text-xl font-extrabold text-slate-900 mt-1">
            {metrics.total_candidates}
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-blue-200 shadow-sm">
          <div className="text-[11px] font-bold uppercase tracking-wider text-blue-700">
            Pending Review
          </div>
          <div className="text-xl font-extrabold text-blue-900 mt-1">
            {metrics.pending_review}
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-purple-200 shadow-sm">
          <div className="text-[11px] font-bold uppercase tracking-wider text-purple-700">
            In Review
          </div>
          <div className="text-xl font-extrabold text-purple-900 mt-1">
            {metrics.in_review}
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-orange-200 shadow-sm">
          <div className="text-[11px] font-bold uppercase tracking-wider text-orange-700">
            Clarification
          </div>
          <div className="text-xl font-extrabold text-orange-900 mt-1">
            {metrics.needs_clarification}
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-green-200 shadow-sm">
          <div className="text-[11px] font-bold uppercase tracking-wider text-green-700">
            Approved
          </div>
          <div className="text-xl font-extrabold text-green-900 mt-1">
            {metrics.approved}
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-red-200 shadow-sm">
          <div className="text-[11px] font-bold uppercase tracking-wider text-red-700">
            Rejected
          </div>
          <div className="text-xl font-extrabold text-red-900 mt-1">
            {metrics.rejected}
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-amber-200 shadow-sm">
          <div className="text-[11px] font-bold uppercase tracking-wider text-amber-700">
            Conflicts
          </div>
          <div className="text-xl font-extrabold text-amber-900 mt-1">
            {metrics.conflict_detected}
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by candidate title, concept, or source document..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div className="flex items-center space-x-2">
            <select
              value={schemeFilter}
              onChange={(e) => setSchemeFilter(e.target.value)}
              className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 bg-white font-medium text-slate-700"
            >
              <option value="ALL">All Schemes</option>
              <option value="PM_KISAN">PM-KISAN</option>
              <option value="SSY">Sukanya Samriddhi (SSY)</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 bg-white font-medium text-slate-700"
            >
              <option value="ALL">All Statuses</option>
              <option value="PENDING_REVIEW">Pending Review</option>
              <option value="IN_REVIEW">In Review</option>
              <option value="NEEDS_CLARIFICATION">Needs Clarification</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
              <option value="ARCHIVED">Archived</option>
            </select>

            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 bg-white font-medium text-slate-700"
            >
              <option value="ALL">All Types (10 Categories)</option>
              <option value="ELIGIBILITY_CONDITION">Eligibility Condition</option>
              <option value="EXCLUSION">Exclusion</option>
              <option value="DEFINITIONS">Definitions</option>
              <option value="DOCUMENTATION_REQUIREMENT">Documentation Requirement</option>
              <option value="PROCEDURAL_REQUIREMENT">Procedural Requirement</option>
              <option value="BENEFIT_PARAMETER">Benefit Parameter</option>
              <option value="EFFECTIVE_DATE">Effective Date</option>
              <option value="AMENDMENT">Amendment</option>
              <option value="CLARIFICATION">Clarification</option>
              <option value="SOURCE_REFERENCE">Source Reference</option>
            </select>
          </div>
        </div>
      </div>

      {/* Candidate Dossier List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Discovered Policy Candidates ({filteredCandidates.length})
          </div>
          <span className="text-[11px] text-slate-500">
            AI Advisory Confidence displayed for triage only
          </span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto text-blue-600 mb-2" />
            Loading policy discovery queue...
          </div>
        ) : filteredCandidates.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No policy discovery candidates match the selected filters.
            <div className="mt-2">
              <button
                onClick={handleRunDiscovery}
                className="text-blue-600 font-semibold hover:underline"
              >
                Run AI discovery now
              </button>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-slate-200">
            {filteredCandidates.map((cand) => (
              <div
                key={cand.id}
                className="p-5 hover:bg-slate-50/80 transition-colors flex flex-col md:flex-row md:items-start justify-between gap-4"
              >
                <div className="space-y-2 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-900 text-white">
                      {cand.scheme_code || "SCHEME"}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-800 border border-slate-200">
                      {cand.candidate_type}
                    </span>
                    {getProvenanceBadge(cand.provenance_status)}
                    {getStatusBadge(cand.review_status)}
                    {cand.duplicate_status === "POSSIBLE_DUPLICATE" && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-yellow-100 text-yellow-800 border border-yellow-300">
                        POSSIBLE DUPLICATE
                      </span>
                    )}
                    {cand.adversarial_flag_detected && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-800 border border-red-300 flex items-center space-x-1">
                        <AlertTriangle className="w-3 h-3" />
                        <span>ADVERSARIAL ATTEMPT FLAGGED</span>
                      </span>
                    )}
                  </div>

                  <h3 className="text-sm font-bold text-slate-900 leading-snug">
                    {cand.title}
                  </h3>

                  <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                    {cand.candidate_text_en}
                  </p>

                  <div className="flex flex-wrap items-center gap-y-1 gap-x-4 text-[11px] text-slate-500 pt-1">
                    <span className="font-mono text-slate-600">
                      Concept: {cand.normalized_concept}
                    </span>
                    <span>Source: {cand.source_publisher}</span>
                    {cand.source_publication_date && (
                      <span>
                        Published: {new Date(cand.source_publication_date).toLocaleDateString("en-IN")}
                      </span>
                    )}
                    {cand.source_effective_date ? (
                      <span className="text-indigo-700 font-semibold">
                        Effective: {new Date(cand.source_effective_date).toLocaleDateString("en-IN")}
                      </span>
                    ) : (
                      <span className="text-amber-700 font-semibold">
                        Effective: UNKNOWN
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex md:flex-col items-end justify-between gap-3 min-w-[160px] pt-2 md:pt-0">
                  <div className="text-right">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                      AI Advisory Score
                    </div>
                    <div className="flex items-center space-x-1.5 justify-end mt-0.5">
                      <div className="w-16 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            cand.extraction_confidence >= 0.85
                              ? "bg-green-500"
                              : cand.extraction_confidence >= 0.7
                              ? "bg-blue-500"
                              : "bg-amber-500"
                          }`}
                          style={{ width: `${Math.round(cand.extraction_confidence * 100)}%` }}
                        />
                      </div>
                      <span className="text-xs font-bold font-mono text-slate-700">
                        {Math.round(cand.extraction_confidence * 100)}%
                      </span>
                    </div>
                  </div>

                  <Link
                    href={`/officer/policy-discovery/${cand.id}`}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-semibold flex items-center space-x-1 transition-colors shadow-sm"
                  >
                    <span>Inspect & Review</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
