"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  Sparkles,
  ArrowLeft,
  AlertTriangle,
  FileText,
  ExternalLink,
  Shield,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Clock,
  Calendar,
  Layers,
  History,
  Info,
  Check,
  Building,
} from "lucide-react";
import { useOfficerAuth } from "@/context/OfficerAuthContext";

interface ReviewEvent {
  id: string;
  candidate_id: string;
  actor_identity: string;
  actor_role: string;
  previous_status: string | null;
  new_status: string;
  action: string;
  reason: string | null;
  details_json: any;
  created_at: string;
}

interface CandidateDetail {
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
  retrieved_at?: string;
  adversarial_flag_detected?: boolean;
  discovered_by: string;
  ai_provider: string;
  ai_model: string;
  ai_run_id: string;
  extraction_confidence: number;
  confidence_explanation: string | null;
  uncertainty_notes: string | null;
  questions_for_reviewer: string[] | null;
  provenance_status: string;
  effective_date_status: string;
  conflict_detected: boolean;
  conflict_details_json: any;
  duplicate_status: string;
  duplicate_of_id: string | null;
  review_status: string;
  reviewer_id: string | null;
  reviewer_role: string | null;
  reviewed_at: string | null;
  reviewer_reason: string | null;
  created_at: string;
  updated_at: string;
  review_events?: ReviewEvent[];
}

