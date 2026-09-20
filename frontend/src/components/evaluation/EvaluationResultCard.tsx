"use client";

import React from "react";
import Link from "next/link";
import {
  CheckCircle2,
  XCircle,
  HelpCircle,
  FileText,
  AlertCircle,
  Calendar,
  Shield,
  ArrowRight,
  ExternalLink,
  BookOpen,
} from "lucide-react";
import { EligibilityResult } from "../../types/enums";
import { EvaluationResponse } from "../../types/evaluation";
import { StatusBadge } from "../common/StatusBadge";
import { useLanguage } from "../../context/LanguageContext";
import { NextActionGuidance } from "./NextActionGuidance";

interface EvaluationResultCardProps {
  evaluation: EvaluationResponse;
  onViewWhy?: () => void;
  onCompleteInformation?: () => void;
  onReviewDocuments?: () => void;
}

export const EvaluationResultCard: React.FC<EvaluationResultCardProps> = ({
  evaluation,
  onViewWhy,
  onCompleteInformation,
  onReviewDocuments,
}) => {
  const { isHindi, t } = useLanguage();

  const getResultStyle = () => {
    switch (evaluation.overall_result) {
      case EligibilityResult.ELIGIBLE:
        return {
          border: "border-green-300",
          bg: "bg-green-50/50",
          icon: CheckCircle2,
          iconColor: "text-success",
        };
      case EligibilityResult.INELIGIBLE:
        return {
          border: "border-red-300",
          bg: "bg-red-50/50",
          icon: XCircle,
          iconColor: "text-danger",
        };
      case EligibilityResult.INSUFFICIENT_INFORMATION:
        return {
          border: "border-amber-300",
          bg: "bg-amber-50/50",
          icon: HelpCircle,
          iconColor: "text-warning",
        };
      case EligibilityResult.VERIFICATION_REQUIRED:
        return {
          border: "border-blue-300",
          bg: "bg-blue-50/50",
          icon: FileText,
          iconColor: "text-info",
        };
      case EligibilityResult.MANUAL_REVIEW_REQUIRED:
      default:
        return {
          border: "border-purple-300",
          bg: "bg-purple-50/50",
          icon: AlertCircle,
          iconColor: "text-purple-600",
        };
    }
  };

  const style = getResultStyle();
  const Icon = style.icon;
  const reasons = isHindi ? evaluation.reasons_hi : evaluation.reasons_en;

  // Resolve human-readable scheme name
  const schemeDisplayName =
    evaluation.scheme_code === "PM_KISAN"
      ? "PM-KISAN"
      : evaluation.scheme_code === "SSY"
      ? isHindi
        ? "सुकन्या समृद्धि योजना (SSY)"
        : "Sukanya Samriddhi Yojana (SSY)"
      : evaluation.scheme_code;

  // Resolve official statutory source
  const provenance = (evaluation.trace as any)?.provenance;
  const officialSourceTitle =
    provenance?.source_title ||
    (evaluation.scheme_code === "PM_KISAN"
      ? "Operational Guidelines for Pradhan Mantri Kisan Samman Nidhi (PM-KISAN) 2023"
      : evaluation.scheme_code === "SSY"
      ? "Sukanya Samriddhi Account Scheme, 2019 (Ministry of Finance / Gazette of India)"
      : "Official Statutory Gazette Guidelines");

  return (
    <div className={`rounded-xl border-2 ${style.border} ${style.bg} p-6 sm:p-8 shadow-gov-elevated bg-white space-y-6`}>
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-100 pb-5">
        <div className="flex items-start space-x-3.5">
          <div className="mt-0.5 p-2 rounded-lg bg-white border border-gov-border shadow-xs">
            <Icon className={`w-8 h-8 ${style.iconColor}`} aria-hidden="true" />
          </div>
          <div>
            <span className="text-xs font-bold text-gov-secondary tracking-wide uppercase">
              {t("results.decision_title")}
            </span>
            <h2 className="text-2xl font-bold text-primary-dark">
              {t(`results.${evaluation.overall_result}`)}
            </h2>
            <p className="text-xs text-gov-secondary mt-1">
              {t(`results.${evaluation.overall_result}_desc`)}
            </p>
          </div>
        </div>

        <StatusBadge status={evaluation.overall_result} size="lg" />
      </div>

      {/* Primary Reasons */}
      {reasons && reasons.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-bold uppercase tracking-wider text-gov-secondary">
            {t("results.primary_basis")}
          </h4>
          <ul className="space-y-1.5">
            {reasons.map((r, i) => (
              <li key={i} className="flex items-start space-x-2 text-sm text-gov-text font-medium leading-relaxed">
                <span className="text-primary font-bold mt-0.5">•</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommended Next Steps Guidance */}
      <NextActionGuidance
        overall_result={evaluation.overall_result}
        scheme_code={evaluation.scheme_code}
        missing_fields={evaluation.missing_fields}
        onCompleteInformation={onCompleteInformation}
        onReviewDocuments={onReviewDocuments}
      />

      {/* Citizen Policy Presentation Banner — Strictly Clean Citizen Information */}
      <div className="bg-primary-50/70 rounded-xl p-5 border border-primary-100 space-y-3.5">
        <div className="flex items-center space-x-2">
          <Shield className="w-4 h-4 text-primary flex-shrink-0" aria-hidden="true" />
          <span className="text-xs font-bold text-primary-dark uppercase tracking-wider">
            {t("claims.policy_used_assessment")}
          </span>
        </div>

        <div>
          <h3 className="text-lg font-extrabold text-primary-dark tracking-tight">
            {schemeDisplayName}
          </h3>
          <p className="text-xs text-gov-secondary font-medium mt-0.5">
            {t("claims.policy_version_label")}{" "}
            <span className="font-semibold text-primary">{evaluation.policy_version_code}</span>
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-primary-100/60 text-xs">
          <div className="flex items-center space-x-2 text-gov-secondary">
            <Calendar className="w-3.5 h-3.5 text-primary flex-shrink-0" aria-hidden="true" />
            <span>
              {t("claims.policy_effective_from")}{" "}
              <strong className="text-gov-text font-semibold">{evaluation.effective_from}</strong>
            </span>
          </div>

          <div className="flex items-center space-x-2 text-gov-secondary">
            <Calendar className="w-3.5 h-3.5 text-primary flex-shrink-0" aria-hidden="true" />
            <span>
              {t("claims.assessment_date_label")}{" "}
              <strong className="text-gov-text font-semibold">{evaluation.evaluation_date}</strong>
            </span>
          </div>
        </div>

        <div className="pt-2 border-t border-primary-100/60 space-y-1">
          <div className="flex items-center space-x-1.5 text-xs text-gov-secondary">
            <BookOpen className="w-3.5 h-3.5 text-primary flex-shrink-0" aria-hidden="true" />
            <span className="font-semibold text-gov-text">{t("claims.official_source_label")}</span>
          </div>
          <p className="text-xs text-gov-secondary leading-relaxed pl-5">
            {officialSourceTitle}
          </p>
        </div>

        <div className="pt-2 flex justify-end">
          <Link
            href={`/schemes/${evaluation.scheme_code}`}
            className="inline-flex items-center space-x-1.5 text-xs font-bold text-primary hover:text-primary-dark hover:underline focus-visible:ring-2 focus-visible:ring-primary rounded py-1 px-2.5 bg-white border border-primary-100 shadow-xs"
          >
            <span>[ {t("claims.view_policy_details")} ]</span>
            <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
          </Link>
        </div>
      </div>

      {/* Action Footer */}
      {onViewWhy && (
        <div className="pt-2 flex justify-end">
          <button
            type="button"
            onClick={onViewWhy}
            className="px-5 py-2.5 bg-primary hover:bg-primary-dark text-white rounded-md text-xs font-bold transition-colors inline-flex items-center space-x-2 shadow-xs focus-visible:ring-2 focus-visible:ring-primary min-h-[38px]"
          >
            <span>{t("results.why_result")}</span>
            <ArrowRight className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
      )}
    </div>
  );
};
