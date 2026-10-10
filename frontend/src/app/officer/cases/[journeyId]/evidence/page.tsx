"use client";

import React, { useState } from "react";
import {
  FileCheck,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ExternalLink,
  ShieldAlert,
  Clock,
  UserCheck,
  FileText,
} from "lucide-react";
import { useCase } from "../CaseContext";
import { useOfficerAuth } from "@/context/OfficerAuthContext";
import { officerApi } from "@/api/officer";
import { OfficerEvidence } from "@/types/officer";

export default function CaseEvidencePage() {
  const { caseData, loading, reloadCase, journeyId } = useCase();
  const { token } = useOfficerAuth();

  const [selectedEvidence, setSelectedEvidence] = useState<OfficerEvidence | null>(null);
  const [modalAction, setModalAction] = useState<"VERIFY" | "REJECT" | "REQUEST_CLARIFICATION">("VERIFY");
  const [modalReason, setModalReason] = useState("");
  const [modalNotes, setModalNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  if (loading || !caseData) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500 text-sm">
        Loading evidence dossier...
      </div>
    );
  }

  const openVerifyModal = (ev: OfficerEvidence) => {
    setSelectedEvidence(ev);
    setModalAction("VERIFY");
    setModalReason("");
    setModalNotes("");
    setActionError(null);
  };

  const closeModal = () => {
    setSelectedEvidence(null);
    setActionError(null);
  };

  const handleActionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEvidence || !token) return;

    if (
      (modalAction === "REJECT" || modalAction === "REQUEST_CLARIFICATION") &&
      !modalReason.trim()
    ) {
      setActionError("A mandatory justification reason is required for rejection or clarification requests.");
      return;
    }

    setSubmitting(true);
    setActionError(null);

    try {
      await officerApi.verifyEvidence(
        journeyId,
        selectedEvidence.id,
        {
          action: modalAction,
          reason: modalReason.trim() || undefined,
          notes: modalNotes.trim() || undefined,
        },
        token
      );
      await reloadCase();
      closeModal();
    } catch (err: any) {
      setActionError(err?.message || "Failed to submit evidence determination.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Evidence Banner */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-slate-900 tracking-tight">
            Supporting Documentary Evidence ({caseData.evidence_items.length} items)
          </h2>
          <p className="text-xs text-slate-500">
            Official documents submitted to verify claimed statutory eligibility criteria.
          </p>
        </div>

        <div className="text-xs bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg text-slate-600">
          <strong>Invariant:</strong> Documentary verification does not alter citizen claims.
        </div>
      </div>

      {/* Evidence Items List */}
      <div className="space-y-4">
        {caseData.evidence_items.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500 text-xs">
            No documentary evidence has been submitted for this journey.
          </div>
        ) : (
          caseData.evidence_items.map((ev) => (
            <div
              key={ev.id}
              className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <FileText className="w-4 h-4 text-blue-600 flex-shrink-0" />
                    <span className="text-sm font-bold text-slate-900">
                      {ev.evidence_type_label}
                    </span>
                    <span className="text-[11px] font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                      {ev.evidence_type}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500">
                    Linked Claim Type: <span className="font-mono text-slate-700">{ev.claim_type}</span>
                  </div>
                </div>

                <div className="flex items-center space-x-3 self-start sm:self-auto">
                  {ev.status === "VERIFIED" ? (
                    <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-bold bg-green-100 text-green-800 border border-green-200">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>VERIFIED</span>
                    </span>
                  ) : ev.status === "REJECTED" ? (
                    <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-bold bg-red-100 text-red-800 border border-red-200">
                      <XCircle className="w-3.5 h-3.5" />
                      <span>REJECTED</span>
                    </span>
                  ) : ev.status === "CLARIFICATION_REQUIRED" ? (
                    <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-bold bg-orange-100 text-orange-800 border border-orange-200">
                      <AlertCircle className="w-3.5 h-3.5" />
                      <span>CLARIFICATION REQUIRED</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
                      <Clock className="w-3.5 h-3.5" />
                      <span>PENDING VERIFICATION</span>
                    </span>
                  )}

                  <button
                    type="button"
                    onClick={() => openVerifyModal(ev)}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold transition-colors shadow-sm"
                  >
                    Take Action
                  </button>
                </div>
              </div>

              {/* Metadata & Storage Ref */}
              <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-slate-500 block">Secure Storage Reference:</span>
                  <span className="font-mono text-slate-800 break-all">
                    {ev.storage_reference}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">Document Metadata:</span>
                  <span className="text-slate-800">
                    {ev.metadata_json
                      ? Object.entries(ev.metadata_json)
                          .map(([k, v]) => `${k}: ${v}`)
                          .join(" | ")
                      : "None specified"}
                  </span>
                </div>
              </div>

              {/* Adverse Notice / Rejection Reason */}
              {ev.rejection_reason && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-900 flex items-start space-x-2">
                  <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold">Rejection Justification: </span>
                    <span>{ev.rejection_reason}</span>
                  </div>
                </div>
              )}

              {/* Clarification Requests and Responses */}
              {caseData.clarifications && caseData.clarifications.filter((c) => c.evidence_id === ev.id).length > 0 && (
                <div className="border-t border-slate-100 pt-3 space-y-2">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                    Clarification Requests & Responses:
                  </div>
                  {caseData.clarifications
                    .filter((c) => c.evidence_id === ev.id)
                    .map((c) => (
                      <div
                        key={c.id}
                        className="p-3 bg-amber-50/70 border border-amber-200 rounded-lg text-xs space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-amber-900">
                            Round {c.round}: Clarification {c.status}
                          </span>
                          <span className="text-[11px] text-amber-700">
                            Requested: {new Date(c.requested_at).toLocaleString("en-IN")}
                          </span>
                        </div>
                        <p className="text-slate-700">
                          <strong>Reason:</strong> {c.request_reason}
                        </p>
                        {c.notes && (
                          <p className="text-slate-600 italic">
                            <strong>Officer Notes:</strong> {c.notes}
                          </p>
                        )}
                        {c.response_text ? (
                          <div className="p-2.5 bg-white border border-amber-300 rounded text-slate-800 space-y-1">
                            <div className="text-[11px] font-bold text-slate-500 uppercase">
                              Citizen Response ({c.responded_at ? new Date(c.responded_at).toLocaleString("en-IN") : "Submitted"}):
                            </div>
                            <p className="text-xs">{c.response_text}</p>
                            {c.replacement_evidence_id && (
                              <div className="text-[11px] text-blue-700 font-mono">
                                Replacement Evidence Ref: {c.replacement_evidence_id}
                              </div>
                            )}
                          </div>
                        ) : (
                          <p className="text-xs text-amber-700 font-medium">
                            Awaiting citizen response...
                          </p>
                        )}
                      </div>
                    ))}
                </div>
              )}

              {/* Verification Audit Records */}
              {ev.verification_records && ev.verification_records.length > 0 && (
                <div className="border-t border-slate-100 pt-3 space-y-1.5">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    Document Verification Log:
                  </div>
                  {ev.verification_records.map((vr) => (
                    <div
                      key={vr.id}
                      className="text-xs text-slate-600 flex flex-wrap items-center gap-2 bg-white px-2.5 py-1.5 rounded border border-slate-100"
                    >
                      <span className="font-semibold text-slate-800">{vr.status}</span>
                      <span>by</span>
                      <span className="font-mono text-slate-700">{vr.verified_by || "OFFICER"}</span>
                      <span>via</span>
                      <span className="italic">{vr.method}</span>
                      {vr.verified_at && (
                        <span className="text-slate-400 text-[11px]">
                          ({new Date(vr.verified_at).toLocaleString("en-IN")})
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Verification Determination Modal */}
      {selectedEvidence && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full border border-slate-200 overflow-hidden">
            <div className="p-5 bg-slate-900 text-white flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold">Document Verification Determination</h3>
                <p className="text-xs text-blue-300 font-mono mt-0.5">
                  {selectedEvidence.evidence_type_label}
                </p>
              </div>
              <button
                onClick={closeModal}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleActionSubmit} noValidate className="p-5 space-y-4">
              {actionError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded text-xs text-red-800">
                  {actionError}
                </div>
              )}

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                  Select Action:
                </label>
                <div className="space-y-2">
                  <label className="flex items-center space-x-2.5 p-3 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer">
                    <input
                      type="radio"
                      name="modalAction"
                      value="VERIFY"
                      checked={modalAction === "VERIFY"}
                      onChange={() => setModalAction("VERIFY")}
                      className="text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <span className="text-xs font-bold text-slate-900 block">
                        Verify Document
                      </span>
                      <span className="text-[11px] text-slate-500 block">
                        Review and accept submitted proof according to verification procedure.
                      </span>
                    </div>
                  </label>

                  <label className="flex items-center space-x-2.5 p-3 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer">
                    <input
                      type="radio"
                      name="modalAction"
                      value="REJECT"
                      checked={modalAction === "REJECT"}
                      onChange={() => setModalAction("REJECT")}
                      className="text-red-600 focus:ring-red-500"
                    />
                    <div>
                      <span className="text-xs font-bold text-red-700 block">
                        Reject Document
                      </span>
                      <span className="text-[11px] text-slate-500 block">
                        Mark document invalid or fraudulent (Mandatory justification required).
                      </span>
                    </div>
                  </label>

                  <label className="flex items-center space-x-2.5 p-3 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer">
                    <input
                      type="radio"
                      name="modalAction"
                      value="REQUEST_CLARIFICATION"
                      checked={modalAction === "REQUEST_CLARIFICATION"}
                      onChange={() => setModalAction("REQUEST_CLARIFICATION")}
                      className="text-orange-600 focus:ring-orange-500"
                    />
                    <div>
                      <span className="text-xs font-bold text-orange-700 block">
                        Request Clarification
                      </span>
                      <span className="text-[11px] text-slate-500 block">
                        Request applicant re-upload or provide clear documentation (Mandatory justification required).
                      </span>
                    </div>
                  </label>
                </div>
              </div>

              {(modalAction === "REJECT" || modalAction === "REQUEST_CLARIFICATION") && (
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                    Mandatory Justification Reason <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    required
                    rows={3}
                    value={modalReason}
                    onChange={(e) => setModalReason(e.target.value)}
                    placeholder="Provide specific, evidence-grounded justification for rejection or clarification..."
                    className="w-full text-xs p-2.5 border border-slate-300 rounded-lg focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                  Administrative Notes (Optional)
                </label>
                <textarea
                  rows={2}
                  value={modalNotes}
                  onChange={(e) => setModalNotes(e.target.value)}
                  placeholder="Optional internal review notes..."
                  className="w-full text-xs p-2.5 border border-slate-300 rounded-lg focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>

              <div className="pt-2 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={closeModal}
                  disabled={submitting}
                  className="px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition-colors disabled:opacity-50"
                >
                  {submitting ? "Recording Determination..." : "Confirm & Record Action"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
