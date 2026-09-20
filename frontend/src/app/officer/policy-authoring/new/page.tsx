"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  FileCode2,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Sliders,
  ExternalLink,
  RefreshCw,
} from "lucide-react";
import { useOfficerAuth } from "@/context/OfficerAuthContext";
import { policyAuthoringApi } from "@/api/policyAuthoring";

interface ApprovedCandidate {
  id: string;
  scheme_id: string;
  scheme_code: string | null;
  scheme_name: string | null;
  title: string;
  candidate_type: string;
  candidate_text_en: string;
  source_url: string;
  source_publisher: string;
  source_document_identifier: string | null;
  source_effective_date: string | null;
  source_excerpt: string;
  review_status: string;
}

export default function NewPolicyDraftPage() {
  const { isAuthenticated, isLoading: authLoading, token } = useOfficerAuth();
  const router = useRouter();

  const [mode, setMode] = useState<"scratch" | "import">("scratch");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form fields
  const [schemeCode, setSchemeCode] = useState<string>("PM_KISAN");
  const [policyTitle, setPolicyTitle] = useState("");
  const [description, setDescription] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [effectiveTo, setEffectiveTo] = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState<ApprovedCandidate | null>(null);

  // Approved candidates list for Mode 2
  const [approvedCandidates, setApprovedCandidates] = useState<ApprovedCandidate[]>([]);
  const [loadingCandidates, setLoadingCandidates] = useState(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/officer/login");
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (mode === "import" && token) {
      setLoadingCandidates(true);
      fetch(`/api/v1/officer/policy-discovery/candidates?status=APPROVED`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
        .then((res) => res.json())
        .then((data) => {
          setApprovedCandidates(data.candidates || []);
        })
        .catch((err) => {
          setError("Failed to load approved candidates for import.");
        })
        .finally(() => {
          setLoadingCandidates(false);
        });
    }
  }, [mode, token]);

  const handleSelectCandidate = (cand: ApprovedCandidate) => {
    setSelectedCandidate(cand);
    setSchemeCode(cand.scheme_code || "PM_KISAN");
    setPolicyTitle(cand.title);
    setDescription(
      `Statutory authoring derived from approved discovery candidate: ${cand.title}. Source: ${cand.source_publisher}.`
    );
    if (cand.source_effective_date) {
      setEffectiveFrom(cand.source_effective_date.substring(0, 10));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setError(null);

    if (!policyTitle || policyTitle.trim().length < 3) {
      setError("Policy title must be at least 3 characters.");
      return;
    }

    if (!description || description.trim().length < 5) {
      setError("Description must be at least 5 characters.");
      return;
    }

    setSubmitting(true);

    try {
      const payload: any = {
        scheme_code: schemeCode,
        policy_title: policyTitle.trim(),
        description: description.trim(),
        effective_from: effectiveFrom || undefined,
        effective_to: effectiveTo || undefined,
        source_candidate_id: selectedCandidate?.id || undefined,
        authored_rules_json: {
          schema_version: "2.0",
          rules: [],
        },
      };

      const newDraft = await policyAuthoringApi.createDraft(payload, token);
      router.push(`/officer/policy-authoring/${newDraft.id}`);
    } catch (err: any) {
      setError(err?.message || "Failed to create policy draft.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Back button */}
      <Link
        href="/officer/policy-authoring"
        className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to Policy Authoring Queue</span>
      </Link>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
          <FileCode2 className="w-6 h-6 text-blue-600" />
          <span>Initialize Policy Draft</span>
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Create a new statutory policy draft from scratch or derive from an approved AI discovery candidate.
        </p>
      </div>

      {/* Mode Switcher */}
      <div className="flex border-b border-slate-200">
        <button
          type="button"
          onClick={() => {
            setMode("scratch");
            setSelectedCandidate(null);
          }}
          className={`pb-3 px-4 text-xs font-bold transition-colors border-b-2 ${
            mode === "scratch"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          1. Author From Scratch
        </button>
        <button
          type="button"
          onClick={() => setMode("import")}
          className={`pb-3 px-4 text-xs font-bold transition-colors border-b-2 flex items-center space-x-1.5 ${
            mode === "import"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-blue-500" />
          <span>2. Derive From Approved Candidate</span>
        </button>
      </div>

      {/* Error alert */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-xs">
          {error}
        </div>
      )}

      {/* If Mode is Import: Candidate Selection List */}
      {mode === "import" && (
        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-blue-500" />
              <span>Select Approved Policy Candidate</span>
            </h3>
            <span className="text-xs text-slate-400">
              Only candidates with status <strong>APPROVED</strong> can be imported.
            </span>
          </div>

          {loadingCandidates ? (
            <div className="p-8 text-center text-slate-400">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto text-blue-500 mb-2" />
              <p className="text-xs">Loading approved candidates...</p>
            </div>
          ) : approvedCandidates.length === 0 ? (
            <div className="p-6 text-center border-2 border-dashed border-slate-200 rounded-lg">
              <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
              <p className="text-xs font-semibold text-slate-700">No Approved Candidates Available</p>
              <p className="text-[11px] text-slate-500 mt-1 max-w-sm mx-auto">
                No policy discovery candidates have been approved by a reviewing officer yet. You can author from scratch or approve candidates in Policy Discovery.
              </p>
            </div>
          ) : (
            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              {approvedCandidates.map((cand) => {
                const isSelected = selectedCandidate?.id === cand.id;
                return (
                  <div
                    key={cand.id}
                    onClick={() => handleSelectCandidate(cand)}
                    className={`p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                      isSelected
                        ? "border-blue-600 bg-blue-50/50 shadow-sm"
                        : "border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-bold text-slate-900 flex items-center space-x-2">
                        <span>{cand.title}</span>
                        <span className="px-1.5 py-0.2 rounded text-[10px] bg-blue-100 text-blue-800 font-semibold">
                          {cand.scheme_code}
                        </span>
                      </div>
                      {isSelected && (
                        <span className="text-blue-600 font-bold flex items-center space-x-1 text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Selected</span>
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-1">
                      {cand.source_publisher} • Effective:{" "}
                      {cand.source_effective_date
                        ? new Date(cand.source_effective_date).toLocaleDateString()
                        : "Not specified"}
                    </div>
                    <div className="text-[11px] text-slate-600 mt-1 line-clamp-2 italic">
                      "{cand.source_excerpt}"
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Creation Form */}
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-5">
        {selectedCandidate && (
          <div className="bg-cyan-50 border border-cyan-200 rounded-lg p-3 text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2 text-cyan-800">
              <Sparkles className="w-4 h-4 text-cyan-600 flex-shrink-0" />
              <span>
                Importing provenance from: <strong>{selectedCandidate.title}</strong>
              </span>
            </div>
            <button
              type="button"
              onClick={() => setSelectedCandidate(null)}
              className="text-cyan-700 hover:text-cyan-900 font-bold text-[11px]"
            >
              Clear
            </button>
          </div>
        )}

        {/* Scheme selection */}
        <div>
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
            Statutory Target Scheme *
          </label>
          <select
            value={schemeCode}
            onChange={(e) => setSchemeCode(e.target.value)}
            disabled={!!selectedCandidate}
            className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-slate-50 focus:outline-none focus:ring-1 focus:ring-blue-500 font-medium"
          >
            <option value="PM_KISAN">PM-KISAN Samman Nidhi (PM_KISAN)</option>
            <option value="SSY">Sukanya Samriddhi Yojana (SSY)</option>
          </select>
          <p className="text-[11px] text-slate-400 mt-1">
            Authoring is constrained to established statutory schemes with frozen baseline policies.
          </p>
        </div>

        {/* Policy Title */}
        <div>
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
            Policy Draft Title *
          </label>
          <input
            type="text"
            required
            placeholder="e.g. PM-KISAN 2026 Revised Landholding and Aadhaar Mandatory Guidelines"
            value={policyTitle}
            onChange={(e) => setPolicyTitle(e.target.value)}
            className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-slate-50 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
            Legislative Intent & Scope Description *
          </label>
          <textarea
            required
            rows={3}
            placeholder="Describe the statutory purpose, policy changes, and legislative gazette context..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-slate-50 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* Temporality / Dates */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Prospective Effective From Date
            </label>
            <input
              type="date"
              value={effectiveFrom}
              onChange={(e) => setEffectiveFrom(e.target.value)}
              className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-slate-50 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Statutory Sunset / Effective To Date
            </label>
            <input
              type="date"
              value={effectiveTo}
              onChange={(e) => setEffectiveTo(e.target.value)}
              className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-slate-50 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Submit */}
        <div className="pt-4 border-t border-slate-200 flex items-center justify-end space-x-3">
          <Link
            href="/officer/policy-authoring"
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 transition-colors"
          >
            Cancel
          </Link>

          <button
            type="submit"
            disabled={submitting}
            className="px-5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition-colors flex items-center space-x-1.5 disabled:opacity-50"
          >
            {submitting ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Initializing Draft...</span>
              </>
            ) : (
              <span>Create & Open Rule Builder</span>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
