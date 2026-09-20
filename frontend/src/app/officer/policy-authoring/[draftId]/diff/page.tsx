"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  GitCompare,
  PlusCircle,
  MinusCircle,
  Edit3,
  RefreshCw,
  Layers,
  FileCode2,
  Calendar,
  AlertTriangle,
} from "lucide-react";
import { useOfficerAuth } from "@/context/OfficerAuthContext";
import { policyAuthoringApi } from "@/api/policyAuthoring";
import { PolicyDraftDetail, PolicyDiffResponse } from "@/types/policyAuthoring";
import { DraftSubNav } from "@/components/policy-authoring/DraftSubNav";

export default function PolicyDiffViewerPage() {
  const { isAuthenticated, isLoading: authLoading, token } = useOfficerAuth();
  const params = useParams();
  const router = useRouter();
  const draftId = params.draftId as string;

  const [draft, setDraft] = useState<PolicyDraftDetail | null>(null);
  const [diff, setDiff] = useState<PolicyDiffResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/officer/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const loadData = useCallback(async () => {
    if (!token || !draftId) return;
    setLoading(true);
    setError(null);

    try {
      const [draftData, diffData] = await Promise.all([
        policyAuthoringApi.getDraft(draftId, token),
        policyAuthoringApi.getDiff(draftId, token),
      ]);
      setDraft(draftData);
      setDiff(diffData);
    } catch (err: any) {
      setError(err?.message || "Failed to load policy diff.");
    } finally {
      setLoading(false);
    }
  }, [draftId, token]);

  useEffect(() => {
    if (isAuthenticated && token && draftId) {
      loadData();
    }
  }, [isAuthenticated, token, draftId, loadData]);

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-500 mb-2" />
        <p className="text-sm">Comparing against baseline policy version...</p>
      </div>
    );
  }

  if (!draft) return null;

  const added = diff?.added_rules || [];
  const removed = diff?.removed_rules || [];
  const modified = diff?.modified_rules || [];
  const metadataChanges = diff?.metadata_changes || [];

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
        <span className="text-xs text-slate-500">
          Baseline Version: <strong className="text-blue-700">{diff?.parent_version_code || "Active Statutory Policy"}</strong>
        </span>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
            <GitCompare className="w-6 h-6 text-indigo-600" />
            <span>Visual Policy Differential</span>
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Structural AST and semantic comparison between baseline statutory policy and draft rules.
          </p>
        </div>

        <button
          onClick={loadData}
          className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded hover:bg-slate-50 shadow-sm flex items-center space-x-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Diff</span>
        </button>
      </div>

      {/* SubNav */}
      <DraftSubNav draftId={draft.id} />

      {/* Error alert */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-xs">
          {error}
        </div>
      )}

      {/* Hash comparison card */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-1">
          <span className="text-[10px] uppercase font-bold text-slate-500 block">
            Baseline Version Hash ({diff?.parent_version_code || "Active"})
          </span>
          <div className="font-mono text-[11px] text-slate-700 break-all bg-white p-2 rounded border border-slate-200">
            {diff?.parent_rule_hash || "No parent baseline hash"}
          </div>
        </div>

        <div className="p-3 bg-indigo-50/60 rounded border border-indigo-200 space-y-1">
          <span className="text-[10px] uppercase font-bold text-indigo-800 block">
            Target Authored Draft Hash
          </span>
          <div className="font-mono text-[11px] text-indigo-900 break-all bg-white p-2 rounded border border-indigo-200">
            {diff?.draft_rule_hash || draft.rule_hash || "Uncompiled draft"}
          </div>
        </div>
      </div>

      {/* Diff Metrics */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white p-3.5 rounded-lg border border-emerald-200 bg-emerald-50/30 shadow-sm">
          <div className="text-xs font-semibold text-emerald-700 uppercase tracking-wider flex items-center space-x-1">
            <PlusCircle className="w-4 h-4" />
            <span>Rules Added</span>
          </div>
          <div className="text-2xl font-black text-emerald-800 mt-1">{added.length}</div>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-rose-200 bg-rose-50/30 shadow-sm">
          <div className="text-xs font-semibold text-rose-700 uppercase tracking-wider flex items-center space-x-1">
            <MinusCircle className="w-4 h-4" />
            <span>Rules Removed</span>
          </div>
          <div className="text-2xl font-black text-rose-800 mt-1">{removed.length}</div>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-amber-200 bg-amber-50/30 shadow-sm">
          <div className="text-xs font-semibold text-amber-700 uppercase tracking-wider flex items-center space-x-1">
            <Edit3 className="w-4 h-4" />
            <span>Rules Modified</span>
          </div>
          <div className="text-2xl font-black text-amber-800 mt-1">{modified.length}</div>
        </div>
      </div>

      {/* Human Summary */}
      {diff?.human_summary && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 shadow-sm text-xs text-blue-950 space-y-1">
          <span className="font-bold text-[11px] uppercase tracking-wider text-blue-900 block">
            Statutory Differential Summary
          </span>
          <p className="leading-relaxed text-blue-900">{diff.human_summary}</p>
        </div>
      )}

      {/* Detailed Diff List */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200">
          <h3 className="text-sm font-bold text-slate-900">
            Rule-Level Structural Variations
          </h3>
        </div>

        {added.length === 0 && removed.length === 0 && modified.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <GitCompare className="w-10 h-10 mx-auto text-slate-300 mb-2" />
            <p className="text-xs font-semibold text-slate-700">No Rule Differences Detected</p>
            <p className="text-[11px] text-slate-500 mt-1">
              Authored rules are identical in structure to the baseline policy.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {/* Added Rules */}
            {added.map((item) => (
              <div key={`add-${item.rule_id}`} className="p-4 bg-emerald-50/40 space-y-1.5 text-xs">
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                    + ADDED
                  </span>
                  <span className="font-mono font-bold text-slate-900">{item.rule_id}</span>
                </div>
                <div className="font-semibold text-slate-800">
                  {item.description_en || "Newly authored statutory rule"}
                </div>
                {item.description_hi && (
                  <div className="text-slate-500 text-[11px]">{item.description_hi}</div>
                )}
                <div className="text-[11px] text-emerald-900 bg-white p-2 rounded border border-emerald-200">
                  {item.human_explanation}
                </div>
              </div>
            ))}

            {/* Modified Rules */}
            {modified.map((item) => (
              <div key={`mod-${item.rule_id}`} className="p-4 bg-amber-50/40 space-y-1.5 text-xs">
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                    ~ MODIFIED
                  </span>
                  <span className="font-mono font-bold text-slate-900">{item.rule_id}</span>
                </div>
                <div className="font-semibold text-slate-800">
                  {item.description_en || "Modified rule criteria"}
                </div>
                {item.description_hi && (
                  <div className="text-slate-500 text-[11px]">{item.description_hi}</div>
                )}
                <div className="text-[11px] text-amber-900 bg-white p-2 rounded border border-amber-200">
                  {item.human_explanation}
                </div>
              </div>
            ))}

            {/* Removed Rules */}
            {removed.map((item) => (
              <div key={`rem-${item.rule_id}`} className="p-4 bg-rose-50/40 space-y-1.5 text-xs">
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300">
                    - REMOVED
                  </span>
                  <span className="font-mono font-bold text-slate-900">{item.rule_id}</span>
                </div>
                <div className="font-semibold text-slate-800 line-through">
                  {item.description_en || "Retired statutory rule"}
                </div>
                <div className="text-[11px] text-rose-900 bg-white p-2 rounded border border-rose-200">
                  {item.human_explanation}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
