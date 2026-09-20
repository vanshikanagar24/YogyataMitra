"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  UserCheck,
  RotateCcw,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Lock,
  FileCheck2,
} from "lucide-react";
import { useOfficerAuth } from "@/context/OfficerAuthContext";
import { policyAuthoringApi } from "@/api/policyAuthoring";
import { PolicyDraftDetail } from "@/types/policyAuthoring";
import { DraftStatusBadge } from "@/components/policy-authoring/DraftStatusBadge";
import { DraftSubNav } from "@/components/policy-authoring/DraftSubNav";

export default function PolicyReviewPage() {
  const { isAuthenticated, isLoading: authLoading, token, officer } = useOfficerAuth();
  const params = useParams();
  const router = useRouter();
  const draftId = params.draftId as string;

  const [draft, setDraft] = useState<PolicyDraftDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Review form state
  const [selectedAction, setSelectedAction] = useState<string>("");
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/officer/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const fetchDraft = useCallback(async () => {
    if (!token || !draftId) return;
    setLoading(true);
    setError(null);

    try {
      const data = await policyAuthoringApi.getDraft(draftId, token);
      setDraft(data);
      // Initialize default action based on lifecycle status
      if (
        data.lifecycle_status === "REVIEW_PENDING" ||
        data.lifecycle_status === "PENDING_REVIEW" ||
        data.lifecycle_status === "IN_REVIEW"
      ) {
        setSelectedAction("STAGE");
      } else if (data.lifecycle_status === "REVISED" || data.lifecycle_status === "NEEDS_CLARIFICATION") {
        setSelectedAction("RESUME_AUTHORING");
      } else {
        setSelectedAction("SUBMIT_FOR_REVIEW");
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load policy draft.");
    } finally {
      setLoading(false);
    }
  }, [draftId, token]);

  useEffect(() => {
    if (isAuthenticated && token && draftId) {
      fetchDraft();
    }
  }, [isAuthenticated, token, draftId, fetchDraft]);

  // Separation of duties checks
  const isAuthor = Boolean(
    officer &&
      draft &&
      (draft.author_id === officer.id ||
        draft.author_id === officer.name ||
        draft.author_id === officer.email)
  );

  const isSupervisor = officer?.role === "SUPERVISOR";
  const canStage = isSupervisor && !isAuthor;

  const handleTransition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !draftId || !selectedAction) return;
    setError(null);
    setSuccessMsg(null);

    if (reason.trim().length < 5) {
      setError("Substantive justification reason must be at least 5 characters long.");
      return;
    }

    if (selectedAction === "STAGE" && !canStage) {
      if (isAuthor) {
        setError("Separation of Duties violation: The author cannot stage their own policy draft.");
      } else if (!isSupervisor) {
        setError("Role Violation: Staging requires the SUPERVISOR role.");
      }
      return;
    }

    setActionLoading(true);
    try {
      const updated = await policyAuthoringApi.transitionDraft(
        draftId,
        {
          action: selectedAction,
          reason: reason.trim(),
          notes: notes.trim() || undefined,
        },
        token
      );
      setDraft(updated);
      setSuccessMsg(`Transition to ${updated.lifecycle_status} completed successfully!`);
      setReason("");
      setNotes("");
    } catch (err: any) {
      setError(err?.message || "Failed to execute lifecycle transition.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-500 mb-2" />
        <p className="text-sm">Loading review panel...</p>
      </div>
    );
  }

  if (!draft) return null;

  const isStaged = draft.lifecycle_status === "STAGED";

  return (
    <div className="space-y-6">
      {/* Top Banner Notice: STAGED IS NOT ACTIVE */}
      <div className="bg-amber-500/10 border-l-4 border-amber-500 p-4 rounded-r-lg shadow-sm">
        <div className="flex items-start space-x-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-slate-800 space-y-1">
            <p className="font-bold text-amber-900 tracking-wide uppercase text-[11px]">
              SUPERVISORY DETERMINATION • STAGED IS NOT ACTIVE
            </p>
            <p className="text-slate-600">
              Staging policy drafts confirms mathematical AST compilation and statutory compliance.
              Staged policies are strictly quarantined and cannot evaluate live citizen profiles.
            </p>
          </div>
        </div>
      </div>

      {/* Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          href={`/officer/policy-authoring/${draft.id}`}
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Dossier</span>
        </Link>
        <DraftStatusBadge status={draft.lifecycle_status} />
      </div>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
          <UserCheck className="w-6 h-6 text-amber-600" />
          <span>Supervisory Review & Lifecycle Determination</span>
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Authorized determination for policy draft: <strong>{draft.policy_title}</strong>.
        </p>
      </div>

      {/* SubNav */}
      <DraftSubNav draftId={draft.id} />

      {/* Notifications */}
      {successMsg && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-lg text-xs flex items-center justify-between shadow-sm">
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="font-bold underline ml-2">
            Dismiss
          </button>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-xs flex items-center justify-between shadow-sm">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="font-bold underline ml-2">
            Dismiss
          </button>
        </div>
      )}

      {/* Separation of Duties & Officer Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Officer info */}
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm text-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-bold text-slate-500 uppercase tracking-wider text-[11px]">
              Active Reviewing Officer
            </span>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                isSupervisor
                  ? "bg-purple-100 text-purple-800 border border-purple-300"
                  : "bg-blue-100 text-blue-800 border border-blue-300"
              }`}
            >
              {officer?.role}
            </span>
          </div>
          <div className="font-bold text-slate-900 text-sm">{officer?.name}</div>
          <div className="text-slate-500 text-[11px]">Identity: {officer?.id || officer?.email}</div>
        </div>

        {/* Separation of Duties status */}
        <div
          className={`p-4 rounded-lg border shadow-sm text-xs space-y-2 ${
            isAuthor
              ? "bg-amber-50 border-amber-300 text-amber-950"
              : "bg-emerald-50 border-emerald-300 text-emerald-950"
          }`}
        >
          <div className="flex items-center space-x-2 font-bold">
            {isAuthor ? (
              <>
                <ShieldAlert className="w-4 h-4 text-amber-600 flex-shrink-0" />
                <span>Separation of Duties Restriction Active</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>Separation of Duties Satisfied</span>
              </>
            )}
          </div>
          <p className="text-[11px] leading-relaxed">
            {isAuthor
              ? "You authored this draft. To maintain legislative integrity, policy staging requires an independent supervisor review."
              : "You are not the author of this policy draft. You are authorized to conduct supervisory review."}
          </p>
        </div>
      </div>

      {/* Staged State Notice if already STAGED */}
      {isStaged ? (
        <div className="bg-purple-50 border border-purple-300 rounded-lg p-6 shadow-sm text-xs space-y-3">
          <div className="flex items-center space-x-2 font-bold text-purple-900 text-sm">
            <ShieldCheck className="w-5 h-5 text-purple-700" />
            <span>Policy Draft Successfully Staged in Verified Quarantine</span>
          </div>
          <p className="text-purple-800 leading-relaxed">
            This policy draft has completed compilation, boundary test validation, and supervisory approval. It is
            quarantined in the STAGED lifecycle status.
          </p>
          <div className="bg-white p-3 rounded border border-purple-200 font-mono text-[11px] text-purple-900 space-y-1">
            <div>Staged By: {draft.staged_by} ({draft.staged_by_role})</div>
            <div>Staged At: {draft.staged_at ? new Date(draft.staged_at).toLocaleString() : "Confirmed"}</div>
            <div>Rule SHA-256: {draft.rule_hash}</div>
          </div>
        </div>
      ) : (
        /* Review Determination Form */
        <form
          onSubmit={handleTransition}
          className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-5"
        >
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Select Lifecycle Transition Action
            </h3>
            <p className="text-xs text-slate-500">
              Current Status: <strong>{draft.lifecycle_status}</strong>
            </p>
          </div>

          {/* Action options */}
          <div className="space-y-2">
            {/* SUBMIT_FOR_REVIEW */}
            {draft.lifecycle_status !== "STAGED" &&
              draft.lifecycle_status !== "ARCHIVED" &&
              draft.lifecycle_status !== "REVIEW_PENDING" &&
              draft.lifecycle_status !== "PENDING_REVIEW" &&
              draft.lifecycle_status !== "IN_REVIEW" && (
              <label className="flex items-start space-x-3 p-3 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer text-xs">
                <input
                  type="radio"
                  name="action"
                  value="SUBMIT_FOR_REVIEW"
                  checked={selectedAction === "SUBMIT_FOR_REVIEW"}
                  onChange={(e) => setSelectedAction(e.target.value)}
                  className="mt-0.5 text-blue-600"
                />
                <div>
                  <span className="font-bold text-slate-900">
                    Submit for Supervisory Review (SUBMIT_FOR_REVIEW)
                  </span>
                  <p className="text-slate-500 text-[11px] mt-0.5">
                    Locks further authoring changes and moves draft to REVIEW_PENDING queue.
                  </p>
                </div>
              </label>
            )}

            {/* STAGE (Supervisor only, non-author only) */}
            {(draft.lifecycle_status === "REVIEW_PENDING" ||
              draft.lifecycle_status === "PENDING_REVIEW" ||
              draft.lifecycle_status === "IN_REVIEW") && (
              <label
                className={`flex items-start space-x-3 p-3 rounded-lg border text-xs ${
                  canStage
                    ? "border-purple-300 bg-purple-50/40 hover:bg-purple-50 cursor-pointer"
                    : "border-slate-200 bg-slate-100 opacity-60 cursor-not-allowed"
                }`}
              >
                <input
                  type="radio"
                  name="action"
                  value="STAGE"
                  disabled={!canStage}
                  checked={selectedAction === "STAGE"}
                  onChange={(e) => setSelectedAction(e.target.value)}
                  className="mt-0.5 text-purple-600"
                />
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-purple-950">
                      Approve & Stage Policy (STAGE)
                    </span>
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-purple-200 text-purple-900">
                      SUPERVISOR ONLY
                    </span>
                  </div>
                  <p className="text-slate-600 text-[11px] mt-0.5">
                    Quarantines policy in verified STAGED state. STAGED IS NOT ACTIVE. No citizen evaluations are affected.
                  </p>
                  {!canStage && (
                    <p className="text-red-600 font-semibold text-[10px] mt-1">
                      {isAuthor
                        ? "Restricted: You cannot stage a policy draft that you authored."
                        : "Restricted: Staging requires the SUPERVISOR role."}
                    </p>
                  )}
                </div>
              </label>
            )}

            {/* REQUEST_REVISION */}
            {draft.lifecycle_status === "REVIEW_PENDING" && (
              <label className="flex items-start space-x-3 p-3 rounded-lg border border-amber-200 hover:bg-amber-50/50 cursor-pointer text-xs">
                <input
                  type="radio"
                  name="action"
                  value="REQUEST_REVISION"
                  checked={selectedAction === "REQUEST_REVISION"}
                  onChange={(e) => setSelectedAction(e.target.value)}
                  className="mt-0.5 text-amber-600"
                />
                <div>
                  <span className="font-bold text-amber-950">
                    Request Authoring Revision (REQUEST_REVISION)
                  </span>
                  <p className="text-slate-500 text-[11px] mt-0.5">
                    Rejects current compilation and returns draft to REVISED status for author modification.
                  </p>
                </div>
              </label>
            )}

            {/* RESUME_AUTHORING */}
            {draft.lifecycle_status === "REVISED" && (
              <label className="flex items-start space-x-3 p-3 rounded-lg border border-blue-200 hover:bg-blue-50/50 cursor-pointer text-xs">
                <input
                  type="radio"
                  name="action"
                  value="RESUME_AUTHORING"
                  checked={selectedAction === "RESUME_AUTHORING"}
                  onChange={(e) => setSelectedAction(e.target.value)}
                  className="mt-0.5 text-blue-600"
                />
                <div>
                  <span className="font-bold text-blue-950">
                    Resume Human Editing (RESUME_AUTHORING)
                  </span>
                  <p className="text-slate-500 text-[11px] mt-0.5">
                    Moves draft back to HUMAN_EDITING state for editing rule ASTs.
                  </p>
                </div>
              </label>
            )}
          </div>

          {/* Substantive Reason (Mandatory >= 5 chars) */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Substantive Review Justification Reason *
              </label>
              <span
                className={`text-[11px] font-mono ${
                  reason.trim().length >= 5 ? "text-emerald-600 font-bold" : "text-amber-600"
                }`}
              >
                {reason.trim().length}/5 chars minimum
              </span>
            </div>
            <textarea
              rows={3}
              required
              placeholder="Enter detailed statutory, legislative, or technical rationale for this determination..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-1 focus:ring-blue-500 bg-slate-50"
            />
          </div>

          {/* Optional Notes */}
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              Internal Supervisory Notes (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. Verified Gazette reference G.S.R. 2024/77"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 bg-slate-50"
            />
          </div>

          {/* Submit */}
          <div className="pt-4 border-t border-slate-200 flex justify-end space-x-3">
            <Link
              href={`/officer/policy-authoring/${draft.id}`}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
            >
              Cancel
            </Link>

            <button
              type="submit"
              disabled={actionLoading || reason.trim().length < 5 || !selectedAction}
              className="px-5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition-colors flex items-center space-x-1.5 disabled:opacity-50"
            >
              {actionLoading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Recording Determination...</span>
                </>
              ) : (
                <span>Commit Lifecycle Determination</span>
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
