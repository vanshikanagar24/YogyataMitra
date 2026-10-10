"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useAuth } from "@/context/AuthContext";
import { citizenApi } from "@/api/citizen";
import {
  CitizenApplicationDetail,
  CitizenApplicationSummary,
  CitizenEvidenceSubmission,
  SchemeRequirementsResponse,
} from "@/types/citizen";
import { PolicyFormRenderer } from "@/components/forms";
import {
  FileText,
  ShieldCheck,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Save,
  Send,
  AlertCircle,
  HelpCircle,
  Building2,
  Calendar,
  Clock,
  Hash,
  Upload,
  Info,
  ChevronRight,
} from "lucide-react";

type WizardStep = 1 | 2 | 3 | 4 | 5;

function ApplicationWizardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const schemeParam = searchParams.get("scheme")?.toUpperCase() || "PM_KISAN";
  const applicationIdParam = searchParams.get("applicationId");

  const { citizenToken, citizen } = useAuth();

  const [currentStep, setCurrentStep] = useState<WizardStep>(1);
  const [selectedScheme, setSelectedScheme] = useState<string>(schemeParam);
  const [requirements, setRequirements] = useState<SchemeRequirementsResponse | null>(null);
  const [activeApplication, setActiveApplication] = useState<CitizenApplicationSummary | null>(null);

  const [formFacts, setFormFacts] = useState<Record<string, any>>({});
  const [evidenceInputs, setEvidenceInputs] = useState<
    Record<string, { storage_reference: string; document_name: string; doc_number: string }>
  >({});
  const [declarationAccepted, setDeclarationAccepted] = useState(false);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submittedDetail, setSubmittedDetail] = useState<CitizenApplicationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 1. Load Scheme Requirements & Initialize Application Shell
  useEffect(() => {
    async function initWizard() {
      setLoading(true);
      setError(null);
      try {
        // Fetch scheme requirements
        const reqs = await citizenApi.getSchemeRequirements(selectedScheme, citizenToken);
        setRequirements(reqs);

        // Prepopulate default facts
        const defaults: Record<string, any> = {};
        reqs.fields.forEach((f) => {
          defaults[f.field_key] = f.default_value !== null ? f.default_value : (f.field_type === "boolean" ? false : "");
        });
        setFormFacts(defaults);

        // Prepopulate evidence inputs
        const initialEvidence: Record<string, any> = {};
        reqs.evidence_types.forEach((ev) => {
          initialEvidence[ev.evidence_type] = {
            storage_reference: "",
            document_name: "",
            doc_number: "",
          };
        });
        setEvidenceInputs(initialEvidence);

        if (applicationIdParam) {
          // Resume existing draft
          const existingApp = await citizenApi.getApplicationDetail(applicationIdParam, citizenToken);
          setActiveApplication(existingApp);
          if (existingApp.claims && existingApp.claims.length > 0) {
            const restoredFacts: Record<string, any> = { ...defaults };
            const restoredEvidence: Record<string, any> = { ...initialEvidence };
            existingApp.claims.forEach((c) => {
              if (c.value_json) {
                Object.assign(restoredFacts, c.value_json);
              }
              if (c.evidence_items && c.evidence_items.length > 0) {
                c.evidence_items.forEach((ev) => {
                  restoredEvidence[ev.evidence_type] = {
                    storage_reference: ev.storage_reference,
                    document_name: ev.evidence_type,
                    doc_number: "",
                  };
                });
              }
            });
            setFormFacts(restoredFacts);
            setEvidenceInputs(restoredEvidence);
          }
        } else {
          // Initialize DRAFT application in backend
          const createdApp = await citizenApi.createApplication(
            { scheme_code: selectedScheme },
            citizenToken
          );
          setActiveApplication(createdApp);
        }
      } catch (err: any) {
        setError(err?.message || "Failed to initialize application workflow.");
      } finally {
        setLoading(false);
      }
    }

    if (citizenToken) {
      initWizard();
    }
  }, [selectedScheme, applicationIdParam, citizenToken]);

  // Handle fact field input change
  const handleFactChange = (fieldKey: string, value: any) => {
    setFormFacts((prev) => ({
      ...prev,
      [fieldKey]: value,
    }));
  };

  // Handle evidence input change
  const handleEvidenceChange = (evidenceType: string, key: string, value: string) => {
    setEvidenceInputs((prev) => ({
      ...prev,
      [evidenceType]: {
        ...prev[evidenceType],
        [key]: value,
      },
    }));
  };

  // Save draft progress
  const handleSaveDraft = async () => {
    if (!activeApplication) return;
    setSaving(true);
    setError(null);
    try {
      const evidenceList: CitizenEvidenceSubmission[] = [];
      Object.entries(evidenceInputs).forEach(([evType, item]) => {
        if (item.storage_reference.trim() || item.doc_number.trim()) {
          evidenceList.push({
            evidence_type: evType,
            storage_reference: item.storage_reference.trim() || `doc-ref://vault/${evType.toLowerCase()}_${Date.now()}.pdf`,
            document_name: item.document_name.trim() || `${evType.replace(/_/g, " ")} Document`,
            metadata_json: item.doc_number.trim() ? { document_number: item.doc_number.trim() } : null,
          });
        }
      });

      await citizenApi.updateDraft(
        activeApplication.id,
        {
          facts: formFacts,
          evidence_items: evidenceList.length > 0 ? evidenceList : null,
        },
        citizenToken
      );
    } catch (err: any) {
      setError(err?.message || "Failed to save draft progress.");
    } finally {
      setSaving(false);
    }
  };

  // Final submission
  const handleSubmit = async () => {
    if (!activeApplication || !requirements) return;
    if (!declarationAccepted) {
      setError("Please confirm the statutory declaration to proceed with submission.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const evidenceList: CitizenEvidenceSubmission[] = [];
      Object.entries(evidenceInputs).forEach(([evType, item]) => {
        const ref = item.storage_reference.trim() || item.doc_number.trim()
          ? (item.storage_reference.trim() || `doc-ref://vault/${evType.toLowerCase()}_${Date.now()}.pdf`)
          : `doc-ref://vault/${evType.toLowerCase()}_declared.pdf`;

        evidenceList.push({
          evidence_type: evType,
          storage_reference: ref,
          document_name: item.document_name.trim() || `${evType.replace(/_/g, " ")} Document`,
          metadata_json: item.doc_number.trim() ? { document_number: item.doc_number.trim() } : null,
        });
      });

      const detail = await citizenApi.submitApplication(
        activeApplication.id,
        {
          facts: formFacts,
          evidence_items: evidenceList,
          declaration_confirmed: true,
        },
        citizenToken
      );

      setSubmittedDetail(detail);
      setCurrentStep(5);
    } catch (err: any) {
      setError(err?.message || "Submission failed. Please check required fields and try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="gov-container py-8 max-w-5xl mx-auto space-y-6">
      <main className="w-full">
        {/* Breadcrumb / Top Bar */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2 text-xs text-gray-500 font-medium">
            <Link href="/citizen/dashboard" className="hover:text-blue-700">Dashboard</Link>
            <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
            <Link href="/citizen/schemes" className="hover:text-blue-700">Schemes</Link>
            <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-gray-900 font-semibold">New Application ({selectedScheme})</span>
          </div>
          {activeApplication && currentStep < 5 && (
            <div className="text-xs bg-white px-3 py-1.5 rounded-lg border border-gray-200 font-mono font-medium text-gray-700 shadow-sm flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              <span>{activeApplication.application_ref}</span>
              <span className="text-gray-400">|</span>
              <span className="text-amber-700 font-semibold">Draft</span>
            </div>
          )}
        </div>

        {/* Stepper Progress Bar */}
        <div className="bg-white rounded-2xl border border-gray-200 p-4 sm:p-6 shadow-sm mb-8">
          <div className="flex items-center justify-between relative">
            <div className="absolute top-1/2 left-0 right-0 -translate-y-1/2 h-0.5 bg-gray-200 -z-0" />
            {[
              { num: 1, label: "Policy Context", hi: "नीति संदर्भ" },
              { num: 2, label: "Declarations", hi: "तथ्य घोषणाएं" },
              { num: 3, label: "Evidence Docs", hi: "साक्ष्य दस्तावेज़" },
              { num: 4, label: "Review & Confirm", hi: "समीक्षा एवं पुष्टि" },
              { num: 5, label: "Submitted", hi: "जमा हुआ" },
            ].map((step) => {
              const isPassed = currentStep > step.num;
              const isCurrent = currentStep === step.num;
              return (
                <div key={step.num} className="flex flex-col items-center bg-white px-2 z-10">
                  <div
                    className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs transition-colors ${
                      isPassed
                        ? "bg-emerald-600 text-white"
                        : isCurrent
                        ? "bg-blue-700 text-white ring-4 ring-blue-100"
                        : "bg-gray-100 text-gray-400 border border-gray-200"
                    }`}
                  >
                    {isPassed ? <CheckCircle2 className="w-4 h-4" /> : step.num}
                  </div>
                  <span
                    className={`text-xs mt-2 font-medium hidden sm:inline ${
                      isCurrent ? "text-blue-700 font-bold" : isPassed ? "text-emerald-700" : "text-gray-400"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Global Error Banner */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-800 text-sm mb-6 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Attention Required</p>
              <p className="mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* Loading Spinner */}
        {loading && (
          <div className="bg-white rounded-2xl border border-gray-200 p-16 flex flex-col items-center justify-center text-gray-500 shadow-sm">
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-3" />
            <p className="text-sm font-medium">Resolving statutory policy version & application context...</p>
          </div>
        )}

        {!loading && requirements && (
          <div>
            {/* STEP 1: Policy Context & Scheme Invariants */}
            {currentStep === 1 && (
              <div className="bg-white rounded-2xl border border-gray-200 p-6 sm:p-8 shadow-sm">
                <div className="border-b border-gray-100 pb-5 mb-6">
                  <span className="inline-block px-2.5 py-0.5 rounded-md text-xs font-bold uppercase tracking-wider bg-blue-50 text-blue-800 border border-blue-200 mb-2">
                    Step 1 of 4 • Policy Binding
                  </span>
                  <h2 className="text-xl sm:text-2xl font-bold text-gray-900">
                    {requirements.scheme_name_en}
                  </h2>
                  <p className="text-sm text-gray-600 mt-1">{requirements.scheme_name_hi}</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                  <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                    <span className="text-xs text-gray-500 font-medium block">Nodal Ministry</span>
                    <span className="text-sm font-semibold text-gray-900 mt-1 block">
                      {requirements.ministry || "Government of India"}
                    </span>
                  </div>

                  <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                    <span className="text-xs text-gray-500 font-medium block">Statutory Policy Version</span>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-blue-100 text-blue-900 border border-blue-200">
                        {requirements.policy_version_code}
                      </span>
                      <span className="text-xs text-emerald-700 font-medium flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Effective {requirements.effective_from}
                      </span>
                    </div>
                  </div>

                  <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 md:col-span-2">
                    <span className="text-xs text-gray-500 font-medium block">Policy Immutability Invariant</span>
                    <p className="text-xs text-gray-600 mt-1 leading-relaxed">
                      By proceeding, this application will be permanently bound to statutory version{" "}
                      <span className="font-semibold text-gray-900">{requirements.policy_version_code}</span>.
                      Even if subsequent policy revisions are gazetted in the future, your application remains
                      evaluated under the statutory rules enacted at the time of creation.
                    </p>
                    {requirements.rule_definition_hash && (
                      <div className="mt-2 text-[11px] font-mono text-gray-500 flex items-center gap-1.5">
                        <Hash className="w-3 h-3 text-gray-400" />
                        <span>Rule AST Hash: {requirements.rule_definition_hash.slice(0, 16)}...</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-end gap-4 pt-6 border-t border-gray-100">
                  <button
                    type="button"
                    onClick={() => setCurrentStep(2)}
                    className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-700 text-white text-sm font-semibold hover:bg-blue-800 transition-colors shadow-sm"
                  >
                    <span>Continue to Declarations</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* STEP 2: Citizen Factual Declarations */}
            {currentStep === 2 && (
              <div className="bg-white rounded-2xl border border-gray-200 p-6 sm:p-8 shadow-sm">
                <div className="border-b border-gray-100 pb-5 mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <span className="inline-block px-2.5 py-0.5 rounded-md text-xs font-bold uppercase tracking-wider bg-blue-50 text-blue-800 border border-blue-200 mb-1.5">
                      Step 2 of 4 • Factual Declarations
                    </span>
                    <h2 className="text-xl sm:text-2xl font-bold text-gray-900">
                      Declare Statutory Criteria Facts
                    </h2>
                    <p className="text-sm text-gray-500 mt-0.5">
                      Answer the required statutory questions truthfully according to your records.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleSaveDraft}
                    disabled={saving}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-gray-200 bg-white text-xs font-semibold text-gray-700 hover:bg-gray-50 shadow-sm shrink-0 self-start sm:self-auto"
                  >
                    <Save className="w-3.5 h-3.5 text-gray-500" />
                    <span>{saving ? "Saving..." : "Save Draft"}</span>
                  </button>
                </div>

                <div className="mb-8">
                  <PolicyFormRenderer
                    requirements={requirements}
                    facts={formFacts}
                    onChange={handleFactChange}
                    disabled={saving || submitting}
                  />
                </div>

                <div className="flex items-center justify-between pt-6 border-t border-gray-100">
                  <button
                    type="button"
                    onClick={() => setCurrentStep(1)}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-gray-200 text-gray-700 text-sm font-semibold hover:bg-gray-50 transition-colors"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>Back</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setCurrentStep(3)}
                    className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-700 text-white text-sm font-semibold hover:bg-blue-800 transition-colors shadow-sm"
                  >
                    <span>Next: Supporting Evidence</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* STEP 3: Supporting Evidence Documents */}
            {currentStep === 3 && (
              <div className="bg-white rounded-2xl border border-gray-200 p-6 sm:p-8 shadow-sm">
                <div className="border-b border-gray-100 pb-5 mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <span className="inline-block px-2.5 py-0.5 rounded-md text-xs font-bold uppercase tracking-wider bg-blue-50 text-blue-800 border border-blue-200 mb-1.5">
                      Step 3 of 4 • Supporting Evidence
                    </span>
                    <h2 className="text-xl sm:text-2xl font-bold text-gray-900">
                      Corroborating Document Details
                    </h2>
                    <p className="text-sm text-gray-500 mt-0.5">
                      Provide references or document identifiers for the required statutory evidence.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleSaveDraft}
                    disabled={saving}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-gray-200 bg-white text-xs font-semibold text-gray-700 hover:bg-gray-50 shadow-sm shrink-0 self-start sm:self-auto"
                  >
                    <Save className="w-3.5 h-3.5 text-gray-500" />
                    <span>{saving ? "Saving..." : "Save Draft"}</span>
                  </button>
                </div>

                <div className="space-y-6 mb-8">
                  {requirements.evidence_types.map((ev) => {
                    const currentEv = evidenceInputs[ev.evidence_type] || {
                      storage_reference: "",
                      document_name: "",
                      doc_number: "",
                    };
                    return (
                      <div
                        key={ev.evidence_type}
                        className="p-5 rounded-xl border border-gray-200 bg-white hover:border-blue-300 transition-colors shadow-sm"
                      >
                        <div className="flex items-start justify-between gap-4 mb-3">
                          <div>
                            <span className="text-xs font-mono font-bold text-blue-700 block uppercase">
                              {ev.evidence_type}
                            </span>
                            <h3 className="text-base font-bold text-gray-900 mt-0.5">
                              {ev.label_en}
                            </h3>
                            <p className="text-xs text-gray-500 mt-0.5">{ev.label_hi}</p>
                          </div>
                          {ev.mandatory ? (
                            <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-amber-50 text-amber-800 border border-amber-200 shrink-0">
                              Mandatory
                            </span>
                          ) : (
                            <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-gray-100 text-gray-600 border border-gray-200 shrink-0">
                              Optional
                            </span>
                          )}
                        </div>

                        <p className="text-xs text-gray-600 mb-4 leading-relaxed">
                          {ev.description_en}
                        </p>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div>
                            <label className="text-xs font-semibold text-gray-700 block mb-1">
                              Document / Certificate Number (e.g. 7/12, Reg No)
                            </label>
                            <input
                              type="text"
                              value={currentEv.doc_number}
                              onChange={(e) =>
                                handleEvidenceChange(ev.evidence_type, "doc_number", e.target.value)
                              }
                              placeholder="e.g. MH/2026/PUN/88421"
                              className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                            />
                          </div>

                          <div>
                            <label className="text-xs font-semibold text-gray-700 block mb-1">
                              File Reference / Uploaded Document Identifier
                            </label>
                            <input
                              type="text"
                              value={currentEv.storage_reference}
                              onChange={(e) =>
                                handleEvidenceChange(ev.evidence_type, "storage_reference", e.target.value)
                              }
                              placeholder="e.g. doc-vault://land_record_pune_2026.pdf"
                              className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 font-mono text-xs"
                            />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="flex items-center justify-between pt-6 border-t border-gray-100">
                  <button
                    type="button"
                    onClick={() => setCurrentStep(2)}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-gray-200 text-gray-700 text-sm font-semibold hover:bg-gray-50 transition-colors"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>Back</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setCurrentStep(4)}
                    className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-700 text-white text-sm font-semibold hover:bg-blue-800 transition-colors shadow-sm"
                  >
                    <span>Next: Review Application</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* STEP 4: Review & Legal Self-Declaration */}
            {currentStep === 4 && (
              <div className="bg-white rounded-2xl border border-gray-200 p-6 sm:p-8 shadow-sm">
                <div className="border-b border-gray-100 pb-5 mb-6">
                  <span className="inline-block px-2.5 py-0.5 rounded-md text-xs font-bold uppercase tracking-wider bg-blue-50 text-blue-800 border border-blue-200 mb-1.5">
                    Step 4 of 4 • Final Review
                  </span>
                  <h2 className="text-xl sm:text-2xl font-bold text-gray-900">
                    Review Application & Submit
                  </h2>
                  <p className="text-sm text-gray-500 mt-0.5">
                    Please inspect all declared facts and attached evidence carefully prior to official submission.
                  </p>
                </div>

                {/* Scheme & Reference Badge */}
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 mb-6 flex flex-wrap items-center justify-between gap-3 text-xs">
                  <div>
                    <span className="text-gray-500 font-medium">Scheme:</span>{" "}
                    <span className="font-bold text-gray-900">{requirements.scheme_name_en}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 font-medium">Policy Version:</span>{" "}
                    <span className="font-bold text-blue-900 bg-blue-100 px-2 py-0.5 rounded font-mono">
                      {requirements.policy_version_code}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 font-medium">Application Ref:</span>{" "}
                    <span className="font-bold text-gray-900 font-mono">
                      {activeApplication?.application_ref}
                    </span>
                  </div>
                </div>

                {/* Summary Table of Facts */}
                <div className="mb-6">
                  <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-1.5">
                    <FileText className="w-4 h-4 text-blue-600" />
                    Declared Statutory Facts
                  </h3>
                  <div className="rounded-xl border border-gray-200 overflow-hidden divide-y divide-gray-100 text-xs">
                    {requirements.fields.map((field) => {
                      const val = formFacts[field.field_key];
                      let displayVal = "Not provided";
                      if (typeof val === "boolean") {
                        displayVal = val ? "Yes (हाँ)" : "No (नहीं)";
                      } else if (val !== undefined && val !== null && val !== "") {
                        displayVal = String(val);
                      }
                      return (
                        <div key={field.field_key} className="p-3 bg-white flex justify-between gap-4">
                          <span className="text-gray-700 font-medium">{field.label_en}</span>
                          <span className="font-bold text-gray-900 text-right">{displayVal}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Summary Table of Evidence */}
                <div className="mb-8">
                  <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-blue-600" />
                    Attached Documentary Evidence
                  </h3>
                  <div className="rounded-xl border border-gray-200 overflow-hidden divide-y divide-gray-100 text-xs">
                    {requirements.evidence_types.map((ev) => {
                      const item = evidenceInputs[ev.evidence_type];
                      const hasItem = item && (item.storage_reference.trim() || item.doc_number.trim());
                      return (
                        <div key={ev.evidence_type} className="p-3 bg-white flex justify-between items-center gap-4">
                          <div>
                            <span className="text-gray-900 font-semibold block">{ev.label_en}</span>
                            <span className="text-gray-500 font-mono text-[11px] block mt-0.5">
                              {hasItem ? (item.doc_number || item.storage_reference) : "Reference will be generated"}
                            </span>
                          </div>
                          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                            Pending Verification
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Statutory Self-Declaration Box */}
                <div className="p-5 rounded-xl border border-amber-300 bg-amber-50/80 mb-8">
                  <div className="flex items-start gap-3">
                    <Info className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-bold text-amber-950">
                        Official Statutory Self-Declaration Notice • स्व-घोषणा सूचना
                      </h4>
                      <p className="text-xs text-amber-900 mt-1 leading-relaxed">
                        I hereby declare that all information furnished and claims asserted in this application
                        are true, correct, and complete according to statutory guidelines. I acknowledge that
                        submission of this application initiates official welfare officer verification and does
                        not itself constitute automatic eligibility or guarantee benefit sanction.
                      </p>
                      <label className="flex items-start gap-2.5 mt-4 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={declarationAccepted}
                          onChange={(e) => setDeclarationAccepted(e.target.checked)}
                          className="mt-0.5 h-4 w-4 rounded border-amber-400 text-blue-700 focus:ring-blue-600"
                        />
                        <span className="text-xs font-bold text-amber-950 leading-tight">
                          I confirm and accept this statutory declaration • मैं इस घोषणा की पुष्टि करता/करती हूँ।
                        </span>
                      </label>
                    </div>
                  </div>
                </div>

                {/* Footer Buttons */}
                <div className="flex items-center justify-between pt-6 border-t border-gray-100">
                  <button
                    type="button"
                    onClick={() => setCurrentStep(3)}
                    disabled={submitting}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-gray-200 text-gray-700 text-sm font-semibold hover:bg-gray-50 transition-colors"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>Back to Evidence</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleSubmit}
                    disabled={submitting || !declarationAccepted}
                    className={`inline-flex items-center gap-2 px-7 py-2.5 rounded-xl text-white text-sm font-bold shadow-md transition-colors ${
                      declarationAccepted && !submitting
                        ? "bg-emerald-700 hover:bg-emerald-800"
                        : "bg-gray-400 cursor-not-allowed"
                    }`}
                  >
                    <Send className="w-4 h-4" />
                    <span>{submitting ? "Submitting Application..." : "Submit Application • आवेदन जमा करें"}</span>
                  </button>
                </div>
              </div>
            )}

            {/* STEP 5: Submission Success Confirmation */}
            {currentStep === 5 && submittedDetail && (
              <div className="bg-white rounded-2xl border border-gray-200 p-8 sm:p-12 shadow-sm text-center">
                <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center mx-auto mb-6">
                  <CheckCircle2 className="w-10 h-10" />
                </div>

                <span className="inline-block px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 mb-3">
                  Application Successfully Submitted • आवेदन सफलतापूर्वक जमा हुआ
                </span>

                <h2 className="text-2xl sm:text-3xl font-extrabold text-gray-900 mb-2">
                  {submittedDetail.scheme_name}
                </h2>
                <p className="text-sm text-gray-500 max-w-lg mx-auto mb-8">
                  Your application has been persisted and registered into the official welfare verification stream.
                </p>

                <div className="max-w-md mx-auto bg-slate-50 rounded-xl p-5 border border-slate-200 text-left space-y-3 mb-8 text-xs">
                  <div className="flex justify-between border-b border-slate-200 pb-2">
                    <span className="text-gray-500 font-medium">Application Reference:</span>
                    <span className="font-mono font-bold text-gray-900">{submittedDetail.application_ref}</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-200 pb-2">
                    <span className="text-gray-500 font-medium">Bound Policy Version:</span>
                    <span className="font-mono font-semibold text-blue-900">{submittedDetail.policy_version_code}</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-200 pb-2">
                    <span className="text-gray-500 font-medium">Submission Timestamp:</span>
                    <span className="font-semibold text-gray-800">
                      {submittedDetail.submitted_at
                        ? new Date(submittedDetail.submitted_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })
                        : "Just now"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500 font-medium">Current Status:</span>
                    <span className="font-bold text-indigo-700">
                      {submittedDetail.status_label_en} ({submittedDetail.status_label_hi})
                    </span>
                  </div>
                </div>

                {/* What Happens Next Sequence */}
                <div className="max-w-lg mx-auto bg-blue-50/60 rounded-xl p-5 border border-blue-100 text-left mb-8">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-blue-950 mb-3">
                    What Happens Next? • आगे की प्रक्रिया:
                  </h4>
                  <ol className="text-xs text-blue-900 space-y-2 list-decimal list-inside leading-relaxed">
                    <li>
                      <span className="font-semibold text-blue-950">Officer Queueing</span>: Your case dossier will be queued for Welfare Verification Officer inspection.
                    </li>
                    <li>
                      <span className="font-semibold text-blue-950">Evidence Inspection</span>: Officer inspects your land/identity records against government databases.
                    </li>
                    <li>
                      <span className="font-semibold text-blue-950">Deterministic Evaluation</span>: Once verified, statutory rule AST executes transparently.
                    </li>
                  </ol>
                </div>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                  <Link
                    href={`/citizen/applications/${submittedDetail.id}`}
                    className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-blue-700 text-white text-sm font-semibold hover:bg-blue-800 transition-colors shadow-sm"
                  >
                    <span>View Application Dossier • विवरण देखें</span>
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                  <Link
                    href="/citizen/applications"
                    className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl border border-gray-200 bg-white text-gray-700 text-sm font-semibold hover:bg-gray-50 transition-colors"
                  >
                    <span>Go to My Applications • मेरे आवेदन</span>
                  </Link>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default function NewApplicationPage() {
  return (
    <ProtectedRoute requiredRole="CITIZEN">
      <Suspense fallback={<div className="min-h-screen bg-slate-50 flex items-center justify-center text-sm text-gray-500">Loading wizard...</div>}>
        <ApplicationWizardContent />
      </Suspense>
    </ProtectedRoute>
  );
}
