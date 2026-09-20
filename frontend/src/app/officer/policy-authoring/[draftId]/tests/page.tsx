"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  FlaskConical,
  Play,
  Sparkles,
  Plus,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  RefreshCw,
  ShieldCheck,
  Code,
  FileCheck2,
} from "lucide-react";
import { useOfficerAuth } from "@/context/OfficerAuthContext";
import { policyAuthoringApi } from "@/api/policyAuthoring";
import {
  PolicyDraftDetail,
  PolicyDraftTestCase,
  PolicyDraftTestCreateRequest,
} from "@/types/policyAuthoring";
import { TestStatusBadge } from "@/components/policy-authoring/DraftStatusBadge";
import { DraftSubNav } from "@/components/policy-authoring/DraftSubNav";

export default function PolicyTestSuitePage() {
  const { isAuthenticated, isLoading: authLoading, token } = useOfficerAuth();
  const params = useParams();
  const router = useRouter();
  const draftId = params.draftId as string;

  const [draft, setDraft] = useState<PolicyDraftDetail | null>(null);
  const [tests, setTests] = useState<PolicyDraftTestCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Add Test Modal
  const [showAddModal, setShowAddModal] = useState(false);
  const [testName, setTestName] = useState("");
  const [testDesc, setTestDesc] = useState("");
  const [testType, setTestType] = useState("MANUAL_HUMAN");
  const [factsInput, setFactsInput] = useState(`{\n  "land_size_hectares": 1.5,\n  "institution_holder": false,\n  "income_tax_payer": false\n}`);
  const [expectedResult, setExpectedResult] = useState<"ELIGIBLE" | "INELIGIBLE" | "UNKNOWN">("ELIGIBLE");

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
      const [draftData, testsData] = await Promise.all([
        policyAuthoringApi.getDraft(draftId, token),
        policyAuthoringApi.listTests(draftId, token),
      ]);
      setDraft(draftData);
      setTests(testsData || []);
    } catch (err: any) {
      setError(err?.message || "Failed to load test suite.");
    } finally {
      setLoading(false);
    }
  }, [draftId, token]);

  useEffect(() => {
    if (isAuthenticated && token && draftId) {
      loadData();
    }
  }, [isAuthenticated, token, draftId, loadData]);

  const handleGenerateTests = async () => {
    if (!token || !draftId) return;
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const generated = await policyAuthoringApi.generateTests(draftId, token);
      setSuccessMsg(`Generated ${generated.length} automated boundary & Strong Kleene test cases!`);
      loadData();
    } catch (err: any) {
      setError(err?.message || "Failed to generate test cases.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRunTests = async () => {
    if (!token || !draftId) return;
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const runSummary = await policyAuthoringApi.runTests(draftId, token);
      setSuccessMsg(
        `Test run complete: ${runSummary.passed_tests} passed, ${runSummary.failed_tests} failed out of ${runSummary.total_tests} tests.`
      );
      loadData();
    } catch (err: any) {
      setError(err?.message || "Failed to execute test suite.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateTest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !draftId) return;

    let parsedFacts = {};
    try {
      parsedFacts = JSON.parse(factsInput);
    } catch {
      setError("Invalid JSON format for facts context.");
      return;
    }

    setActionLoading(true);
    try {
      const payload: PolicyDraftTestCreateRequest = {
        name: testName.trim(),
        description: testDesc.trim() || undefined,
        test_type: testType,
        facts_json: parsedFacts,
        expected_result: expectedResult,
      };

      await policyAuthoringApi.addTest(draftId, payload, token);
      setSuccessMsg("Human test case added successfully.");
      setShowAddModal(false);
      setTestName("");
      setTestDesc("");
      loadData();
    } catch (err: any) {
      setError(err?.message || "Failed to add manual test case.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-500 mb-2" />
        <p className="text-sm">Loading test suite...</p>
      </div>
    );
  }

  if (!draft) return null;

  const passedCount = tests.filter((t) => t.status === "PASSED").length;
  const failedCount = tests.filter((t) => t.status === "FAILED").length;
  const pendingCount = tests.filter((t) => t.status === "PENDING").length;

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
        <TestStatusBadge status={draft.test_status} />
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
            <FlaskConical className="w-6 h-6 text-sky-600" />
            <span>Deterministic Test Suite & Statutory Regression</span>
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Validate boundary conditions, Strong Kleene three-valued logic, and regression against frozen policies.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleGenerateTests}
            disabled={actionLoading}
            className="px-3 py-1.5 text-xs font-bold text-sky-800 bg-sky-100 hover:bg-sky-200 border border-sky-300 rounded shadow-sm flex items-center space-x-1.5 transition-colors disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5 text-sky-600" />
            <span>Auto-Generate Tests</span>
          </button>

          <button
            onClick={() => setShowAddModal(true)}
            className="px-3 py-1.5 text-xs font-bold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded shadow-sm flex items-center space-x-1.5 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>+ Add Manual Test</span>
          </button>

          <button
            onClick={handleRunTests}
            disabled={actionLoading || tests.length === 0}
            className="px-4 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded shadow-sm flex items-center space-x-1.5 transition-colors disabled:opacity-50"
          >
            {actionLoading ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-white" />
            )}
            <span>Run All Tests</span>
          </button>
        </div>
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

      {/* Metrics Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Total Test Cases
          </div>
          <div className="text-2xl font-black text-slate-900 mt-1">{tests.length}</div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">
            Passed
          </div>
          <div className="text-2xl font-black text-emerald-700 mt-1">{passedCount}</div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold text-rose-600 uppercase tracking-wider">
            Failed
          </div>
          <div className="text-2xl font-black text-rose-700 mt-1">{failedCount}</div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Pending Execution
          </div>
          <div className="text-2xl font-black text-slate-500 mt-1">{pendingCount}</div>
        </div>
      </div>

      {/* Statutory Baseline Regression Assurance Card */}
      <div className="bg-emerald-50/70 border border-emerald-300 rounded-lg p-4 shadow-sm space-y-2">
        <div className="flex items-center space-x-2 text-emerald-950 font-bold text-xs uppercase tracking-wide">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>Statutory Baseline Invariance & Regression Safety (6 Frozen Hashes)</span>
        </div>
        <p className="text-xs text-emerald-900 leading-relaxed">
          Test runs execute within an isolated evaluation sandbox. The 6 canonical statutory policies
          (<code>PM_KISAN_2019_ORIGINAL</code>, <code>PM_KISAN_2019_AMENDMENT</code>, <code>PM_KISAN_2020_REVISED</code>,{" "}
          <code>SSY_2014_ORIGINAL</code>, <code>SSY_2016_AMENDMENT</code>, <code>SSY_2018_REVISED</code>)
          remain permanently immutable. Historical evaluation outcomes for existing citizens cannot regress.
        </p>
      </div>

      {/* Tests Table */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900">
            Test Case Specifications ({tests.length})
          </h3>
          <span className="text-xs text-slate-400">Deterministic Evaluator Matrix</span>
        </div>

        {tests.length === 0 ? (
          <div className="p-12 text-center">
            <FlaskConical className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <p className="text-xs font-semibold text-slate-700">No Test Cases Added</p>
            <p className="text-[11px] text-slate-500 mt-1 max-w-sm mx-auto">
              Auto-generate recommended boundary and Strong Kleene tests or author custom citizen test scenarios.
            </p>
            <div className="mt-3 flex justify-center space-x-2">
              <button
                onClick={handleGenerateTests}
                className="px-3 py-1.5 text-xs font-bold text-white bg-sky-600 hover:bg-sky-700 rounded shadow-sm"
              >
                Auto-Generate Tests
              </button>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {tests.map((test) => {
              let badgeColor = "bg-blue-100 text-blue-800";
              if (test.test_type === "STRONG_KLEENE_UNKNOWN") {
                badgeColor = "bg-purple-100 text-purple-800";
              } else if (test.test_type === "STATUTORY_REGRESSION") {
                badgeColor = "bg-amber-100 text-amber-800";
              } else if (test.test_type === "MANUAL_HUMAN") {
                badgeColor = "bg-emerald-100 text-emerald-800";
              }

              return (
                <div key={test.id} className="p-4 hover:bg-slate-50/70 transition-colors space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-slate-900 text-sm">{test.name}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${badgeColor}`}>
                        {test.test_type}
                      </span>
                    </div>

                    <div className="flex items-center space-x-2">
                      {test.status === "PASSED" ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300 font-bold text-[11px] flex items-center space-x-1">
                          <CheckCircle className="w-3 h-3" />
                          <span>PASSED</span>
                        </span>
                      ) : test.status === "FAILED" ? (
                        <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-300 font-bold text-[11px] flex items-center space-x-1">
                          <XCircle className="w-3 h-3" />
                          <span>FAILED</span>
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-medium text-[11px] flex items-center space-x-1">
                          <Clock className="w-3 h-3" />
                          <span>PENDING</span>
                        </span>
                      )}
                    </div>
                  </div>

                  {test.description && (
                    <p className="text-slate-600 text-[11px]">{test.description}</p>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                    {/* Facts input preview */}
                    <div className="bg-slate-50 p-2 rounded border border-slate-200">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                        Citizen Fact Context
                      </span>
                      <pre className="font-mono text-[10px] text-slate-700 overflow-x-auto max-h-24">
                        {JSON.stringify(test.facts_json, null, 2)}
                      </pre>
                    </div>

                    {/* Outcome expectations */}
                    <div className="bg-slate-50 p-2 rounded border border-slate-200 space-y-1">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                        Evaluation Results
                      </span>
                      <div className="flex justify-between items-center text-[11px]">
                        <span className="text-slate-500">Expected Outcome:</span>
                        <strong className="text-blue-700">{test.expected_result}</strong>
                      </div>
                      <div className="flex justify-between items-center text-[11px]">
                        <span className="text-slate-500">Actual Outcome:</span>
                        <strong className={test.actual_result === test.expected_result ? "text-emerald-700" : "text-rose-700"}>
                          {test.actual_result || "Not executed"}
                        </strong>
                      </div>
                      {test.execution_notes && (
                        <div className="pt-1 text-[10px] text-slate-500 border-t border-slate-200">
                          {test.execution_notes}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add Manual Test Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-base font-bold text-slate-900">
                Add Human-Authored Test Case
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateTest} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Test Case Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Small Farmer with 1.5 Ha and No Institutional Land"
                  value={testName}
                  onChange={(e) => setTestName(e.target.value)}
                  className="w-full border border-slate-300 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Description
                </label>
                <input
                  type="text"
                  placeholder="e.g. Verifies standard positive entitlement path."
                  value={testDesc}
                  onChange={(e) => setTestDesc(e.target.value)}
                  className="w-full border border-slate-300 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Expected Result *
                </label>
                <select
                  value={expectedResult}
                  onChange={(e) => setExpectedResult(e.target.value as any)}
                  className="w-full border border-slate-300 rounded px-2.5 py-1.5 bg-slate-50 font-bold"
                >
                  <option value="ELIGIBLE">ELIGIBLE</option>
                  <option value="INELIGIBLE">INELIGIBLE</option>
                  <option value="UNKNOWN">UNKNOWN (Strong Kleene Missing Fact)</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Simulated Citizen Facts JSON *
                </label>
                <textarea
                  rows={5}
                  required
                  value={factsInput}
                  onChange={(e) => setFactsInput(e.target.value)}
                  className="w-full font-mono text-[11px] border border-slate-300 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 bg-slate-50"
                />
              </div>

              <div className="pt-4 border-t border-slate-200 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 font-semibold text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-1.5 font-bold text-white bg-blue-600 hover:bg-blue-700 rounded shadow-sm"
                >
                  Save Test Case
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
