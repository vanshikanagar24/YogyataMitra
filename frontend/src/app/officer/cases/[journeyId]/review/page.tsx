"use client";

import React, { useState } from "react";
import {
  ClipboardCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowUpRight,
  ShieldAlert,
  Info,
} from "lucide-react";
import { useCase } from "../CaseContext";
import { useOfficerAuth } from "@/context/OfficerAuthContext";
import { officerApi } from "@/api/officer";

export default function CaseReviewPage() {
  const { caseData, loading, reloadCase, journeyId } = useCase();
  const { token, officer, isSupervisor } = useOfficerAuth();

  const [decision, setDecision] = useState<string>("VERIFIED");
  const [reason, setReason] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  if (loading || !caseData) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500 text-sm">
        Loading case determination panel...
      </div>
    );
  }

  const isCaseEscalated = caseData.review_status === "ESCALATED";
  const cannotResolveEscalated = isCaseEscalated && !isSupervisor;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setError(null);
    setSuccessMsg(null);

    // Validate mandatory reason for adverse, escalated, or supervisor resolution actions
    const needsReason =
      decision === "CLARIFICATION_REQUIRED" ||
      decision === "REJECTED" ||
      decision === "ESCALATED" ||
      isCaseEscalated;

    if (needsReason && !reason.trim()) {
      setError("A mandatory justification reason is required for this determination.");
      return;
    }

    if (cannotResolveEscalated && (decision === "COMPLETED" || decision === "VERIFIED" || decision === "REJECTED")) {
      setError("Permission Denied: Only a Welfare Review Supervisor can resolve an escalated case.");
      return;
    }

    setSubmitting(true);
    try {
      await officerApi.reviewCase(
        journeyId,
        {
          decision,
          reason: reason.trim() || undefined,
          notes: notes.trim() || undefined,
        },
        token
      );
      await reloadCase();
      setSuccessMsg(`Determination '${decision}' was successfully recorded into the immutable audit trail.`);
      setReason("");
      setNotes("");
    } catch (err: any) {
      setError(err?.message || "Failed to submit case review determination.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Escalation Warning if case is escalated */}
      {isCaseEscalated && (
        <div className="p-4 bg-purple-50 border border-purple-300 rounded-xl flex items-start space-x-3">
          <ShieldAlert className="w-5 h-5 text-purple-700 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-purple-900 leading-relaxed">
            <span className="font-bold block text-sm">
              SUPERVISORY ESCALATION ACTIVE
            </span>
            This case was escalated for supervisory policy or integrity review.
            {isSupervisor ? (
              <span className="text-purple-800 font-semibold block mt-1">
                You are authenticated as a Welfare Review Supervisor. You may provide official supervisory resolution below.
              </span>
            ) : (
              <span className="text-red-700 font-semibold block mt-1">
                Elevated Role Required: You are logged in as an Officer. Only a Welfare Review Supervisor can resolve an escalated case.
              </span>
            )}
          </div>
        </div>
      )}

      {/* Main Review Form Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
        <div>
          <div className="flex items-center space-x-2">
            <ClipboardCheck className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              Record Official Verification Determination
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Decisions are permanently committed to the immutable append-only audit trail.
          </p>
        </div>

        {error && (
          <div className="p-3.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-start space-x-2">
            <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="p-3.5 bg-green-50 border border-green-200 rounded-lg text-xs text-green-800 flex items-start space-x-2">
            <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
            <span>{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate className="space-y-5">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2.5">
              Select Case Determination:
            </label>
            <div className="space-y-2">
              <label className="flex items-start space-x-3 p-3.5 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer">
                <input
                  type="radio"
                  name="caseDecision"
                  value="VERIFIED"
                  checked={decision === "VERIFIED"}
                  onChange={(e) => setDecision(e.target.value)}
                  className="mt-0.5 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-xs font-bold text-slate-900 block">
                    VERIFIED — Evidence Reviewed and Accepted
                  </span>
                  <span className="text-[11px] text-slate-500 block">
                    Evidence reviewed and accepted by the authorized reviewer according to the configured review procedure.
                  </span>
                </div>
              </label>

              <label className="flex items-start space-x-3 p-3.5 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer">
                <input
                  type="radio"
                  name="caseDecision"
                  value="CLARIFICATION_REQUIRED"
                  checked={decision === "CLARIFICATION_REQUIRED"}
                  onChange={(e) => setDecision(e.target.value)}
                  className="mt-0.5 text-orange-600 focus:ring-orange-500"
                />
                <div>
                  <span className="text-xs font-bold text-orange-700 block">
                    CLARIFICATION REQUIRED — Applicant Follow-Up
                  </span>
                  <span className="text-[11px] text-slate-500 block">
                    Applicant must provide clearer copies or supplemental documentation (Mandatory justification required).
                  </span>
                </div>
              </label>

              <label className="flex items-start space-x-3 p-3.5 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer">
                <input
                  type="radio"
                  name="caseDecision"
                  value="REJECTED"
                  checked={decision === "REJECTED"}
                  onChange={(e) => setDecision(e.target.value)}
                  className="mt-0.5 text-red-600 focus:ring-red-500"
                />
                <div>
                  <span className="text-xs font-bold text-red-700 block">
                    REJECTED — Verification Failed
                  </span>
                  <span className="text-[11px] text-slate-500 block">
                    Submitted evidence is invalid or citizen is disqualified under statutory criteria (Mandatory justification required).
                  </span>
                </div>
              </label>

              <label className="flex items-start space-x-3 p-3.5 rounded-lg border border-slate-200 hover:bg-purple-50/50 cursor-pointer">
                <input
                  type="radio"
                  name="caseDecision"
                  value="ESCALATED"
                  checked={decision === "ESCALATED"}
                  onChange={(e) => setDecision(e.target.value)}
                  className="mt-0.5 text-purple-600 focus:ring-purple-500"
                />
                <div>
                  <span className="text-xs font-bold text-purple-800 block">
                    ESCALATED — Refer to Welfare Review Supervisor
                  </span>
                  <span className="text-[11px] text-slate-500 block">
                    Complex statutory exception or document conflict requiring supervisory determination (Mandatory justification required).
                  </span>
                </div>
              </label>

              <label className="flex items-start space-x-3 p-3.5 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer">
                <input
                  type="radio"
                  name="caseDecision"
                  value="COMPLETED"
                  checked={decision === "COMPLETED"}
                  onChange={(e) => setDecision(e.target.value)}
                  className="mt-0.5 text-green-600 focus:ring-green-500"
                />
                <div>
                  <span className="text-xs font-bold text-green-800 block">
                    COMPLETED — Finalize Review
                  </span>
                  <span className="text-[11px] text-slate-500 block">
                    Human verification review concluded and signed off.
                  </span>
                </div>
              </label>
            </div>
          </div>

          {/* Mandatory Reason Textarea */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Determination Reason / Justification{" "}
              {(decision !== "VERIFIED" || isCaseEscalated) && (
                <span className="text-red-500">* (Mandatory)</span>
              )}
            </label>
            <textarea
              rows={3}
              required={decision !== "VERIFIED" || isCaseEscalated}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Provide clear, evidence-grounded statutory justification for this determination..."
              className="w-full text-xs p-3 border border-slate-300 rounded-lg focus:ring-1 focus:ring-blue-500 outline-none"
            />
          </div>

          {/* Optional Administrative Notes */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Internal Administrative Notes (Optional)
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Internal case management notes or references..."
              className="w-full text-xs p-3 border border-slate-300 rounded-lg focus:ring-1 focus:ring-blue-500 outline-none"
            />
          </div>

          <div className="pt-2 flex items-center justify-between border-t border-slate-100">
            <div className="text-[11px] text-slate-500 flex items-center space-x-1.5">
              <Info className="w-4 h-4 text-slate-400 flex-shrink-0" />
              <span>
                Acting Officer: <strong className="text-slate-700">{officer?.email}</strong> ({officer?.role})
              </span>
            </div>

            <button
              type="submit"
              disabled={submitting || cannotResolveEscalated}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg shadow-sm transition-colors disabled:opacity-50"
            >
              {submitting ? "Committing Decision..." : "Commit Official Determination"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