export default function CandidateReviewPage() {
  const { candidateId } = useParams<{ candidateId: string }>();
  const { isAuthenticated, isLoading: authLoading, token, officer } = useOfficerAuth();
  const router = useRouter();

  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [history, setHistory] = useState<ReviewEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Review Form
  const [action, setAction] = useState<string>("START_REVIEW");
  const [reason, setReason] = useState<string>("");
  const [notes, setNotes] = useState<string>("");

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/officer/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const loadCandidate = useCallback(async () => {
    if (!token || !candidateId) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/v1/officer/policy-discovery/candidates/${candidateId}`, {
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
        throw new Error(`Failed to load candidate dossier (HTTP ${res.status})`);
      }

      const data: CandidateDetail = await res.json();
      setCandidate(data);

      // Set default valid action based on candidate review state
      if (data.review_status === "PENDING_REVIEW") {
        setAction("START_REVIEW");
      } else if (data.review_status === "IN_REVIEW") {
        setAction("APPROVE");
      } else if (data.review_status === "NEEDS_CLARIFICATION") {
        setAction("START_REVIEW");
      } else if (data.review_status === "APPROVED" || data.review_status === "REJECTED") {
        setAction("ARCHIVE");
      }

      // Fetch history
      const histRes = await fetch(`/api/v1/officer/policy-discovery/candidates/${candidateId}/history`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });
      if (histRes.ok) {
        const histData = await histRes.json();
        setHistory(histData);
      }
    } catch (err: any) {
      setError(err?.message || "An unexpected error occurred loading candidate.");
    } finally {
      setLoading(false);
    }
  }, [token, candidateId, router]);

  useEffect(() => {
    if (isAuthenticated && token) {
      loadCandidate();
    }
  }, [isAuthenticated, token, loadCandidate]);

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !candidate) return;

    if (reason.trim().length < 5) {
      setError("Mandatory substantive justification reason (at least 5 characters) is required.");
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const res = await fetch(`/api/v1/officer/policy-discovery/candidates/${candidate.id}/review`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          action,
          reason: reason.trim(),
          notes: notes.trim() || undefined,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData?.detail || `Review action failed with status ${res.status}`);
      }

      const updated = await res.json();
      setCandidate(updated);
      setSuccessMessage(`Determination '${action}' recorded successfully into immutable audit trail.`);
      setReason("");
      setNotes("");
      await loadCandidate();
    } catch (err: any) {
      setError(err?.message || "Failed to commit review determination.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading && !candidate) {
    return (
      <div className="p-12 text-center text-xs text-slate-500">
        <Clock className="w-5 h-5 animate-spin mx-auto text-blue-600 mb-2" />
        Loading candidate policy dossier...
      </div>
    );
  }

  if (!candidate) {
    return (
      <div className="p-8 bg-red-50 border border-red-200 rounded-lg text-xs text-red-900">
        Candidate not found. <Link href="/officer/policy-discovery" className="underline font-bold">Return to Queue</Link>
      </div>
    );
  }

  const isArchived = candidate.review_status === "ARCHIVED";

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Navigation Breadcrumb */}
      <div className="flex items-center space-x-2 text-xs text-slate-500">
        <Link
          href="/officer/policy-discovery"
          className="hover:text-blue-600 flex items-center space-x-1 font-medium transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Policy Discovery Queue</span>
        </Link>
        <span>&bull;</span>
        <span className="text-slate-700 font-semibold">{candidate.scheme_code}</span>
        <span>&bull;</span>
        <span className="font-mono text-slate-500">{candidate.normalized_concept}</span>
      </div>

      {/* Advisory Warning Banner */}
      <div className="p-4 bg-amber-50 border border-amber-300 rounded-xl flex items-start space-x-3 text-amber-900 shadow-sm">
        <AlertTriangle className="w-5 h-5 text-amber-700 flex-shrink-0 mt-0.5" />
        <div className="text-xs leading-relaxed">
          <strong>AI ADVISORY DISCOVERY &bull; HUMAN APPROVAL REQUIRED:</strong> This candidate was extracted
          from official sources by AI for human triage. AI is not a statutory authority. Approving this candidate
          indicates acceptance for consideration in the controlled policy-authoring process.
          It does <strong>NOT</strong> enact law, activate a statutory rule, or alter existing deterministic policies.
        </div>
      </div>

      {/* Adversarial Content Alert Banner (if flagged) */}
      {candidate.adversarial_flag_detected && (
        <div className="p-4 bg-red-50 border border-red-300 rounded-xl flex items-start space-x-3 text-red-900 shadow-sm">
          <AlertTriangle className="w-5 h-5 text-red-700 flex-shrink-0 mt-0.5" />
          <div className="text-xs leading-relaxed">
            <strong className="font-bold block text-red-950">POTENTIAL ADVERSARIAL CONTENT / PROMPT INJECTION DETECTED:</strong>
            The original source text contains phrases attempting to manipulate automated systems (e.g. instructions to bypass verification or auto-approve rules).
            All evidence has been preserved <strong>verbatim</strong> for supervisory inspection.
            The system treats this text strictly as untrusted content; it possesses zero executable authority and cannot alter the verification state machine.
          </div>
        </div>
      )}

      {/* Candidate Dossier Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-2.5 py-1 rounded text-xs font-bold bg-slate-900 text-white">
              {candidate.scheme_code || "SCHEME"}
            </span>
            <span className="px-2.5 py-1 rounded text-xs font-bold bg-slate-100 text-slate-800 border border-slate-200">
              {candidate.candidate_type}
            </span>
            <span className="px-2.5 py-1 rounded text-xs font-bold bg-blue-100 text-blue-800 border border-blue-200">
              {candidate.review_status}
            </span>
            {candidate.conflict_detected && (
              <span className="px-2.5 py-1 rounded text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
                CONFLICT DETECTED
              </span>
            )}
            {candidate.duplicate_status === "POSSIBLE_DUPLICATE" && (
              <span className="px-2.5 py-1 rounded text-xs font-bold bg-yellow-100 text-yellow-800 border border-yellow-300">
                POSSIBLE DUPLICATE
              </span>
            )}
          </div>

          <div className="text-right">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Advisory Confidence
            </div>
            <div className="text-base font-extrabold font-mono text-blue-700">
              {Math.round(candidate.extraction_confidence * 100)}%
            </div>
          </div>
        </div>

        <h1 className="text-lg font-bold text-slate-950 leading-snug">
          {candidate.title}
        </h1>

        <div className="text-xs text-slate-500 font-mono">
          Concept Key: <span className="text-slate-800 font-semibold">{candidate.normalized_concept}</span>
        </div>
      </div>

      {/* Visual Separation Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SECTION A: AI Suggestion & Extracted Intelligence */}
        <div className="bg-white rounded-xl border border-blue-200 shadow-sm overflow-hidden flex flex-col">
          <div className="px-5 py-3 bg-blue-50/80 border-b border-blue-200 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-blue-600" />
              <span className="text-xs font-bold uppercase tracking-wider text-blue-900">
                AI Suggestion (Advisory Extraction)
              </span>
            </div>
            <span className="text-[10px] font-mono text-blue-700">
              {candidate.ai_provider}
            </span>
          </div>

          <div className="p-5 space-y-4 flex-1">
            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                Candidate Statement (English):
              </label>
              <div className="p-3 bg-slate-50 rounded-lg text-xs text-slate-800 border border-slate-200 leading-relaxed">
                {candidate.candidate_text_en}
              </div>
            </div>

            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                Candidate Statement (Hindi):
              </label>
              <div className="p-3 bg-slate-50 rounded-lg text-xs text-slate-800 border border-slate-200 leading-relaxed font-hindi">
                {candidate.candidate_text_hi}
              </div>
            </div>

            {candidate.confidence_explanation && (
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                  Confidence Rationale:
                </label>
                <div className="text-xs text-slate-600 italic">
                  {candidate.confidence_explanation}
                </div>
              </div>
            )}

            {candidate.uncertainty_notes && (
              <div className="p-3 bg-amber-50/60 rounded-lg border border-amber-200 text-xs text-amber-900">
                <strong className="block mb-0.5">Identified Uncertainty:</strong>
                {candidate.uncertainty_notes}
              </div>
            )}

            {candidate.questions_for_reviewer && candidate.questions_for_reviewer.length > 0 && (
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1.5">
                  AI Questions for Human Reviewer:
                </label>
                <ul className="space-y-1.5 pl-4 list-disc text-xs text-slate-700">
                  {candidate.questions_for_reviewer.map((q, idx) => (
                    <li key={idx}>{q}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* SECTION B: Official Source Evidence & Provenance */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="px-5 py-3 bg-slate-100 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Building className="w-4 h-4 text-slate-700" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-800">
                Official Government Source & Provenance
              </span>
            </div>
            <span className="px-2 py-0.5 text-[10px] font-bold bg-white text-slate-700 border border-slate-300 rounded">
              {candidate.provenance_status}
            </span>
          </div>

          <div className="p-5 space-y-4 flex-1">
            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                Source Document Title & Publisher:
              </label>
              <div className="text-xs font-semibold text-slate-900">
                {candidate.source_title}
              </div>
              <div className="text-[11px] text-slate-600 mt-0.5">
                Issued by: <strong>{candidate.source_publisher}</strong>
              </div>
              {candidate.source_document_identifier && (
                <div className="text-[11px] font-mono text-slate-500 mt-0.5">
                  Gazette/Circular Ref: {candidate.source_document_identifier}
                </div>
              )}
            </div>

            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                Official Source URL:
              </label>
              <a
                href={candidate.source_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center space-x-1.5 text-xs text-blue-600 hover:text-blue-800 font-mono break-all"
              >
                <span>{candidate.source_url}</span>
                <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
              </a>
            </div>

            {/* Separate Publication Date vs Effective Date vs Retrieved At */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div>
                <span className="text-[10px] font-bold uppercase text-slate-500 block">
                  Publication Date
                </span>
                <span className="text-xs font-semibold text-slate-800">
                  {candidate.source_publication_date
                    ? new Date(candidate.source_publication_date).toLocaleDateString("en-IN")
                    : "UNKNOWN"}
                </span>
              </div>

              <div>
                <span className="text-[10px] font-bold uppercase text-slate-500 block">
                  Effective Date
                </span>
                <span
                  className={`text-xs font-bold ${
                    candidate.source_effective_date ? "text-indigo-800" : "text-amber-700"
                  }`}
                >
                  {candidate.source_effective_date
                    ? new Date(candidate.source_effective_date).toLocaleDateString("en-IN")
                    : "UNKNOWN (Requires Review)"}
                </span>
              </div>

              <div>
                <span className="text-[10px] font-bold uppercase text-slate-500 block">
                  Retrieved At
                </span>
                <span className="text-xs font-semibold text-slate-800">
                  {candidate.retrieved_at
                    ? new Date(candidate.retrieved_at).toLocaleString("en-IN")
                    : (candidate.discovered_at ? new Date(candidate.discovered_at).toLocaleString("en-IN") : "UNKNOWN")}
                </span>
              </div>
            </div>

            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                Exact Bounded Source Excerpt:
              </label>
              <blockquote className="p-3 bg-amber-50/40 rounded-lg border-l-4 border-amber-400 text-xs text-slate-700 italic leading-relaxed">
                &ldquo;{candidate.source_excerpt}&rdquo;
              </blockquote>
            </div>
          </div>
        </div>
      </div>

      {/* SECTION C: Conflict & Duplicate Analysis (if present) */}
      {(candidate.conflict_detected || candidate.duplicate_status === "POSSIBLE_DUPLICATE") && (
        <div className="bg-white p-5 rounded-xl border border-amber-300 shadow-sm space-y-3">
          <div className="flex items-center space-x-2 text-amber-900 font-bold text-xs uppercase tracking-wider">
            <AlertTriangle className="w-4 h-4 text-amber-700" />
            <span>Source Discrepancy & Conflict Analysis</span>
          </div>

          {candidate.conflict_detected && candidate.conflict_details_json && (
            <div className="p-4 bg-amber-50/80 rounded-lg border border-amber-200 text-xs text-amber-950 space-y-2">
              <div>
                <strong>Apparent Conflict:</strong>{" "}
                {candidate.conflict_details_json.apparent_conflict || "Conflicting directives between multiple authorities."}
              </div>
              {candidate.conflict_details_json.conflicting_sources && (
                <div className="space-y-1 mt-1 pl-4 list-disc">
                  {candidate.conflict_details_json.conflicting_sources.map((s: any, idx: number) => (
                    <div key={idx}>
                      &bull; <strong>{s.source}:</strong> {s.rule}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {candidate.duplicate_status === "POSSIBLE_DUPLICATE" && (
            <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-200 text-xs text-yellow-900">
              <strong>Possible Duplicate Detected:</strong> A candidate with equivalent concept key and
              type already exists in the system. Check previous candidate records before approving.
            </div>
          )}
        </div>
      )}

      {/* SECTION D: Authorized Officer Review Panel */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-5">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div className="flex items-center space-x-2">
            <Shield className="w-4 h-4 text-blue-600" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-900">
              Authorized Review Determination
            </h2>
          </div>
          <span className="text-xs text-slate-500">
            Reviewer: <strong className="font-mono text-slate-700">{officer?.email}</strong> ({officer?.role})
          </span>
        </div>

        {isArchived ? (
          <div className="p-4 bg-slate-100 rounded-lg text-xs text-slate-700">
            This candidate is archived in a terminal state. No further determinations can be recorded.
          </div>
        ) : (
          <form onSubmit={handleReviewSubmit} className="space-y-4">
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-900 flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {successMessage && (
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-xs text-green-900 flex items-center space-x-2">
                <Check className="w-4 h-4 text-green-600 flex-shrink-0" />
                <span>{successMessage}</span>
              </div>
            )}

            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-2">
                Select Determination Action:
              </label>

              {candidate.review_status === "PENDING_REVIEW" && (
                <div className="p-4 bg-purple-50 rounded-lg border border-purple-200 space-y-3">
                  <div className="text-xs font-bold text-purple-900">
                    Step 1: Commence Official Verification (START_REVIEW)
                  </div>
                  <p className="text-[11px] text-purple-800 leading-relaxed">
                    Per Phase 15 governance rules, candidate intelligence in <strong>PENDING_REVIEW</strong> must be actively transitioned to <strong>IN_REVIEW</strong> before any determination (APPROVE / REJECT / REQUEST_CLARIFICATION) can be submitted. Direct transition shortcuts are strictly prohibited.
                  </p>
                  <label className="flex items-start space-x-3 p-3.5 rounded-lg border border-purple-300 bg-white hover:bg-purple-50/50 cursor-pointer shadow-sm">
                    <input
                      type="radio"
                      name="reviewAction"
                      value="START_REVIEW"
                      checked={action === "START_REVIEW"}
                      onChange={(e) => setAction(e.target.value)}
                      className="mt-0.5 text-purple-600"
                    />
                    <div>
                      <span className="text-xs font-bold text-purple-900 block">
                        Start Review & Transition to IN_REVIEW
                      </span>
                      <span className="text-[11px] text-slate-600 block">
                        Assumes active responsibility for evaluating official source texts and provenance.
                      </span>
                    </div>
                  </label>
                </div>
              )}

              {candidate.review_status === "IN_REVIEW" && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  <label className="flex items-start space-x-3 p-3.5 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer">
                    <input
                      type="radio"
                      name="reviewAction"
                      value="APPROVE"
                      checked={action === "APPROVE"}
                      onChange={(e) => setAction(e.target.value)}
                      className="mt-0.5 text-blue-600"
                    />
                    <div>
                      <span className="text-xs font-bold text-slate-900 block">
                        Approve for policy-authoring consideration
                      </span>
                      <span className="text-[11px] text-slate-500 block">
                        Source is sufficient and concept is accepted for future controlled drafting.
                      </span>
                    </div>
                  </label>

                  <label className="flex items-start space-x-3 p-3.5 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer">
                    <input
                      type="radio"
                      name="reviewAction"
                      value="REJECT"
                      checked={action === "REJECT"}
                      onChange={(e) => setAction(e.target.value)}
                      className="mt-0.5 text-red-600"
                    />
                    <div>
                      <span className="text-xs font-bold text-red-700 block">
                        Reject Candidate
                      </span>
                      <span className="text-[11px] text-slate-500 block">
                        Candidate statement is inaccurate, unverified, or legally inadmissible.
                      </span>
                    </div>
                  </label>

                  <label className="flex items-start space-x-3 p-3.5 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer">
                    <input
                      type="radio"
                      name="reviewAction"
                      value="REQUEST_CLARIFICATION"
                      checked={action === "REQUEST_CLARIFICATION"}
                      onChange={(e) => setAction(e.target.value)}
                      className="mt-0.5 text-orange-600"
                    />
                    <div>
                      <span className="text-xs font-bold text-orange-700 block">
                        Request Clarification / Hold
                      </span>
                      <span className="text-[11px] text-slate-500 block">
                        Insufficient documentation, conflicting source, or ambiguous effective date.
                      </span>
                    </div>
                  </label>
                </div>
              )}

              {candidate.review_status === "NEEDS_CLARIFICATION" && (
                <div className="p-4 bg-orange-50 rounded-lg border border-orange-200 space-y-3">
                  <div className="text-xs font-bold text-orange-900">
                    Candidate on Hold (NEEDS_CLARIFICATION)
                  </div>
                  <p className="text-[11px] text-orange-800 leading-relaxed">
                    Clarification was previously requested. Once clarification from nodal ministry or state revenue records is received, transition back to <strong>IN_REVIEW</strong> to resume evaluation.
                  </p>
                  <label className="flex items-start space-x-3 p-3.5 rounded-lg border border-orange-300 bg-white hover:bg-orange-50/50 cursor-pointer shadow-sm">
                    <input
                      type="radio"
                      name="reviewAction"
                      value="START_REVIEW"
                      checked={action === "START_REVIEW"}
                      onChange={(e) => setAction(e.target.value)}
                      className="mt-0.5 text-orange-600"
                    />
                    <div>
                      <span className="text-xs font-bold text-orange-900 block">
                        Resume Review & Transition to IN_REVIEW
                      </span>
                      <span className="text-[11px] text-slate-600 block">
                        Re-open active evaluation with newly received clarification documents.
                      </span>
                    </div>
                  </label>
                </div>
              )}

              {(candidate.review_status === "APPROVED" || candidate.review_status === "REJECTED") && (
                <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-3">
                  <div className="text-xs font-bold text-slate-800">
                    Completed Determination ({candidate.review_status})
                  </div>
                  <p className="text-[11px] text-slate-600 leading-relaxed">
                    Candidate evaluation has concluded. You may archive this dossier into terminal storage.
                  </p>
                  <label className="flex items-start space-x-3 p-3.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-100 cursor-pointer shadow-sm">
                    <input
                      type="radio"
                      name="reviewAction"
                      value="ARCHIVE"
                      checked={action === "ARCHIVE"}
                      onChange={(e) => setAction(e.target.value)}
                      className="mt-0.5 text-slate-700"
                    />
                    <div>
                      <span className="text-xs font-bold text-slate-900 block">
                        Archive Candidate Record (ARCHIVE)
                      </span>
                      <span className="text-[11px] text-slate-600 block">
                        Permanently transitions candidate to terminal ARCHIVED state.
                      </span>
                    </div>
                  </label>
                </div>
              )}
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Mandatory Justification Reason <span className="text-red-500">*</span>
              </label>
              <textarea
                required
                rows={3}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Explain the evidentiary basis for approving, rejecting, or requesting clarification..."
                className="w-full text-xs p-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Supervisory Notes (Optional)
              </label>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Internal verification remarks or legal references..."
                className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="submit"
                disabled={submitting}
                className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-400 text-white text-xs font-bold rounded-lg shadow-sm transition-colors flex items-center space-x-2"
              >
                <span>{submitting ? "Committing..." : "Commit Determination to Audit Trail"}</span>
              </button>
            </div>
          </form>
        )}
      </div>

      {/* SECTION E: Chronological Append-Only Audit Trail */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center space-x-2 border-b border-slate-200 pb-3">
          <History className="w-4 h-4 text-slate-700" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-900">
            Append-Only Review Audit Trail ({history.length})
          </h2>
        </div>

        {history.length === 0 ? (
          <div className="text-xs text-slate-500">No review events logged yet.</div>
        ) : (
          <div className="space-y-3">
            {history.map((ev, idx) => (
              <div
                key={ev.id || idx}
                className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-slate-900">{ev.action}</span>
                    <span className="text-slate-400">&bull;</span>
                    <span className="font-mono text-slate-600">{ev.actor_identity}</span>
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-700">
                      {ev.actor_role}
                    </span>
                  </div>
                  {ev.reason && (
                    <p className="text-slate-700 italic">&ldquo;{ev.reason}&rdquo;</p>
                  )}
                </div>
                <div className="text-[11px] text-slate-500 whitespace-nowrap">
                  {new Date(ev.created_at).toLocaleString("en-IN")}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
