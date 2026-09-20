"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Sliders,
  Plus,
  Trash2,
  Edit2,
  Save,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  Code,
  FileCode2,
} from "lucide-react";
import { useOfficerAuth } from "@/context/OfficerAuthContext";
import { policyAuthoringApi } from "@/api/policyAuthoring";
import { PolicyDraftDetail } from "@/types/policyAuthoring";
import { DraftSubNav } from "@/components/policy-authoring/DraftSubNav";

interface RuleItem {
  rule_id: string;
  name_en: string;
  name_hi?: string;
  description_en?: string;
  description_hi?: string;
  field_path: string;
  operator: string;
  target_value: any;
  is_disqualification?: boolean;
}

const COMMON_FIELDS_BY_SCHEME: Record<string, string[]> = {
  PM_KISAN: [
    "land_size_hectares",
    "institution_holder",
    "constitutional_post_holder",
    "institutional_landholder",
    "income_tax_payer",
    "doctor_engineer_ca_lawyer",
    "family_pensioner_10k_plus",
    "aadhaar_seeded",
    "farmer_status",
  ],
  SSY: [
    "age",
    "gender",
    "family_girl_child_count",
    "citizenship",
    "account_opened_prior",
  ],
};

const OPERATORS = [
  { value: "EQUALS", label: "EQUALS (==)" },
  { value: "NOT_EQUALS", label: "NOT EQUALS (!=)" },
  { value: "GREATER_THAN", label: "GREATER THAN (>)" },
  { value: "LESS_THAN", label: "LESS THAN (<)" },
  { value: "GREATER_THAN_OR_EQUAL", label: "GREATER THAN OR EQUAL (>=)" },
  { value: "LESS_THAN_OR_EQUAL", label: "LESS THAN OR EQUAL (<=)" },
  { value: "IN", label: "IN (Array inclusion)" },
  { value: "NOT_IN", label: "NOT IN (Array exclusion)" },
];

