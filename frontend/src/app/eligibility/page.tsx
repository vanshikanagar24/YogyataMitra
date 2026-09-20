"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  ArrowRight,
  ArrowLeft,
  CheckCircle,
  AlertTriangle,
  Loader2,
  Info,
} from "lucide-react";
import { Breadcrumbs } from "../../components/layout/Breadcrumbs";
import { PageHeader } from "../../components/layout/PageHeader";
import { JourneyStepper, StepId } from "../../components/journey/JourneyStepper";
import { ClaimCard } from "../../components/journey/ClaimCard";
import { EvaluationResultCard } from "../../components/evaluation/EvaluationResultCard";
import { ExplainabilityView } from "../../components/evaluation/ExplainabilityView";
import { LoadingState } from "../../components/common/FeedbackStates";
import { useLanguage } from "../../context/LanguageContext";
import {
  createJourney,
  addJourneyClaim,
  addJourneyEvidence,
  verifyJourneyEvidence,
} from "../../api/journeys";
import { evaluateEligibility } from "../../api/evaluations";
import { EvaluationFacts, EvaluationResponse } from "../../types/evaluation";
import { JourneyClaim, JourneyResponse } from "../../types/journey";
import { EvidenceStatus } from "../../types/enums";

function EligibilityJourneyContent() {
  const { isHindi, t } = useLanguage();
  const searchParams = useSearchParams();
  const router = useRouter();

  const schemeParam = searchParams.get("scheme");
  const initialScheme = schemeParam?.toUpperCase() === "SSY" ? "SSY" : "PM_KISAN";

  const [currentStep, setCurrentStep] = useState<StepId>("facts");
  const [selectedScheme, setSelectedScheme] = useState<string>(initialScheme);
  const [evaluationDate] = useState<string>(() => new Date().toISOString().split("T")[0]);
  const [citizenRef] = useState<string>("SYN-CIT-2026-001");

  // Facts form state for PM-KISAN
  const [pmKisanFacts, setPmKisanFacts] = useState({
    owns_cultivable_land: true,
    total_land_area_hectares: 1.5,
    is_institutional_landholder: false,
    has_constitutional_post_holder: false,
    has_public_representative: false,
    has_disqualified_government_employee: false,
    has_pensioner_above_ten_thousand: false,
    has_income_tax_payer: false,
    has_registered_practicing_professional: false,
    is_nri: false,
    transferred_after_cutoff: false,
    acquired_via_succession: false,
  });

  // Facts form state for SSY
  const [ssyFacts, setSsyFacts] = useState({
    gender: "FEMALE",
    date_of_birth: "2016-06-10",
    is_indian_resident: true,
    is_natural_guardian: true,
    is_court_appointed_legal_guardian: false,
    active_ssy_accounts_count: 0,
    has_multiple_birth_exception: false,
    opening_date: new Date().toISOString().split("T")[0],
  });

  // Server state
  const [activeJourney, setActiveJourney] = useState<JourneyResponse | null>(null);
  const [journeyClaims, setJourneyClaims] = useState<JourneyClaim[]>([]);
  const [evaluationResult, setEvaluationResult] = useState<EvaluationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Evidence modal state
  const [evidenceModalClaimId, setEvidenceModalClaimId] = useState<string | null>(null);
  const [evidenceTypeInput, setEvidenceTypeInput] = useState("");
  const [evidenceRefInput, setEvidenceRefInput] = useState("");

  useEffect(() => {
    if (schemeParam && (schemeParam.toUpperCase() === "SSY" || schemeParam.toUpperCase() === "PM_KISAN")) {
      setSelectedScheme(schemeParam.toUpperCase());
    }
  }, [schemeParam]);

  // Modal keyboard handling (Escape to close)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && evidenceModalClaimId) {
        setEvidenceModalClaimId(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [evidenceModalClaimId]);

  // Build composite evaluation facts payload
  const buildFactsPayload = (): EvaluationFacts => {
    if (selectedScheme === "PM_KISAN") {
      return {
        family: {
          owns_cultivable_land: pmKisanFacts.owns_cultivable_land,
          total_land_area_hectares: Number(pmKisanFacts.total_land_area_hectares),
          is_institutional_landholder: pmKisanFacts.is_institutional_landholder,
          has_constitutional_post_holder: pmKisanFacts.has_constitutional_post_holder,
          has_public_representative: pmKisanFacts.has_public_representative,
          has_disqualified_government_employee: pmKisanFacts.has_disqualified_government_employee,
          has_pensioner_above_ten_thousand: pmKisanFacts.has_pensioner_above_ten_thousand,
          has_income_tax_payer: pmKisanFacts.has_income_tax_payer,
          has_registered_practicing_professional: pmKisanFacts.has_registered_practicing_professional,
          is_nri: pmKisanFacts.is_nri,
        },
        land: {
          transferred_after_cutoff: pmKisanFacts.transferred_after_cutoff,
          acquired_via_succession: pmKisanFacts.acquired_via_succession,
        },
      };
    } else {
      return {
        beneficiary: {
          gender: ssyFacts.gender,
          date_of_birth: ssyFacts.date_of_birth,
          is_indian_resident: ssyFacts.is_indian_resident,
        },
        guardian: {
          is_natural_guardian: ssyFacts.is_natural_guardian,
          is_court_appointed_legal_guardian: ssyFacts.is_court_appointed_legal_guardian,
        },
        family: {
          active_ssy_accounts_count: Number(ssyFacts.active_ssy_accounts_count),
          has_multiple_birth_exception: ssyFacts.has_multiple_birth_exception,
        },
        account: {
          opening_date: ssyFacts.opening_date,
        },
      };
    }
  };

  // Step 1 -> Step 2: Initialize Journey & Claims
  const handleCreateJourneyAndClaims = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const journey = await createJourney({
        citizen_ref: citizenRef,
        scheme_code: selectedScheme,
      });
      setActiveJourney(journey);

      const createdClaims: JourneyClaim[] = [];

      if (selectedScheme === "PM_KISAN") {
        const c1 = await addJourneyClaim(journey.id, {
          claim_type: "family.owns_cultivable_land",
          value_json: { value: pmKisanFacts.owns_cultivable_land },
          source: "SELF_DECLARATION",
        });
        createdClaims.push(c1);

        const c2 = await addJourneyClaim(journey.id, {
          claim_type: "family.is_institutional_landholder",
          value_json: { value: pmKisanFacts.is_institutional_landholder },
          source: "SELF_DECLARATION",
        });
        createdClaims.push(c2);

        const c3 = await addJourneyClaim(journey.id, {
          claim_type: "family.has_income_tax_payer",
          value_json: { value: pmKisanFacts.has_income_tax_payer },
          source: "SELF_DECLARATION",
        });
        createdClaims.push(c3);

        const c4 = await addJourneyClaim(journey.id, {
          claim_type: "family.is_nri",
          value_json: { value: pmKisanFacts.is_nri },
          source: "SELF_DECLARATION",
        });
        createdClaims.push(c4);
      } else {
        const c1 = await addJourneyClaim(journey.id, {
          claim_type: "beneficiary.gender",
          value_json: { value: ssyFacts.gender },
          source: "SELF_DECLARATION",
        });
        createdClaims.push(c1);

        const c2 = await addJourneyClaim(journey.id, {
          claim_type: "beneficiary.date_of_birth",
          value_json: { value: ssyFacts.date_of_birth },
          source: "SELF_DECLARATION",
        });
        createdClaims.push(c2);

        const c3 = await addJourneyClaim(journey.id, {
          claim_type: "family.active_ssy_accounts_count",
          value_json: { value: Number(ssyFacts.active_ssy_accounts_count) },
          source: "SELF_DECLARATION",
        });
        createdClaims.push(c3);
      }

      setJourneyClaims(createdClaims);
      setCurrentStep("claims");
    } catch (err: any) {
      setErrorMessage(err?.message || t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  // Open Evidence Attachment Modal
  const handleOpenEvidenceModal = (claimId: string) => {
    setEvidenceModalClaimId(claimId);
    const targetClaim = journeyClaims.find((c) => c.id === claimId);
    if (targetClaim?.claim_type.includes("land")) {
      setEvidenceTypeInput("LAND_RECORD_7_12");
      setEvidenceRefInput("UP-REV-2024-KHASRA-88");
    } else if (targetClaim?.claim_type.includes("birth") || targetClaim?.claim_type.includes("gender")) {
      setEvidenceTypeInput("BIRTH_CERTIFICATE");
      setEvidenceRefInput("MCD-CIVIL-2016-09412");
    } else if (targetClaim?.claim_type.includes("tax")) {
      setEvidenceTypeInput("ITR_ACKNOWLEDGEMENT");
      setEvidenceRefInput("ITR-V-ACK-2023-8891");
    } else {
      setEvidenceTypeInput("SUPPORTING_AFFIDAVIT");
      setEvidenceRefInput("AFFIDAVIT-NOTARY-001");
    }
  };

  // Attach Evidence
  const handleAttachEvidence = async () => {
    if (!activeJourney || !evidenceModalClaimId) return;
    setLoading(true);
    try {
      const newEv = await addJourneyEvidence(activeJourney.id, evidenceModalClaimId, {
        evidence_type: evidenceTypeInput || "SUPPORTING_DOCUMENT",
        storage_reference: evidenceRefInput || "DOC-REF-001",
      });

      setJourneyClaims((prev) =>
        prev.map((c) => {
          if (c.id === evidenceModalClaimId) {
            return {
              ...c,
              evidence_items: [...c.evidence_items, newEv],
            };
          }
          return c;
        })
      );
      setEvidenceModalClaimId(null);
    } catch (err: any) {
      setErrorMessage(err?.message || "Failed to attach evidence document");
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Verify Evidence
  const handleVerifyEvidence = async (evidenceId: string) => {
    if (!activeJourney) return;
    setLoading(true);
    try {
      const updatedEv = await verifyJourneyEvidence(activeJourney.id, evidenceId, {
        status: EvidenceStatus.VERIFIED,
        verification_method: "REVENUE_PORTAL_API",
        verified_by: "VERIFICATION_OFFICER_402",
      });

      setJourneyClaims((prev) =>
        prev.map((c) => ({
          ...c,
          evidence_items: c.evidence_items.map((e) => (e.id === evidenceId ? updatedEv : e)),
        }))
      );
    } catch (err: any) {
      setErrorMessage(err?.message || "Failed to verify evidence");
    } finally {
      setLoading(false);
    }
  };

  // Step 3 -> Step 4: Execute Statutory Evaluation
  const handleExecuteEvaluation = async () => {
    setCurrentStep("evaluation");
    setLoading(true);
    setErrorMessage(null);
    try {
      const facts = buildFactsPayload();
      const evalResp = await evaluateEligibility({
        scheme_code: selectedScheme,
        evaluation_date: evaluationDate,
        facts,
        citizen_ref: citizenRef,
      });

      setEvaluationResult(evalResp);
      if (typeof window !== "undefined") {
        try {
          const stored = JSON.parse(sessionStorage.getItem("ym_recent_assessments") || "[]");
          const record = {
            id: evalResp.evaluation_id,
            scheme_code: evalResp.scheme_code,
            policy_version_code: evalResp.policy_version_code,
            evaluation_date: evalResp.evaluation_date,
            overall_result: evalResp.overall_result,
            created_at: evalResp.created_at,
            reasons_en: evalResp.reasons_en,
            reasons_hi: evalResp.reasons_hi,
            facts_snapshot: facts,
          };
          const updated = [record, ...stored.filter((r: any) => r.id !== evalResp.evaluation_id)].slice(0, 10);
          sessionStorage.setItem("ym_recent_assessments", JSON.stringify(updated));
        } catch {
          // ignore session storage errors
        }
      }
      setCurrentStep("result");
    } catch (err: any) {
      setErrorMessage(err?.message || "Failed to execute evaluation against statutory engine");
      setCurrentStep("claims");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="gov-container py-6 space-y-6">
      <Breadcrumbs
        items={[
          { label: t("nav.schemes"), href: "/schemes" },
          { label: selectedScheme, href: `/schemes/${selectedScheme}` },
          { label: t("nav.eligibility") },
        ]}
      />

      <PageHeader
        title={isHindi ? "नागरिक पात्रता मूल्यांकन एवं सत्यापन" : "Citizen Entitlement Evaluation & Verification"}
        subtitle={
          isHindi
            ? "पारदर्शी नियम इंजन द्वारा अपने दावों की वैधानिक पात्रता की निष्पक्ष जाँच करें।"
            : "Complete a transparent four-step statutory eligibility journey driven by certified policy rulesets."
        }
      />

      {/* 4-Step Stepper Navigation */}
      <JourneyStepper
        currentStep={currentStep}
        onSelectStep={(step) => {
          if (step === "facts") setCurrentStep("facts");
          else if (step === "claims" && activeJourney) setCurrentStep("claims");
          else if (step === "result" && evaluationResult) setCurrentStep("result");
        }}
      />

      {/* Global Notification Banner */}
      {errorMessage && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start space-x-3" role="alert">
          <AlertTriangle className="w-5 h-5 text-danger flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div className="flex-grow text-xs">
            <span className="font-bold text-danger-700 block">{t("common.error")}</span>
            <span className="text-gov-text">{errorMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setErrorMessage(null)}
            className="text-xs text-gray-500 hover:text-gray-800 font-bold p-1 min-h-[32px]"
            aria-label={t("a11y.close")}
          >
            ✕
          </button>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STEP 1: FACT COLLECTION FORM */}
      {/* ========================================================================= */}
      {currentStep === "facts" && (
        <div className="bg-white rounded-xl border border-gov-border p-6 sm:p-8 shadow-gov-card space-y-6">
          {/* Scheme Selection Only — Synthetic ID and Evaluation Date hidden from citizen */}
          <div className="max-w-md pb-4 border-b border-gray-100">
            <label htmlFor="scheme-select" className="block text-xs font-bold text-gov-text uppercase tracking-wider mb-1.5">
              {t("forms.select_scheme_label")}
            </label>
            <select
              id="scheme-select"
              value={selectedScheme}
              onChange={(e) => {
                setSelectedScheme(e.target.value);
                router.push(`/eligibility?scheme=${e.target.value}`);
              }}
              className="w-full text-xs font-semibold p-2.5 border border-gov-border rounded-md bg-white text-primary-dark focus:outline-none focus-visible:ring-2 focus-visible:ring-primary min-h-[40px]"
            >
              <option value="PM_KISAN">PM-KISAN (पीएम किसान सम्मान निधि)</option>
              <option value="SSY">SSY (सुकन्या समृद्धि योजना)</option>
            </select>
          </div>

          {/* Scheme-Specific Facts Form */}
          {selectedScheme === "PM_KISAN" ? (
            <fieldset className="space-y-4">
              <legend className="text-sm font-bold text-primary-dark border-b border-gray-100 pb-2 w-full">
                {t("forms.pm_kisan_facts_heading")}
              </legend>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                {/* Owns cultivable land */}
                <div className="bg-gov-bg p-3.5 rounded border border-gov-border space-y-2">
                  <label htmlFor="pmkisan-owns-land" className="font-semibold text-gov-text block">
                    {t("forms.pm_kisan_land_label")}
                  </label>
                  <select
                    id="pmkisan-owns-land"
                    value={pmKisanFacts.owns_cultivable_land ? "yes" : "no"}
                    onChange={(e) =>
                      setPmKisanFacts({ ...pmKisanFacts, owns_cultivable_land: e.target.value === "yes" })
                    }
                    className="w-full p-2 border border-gov-border rounded bg-white text-xs min-h-[36px]"
                  >
                    <option value="yes">{t("forms.yes")}</option>
                    <option value="no">{t("forms.no")}</option>
                  </select>
                </div>

                {/* Land area */}
                <div className="bg-gov-bg p-3.5 rounded border border-gov-border space-y-2">
                  <label htmlFor="pmkisan-land-area" className="font-semibold text-gov-text block">
                    {t("forms.pm_kisan_land_area_label")}
                  </label>
                  <input
                    id="pmkisan-land-area"
                    type="number"
                    step="0.1"
                    min="0"
                    value={pmKisanFacts.total_land_area_hectares}
                    onChange={(e) =>
                      setPmKisanFacts({
                        ...pmKisanFacts,
                        total_land_area_hectares: parseFloat(e.target.value) || 0,
                      })
                    }
                    className="w-full p-2 border border-gov-border rounded bg-white text-xs min-h-[36px]"
                  />
                </div>

                {/* Institutional landholder exclusion */}
                <div className="bg-gov-bg p-3.5 rounded border border-gov-border space-y-2">
                  <label htmlFor="pmkisan-institutional" className="font-semibold text-gov-text block">
                    {t("forms.pm_kisan_institutional_label")}
                  </label>
                  <select
                    id="pmkisan-institutional"
                    value={pmKisanFacts.is_institutional_landholder ? "yes" : "no"}
                    onChange={(e) =>
                      setPmKisanFacts({
                        ...pmKisanFacts,
                        is_institutional_landholder: e.target.value === "yes",
                      })
                    }
                    className="w-full p-2 border border-gov-border rounded bg-white text-xs min-h-[36px]"
                  >
                    <option value="no">{t("forms.no")}</option>
                    <option value="yes">{t("forms.yes")}</option>
                  </select>
                </div>

                {/* Income Tax payer exclusion */}
                <div className="bg-gov-bg p-3.5 rounded border border-gov-border space-y-2">
                  <label htmlFor="pmkisan-tax" className="font-semibold text-gov-text block">
                    {t("forms.pm_kisan_tax_label")}
                  </label>
                  <select
                    id="pmkisan-tax"
                    value={pmKisanFacts.has_income_tax_payer ? "yes" : "no"}
                    onChange={(e) =>
                      setPmKisanFacts({
                        ...pmKisanFacts,
                        has_income_tax_payer: e.target.value === "yes",
                      })
                    }
                    className="w-full p-2 border border-gov-border rounded bg-white text-xs min-h-[36px]"
                  >
                    <option value="no">{t("forms.no")}</option>
                    <option value="yes">{t("forms.yes")}</option>
                  </select>
                </div>

                {/* NRI exclusion */}
                <div className="bg-gov-bg p-3.5 rounded border border-gov-border space-y-2">
                  <label htmlFor="pmkisan-nri" className="font-semibold text-gov-text block">
                    {t("forms.pm_kisan_nri_label")}
                  </label>
                  <select
                    id="pmkisan-nri"
                    value={pmKisanFacts.is_nri ? "yes" : "no"}
                    onChange={(e) =>
                      setPmKisanFacts({
                        ...pmKisanFacts,
                        is_nri: e.target.value === "yes",
                      })
                    }
                    className="w-full p-2 border border-gov-border rounded bg-white text-xs min-h-[36px]"
                  >
                    <option value="no">{t("forms.no")}</option>
                    <option value="yes">{t("forms.yes")}</option>
                  </select>
                </div>

                {/* Constitutional post */}
                <div className="bg-gov-bg p-3.5 rounded border border-gov-border space-y-2">
                  <label htmlFor="pmkisan-constitutional" className="font-semibold text-gov-text block">
                    {t("forms.pm_kisan_constitutional_label")}
                  </label>
                  <select
                    id="pmkisan-constitutional"
                    value={pmKisanFacts.has_constitutional_post_holder ? "yes" : "no"}
                    onChange={(e) =>
                      setPmKisanFacts({
                        ...pmKisanFacts,
                        has_constitutional_post_holder: e.target.value === "yes",
                      })
                    }
                    className="w-full p-2 border border-gov-border rounded bg-white text-xs min-h-[36px]"
                  >
                    <option value="no">{t("forms.no")}</option>
                    <option value="yes">{t("forms.yes")}</option>
                  </select>
                </div>
              </div>
            </fieldset>
          ) : (
            <fieldset className="space-y-4">
              <legend className="text-sm font-bold text-primary-dark border-b border-gray-100 pb-2 w-full">
                {t("forms.ssy_facts_heading")}
              </legend>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                {/* Beneficiary Gender */}
                <div className="bg-gov-bg p-3.5 rounded border border-gov-border space-y-2">
                  <label htmlFor="ssy-gender" className="font-semibold text-gov-text block">
                    {t("forms.ssy_gender_label")}
                  </label>
                  <select
                    id="ssy-gender"
                    value={ssyFacts.gender}
                    onChange={(e) => setSsyFacts({ ...ssyFacts, gender: e.target.value })}
                    className="w-full p-2 border border-gov-border rounded bg-white text-xs min-h-[36px]"
                  >
                    <option value="FEMALE">{t("forms.ssy_gender_female")}</option>
                    <option value="MALE">{t("forms.ssy_gender_male")}</option>
                  </select>
                </div>

                {/* Date of Birth */}
                <div className="bg-gov-bg p-3.5 rounded border border-gov-border space-y-2">
                  <label htmlFor="ssy-dob" className="font-semibold text-gov-text block">
                    {t("forms.ssy_dob_label")}
                  </label>
                  <input
                    id="ssy-dob"
                    type="date"
                    value={ssyFacts.date_of_birth}
                    onChange={(e) => setSsyFacts({ ...ssyFacts, date_of_birth: e.target.value })}
                    className="w-full p-2 border border-gov-border rounded bg-white text-xs font-mono min-h-[36px]"
                  />
                </div>

                {/* Indian Resident */}
                <div className="bg-gov-bg p-3.5 rounded border border-gov-border space-y-2">
                  <label htmlFor="ssy-resident" className="font-semibold text-gov-text block">
                    {t("forms.ssy_resident_label")}
                  </label>
                  <select
                    id="ssy-resident"
                    value={ssyFacts.is_indian_resident ? "yes" : "no"}
                    onChange={(e) => setSsyFacts({ ...ssyFacts, is_indian_resident: e.target.value === "yes" })}
                    className="w-full p-2 border border-gov-border rounded bg-white text-xs min-h-[36px]"
                  >
                    <option value="yes">{t("forms.yes")}</option>
                    <option value="no">{t("forms.no")}</option>
                  </select>
                </div>

                {/* Natural Guardian */}
                <div className="bg-gov-bg p-3.5 rounded border border-gov-border space-y-2">
                  <label htmlFor="ssy-guardian" className="font-semibold text-gov-text block">
                    {t("forms.ssy_natural_guardian_label")}
                  </label>
                  <select
                    id="ssy-guardian"
                    value={ssyFacts.is_natural_guardian ? "yes" : "no"}
                    onChange={(e) => setSsyFacts({ ...ssyFacts, is_natural_guardian: e.target.value === "yes" })}
                    className="w-full p-2 border border-gov-border rounded bg-white text-xs min-h-[36px]"
                  >
                    <option value="yes">{t("forms.yes")}</option>
                    <option value="no">{t("forms.no")}</option>
                  </select>
                </div>

                {/* Active SSY accounts count */}
                <div className="bg-gov-bg p-3.5 rounded border border-gov-border space-y-2">
                  <label htmlFor="ssy-accounts" className="font-semibold text-gov-text block">
                    {t("forms.ssy_accounts_count_label")}
                  </label>
                  <input
                    id="ssy-accounts"
                    type="number"
                    min="0"
                    max="5"
                    value={ssyFacts.active_ssy_accounts_count}
                    onChange={(e) =>
                      setSsyFacts({ ...ssyFacts, active_ssy_accounts_count: parseInt(e.target.value, 10) || 0 })
                    }
                    className="w-full p-2 border border-gov-border rounded bg-white text-xs min-h-[36px]"
                  />
                </div>

                {/* Account opening date */}
                <div className="bg-gov-bg p-3.5 rounded border border-gov-border space-y-2">
                  <label htmlFor="ssy-opening" className="font-semibold text-gov-text block">
                    {t("forms.ssy_opening_date_label")}
                  </label>
                  <input
                    id="ssy-opening"
                    type="date"
                    value={ssyFacts.opening_date}
                    onChange={(e) => setSsyFacts({ ...ssyFacts, opening_date: e.target.value })}
                    className="w-full p-2 border border-gov-border rounded bg-white text-xs font-mono min-h-[36px]"
                  />
                </div>
              </div>
            </fieldset>
          )}

          {/* Action Row */}
          <div className="pt-4 border-t border-gray-100 flex items-center justify-end">
            <button
              type="button"
              disabled={loading}
              onClick={handleCreateJourneyAndClaims}
              className="inline-flex items-center space-x-2 px-6 py-2.5 bg-primary hover:bg-primary-dark disabled:opacity-50 text-white rounded-md text-xs font-bold shadow-xs transition-colors focus-visible:ring-2 focus-visible:ring-primary min-h-[40px]"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                  <span>{t("common.loading")}</span>
                </>
              ) : (
                <>
                  <span>{t("forms.proceed_to_claims")}</span>
                  <ArrowRight className="w-4 h-4" aria-hidden="true" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STEP 2: REGISTERED CLAIMS & EVIDENCE WORKFLOW */}
      {/* ========================================================================= */}
      {currentStep === "claims" && (
        <div className="bg-white rounded-xl border border-gov-border p-6 sm:p-8 shadow-gov-card space-y-6">
          <div className="border-b border-gray-100 pb-4">
            <h2 className="text-lg font-bold text-primary-dark">
              {t("journey.step_2_of_4")}
            </h2>
            <p className="text-xs text-gov-secondary mt-1">
              {t("journey.step_2_of_4_desc")}
            </p>
          </div>

          <div className="space-y-4">
            {journeyClaims.length > 0 ? (
              journeyClaims.map((claim) => (
                <ClaimCard
                  key={claim.id}
                  claim={claim}
                  onAttachEvidence={handleOpenEvidenceModal}
                  onVerifyEvidence={handleVerifyEvidence}
                />
              ))
            ) : (
              <p className="text-xs text-gov-secondary py-4 text-center">
                {t("journey.no_claims")}
              </p>
            )}
          </div>

          <div className="pt-4 border-t border-gray-100 flex items-center justify-between flex-wrap gap-3">
            <button
              type="button"
              onClick={() => setCurrentStep("facts")}
              className="inline-flex items-center space-x-1.5 px-4 py-2 border border-gov-border rounded-md text-xs font-semibold text-gov-secondary hover:text-gov-text min-h-[36px] focus-visible:ring-2 focus-visible:ring-primary"
            >
              <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" />
              <span>{t("common.back")}</span>
            </button>

            <button
              type="button"
              disabled={loading}
              onClick={handleExecuteEvaluation}
              className="inline-flex items-center space-x-2 px-6 py-2.5 bg-primary hover:bg-primary-dark disabled:opacity-50 text-white rounded-md text-xs font-bold shadow-xs transition-colors min-h-[40px] focus-visible:ring-2 focus-visible:ring-primary"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                  <span>{t("common.loading")}</span>
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4" aria-hidden="true" />
                  <span>{t("journey.evaluate_now")}</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STEP 3: STATUTORY EVALUATION EXECUTION */}
      {/* ========================================================================= */}
      {currentStep === "evaluation" && (
        <div className="bg-white rounded-xl border border-gov-border p-12 shadow-gov-card text-center space-y-4">
          <Loader2 className="w-10 h-10 text-primary animate-spin mx-auto" aria-hidden="true" />
          <h3 className="text-lg font-bold text-primary-dark">
            {isHindi ? "वैधानिक पात्रता मूल्यांकन जारी है..." : "Executing Statutory Rules Evaluation..."}
          </h3>
          <p className="text-xs text-gov-secondary max-w-md mx-auto leading-relaxed">
            {isHindi
              ? "आपके द्वारा घोषित विवरणों और साक्ष्यों का मिलान भारत सरकार की राजपत्रित नीतियों से निष्पक्ष एवं पारदर्शी रूप से किया जा रहा है।"
              : "Verifying facts and declared evidence against codified statutory gazette policy rulesets without discretionary bias."}
          </p>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STEP 4: EVALUATION DECISION, GUIDANCE & EXPLAINABILITY */}
      {/* ========================================================================= */}
      {currentStep === "result" && evaluationResult && !loading && (
        <div className="space-y-6">
          <EvaluationResultCard
            evaluation={evaluationResult}
            onCompleteInformation={() => setCurrentStep("facts")}
            onReviewDocuments={() => setCurrentStep("claims")}
          />
          <ExplainabilityView evaluation={evaluationResult} />

          <div className="flex items-center justify-between pt-4">
            <button
              type="button"
              onClick={() => setCurrentStep("claims")}
              className="inline-flex items-center space-x-1.5 px-4 py-2 border border-gov-border rounded-md text-xs font-semibold text-gov-secondary hover:text-gov-text min-h-[36px] focus-visible:ring-2 focus-visible:ring-primary"
            >
              <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" />
              <span>{t("common.back")}</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setCurrentStep("facts");
                setEvaluationResult(null);
                setActiveJourney(null);
                setJourneyClaims([]);
              }}
              className="inline-flex items-center space-x-1.5 px-5 py-2.5 bg-primary hover:bg-primary-dark text-white rounded-md text-xs font-bold shadow-xs transition-colors min-h-[40px] focus-visible:ring-2 focus-visible:ring-primary"
            >
              <span>{t("common.retry")}</span>
            </button>
          </div>
        </div>
      )}

      {/* Accessible Attach Document Modal Dialog */}
      {evidenceModalClaimId && (
        <div
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-xs"
          role="dialog"
          aria-modal="true"
          aria-labelledby="evidence-modal-title"
          aria-describedby="evidence-modal-desc"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setEvidenceModalClaimId(null);
            }
          }}
        >
          <div className="bg-white rounded-xl border border-gov-border p-6 max-w-md w-full shadow-gov-modal space-y-4 animate-in zoom-in-95">
            <h3 id="evidence-modal-title" className="text-base font-bold text-primary-dark">
              {t("forms.modal_attach_title")}
            </h3>
            <p id="evidence-modal-desc" className="text-xs text-gov-secondary leading-relaxed">
              {t("forms.modal_attach_desc")}
            </p>

            {/* Explanation why evidence is needed */}
            <div className="bg-primary-50/70 border border-primary-100 rounded-lg p-3 text-xs text-primary-dark leading-relaxed flex items-start space-x-2">
              <Info className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" aria-hidden="true" />
              <span>{t("forms.modal_why_explanation")}</span>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label htmlFor="evidence-type-input" className="block font-semibold text-gov-text mb-1">
                  {t("forms.modal_evidence_type_label")}
                </label>
                <select
                  id="evidence-type-input"
                  value={evidenceTypeInput}
                  onChange={(e) => setEvidenceTypeInput(e.target.value)}
                  className="w-full p-2.5 border border-gov-border rounded bg-white text-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-primary min-h-[38px]"
                >
                  <option value="LAND_RECORD_7_12">
                    {isHindi ? "भूमि स्वामित्व अभिलेख (खतौनी / खसरा / 7-12)" : "Land Ownership Record (Khatauni / Khasra / 7-12)"}
                  </option>
                  <option value="BIRTH_CERTIFICATE">
                    {isHindi ? "जन्म प्रमाण पत्र (पंजीयक द्वारा जारी)" : "Birth Certificate (Issued by Registrar)"}
                  </option>
                  <option value="ITR_ACKNOWLEDGEMENT">
                    {isHindi ? "आयकर रिटर्न (ITR-V) पावती" : "Income Tax Return (ITR-V) Acknowledgement"}
                  </option>
                  <option value="SUPPORTING_AFFIDAVIT">
                    {isHindi ? "शपथ पत्र (स्वप्रमाणित / नोटरी)" : "Supporting Sworn Affidavit"}
                  </option>
                  <option value="SUPPORTING_DOCUMENT">
                    {isHindi ? "अन्य सहायक दस्तावेज़" : "Other Supporting Document"}
                  </option>
                </select>
              </div>

              <div>
                <label htmlFor="evidence-ref-input" className="block font-semibold text-gov-text mb-1">
                  {t("forms.modal_ref_label")}
                </label>
                <input
                  id="evidence-ref-input"
                  type="text"
                  value={evidenceRefInput}
                  onChange={(e) => setEvidenceRefInput(e.target.value)}
                  placeholder={t("forms.modal_ref_placeholder")}
                  className="w-full p-2.5 border border-gov-border rounded text-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-primary min-h-[38px]"
                />
              </div>
            </div>

            <div className="pt-3 flex items-center justify-end space-x-2">
              <button
                type="button"
                onClick={() => setEvidenceModalClaimId(null)}
                className="px-3.5 py-2 border border-gov-border rounded text-xs text-gov-secondary hover:text-gov-text min-h-[36px] focus-visible:ring-2 focus-visible:ring-primary"
              >
                {t("forms.cancel")}
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={handleAttachEvidence}
                className="px-4 py-2 bg-primary hover:bg-primary-dark disabled:opacity-50 text-white rounded text-xs font-bold transition-colors min-h-[36px] focus-visible:ring-2 focus-visible:ring-primary"
              >
                {loading ? t("common.loading") : t("forms.attach_artifact")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function EligibilityJourneyPage() {
  return (
    <Suspense fallback={<div className="gov-container py-12"><LoadingState /></div>}>
      <EligibilityJourneyContent />
    </Suspense>
  );
}
