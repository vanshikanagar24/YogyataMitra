"use client";

import React from "react";
import { Cpu, CheckCircle2, XCircle, AlertCircle, Shield, Hash, Clock } from "lucide-react";
import { useCase } from "../CaseContext";

export default function CaseAssessmentPage() {
  const { caseData, loading } = useCase();

  if (loading || !caseData) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500 text-sm">
        Loading automated statutory assessment...
      </div>
    );
  }

  const assessment = caseData.automated_assessment;

  if (!assessment) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500 text-xs">
        No automated statutory evaluation trace has been recorded for this case yet.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Assessment Summary Banner */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center space-x-2">
              <Cpu className="w-5 h-5 text-blue-600" />
              <h2 className="text-base font-bold text-slate-900 tracking-tight">
                Deterministic Statutory Evaluation
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Automated execution against the statutory Kleene-logic evaluation engine.
            </p>
          </div>

          <div>
            {assessment.determination === "ELIGIBLE" ? (
              <span className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-green-100 text-green-800 border border-green-300">
                <CheckCircle2 className="w-4 h-4 text-green-600" />
                <span>DETERMINATION: ELIGIBLE</span>
              </span>
            ) : assessment.determination === "INELIGIBLE" ? (
              <span className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-red-100 text-red-800 border border-red-300">
                <XCircle className="w-4 h-4 text-red-600" />
                <span>DETERMINATION: INELIGIBLE</span>
              </span>
            ) : (
              <span className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
                <AlertCircle className="w-4 h-4 text-amber-600" />
                <span>DETERMINATION: INSUFFICIENT INFO</span>
              </span>
            )}
          </div>
        </div>

        {/* Technical Provenance Metrics */}
        <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div>
            <span className="text-slate-500 block">Evaluated At:</span>
            <span className="font-semibold text-slate-800">
              {assessment.evaluated_at
                ? new Date(assessment.evaluated_at).toLocaleString("en-IN")
                : "N/A"}
            </span>
          </div>

          <div>
            <span className="text-slate-500 block">Policy Version:</span>
            <span className="font-mono font-semibold text-slate-800">
              {assessment.ruleset_version || "1.0"}
            </span>
          </div>

          <div>
            <span className="text-slate-500 block">Execution Trace ID:</span>
            <span className="font-mono text-slate-800 text-[11px] break-all">
              {assessment.evaluation_id || "N/A"}
            </span>
          </div>
        </div>

        {/* Ruleset Content Hash */}
        {assessment.ruleset_hash && (
          <div className="p-3 bg-slate-900 text-slate-300 rounded-lg text-xs flex items-center space-x-2.5 overflow-x-auto">
            <Hash className="w-4 h-4 text-blue-400 flex-shrink-0" />
            <div className="font-mono text-[11px]">
              <span className="text-slate-400">Canonical SHA-256 Rule Hash: </span>
              <span className="text-blue-300 font-bold">{assessment.ruleset_hash}</span>
            </div>
          </div>
        )}
      </div>

      {/* Disqualifiers / Blockers if any */}
      {assessment.disqualifiers && assessment.disqualifiers.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-5 space-y-2">
          <div className="flex items-center space-x-2 text-red-900 font-bold text-xs uppercase tracking-wide">
            <XCircle className="w-4 h-4 text-red-600" />
            <span>Statutory Disqualifying Factors ({assessment.disqualifiers.length})</span>
          </div>
          <ul className="list-disc list-inside text-xs text-red-800 space-y-1 pl-1">
            {assessment.disqualifiers.map((disq, i) => (
              <li key={i}>{disq}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Missing Facts if any */}
      {assessment.missing_facts && assessment.missing_facts.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 space-y-2">
          <div className="flex items-center space-x-2 text-amber-900 font-bold text-xs uppercase tracking-wide">
            <AlertCircle className="w-4 h-4 text-amber-600" />
            <span>Missing Statutory Facts ({assessment.missing_facts.length})</span>
          </div>
          <p className="text-xs text-amber-800">
            The deterministic engine requires the following facts before a definitive eligibility outcome can be finalized:
          </p>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {assessment.missing_facts.map((mf, i) => (
              <span
                key={i}
                className="font-mono text-[11px] bg-white px-2 py-0.5 rounded border border-amber-300 text-amber-900"
              >
                {mf}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Evaluated Rules Breakdown */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200">
          <h3 className="text-base font-bold text-slate-900 tracking-tight">
            Statutory Rules Evaluation Breakdown ({assessment.rules_evaluated.length})
          </h3>
          <p className="text-xs text-slate-500">
            Deterministic evaluation of individual scheme eligibility rules and exclusion clauses.
          </p>
        </div>

        <div className="divide-y divide-slate-100">
          {assessment.rules_evaluated.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-xs">
              No individual rule breakdowns recorded in this evaluation trace.
            </div>
          ) : (
            assessment.rules_evaluated.map((rule) => (
              <div
                key={rule.rule_id}
                className="p-4 hover:bg-slate-50/70 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="space-y-0.5">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">
                      {rule.rule_id}
                    </span>
                    <span className="text-sm font-semibold text-slate-900">
                      {rule.rule_name}
                    </span>
                  </div>
                  {rule.description && (
                    <p className="text-xs text-slate-500">{rule.description}</p>
                  )}
                  {rule.details && (
                    <p className="text-xs text-slate-600 italic mt-1">
                      Reason: {rule.details}
                    </p>
                  )}
                </div>

                <div className="self-start sm:self-auto">
                  {rule.result === "PASS" ? (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-green-100 text-green-800 border border-green-200">
                      PASS
                    </span>
                  ) : rule.result === "FAIL" ? (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-red-100 text-red-800 border border-red-200">
                      FAIL
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-slate-100 text-slate-600 border border-slate-200">
                      UNKNOWN
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