export default function PolicyRuleBuilderPage() {
  const { isAuthenticated, isLoading: authLoading, token } = useOfficerAuth();
  const params = useParams();
  const router = useRouter();
  const draftId = params.draftId as string;

  const [draft, setDraft] = useState<PolicyDraftDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Editable rules state
  const [rules, setRules] = useState<RuleItem[]>([]);
  const [changeSummary, setChangeSummary] = useState("");

  // Add / Edit modal or inline form state
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [ruleId, setRuleId] = useState("");
  const [nameEn, setNameEn] = useState("");
  const [nameHi, setNameHi] = useState("");
  const [descEn, setDescEn] = useState("");
  const [descHi, setDescHi] = useState("");
  const [fieldPath, setFieldPath] = useState("");
  const [customField, setCustomField] = useState("");
  const [operator, setOperator] = useState("EQUALS");
  const [targetValue, setTargetValue] = useState("");
  const [isDisqualification, setIsDisqualification] = useState(false);
  const [showRuleModal, setShowRuleModal] = useState(false);

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
      const existingRules = data.authored_rules_json?.rules || [];
      setRules(existingRules);
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

  const openAddRule = () => {
    setEditingIndex(null);
    setRuleId(`${draft?.scheme_code?.toLowerCase() || "rule"}_${Date.now().toString().slice(-4)}`);
    setNameEn("");
    setNameHi("");
    setDescEn("");
    setDescHi("");
    const scheme = draft?.scheme_code || "PM_KISAN";
    const available = COMMON_FIELDS_BY_SCHEME[scheme] || [];
    setFieldPath(available[0] || "custom");
    setCustomField("");
    setOperator("EQUALS");
    setTargetValue("true");
    setIsDisqualification(false);
    setShowRuleModal(true);
  };

  const openEditRule = (idx: number) => {
    const r = rules[idx];
    setEditingIndex(idx);
    setRuleId(r.rule_id);
    setNameEn(r.name_en || "");
    setNameHi(r.name_hi || "");
    setDescEn(r.description_en || "");
    setDescHi(r.description_hi || "");
    const scheme = draft?.scheme_code || "PM_KISAN";
    const available = COMMON_FIELDS_BY_SCHEME[scheme] || [];
    if (available.includes(r.field_path)) {
      setFieldPath(r.field_path);
      setCustomField("");
    } else {
      setFieldPath("custom");
      setCustomField(r.field_path);
    }
    setOperator(r.operator || "EQUALS");
    setTargetValue(
      typeof r.target_value === "object"
        ? JSON.stringify(r.target_value)
        : String(r.target_value ?? "")
    );
    setIsDisqualification(!!r.is_disqualification);
    setShowRuleModal(true);
  };

  const handleSaveRuleItem = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruleId.trim()) {
      setError("Rule ID is required.");
      return;
    }
    if (!nameEn.trim()) {
      setError("English name is required.");
      return;
    }

    const actualField = fieldPath === "custom" ? customField.trim() : fieldPath;
    if (!actualField) {
      setError("Field path is required.");
      return;
    }

    let parsedVal: any = targetValue.trim();
    if (parsedVal === "true") parsedVal = true;
    else if (parsedVal === "false") parsedVal = false;
    else if (!isNaN(Number(parsedVal)) && parsedVal !== "") parsedVal = Number(parsedVal);
    else if (parsedVal.startsWith("[") && parsedVal.endsWith("]")) {
      try {
        parsedVal = JSON.parse(parsedVal);
      } catch {
        // Keep as string if not valid JSON
      }
    }

    const newRuleItem: RuleItem = {
      rule_id: ruleId.trim(),
      name_en: nameEn.trim(),
      name_hi: nameHi.trim() || undefined,
      description_en: descEn.trim() || undefined,
      description_hi: descHi.trim() || undefined,
      field_path: actualField,
      operator,
      target_value: parsedVal,
      is_disqualification: isDisqualification,
    };

    if (editingIndex !== null) {
      const updated = [...rules];
      updated[editingIndex] = newRuleItem;
      setRules(updated);
    } else {
      setRules([...rules, newRuleItem]);
    }

    setShowRuleModal(false);
  };

  const handleDeleteRule = (idx: number) => {
    const updated = [...rules];
    updated.splice(idx, 1);
    setRules(updated);
  };

  const handleSaveDraft = async () => {
    if (!token || !draftId) return;
    setSaving(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const authored_rules_json = {
        schema_version: "2.0",
        rules: rules,
      };

      await policyAuthoringApi.updateDraft(
        draftId,
        {
          authored_rules_json,
          change_summary: changeSummary.trim() || `Updated ${rules.length} statutory authored rules.`,
        },
        token
      );

      setSuccessMsg("Authored rules saved successfully! A new revision snapshot was recorded.");
      setChangeSummary("");
      fetchDraft();
    } catch (err: any) {
      setError(err?.message || "Failed to save authored rules.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-500 mb-2" />
        <p className="text-sm">Loading rule builder...</p>
      </div>
    );
  }

  if (!draft) return null;

  const schemeFields = COMMON_FIELDS_BY_SCHEME[draft.scheme_code || "PM_KISAN"] || [];

  return (
    <div className="space-y-6">
      {/* Breadcrumbs */}
      <div className="flex items-center justify-between">
        <Link
          href={`/officer/policy-authoring/${draft.id}`}
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Dossier</span>
        </Link>
        <span className="text-xs text-slate-500">
          Scheme: <strong className="text-blue-600">{draft.scheme_code}</strong>
        </span>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
            <Sliders className="w-6 h-6 text-blue-600" />
            <span>Interactive Statutory Rule Builder</span>
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Author and refine AST rule criteria for {draft.policy_title}.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={openAddRule}
            className="px-3 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded shadow-sm flex items-center space-x-1.5 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Rule</span>
          </button>

          <button
            onClick={handleSaveDraft}
            disabled={saving}
            className="px-4 py-1.5 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded shadow-sm flex items-center space-x-1.5 transition-colors disabled:opacity-50"
          >
            {saving ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Save className="w-3.5 h-3.5" />
            )}
            <span>Save Rules</span>
          </button>
        </div>
      </div>

      {/* Draft SubNav */}
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

      {/* Rules List & AST JSON Split View */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Rules Table / Cards (8 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900">
                Rule List ({rules.length} configured)
              </h3>
              <span className="text-[11px] text-slate-400">
                Ordered AST Evaluation Flow
              </span>
            </div>

            {rules.length === 0 ? (
              <div className="p-8 text-center border-2 border-dashed border-slate-200 rounded-lg">
                <Sliders className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-xs font-semibold text-slate-700">No Rules Defined</p>
                <p className="text-[11px] text-slate-500 mt-1 max-w-xs mx-auto">
                  Click "+ Add Rule" to define eligibility thresholds or exclusion parameters.
                </p>
                <button
                  onClick={openAddRule}
                  className="mt-3 px-3 py-1 text-xs font-bold text-white bg-blue-600 rounded"
                >
                  Add First Rule
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                {rules.map((rule, idx) => (
                  <div
                    key={rule.rule_id || idx}
                    className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg text-xs hover:border-slate-300 transition-colors space-y-2"
                  >
                    <div className="flex items-start justify-between">
                      <div className="space-y-0.5">
                        <div className="flex items-center space-x-2">
                          <span className="font-mono font-bold text-slate-900 text-[11px]">
                            {rule.rule_id}
                          </span>
                          <span className="px-1.5 py-0.2 rounded text-[10px] font-semibold bg-blue-100 text-blue-800">
                            {rule.operator}
                          </span>
                          {rule.is_disqualification && (
                            <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-rose-100 text-rose-800">
                              Disqualification
                            </span>
                          )}
                        </div>
                        <p className="font-semibold text-slate-800 text-xs">{rule.name_en}</p>
                        {rule.name_hi && (
                          <p className="text-slate-500 text-[11px]">{rule.name_hi}</p>
                        )}
                      </div>

                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => openEditRule(idx)}
                          className="p-1 text-slate-500 hover:text-blue-600 rounded"
                          title="Edit Rule"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteRule(idx)}
                          className="p-1 text-slate-500 hover:text-rose-600 rounded"
                          title="Delete Rule"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <div className="bg-white p-2 rounded border border-slate-200 text-[11px] font-mono flex flex-wrap gap-x-4 gap-y-1 text-slate-600">
                      <div>
                        Field: <strong className="text-slate-900">{rule.field_path}</strong>
                      </div>
                      <div>
                        Target: <strong className="text-indigo-700">{JSON.stringify(rule.target_value)}</strong>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Change summary input */}
          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm space-y-2">
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              Revision Change Summary (Mandatory for Audit Trail)
            </label>
            <input
              type="text"
              placeholder="e.g. Added mandatory biometric e-KYC requirement rule..."
              value={changeSummary}
              onChange={(e) => setChangeSummary(e.target.value)}
              className="w-full text-xs border border-slate-300 rounded px-3 py-1.5 focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Live AST JSON Preview (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-slate-900 text-slate-100 rounded-lg p-4 shadow-sm space-y-2">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-xs font-mono font-bold text-blue-400 flex items-center space-x-1.5">
                <Code className="w-4 h-4" />
                <span>Canonical AST Schema v2.0</span>
              </span>
              <span className="text-[10px] font-mono text-slate-400">
                {rules.length} rule node{rules.length === 1 ? "" : "s"}
              </span>
            </div>

            <pre className="text-[11px] font-mono overflow-x-auto max-h-[460px] p-2 text-slate-300">
              {JSON.stringify(
                {
                  schema_version: "2.0",
                  rules: rules,
                },
                null,
                2
              )}
            </pre>
          </div>
        </div>
      </div>

      {/* Add / Edit Rule Modal */}
      {showRuleModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-base font-bold text-slate-900">
                {editingIndex !== null ? "Edit Rule AST Node" : "Add Statutory Rule AST Node"}
              </h3>
              <button
                onClick={() => setShowRuleModal(false)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveRuleItem} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Rule ID *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. pmkisan_land_size_limit"
                  value={ruleId}
                  onChange={(e) => setRuleId(e.target.value)}
                  className="w-full font-mono border border-slate-300 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Rule Name (English) *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Land Limit Condition"
                    value={nameEn}
                    onChange={(e) => setNameEn(e.target.value)}
                    className="w-full border border-slate-300 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Rule Name (Hindi)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. भूमि सीमा शर्त"
                    value={nameHi}
                    onChange={(e) => setNameHi(e.target.value)}
                    className="w-full border border-slate-300 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Field Path Selection */}
              <div>
                <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Evaluator Fact Field Path *
                </label>
                <select
                  value={fieldPath}
                  onChange={(e) => setFieldPath(e.target.value)}
                  className="w-full border border-slate-300 rounded px-2.5 py-1.5 bg-slate-50 focus:ring-1 focus:ring-blue-500 font-medium"
                >
                  {schemeFields.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                  <option value="custom">-- Custom Fact Field Path --</option>
                </select>

                {fieldPath === "custom" && (
                  <input
                    type="text"
                    placeholder="Enter custom fact path (e.g. applicant.monthly_income)"
                    value={customField}
                    onChange={(e) => setCustomField(e.target.value)}
                    className="mt-2 w-full font-mono border border-slate-300 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500"
                  />
                )}
              </div>

              {/* Operator and Target Value */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Operator *
                  </label>
                  <select
                    value={operator}
                    onChange={(e) => setOperator(e.target.value)}
                    className="w-full border border-slate-300 rounded px-2.5 py-1.5 bg-slate-50 focus:ring-1 focus:ring-blue-500 font-medium"
                  >
                    {OPERATORS.map((op) => (
                      <option key={op.value} value={op.value}>
                        {op.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Target Value *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 2, true, or [1, 2]"
                    value={targetValue}
                    onChange={(e) => setTargetValue(e.target.value)}
                    className="w-full font-mono border border-slate-300 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Disqualification checkbox */}
              <div className="pt-2">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isDisqualification}
                    onChange={(e) => setIsDisqualification(e.target.checked)}
                    className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="font-semibold text-slate-700">
                    Disqualification / Ineligibility Exclusion Rule
                  </span>
                </label>
                <p className="text-[11px] text-slate-500 ml-5 mt-0.5">
                  If this condition matches, citizen evaluation evaluates to INELIGIBLE.
                </p>
              </div>

              {/* Modal Buttons */}
              <div className="pt-4 border-t border-slate-200 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowRuleModal(false)}
                  className="px-3 py-1.5 font-semibold text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 font-bold text-white bg-blue-600 hover:bg-blue-700 rounded shadow-sm"
                >
                  {editingIndex !== null ? "Update Node" : "Add to AST"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
