"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  RefreshCw,
  ShieldCheck,
  ShieldAlert,
  Sliders,
  FileCheck,
} from "lucide-react";
import { useOfficerAuth } from "@/context/OfficerAuthContext";
import { policyAuthoringApi } from "@/api/policyAuthoring";
import { PolicyDraftDetail, ValidationReportResponse } from "@/types/policyAuthoring";
import { ValidationStatusBadge } from "@/components/policy-authoring/DraftStatusBadge";
import { DraftSubNav } from "@/components/policy-authoring/DraftSubNav";

export default function PolicyValidationPage() {
  const { isAuthenticated, isLoading: authLoading, token } = useOfficerAuth();
  const params = useParams();
  const router = useRouter();
  const draftId = params.draftId as string;

  const [draft, setDraft] = useState<PolicyDraftDetail | null>(null);
  const [report, setReport] = useState<ValidationReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

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
      if (data.validation_details_json) {
        setReport(data.validation_details_json as any);
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

  const handleRunValidation = async () => {
    if (!token || !draftId) return;
    setValidating(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await policyAuthoringApi.validateDraft(draftId, token);
      setReport(res);
      if (res.is_valid) {
        setSuccessMsg("Deterministic static validation passed with 0 errors!");
      } else {
        setError(`Validation detected ${res.errors.length} error(s). Please review findings below.`);
      }
      fetchDraft();
    } catch (err: any) {
      setError(err?.message || "Static validation failed.");
    } finally {
      setValidating(false);
    }
  };

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-500 mb-2" />
        <p className="text-sm">Loading validation report...</p>
      </div>
    );
  }

  if (!draft) return null;

  const errors = report?.errors || [];
  const warnings = report?.warnings || [];
  const infos = report?.info || [];

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          href={`/officer/policy-authoring/${draft.id}`}
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Dossier</span>
        </Link>
        <ValidationStatusBadge status={draft.validation_status} />
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
            <CheckCircle className="w-6 h-6 text-teal-600" />
            <span>Deterministic Static AST Validation</span>
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Static analysis, invariant verification, and syntax safety checks for {draft.policy_title}.
          </p>
        </div>

        <button
          onClick={handleRunValidation}
          disabled={validating}
          className="px-4 py-2 text-xs font-bold text-white bg-teal-600 hover:bg-teal-700 rounded-lg shadow-sm flex items-center space-x-1.5 transition-colors disabled:opacity-50"
        >
          {validating ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <ShieldCheck className="w-3.5 h-3.5" />
          )}
          <span>Run Static Validation</span>
        </button>
      </div>

      {/* SubNav */}
      <DraftSubNav draftId={draft.id} />

      {/* Alerts */}
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

      {/* Overview Metrics Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Overall Result
          </div>
          <div className="mt-1 flex items-center space-x-2">
            {report?.is_valid ? (
              <span className="text-xl font-bold text-emerald-600 flex items-center space-x-1">
                <CheckCircle className="w-5 h-5" />
                <span>VALID</span>
              </span>
            ) : report ? (
              <span className="text-xl font-bold text-rose-600 flex items-center space-x-1">
                <XCircle className="w-5 h-5" />
                <span>INVALID</span>
              </span>
            ) : (
              <span className="text-xl font-bold text-slate-400">UNTESTED</span>
            )}
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold text-rose-600 uppercase tracking-wider">
            Critical Errors
          </div>
          <div className="text-2xl font-black text-rose-700 mt-1">{errors.length}</div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold text-amber-600 uppercase tracking-wider">
            Warnings
          </div>
          <div className="text-2xl font-black text-amber-700 mt-1">{warnings.length}</div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold text-blue-600 uppercase tracking-wider">
            Rules Analyzed
          </div>
          <div className="text-2xl font-black text-slate-900 mt-1">
            {report?.rule_count ?? (draft.authored_rules_json?.rules?.length || 0)}
          </div>
        </div>
      </div>

      {/* Five Static Check Categories */}
      <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Statutory Verification Invariants
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
          <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-1">
            <div className="font-bold text-slate-800 flex items-center space-x-1.5">
              <CheckCircle className="w-3.5 h-3.5 text-teal-600" />
              <span>AST Syntax</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Valid operators, allowed evaluation fields, well-formed operands.
            </p>
          </div>

          <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-1">
            <div className="font-bold text-slate-800 flex items-center space-x-1.5">
              <CheckCircle className="w-3.5 h-3.5 text-teal-600" />
              <span>Uniqueness</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Unique rule IDs across the entire scheme ruleset.
            </p>
          </div>

          <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-1">
            <div className="font-bold text-slate-800 flex items-center space-x-1.5">
              <CheckCircle className="w-3.5 h-3.5 text-teal-600" />
              <span>Temporality</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Chronological date invariants (effective_from &lt;= effective_to).
            </p>
          </div>

          <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-1">
            <div className="font-bold text-slate-800 flex items-center space-x-1.5">
              <CheckCircle className="w-3.5 h-3.5 text-teal-600" />
              <span>Field Overlap</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Checks for contradictory or mutually exclusive boundary thresholds.
            </p>
          </div>

          <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-1">
            <div className="font-bold text-slate-800 flex items-center space-x-1.5">
              <CheckCircle className="w-3.5 h-3.5 text-teal-600" />
              <span>Code Safety</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Zero executable or malicious code injections permitted.
            </p>
          </div>
        </div>
      </div>

      {/* Detailed Findings List */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-5 space-y-4">
        <h3 className="text-sm font-bold text-slate-900">
          Validation Findings & Diagnostic Log
        </h3>

        {!report ? (
          <div className="p-8 text-center text-slate-400">
            <FileCheck className="w-10 h-10 mx-auto text-slate-300 mb-2" />
            <p className="text-xs">No validation runs recorded for this draft yet.</p>
            <p className="text-[11px] text-slate-500 mt-1">
              Click "Run Static Validation" above to test the authored rules.
            </p>
          </div>
        ) : errors.length === 0 && warnings.length === 0 && infos.length === 0 ? (
          <div className="p-6 text-center bg-emerald-50/50 border border-emerald-200 rounded-lg text-xs space-y-2">
            <CheckCircle className="w-8 h-8 text-emerald-600 mx-auto" />
            <p className="font-bold text-emerald-900 text-sm">
              Zero Static Invariant Violations Detected
            </p>
            <p className="text-slate-600 max-w-sm mx-auto text-[11px]">
              Authored AST conforms strictly to deterministic schema v2.0 invariants. Ready for compilation.
            </p>
            <Link
              href={`/officer/policy-authoring/${draft.id}`}
              className="mt-2 inline-block px-3 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded shadow-sm"
            >
              Back to Dossier to Compile
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Errors */}
            {errors.map((err, idx) => (
              <div
                key={`err-${idx}`}
                className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs space-y-1 text-red-900"
              >
                <div className="flex items-center space-x-2 font-bold">
                  <XCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
                  <span className="font-mono text-[11px] bg-red-100 px-1.5 py-0.2 rounded border border-red-300">
                    {err.code}
                  </span>
                  <span>{err.message}</span>
                </div>
                {(err.rule_id || err.field_path) && (
                  <div className="text-[11px] text-red-700 pl-6 font-mono">
                    {err.rule_id && <span>Rule ID: {err.rule_id} </span>}
                    {err.field_path && <span>• Field: {err.field_path}</span>}
                  </div>
                )}
              </div>
            ))}

            {/* Warnings */}
            {warnings.map((warn, idx) => (
              <div
                key={`warn-${idx}`}
                className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs space-y-1 text-amber-900"
              >
                <div className="flex items-center space-x-2 font-bold">
                  <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
                  <span className="font-mono text-[11px] bg-amber-100 px-1.5 py-0.2 rounded border border-amber-300">
                    {warn.code}
                  </span>
                  <span>{warn.message}</span>
                </div>
                {(warn.rule_id || warn.field_path) && (
                  <div className="text-[11px] text-amber-700 pl-6 font-mono">
                    {warn.rule_id && <span>Rule ID: {warn.rule_id} </span>}
                    {warn.field_path && <span>• Field: {warn.field_path}</span>}
                  </div>
                )}
              </div>
            ))}

            {/* Infos */}
            {infos.map((inf, idx) => (
              <div
                key={`info-${idx}`}
                className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs space-y-1 text-blue-900"
              >
                <div className="flex items-center space-x-2 font-semibold">
                  <Info className="w-4 h-4 text-blue-600 flex-shrink-0" />
                  <span className="font-mono text-[11px] bg-blue-100 px-1.5 py-0.2 rounded border border-blue-300">
                    {inf.code}
                  </span>
                  <span>{inf.message}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
