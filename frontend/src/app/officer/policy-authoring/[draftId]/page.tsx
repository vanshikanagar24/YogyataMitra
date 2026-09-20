"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  FileCode2,
  Sliders,
  CheckCircle,
  FlaskConical,
  GitCompare,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Clock,
  UserCheck,
  ExternalLink,
  Layers,
  History,
  Info,
  Calendar,
  Sparkles,
} from "lucide-react";
import { useOfficerAuth } from "@/context/OfficerAuthContext";
import { policyAuthoringApi } from "@/api/policyAuthoring";
import { PolicyDraftDetail } from "@/types/policyAuthoring";
import { DraftStatusBadge, ValidationStatusBadge, TestStatusBadge } from "@/components/policy-authoring/DraftStatusBadge";
import { LifecycleStepper } from "@/components/policy-authoring/LifecycleStepper";
import { DraftSubNav } from "@/components/policy-authoring/DraftSubNav";

export default function PolicyDraftDossierPage() {
  const { isAuthenticated, isLoading: authLoading, token, officer } = useOfficerAuth();
  const params = useParams();
  const router = useRouter();
  const draftId = params.draftId as string;

  const [draft, setDraft] = useState<PolicyDraftDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
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
    } catch (err: any) {
      setError(err?.message || "Failed to load policy draft details.");
    } finally {
      setLoading(false);
    }
  }, [draftId, token]);

  useEffect(() => {
    if (isAuthenticated && token && draftId) {
      fetchDraft();
    }
  }, [isAuthenticated, token, draftId, fetchDraft]);

  const handleCompile = async () => {
    if (!token || !draftId) return;
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await policyAuthoringApi.compileDraft(draftId, token);
      setSuccessMsg(`Policy successfully compiled! SHA-256 Hash: ${res.rule_hash}`);
      fetchDraft();
    } catch (err: any) {
      setError(err?.message || "Compilation failed. Ensure rules pass static AST validation first.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleValidate = async () => {
    if (!token || !draftId) return;
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await policyAuthoringApi.validateDraft(draftId, token);
      if (res.is_valid) {
        setSuccessMsg("AST validation passed! Zero errors detected.");
      } else {
        setError(`AST validation failed with ${res.errors.length} error(s).`);
      }
      fetchDraft();
    } catch (err: any) {
      setError(err?.message || "Validation failed.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-500 mb-2" />
        <p className="text-sm">Loading policy draft dossier...</p>
      </div>
    );
  }

  if (error && !draft) {
    return (
      <div className="space-y-4">
        <Link
          href="/officer/policy-authoring"
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Queue</span>
        </Link>
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-xs">
          {error}
        </div>
      </div>
    );
  }

  if (!draft) return null;

  const rules = draft.authored_rules_json?.rules || [];

  return (
    <div className="space-y-6">
      {/* Top Banner Notice: STAGED IS NOT ACTIVE */}
      <div className="bg-amber-500/10 border-l-4 border-amber-500 p-4 rounded-r-lg shadow-sm">
        <div className="flex items-start space-x-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-slate-800 space-y-1">
            <p className="font-bold text-amber-900 tracking-wide uppercase text-[11px]">
              CONTROLLED POLICY ENVIRONMENT • STAGED IS NOT ACTIVE
            </p>
            <p className="text-slate-600">
              This draft is managed in an isolated quarantine environment. Staging prepares the policy for future release protocols.
              Citizen eligibility calculations and active statutory versions remain 100% frozen.
            </p>
          </div>
        </div>
      </div>

      {/* Breadcrumb & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="space-y-1">
          <Link
            href="/officer/policy-authoring"
            className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Policy Authoring Queue</span>
          </Link>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
            <FileCode2 className="w-6 h-6 text-blue-600" />
            <span>{draft.policy_title}</span>
          </h1>
          <div className="text-xs text-slate-500 flex items-center space-x-2">
            <span className="font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
              {draft.scheme_code}
            </span>
            <span>•</span>
            <span>Author: <strong>{draft.author_id}</strong> ({draft.author_role})</span>
            <span>•</span>
            <span>Created: {new Date(draft.created_at).toLocaleDateString()}</span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={fetchDraft}
            disabled={loading || actionLoading}
            className="px-2.5 py-1.5 text-xs font-semibold text-slate-600 bg-white border border-slate-300 rounded hover:bg-slate-50 shadow-sm"
            title="Refresh Draft"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>

          <Link
            href={`/officer/policy-authoring/${draft.id}/rules`}
            className="px-3 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded shadow-sm flex items-center space-x-1.5 transition-colors"
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Rule Builder</span>
          </Link>

          <button
            onClick={handleValidate}
            disabled={actionLoading}
            className="px-3 py-1.5 text-xs font-semibold text-teal-700 bg-teal-50 border border-teal-300 hover:bg-teal-100 rounded shadow-sm flex items-center space-x-1.5 transition-colors"
          >
            <CheckCircle className="w-3.5 h-3.5" />
            <span>Run AST Validation</span>
          </button>

          <button
            onClick={handleCompile}
            disabled={actionLoading}
            className="px-3 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-300 hover:bg-indigo-100 rounded shadow-sm flex items-center space-x-1.5 transition-colors"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Compile & Hash</span>
          </button>

          <Link
            href={`/officer/policy-authoring/${draft.id}/review`}
            className="px-3 py-1.5 text-xs font-bold text-amber-900 bg-amber-100 border border-amber-300 hover:bg-amber-200 rounded shadow-sm flex items-center space-x-1.5 transition-colors"
          >
            <UserCheck className="w-3.5 h-3.5" />
            <span>Supervisory Review</span>
          </Link>
        </div>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-lg text-xs flex items-center justify-between shadow-sm">
          <span>{successMsg}</span>
          <button
            onClick={() => setSuccessMsg(null)}
            className="font-bold underline ml-2 hover:text-emerald-950"
          >
            Dismiss
          </button>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-xs flex items-center justify-between shadow-sm">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="font-bold underline ml-2 hover:text-red-950"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* 10-state Lifecycle Stepper */}
      <LifecycleStepper currentStatus={draft.lifecycle_status} />

      {/* Sub-nav tabs */}
      <DraftSubNav draftId={draft.id} />

      {/* Metadata & Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Card 1: Lifecycle & Hash */}
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Lifecycle & Compilation
          </h3>

          <div className="space-y-2 text-xs">
            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-500">Current Status:</span>
              <DraftStatusBadge status={draft.lifecycle_status} />
            </div>

            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-500">AST Validation:</span>
              <ValidationStatusBadge status={draft.validation_status} />
            </div>

            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-500">Deterministic Tests:</span>
              <TestStatusBadge status={draft.test_status} />
            </div>

            <div className="py-1">
              <span className="text-slate-500 block mb-1">Compiled Rule SHA-256:</span>
              {draft.rule_hash ? (
                <div className="font-mono text-[11px] bg-indigo-50 text-indigo-800 p-2 rounded border border-indigo-200 break-all">
                  {draft.rule_hash}
                </div>
              ) : (
                <div className="text-[11px] text-slate-400 italic bg-slate-50 p-2 rounded border border-slate-200">
                  Not yet compiled into canonical form.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Card 2: Statutory Temporality & Intent */}
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Statutory Scope & Temporality
          </h3>

          <div className="space-y-2 text-xs">
            <div>
              <span className="text-slate-500 block mb-1">Scope & Legislative Intent:</span>
              <p className="text-slate-800 bg-slate-50 p-2.5 rounded border border-slate-200 leading-relaxed text-[11px]">
                {draft.description}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-1">
              <div className="bg-slate-50 p-2 rounded border border-slate-200">
                <span className="text-slate-400 text-[10px] block uppercase font-bold">Effective From</span>
                <span className="font-semibold text-slate-800 text-xs">
                  {draft.effective_from || "Statutory Default"}
                </span>
              </div>
              <div className="bg-slate-50 p-2 rounded border border-slate-200">
                <span className="text-slate-400 text-[10px] block uppercase font-bold">Effective To</span>
                <span className="font-semibold text-slate-800 text-xs">
                  {draft.effective_to || "Indefinite"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Card 3: Provenance & Candidate Linkage */}
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center justify-between">
            <span>Provenance Linkage</span>
            {draft.source_candidate_id && (
              <span className="text-cyan-600 flex items-center space-x-1 text-[10px]">
                <Sparkles className="w-3 h-3" />
                <span>AI Discovery</span>
              </span>
            )}
          </h3>

          <div className="space-y-2 text-xs">
            {draft.source_candidate_id ? (
              <>
                <div>
                  <span className="text-slate-500 text-[11px]">Derived From Candidate:</span>
                  <div className="font-semibold text-slate-900 text-xs mt-0.5">
                    {draft.source_title || "Official Discovery Candidate"}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Publisher: {draft.source_publisher || "Government of India"}
                  </div>
                </div>

                {draft.source_excerpt && (
                  <div>
                    <span className="text-slate-500 text-[10px] uppercase font-bold block mb-1">Gazette Excerpt</span>
                    <p className="italic text-[11px] text-slate-600 bg-slate-50 p-2 rounded border border-slate-200 line-clamp-3">
                      "{draft.source_excerpt}"
                    </p>
                  </div>
                )}

                {draft.source_url && (
                  <a
                    href={draft.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center space-x-1 text-blue-600 hover:text-blue-800 font-semibold text-[11px]"
                  >
                    <span>View Gazette Source</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </>
            ) : (
              <div className="p-4 text-center text-slate-400 bg-slate-50 rounded border border-dashed border-slate-200">
                <FileCode2 className="w-6 h-6 mx-auto mb-1 text-slate-300" />
                <p className="text-[11px]">Authored directly from statutory manual specification.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Rules Snapshot & Audit Trail Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Authored Rules Preview */}
        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Authored Rule AST Specification</h3>
              <p className="text-xs text-slate-500">
                Currently configured rules ({rules.length} rule{rules.length === 1 ? "" : "s"})
              </p>
            </div>
            <Link
              href={`/officer/policy-authoring/${draft.id}/rules`}
              className="text-xs font-bold text-blue-600 hover:text-blue-800 flex items-center space-x-1"
            >
              <span>Edit Rules in Builder</span>
              <Sliders className="w-3.5 h-3.5" />
            </Link>
          </div>

          {rules.length === 0 ? (
            <div className="p-8 text-center border-2 border-dashed border-slate-200 rounded-lg">
              <Sliders className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-xs font-semibold text-slate-700">No Rules Authored Yet</p>
              <p className="text-[11px] text-slate-500 mt-1 max-w-xs mx-auto">
                Open the Rule Builder to add statutory eligibility conditions, limits, or exclusion criteria.
              </p>
              <Link
                href={`/officer/policy-authoring/${draft.id}/rules`}
                className="mt-3 inline-block px-3 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded shadow-sm transition-colors"
              >
                Launch Rule Builder
              </Link>
            </div>
          ) : (
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {rules.map((rule: any, idx: number) => (
                <div
                  key={rule.rule_id || idx}
                  className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-800 font-mono text-[11px]">
                      {rule.rule_id}
                    </span>
                    <span className="px-1.5 py-0.2 text-[10px] font-semibold rounded bg-blue-100 text-blue-800">
                      {rule.operator || "EQUALS"}
                    </span>
                  </div>
                  <div className="text-slate-600 font-medium">
                    {rule.name_en || rule.description_en || "Condition rule"}
                  </div>
                  <div className="text-[11px] text-slate-500 font-mono">
                    Path: {rule.field_path || "custom"} | Target: {JSON.stringify(rule.target_value ?? rule.threshold)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Audit Trail Timeline */}
        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm space-y-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
              <History className="w-4 h-4 text-slate-500" />
              <span>Application-level append-only audit trail protected by authorization</span>
            </h3>
            <p className="text-xs text-slate-500">
              Chronological record of authoring actions, validations, and transitions
            </p>
          </div>

          <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
            {draft.audit_events && draft.audit_events.length > 0 ? (
              draft.audit_events.map((ev) => (
                <div
                  key={ev.id}
                  className="p-3 rounded-lg border border-slate-200 bg-slate-50 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 font-mono text-[11px]">
                      {ev.action}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {new Date(ev.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="text-slate-600 text-[11px]">
                    Actor: <strong>{ev.actor_identity}</strong> ({ev.actor_role})
                  </div>
                  <div className="text-slate-700 bg-white p-2 rounded border border-slate-200 text-[11px]">
                    Reason: <em>"{ev.reason}"</em>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400 italic">No audit events recorded yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
