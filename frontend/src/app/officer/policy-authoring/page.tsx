"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  FileCode2,
  PlusCircle,
  Search,
  Filter,
  Shield,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Layers,
  ChevronRight,
  RefreshCw,
  GitBranch,
  Sliders,
  CheckCircle,
  FlaskConical,
} from "lucide-react";
import { useOfficerAuth } from "@/context/OfficerAuthContext";
import { policyAuthoringApi } from "@/api/policyAuthoring";
import { PolicyDraftItem, PolicyDraftQueueMetrics } from "@/types/policyAuthoring";
import { DraftStatusBadge, ValidationStatusBadge, TestStatusBadge } from "@/components/policy-authoring/DraftStatusBadge";

export default function PolicyAuthoringQueuePage() {
  const { isAuthenticated, isLoading: authLoading, token, officer } = useOfficerAuth();
  const router = useRouter();

  const [drafts, setDrafts] = useState<PolicyDraftItem[]>([]);
  const [metrics, setMetrics] = useState<PolicyDraftQueueMetrics>({
    total_drafts: 0,
    draft_status_count: 0,
    authoring: 0,
    validating: 0,
    testing: 0,
    pending_review: 0,
    in_review: 0,
    needs_clarification: 0,
    staged: 0,
    archived: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState("ALL");
  const [schemeFilter, setSchemeFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  // Auth guard
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/officer/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const fetchDrafts = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);

    try {
      const data = await policyAuthoringApi.listDrafts(
        {
          status: statusFilter,
          scheme: schemeFilter,
          search: searchQuery.trim() || undefined,
        },
        token
      );
      setDrafts(data.drafts || []);
      if (data.metrics) {
        setMetrics(data.metrics);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load policy drafts.");
    } finally {
      setLoading(false);
    }
  }, [token, statusFilter, schemeFilter, searchQuery]);

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchDrafts();
    }
  }, [isAuthenticated, token, fetchDrafts]);

  return (
    <div className="space-y-6">
      {/* Top Banner Notice: STAGED IS NOT ACTIVE */}
      <div className="bg-amber-500/10 border-l-4 border-amber-500 p-4 rounded-r-lg shadow-sm">
        <div className="flex items-start space-x-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-slate-800 space-y-1">
            <p className="font-bold text-amber-900 tracking-wide uppercase text-[11px]">
              CONTROLLED POLICY AUTHORING & DETERMINISTIC COMPILATION • STAGED IS NOT ACTIVE
            </p>
            <p className="text-slate-600">
              Authored rules are compiled into canonical AST structures and validated using deterministic evaluation.
              Policies staged in this environment are quarantined for supervisory review and cannot execute in public
              citizen evaluations until separate release protocol approval.
            </p>
          </div>
        </div>
      </div>

      {/* Header & Create Button */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
            <FileCode2 className="w-6 h-6 text-blue-600" />
            <span>Policy Authoring Queue</span>
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Author statutory rule ASTs, run deterministic compiler checks, and execute regression test suites.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => fetchDrafts()}
            disabled={loading}
            className="px-3 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 flex items-center space-x-1.5 shadow-sm transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>

          <Link
            href="/officer/policy-authoring/new"
            className="px-4 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm flex items-center space-x-2 transition-colors"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Create New Draft</span>
          </Link>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Total Drafts
          </div>
          <div className="text-2xl font-black text-slate-900 mt-1">
            {metrics.total_drafts}
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold text-blue-600 uppercase tracking-wider">
            In Authoring
          </div>
          <div className="text-2xl font-black text-blue-700 mt-1">
            {metrics.authoring + metrics.draft_status_count}
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold text-teal-600 uppercase tracking-wider">
            AST Validated
          </div>
          <div className="text-2xl font-black text-teal-700 mt-1">
            {metrics.validating}
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold text-amber-600 uppercase tracking-wider">
            Review Pending
          </div>
          <div className="text-2xl font-black text-amber-700 mt-1">
            {metrics.pending_review}
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-purple-200 bg-purple-50/50 shadow-sm">
          <div className="text-xs font-semibold text-purple-700 uppercase tracking-wider">
            Staged (Quarantine)
          </div>
          <div className="text-2xl font-black text-purple-900 mt-1">
            {metrics.staged}
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
          {/* Status Filter */}
          <div className="flex items-center space-x-1.5 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-semibold text-slate-600">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-50 border border-slate-300 rounded px-2.5 py-1 text-xs text-slate-800 font-medium focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="DRAFT_CREATION">Draft Creation</option>
              <option value="CANDIDATE_IMPORTED">Candidate Imported</option>
              <option value="HUMAN_EDITING">Human Editing</option>
              <option value="AST_VALIDATED">AST Validated</option>
              <option value="COMPILED">Compiled</option>
              <option value="TEST_GENERATED">Tests Generated</option>
              <option value="REGRESSION_VALIDATED">Regression Validated</option>
              <option value="REVIEW_PENDING">Review Pending</option>
              <option value="REVISED">Revised</option>
              <option value="STAGED">Staged</option>
            </select>
          </div>

          {/* Scheme Filter */}
          <div className="flex items-center space-x-1.5 text-xs">
            <span className="font-semibold text-slate-600">Scheme:</span>
            <select
              value={schemeFilter}
              onChange={(e) => setSchemeFilter(e.target.value)}
              className="bg-slate-50 border border-slate-300 rounded px-2.5 py-1 text-xs text-slate-800 font-medium focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="ALL">All Schemes</option>
              <option value="PM_KISAN">PM-KISAN</option>
              <option value="SSY">Sukanya Samriddhi Yojana (SSY)</option>
            </select>
          </div>
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search drafts by title..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 bg-slate-50"
          />
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-xs flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={() => fetchDrafts()}
            className="font-bold underline ml-2 hover:text-red-900"
          >
            Try Again
          </button>
        </div>
      )}

      {/* Drafts List Table */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-500 mb-2" />
            <p className="text-sm">Loading policy authoring drafts...</p>
          </div>
        ) : drafts.length === 0 ? (
          <div className="p-12 text-center">
            <FileCode2 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-sm font-bold text-slate-700 mb-1">
              No Policy Drafts Found
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mb-4">
              No policy authoring drafts match your selected filters. Create a new draft or import from an approved discovery candidate.
            </p>
            <Link
              href="/officer/policy-authoring/new"
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-sm"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Author New Draft</span>
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">Scheme & Title</th>
                  <th className="py-3 px-4">Lifecycle Status</th>
                  <th className="py-3 px-4">Static AST</th>
                  <th className="py-3 px-4">Test Suite</th>
                  <th className="py-3 px-4">Rule Hash (SHA-256)</th>
                  <th className="py-3 px-4">Author & Updated</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {drafts.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-slate-900">{d.policy_title}</span>
                        {d.source_candidate_id && (
                          <span className="bg-cyan-50 text-cyan-700 border border-cyan-200 px-1.5 py-0.5 rounded text-[10px] font-semibold">
                            Imported
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5 flex items-center space-x-2">
                        <span className="font-semibold text-blue-600">
                          {d.scheme_code || "UNKNOWN"}
                        </span>
                        <span>•</span>
                        <span className="truncate max-w-xs">{d.description}</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <DraftStatusBadge status={d.lifecycle_status} />
                    </td>

                    <td className="py-3.5 px-4">
                      <ValidationStatusBadge status={d.validation_status} />
                    </td>

                    <td className="py-3.5 px-4">
                      <TestStatusBadge status={d.test_status} />
                    </td>

                    <td className="py-3.5 px-4">
                      {d.rule_hash ? (
                        <div className="font-mono text-[11px] text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded inline-block max-w-[130px] truncate" title={d.rule_hash}>
                          {d.rule_hash.substring(0, 12)}...
                        </div>
                      ) : (
                        <span className="text-[11px] text-slate-400 italic">Uncompiled</span>
                      )}
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="font-medium text-slate-800">{d.author_id}</div>
                      <div className="text-[11px] text-slate-400">
                        {new Date(d.updated_at).toLocaleDateString()}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end space-x-2">
                        <Link
                          href={`/officer/policy-authoring/${d.id}`}
                          className="px-2.5 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-50 rounded border border-blue-200 transition-colors"
                        >
                          Dossier
                        </Link>
                        <Link
                          href={`/officer/policy-authoring/${d.id}/rules`}
                          className="px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded border border-slate-200 transition-colors"
                          title="Rule Builder"
                        >
                          <Sliders className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
