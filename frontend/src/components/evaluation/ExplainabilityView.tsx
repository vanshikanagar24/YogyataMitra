"use client";

import React from "react";
import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  ShieldCheck,
  FileQuestion,
  BookOpen,
  ExternalLink,
  ArrowRight,
} from "lucide-react";
import { EvaluationResponse } from "../../types/evaluation";
import { useLanguage } from "../../context/LanguageContext";
import { getFriendlyFieldTitle, sanitizeCitizenMessage } from "../../utils/claimPresentation";
import { getFriendlyRuleTitle, getFriendlyRuleExplanation } from "../../utils/rulePresentation";

interface ExplainabilityViewProps {
  evaluation: EvaluationResponse;
}

export const ExplainabilityView: React.FC<ExplainabilityViewProps> = ({ evaluation }) => {
  const { isHindi, t } = useLanguage();

  const provenance = (evaluation.trace as any)?.provenance;
  const officialSourceTitle =
    provenance?.source_title ||
    (evaluation.scheme_code === "PM_KISAN"
      ? "Operational Guidelines for Pradhan Mantri Kisan Samman Nidhi (PM-KISAN) 2023"
      : evaluation.scheme_code === "SSY"
      ? "Sukanya Samriddhi Account Scheme, 2019 (Ministry of Finance / Gazette of India)"
      : "Official Statutory Gazette Guidelines");

  const officialSourceUrl = provenance?.source_url || null;

  return (
    <div
      id="explainability-section"
      className="bg-white rounded-xl border border-gov-border p-6 shadow-gov-card space-y-6"
    >
      {/* 1. Header: Why This Result */}
      <div className="border-b border-gov-border pb-3">
        <h3 className="text-lg font-bold text-primary-dark flex items-center space-x-2">
          <ShieldCheck className="w-5 h-5 text-primary" aria-hidden="true" />
          <span>{t("results.why_result")}</span>
        </h3>
        <p className="text-xs text-gov-secondary mt-1">
          {t("results.why_result_desc")}
        </p>
      </div>

      {/* 2. Blockers & Disqualifications */}
      {evaluation.blockers && evaluation.blockers.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-danger-700 flex items-center space-x-1.5">
            <AlertTriangle className="w-4 h-4 text-danger" aria-hidden="true" />
            <span>
              {t("results.blockers_title")} ({evaluation.blockers.length})
            </span>
          </h4>
          <div className="space-y-3">
            {evaluation.blockers.map((blocker, idx) => (
              <div
                key={idx}
                className="bg-red-50/80 border border-red-200 rounded-lg p-4 text-xs text-gov-text space-y-1.5 shadow-xs"
              >
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold text-danger-800">
                    {blocker.field_path
                      ? getFriendlyFieldTitle(blocker.field_path, isHindi)
                      : t("results.blockers_title")}
                  </span>
                </div>

                <p className="font-medium text-gov-text text-sm leading-relaxed">
                  {sanitizeCitizenMessage(
                    isHindi ? blocker.message_hi : blocker.message_en,
                    isHindi
                  )}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Missing Information / Required Fields */}
      {evaluation.missing_fields && evaluation.missing_fields.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-bold uppercase tracking-wider text-warning-700 flex items-center space-x-1.5">
            <HelpCircle className="w-4 h-4 text-warning" aria-hidden="true" />
            <span>{t("results.missing_fields_title")}</span>
          </h4>
          <div className="flex flex-wrap gap-2">
            {evaluation.missing_fields.map((f, i) => (
              <span
                key={i}
                className="inline-flex items-center space-x-1.5 text-xs px-3 py-1.5 rounded-md bg-amber-50 text-warning-800 border border-amber-200 font-medium"
              >
                <FileQuestion className="w-3.5 h-3.5 text-warning-700" aria-hidden="true" />
                <span>{getFriendlyFieldTitle(f, isHindi)}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 4. Statutory Criteria Satisfied */}
      {evaluation.satisfied_rules && evaluation.satisfied_rules.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-success-700 flex items-center space-x-1.5">
            <CheckCircle2 className="w-4 h-4 text-success" aria-hidden="true" />
            <span>
              {t("results.satisfied_rules_title")} ({evaluation.satisfied_rules.length})
            </span>
          </h4>
          <div className="bg-green-50/70 border border-green-200 rounded-lg p-3.5 text-xs text-success-800 space-y-2">
            <p className="font-medium leading-relaxed">
              {isHindi
                ? `आपके द्वारा प्रदान किए गए विवरणों के आधार पर योजना के ${evaluation.satisfied_rules.length} वैधानिक मानदंड पूर्णतः संतुष्ट पाए गए हैं।`
                : `Based on your provided details, ${evaluation.satisfied_rules.length} statutory criteria for this scheme have been verified as satisfied.`}
            </p>

            {/* List key friendly satisfied rule descriptions */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 border-t border-green-200/60">
              {evaluation.satisfied_rules.map((ruleId, i) => (
                <div key={i} className="flex items-start space-x-1.5 text-[11px] text-success-900">
                  <span className="text-success-600 font-bold">•</span>
                  <span>{getFriendlyRuleTitle(ruleId, isHindi)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 5. Statutory Policy Provenance & Official Source */}
      <div className="pt-4 border-t border-gray-100 space-y-3">
        <h4 className="text-xs font-bold uppercase tracking-wider text-gov-secondary flex items-center space-x-1.5">
          <BookOpen className="w-4 h-4 text-primary" aria-hidden="true" />
          <span>{t("results.policy_provenance_title")}</span>
        </h4>
        <div className="bg-gray-50 rounded-lg p-4 border border-gov-border text-xs space-y-2.5">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <span className="font-bold text-primary-dark">
              {evaluation.scheme_code === "PM_KISAN"
                ? "PM-KISAN"
                : evaluation.scheme_code === "SSY"
                ? isHindi
                  ? "सुकन्या समृद्धि योजना (SSY)"
                  : "Sukanya Samriddhi Yojana (SSY)"
                : evaluation.scheme_code}{" "}
              — {evaluation.policy_version_code}
            </span>
            <span className="text-gov-secondary font-medium">
              {t("results.effective")} {evaluation.effective_from} {t("common.to")}{" "}
              {evaluation.effective_to || t("common.present")}
            </span>
          </div>

          <p className="text-gov-secondary leading-relaxed text-xs">
            {officialSourceTitle}
          </p>

          <div className="pt-2 border-t border-gray-200 flex items-center justify-between flex-wrap gap-2">
            <Link
              href={`/schemes/${evaluation.scheme_code}`}
              className="inline-flex items-center space-x-1 text-xs font-bold text-primary hover:text-primary-dark hover:underline"
            >
              <span>[ {t("claims.view_policy_details")} ]</span>
              <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </Link>

            {officialSourceUrl && (
              <a
                href={officialSourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-1 text-xs font-semibold text-gov-secondary hover:text-gov-text"
              >
                <span>[ {t("claims.view_official_source")} ]</span>
                <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
