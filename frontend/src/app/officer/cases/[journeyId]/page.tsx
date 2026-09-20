"use client";

import React from "react";
import Link from "next/link";
import { FileText, Shield, CheckCircle2, AlertCircle, ArrowRight, UserCheck } from "lucide-react";
import { useCase } from "./CaseContext";

export default function CaseOverviewPage() {
  const { caseData, loading, journeyId } = useCase();

  if (loading || !caseData) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500 text-sm">
        Loading case claims and factual dossier...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Case Summary Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-4">
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
            <span className="text-slate-500 block">Lifecycle Journey State:</span>
            <span className="font-semibold text-slate-900">
              {caseData.journey_state}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block">Review Determination:</span>
            <span className="font-semibold text-slate-900">
              {caseData.review_decision || "Pending Decision"}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block">Active Reviewer:</span>
            <span className="font-semibold text-slate-900">
              {caseData.reviewer_identity !== "UNASSIGNED"
                ? `${caseData.reviewer_identity} (${caseData.reviewer_role})`
                : "Unassigned"}
            </span>
          </div>
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

      {/* Action Footer Callouts */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link
          href={`/officer/cases/${journeyId}/evidence`}
          className="p-4 bg-white rounded-xl border border-slate-200 hover:border-blue-500 hover:bg-blue-50/20 transition-all shadow-sm flex items-center justify-between group"
        >
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Next Verification Step
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
              Determination Step
            </div>
            <div className="text-sm font-bold text-slate-900 group-hover:text-purple-600 transition-colors mt-0.5">
              Record Official Determination
            </div>
          </div>
          <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-purple-600 group-hover:translate-x-0.5 transition-all" />
        </Link>
      </div>
    </div>
  );
}
