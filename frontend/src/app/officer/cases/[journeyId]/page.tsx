"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  FileText,
  Shield,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  UserCheck,
  Clock,
  History,
  UserX,
  Zap,
  RotateCcw,
} from "lucide-react";
import { useCase } from "./CaseContext";
import { useOfficerAuth } from "@/context/OfficerAuthContext";
import { officerApi } from "@/api/officer";

export default function CaseOverviewPage() {
  const { caseData, loading, journeyId, reloadCase } = useCase();
  const { token, officer } = useOfficerAuth();

  const [showAssignForm, setShowAssignForm] = useState(false);
  const [targetOfficer, setTargetOfficer] = useState("officer@yogyatamitra.local");
  const [reassignReason, setReassignReason] = useState("");
  const [customSlaHours, setCustomSlaHours] = useState<number>(48);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  if (loading || !caseData) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500 text-sm">
        Loading case claims and factual dossier...
      </div>
    );
  }

  const activeAssign = caseData.active_assignment;
  const history = caseData.assignment_history || [];

  const handleManualAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setActionLoading(true);
    setActionError(null);
    setActionSuccess(null);

    try {
      if (activeAssign) {
        // Reassignment requires substantive reason
        if (!reassignReason.trim()) {
          setActionError("A valid justification is required when reassigning an active case.");
          setActionLoading(false);
          return;
        }
        await officerApi.reassignCase(
          journeyId,
          {
            new_officer_identity: targetOfficer,
            reason: reassignReason.trim(),
            sla_hours: customSlaHours || undefined,
          },
          token
        );
        setActionSuccess(`Case successfully reassigned to ${targetOfficer}`);
      } else {
        // Initial manual assignment
        await officerApi.assignCase(
          journeyId,
          {
            officer_identity: targetOfficer,
            reason: reassignReason.trim() || undefined,
            sla_hours: customSlaHours || undefined,
          },
          token
        );
        setActionSuccess(`Case successfully assigned to ${targetOfficer}`);
      }
      setShowAssignForm(false);
      setReassignReason("");
      await reloadCase();
    } catch (err: any) {
      setActionError(err?.message || "Failed to complete assignment operation");
    } finally {
      setActionLoading(false);
    }
  };

  const handleAutoAssign = async () => {
    if (!token) return;
    setActionLoading(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await officerApi.autoAssignCase(journeyId, token);
      setActionSuccess(`Case automatically assigned to least-loaded officer (${res.officer_identity})`);
      await reloadCase();
    } catch (err: any) {
      setActionError(err?.message || "Auto-assignment failed");
    } finally {
      setActionLoading(false);
    }
  };

  const getSLABadge = (slaStatus?: string | null) => {
    switch (slaStatus) {
      case "OVERDUE":
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-bold bg-red-100 text-red-800 border border-red-200">
            <AlertTriangle className="w-3.5 h-3.5 mr-1 text-red-600" />
            Overdue SLA
          </span>
        );
      case "DUE_SOON":
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
            <Clock className="w-3.5 h-3.5 mr-1 text-amber-600" />
            Due Soon (&lt;12h)
          </span>
        );
      case "COMPLETED":
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-semibold bg-green-100 text-green-800 border border-green-200">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-green-600" />
            Completed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            <Clock className="w-3.5 h-3.5 mr-1 text-slate-500" />
            On Track
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Statutory / Non-Statutory Platform Notice */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-600 flex items-start space-x-3">
        <Shield className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-slate-800">Operational Assessment Context:</span>{" "}
          This case dossier contains citizen declarations and documentary evidence references.
          Official eligibility sanction remains the statutory prerogative of the competent government authority.
        </div>
      </div>

      {actionSuccess && (
        <div className="p-3.5 bg-green-50 border border-green-200 rounded-xl text-xs text-green-800 flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {actionError && (
        <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      {/* Case Summary Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-4">
          Case Information Summary
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          <div>
            <span className="text-slate-500 block">Citizen Reference:</span>
            <span className="font-mono font-bold text-slate-900">
              {caseData.citizen_ref}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block">Welfare Scheme:</span>
            <span className="font-semibold text-slate-900">
              {caseData.scheme_name} ({caseData.scheme_code})
            </span>
          </div>
          <div>
            <span className="text-slate-500 block">Lifecycle Journey State:</span>
            <span className="font-semibold text-slate-900">
              {caseData.journey_state}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block">Submission Timestamp:</span>
            <span className="font-semibold text-slate-900">
              {new Date(caseData.submitted_at).toLocaleDateString("en-IN", {
                year: "numeric",
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
        </div>
      </div>

      {/* Operational Officer Assignment & SLA Card (Phase D) */}
      <div className="bg-white rounded-xl border border-blue-200 bg-blue-50/10 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center space-x-2">
              <UserCheck className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-bold text-slate-900 tracking-tight">
                Operational Officer Assignment & SLA Tracking
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Assigned verification responsibility, turnaround SLA target, and auditable reassignment controls.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            {!activeAssign && (
              <button
                onClick={handleAutoAssign}
                disabled={actionLoading}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold shadow-sm flex items-center space-x-1.5 disabled:opacity-50 transition-colors"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>Auto-Assign</span>
              </button>
            )}
            <button
              onClick={() => setShowAssignForm(!showAssignForm)}
              className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded text-xs font-semibold shadow-sm flex items-center space-x-1.5 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
              <span>{activeAssign ? "Reassign Case" : "Manual Assign"}</span>
            </button>
          </div>
        </div>

        <div className="p-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs mb-4">
            <div>
              <span className="text-slate-500 block">Assigned Officer:</span>
              <span className="font-semibold text-slate-900">
                {activeAssign
                  ? `${activeAssign.officer_name || activeAssign.officer_identity} (${activeAssign.officer_identity})`
                  : caseData.reviewer_identity !== "UNASSIGNED"
                  ? `${caseData.reviewer_identity}`
                  : "Unassigned"}
              </span>
            </div>

            <div>
              <span className="text-slate-500 block">Assignment Status:</span>
              <span className="font-semibold text-slate-900">
                {activeAssign ? activeAssign.status : "UNASSIGNED"}
              </span>
            </div>

            <div>
              <span className="text-slate-500 block">SLA Target Due Date:</span>
              <span className="font-semibold text-slate-900">
                {activeAssign?.due_at
                  ? new Date(activeAssign.due_at).toLocaleDateString("en-IN", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : "Not Configured"}
              </span>
            </div>

            <div>
              <span className="text-slate-500 block">SLA Compliance:</span>
              <div className="mt-0.5">{getSLABadge(activeAssign?.sla_status)}</div>
            </div>
          </div>

          {/* Collapsible Assignment / Reassignment Form */}
          {showAssignForm && (
            <form
              onSubmit={handleManualAssign}
              className="mt-4 p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3.5 text-xs"
            >
              <div className="font-bold text-slate-800">
                {activeAssign ? "Reassign Case to New Officer" : "Manually Assign Case"}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-600 font-semibold mb-1">
                    Target Officer Email:
                  </label>
                  <select
                    value={targetOfficer}
                    onChange={(e) => setTargetOfficer(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg p-2 bg-white text-slate-800 focus:ring-1 focus:ring-blue-500 outline-none"
                  >
                    <option value="officer@yogyatamitra.local">
                      officer@yogyatamitra.local (Senior Verification Officer)
                    </option>
                    <option value="officer.varanasi@yogyatamitra.local">
                      officer.varanasi@yogyatamitra.local (Varanasi Verification Officer)
                    </option>
                    <option value="officer.lucknow@yogyatamitra.local">
                      officer.lucknow@yogyatamitra.local (Lucknow Verification Officer)
                    </option>
                    <option value="supervisor@yogyatamitra.local">
                      supervisor@yogyatamitra.local (Welfare Review Supervisor)
                    </option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-600 font-semibold mb-1">
                    SLA Duration (Hours):
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={720}
                    value={customSlaHours}
                    onChange={(e) => setCustomSlaHours(parseInt(e.target.value) || 48)}
                    className="w-full border border-slate-300 rounded-lg p-2 bg-white text-slate-800 focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-600 font-semibold mb-1">
                  Justification / Reason {activeAssign ? "(Mandatory)" : "(Optional)"}:
                </label>
                <textarea
                  rows={2}
                  value={reassignReason}
                  onChange={(e) => setReassignReason(e.target.value)}
                  placeholder={
                    activeAssign
                      ? "State reasons for reassignment (e.g. Officer on leave, district jurisdiction shift, workload balancing)..."
                      : "Optional assignment note..."
                  }
                  className="w-full border border-slate-300 rounded-lg p-2 bg-white text-slate-800 focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-1">
                <button
                  type="button"
                  onClick={() => setShowAssignForm(false)}
                  className="px-3 py-1.5 bg-white border border-slate-300 rounded text-slate-600 hover:bg-slate-100 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded font-semibold disabled:opacity-50 shadow-sm"
                >
                  {actionLoading ? "Submitting..." : activeAssign ? "Confirm Reassignment" : "Confirm Assignment"}
                </button>
              </div>
            </form>
          )}

          {/* Historical Assignment Trail */}
          {history.length > 0 && (
            <div className="mt-4 pt-4 border-t border-slate-200">
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center space-x-1.5">
                <History className="w-3.5 h-3.5 text-slate-400" />
                <span>Assignment & Reassignment History ({history.length} records)</span>
              </div>
              <div className="space-y-2">
                {history.map((h) => (
                  <div
                    key={h.id}
                    className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                  >
                    <div>
                      <span className="font-semibold text-slate-800">
                        {h.officer_name || h.officer_identity}
                      </span>{" "}
                      <span className="text-slate-400">({h.officer_identity})</span>
                      {h.reassignment_reason && (
                        <div className="text-[11px] text-slate-500 italic mt-0.5">
                          Reason: {h.reassignment_reason}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center space-x-3 text-[11px] text-slate-500">
                      <span>Assigned by: {h.assigned_by}</span>
                      <span>&bull;</span>
                      <span>
                        {new Date(h.assigned_at).toLocaleDateString("en-IN", {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                      <span
                        className={`px-1.5 py-0.5 rounded font-semibold text-[10px] ${
                          h.is_active
                            ? "bg-blue-100 text-blue-800"
                            : "bg-slate-200 text-slate-600"
                        }`}
                      >
                        {h.is_active ? "CURRENT" : h.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Citizen Provided Claims Section */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              Citizen Asserted Claims ({caseData.claims.length})
            </h2>
            <p className="text-xs text-slate-500">
              Factual assertions provided by the applicant, translated into standardized plain language.
            </p>
          </div>

          <div className="text-xs text-slate-500 font-medium hidden sm:block">
            Immutable Fact Baseline
          </div>
        </div>

        <div className="divide-y divide-slate-100">
          {caseData.claims.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-xs">
              No factual claims registered for this evaluation journey.
            </div>
          ) : (
            caseData.claims.map((claim) => (
              <div
                key={claim.id}
                className="p-5 hover:bg-slate-50/60 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-semibold text-slate-900">
                      {claim.claim_label}
                    </span>
                    <span className="text-[11px] font-mono text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
                      {claim.claim_type}
                    </span>
                  </div>

                  <div className="text-sm font-bold text-blue-900">
                    {claim.value_display}
                  </div>

                  <div className="text-xs text-slate-500 flex items-center space-x-3 pt-1">
                    <span>Source: {claim.source}</span>
                    <span>&bull;</span>
                    <span>
                      Asserted:{" "}
                      {new Date(claim.claimed_at).toLocaleDateString("en-IN", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                </div>

                <div className="flex items-center space-x-3 self-start md:self-auto">
                  <span
                    className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-semibold ${
                      claim.status === "VERIFIED"
                        ? "bg-green-100 text-green-800 border border-green-200"
                        : "bg-slate-100 text-slate-700 border border-slate-200"
                    }`}
                  >
                    {claim.status}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Submitted Evidence References Section (Part 13: Read-Only Reference Display) */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              Submitted Evidence References ({caseData.evidence_items.length})
            </h2>
            <p className="text-xs text-slate-500">
              Documentary attachments provided by the applicant in support of asserted claims.
            </p>
          </div>
          <div className="text-xs text-slate-500 font-medium hidden sm:block">
            Evidence Verification: Phase E
          </div>
        </div>

        <div className="divide-y divide-slate-100">
          {caseData.evidence_items.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-xs">
              No documentary evidence attached to this application.
            </div>
          ) : (
            caseData.evidence_items.map((ev) => (
              <div
                key={ev.id}
                className="p-4 hover:bg-slate-50/60 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
              >
                <div>
                  <div className="font-semibold text-slate-800">
                    {ev.evidence_type_label || ev.evidence_type}
                  </div>
                  <div className="text-slate-500 font-mono text-[11px] mt-0.5">
                    Storage Ref: {ev.storage_reference}
                  </div>
                </div>

                <div className="flex items-center space-x-2 self-start sm:self-auto">
                  <span
                    className={`px-2 py-0.5 rounded font-semibold text-[11px] ${
                      ev.status === "VERIFIED"
                        ? "bg-green-100 text-green-800"
                        : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {ev.status}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Action Footer Callouts */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link
          href={`/officer/cases/${journeyId}/evidence`}
          className="p-4 bg-white rounded-xl border border-slate-200 hover:border-blue-500 hover:bg-blue-50/20 transition-all shadow-sm flex items-center justify-between group"
        >
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Supporting Evidence
            </div>
            <div className="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition-colors mt-0.5">
              Inspect Supporting Evidence ({caseData.evidence_items.length} items)
            </div>
          </div>
          <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all" />
        </Link>

        <Link
          href={`/officer/cases/${journeyId}/review`}
          className="p-4 bg-white rounded-xl border border-slate-200 hover:border-purple-500 hover:bg-purple-50/20 transition-all shadow-sm flex items-center justify-between group"
        >
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Assessment Summary
            </div>
            <div className="text-sm font-bold text-slate-900 group-hover:text-purple-600 transition-colors mt-0.5">
              Review Case Determination
            </div>
          </div>
          <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-purple-600 group-hover:translate-x-0.5 transition-all" />
        </Link>
      </div>
    </div>
  );
}
