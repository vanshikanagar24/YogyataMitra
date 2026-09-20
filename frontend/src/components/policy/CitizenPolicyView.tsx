"use client";

import React from "react";
import Link from "next/link";
import { Calendar, BookOpen, ExternalLink, ArrowRight, ShieldCheck } from "lucide-react";
import { PolicyVersionDetail } from "../../types/policy";
import { useLanguage } from "../../context/LanguageContext";
import {
  getPolicyStatutorySummary,
  getPolicyTimelineStatus,
  getTimelineStatusLabel,
} from "../../utils/rulePresentation";

interface CitizenPolicyViewProps {
  policy: PolicyVersionDetail;
  index?: number;
}

export const CitizenPolicyView: React.FC<CitizenPolicyViewProps> = ({ policy, index = 0 }) => {
  const { isHindi, t } = useLanguage();

  const schemeDisplayName =
    policy.scheme_code === "PM_KISAN"
      ? "PM-KISAN"
      : policy.scheme_code === "SSY"
      ? isHindi
        ? "सुकन्या समृद्धि योजना (SSY)"
        : "Sukanya Samriddhi Yojana (SSY)"
      : policy.scheme_code;

  const timelineStatus = getPolicyTimelineStatus(policy.effective_to, index);
  const timelineLabel = getTimelineStatusLabel(timelineStatus, isHindi);
  const { summary, reference } = getPolicyStatutorySummary(
    policy.scheme_code,
    policy.version_code,
    isHindi
  );

  const isCurrent = timelineStatus === "CURRENT";

  return (
    <div
      className={`bg-white rounded-xl border p-6 space-y-4 transition-shadow hover:shadow-md ${
        isCurrent ? "border-primary-200 ring-1 ring-primary-100 shadow-gov-card" : "border-gov-border shadow-xs"
      }`}
    >
      {/* Header with Timeline Status Badge */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-gray-100 pb-3.5">
        <div>
          <div className="flex items-center space-x-2 mb-1.5 flex-wrap gap-y-1">
            <span
              className={`text-xs font-extrabold px-2.5 py-0.5 rounded border ${
                isCurrent
                  ? "bg-primary-50 text-primary-dark border-primary-200"
                  : "bg-gray-50 text-gov-secondary border-gray-200"
              }`}
            >
              {policy.version_code}
            </span>
            <span
              className={`text-xs font-semibold px-2 py-0.5 rounded ${
                isCurrent
                  ? "bg-success-50 text-success-800 border border-success-200"
                  : "bg-gray-100 text-gov-secondary"
              }`}
            >
              {timelineLabel}
            </span>
            <span className="text-xs text-gov-secondary font-semibold">{schemeDisplayName}</span>
          </div>
          <h3 className="text-base font-bold text-gov-text leading-snug">{policy.source_title}</h3>
        </div>
      </div>

      {/* Statutory Summary in Plain Citizen Language */}
      <div className="bg-gov-bg/60 rounded-lg p-3.5 border border-gov-border/60 text-xs text-gov-text leading-relaxed">
        <p>{summary}</p>
      </div>

      {/* Effective Period and Official Reference */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-gov-secondary">
        <div className="flex items-center space-x-2">
          <Calendar className="w-4 h-4 text-primary flex-shrink-0" aria-hidden="true" />
          <span>
            {t("claims.policy_effective_from")}{" "}
            <strong className="text-gov-text font-semibold">
              {policy.effective_from} {t("common.to")} {policy.effective_to || t("common.present")}
            </strong>
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <BookOpen className="w-4 h-4 text-primary flex-shrink-0" aria-hidden="true" />
          <span>
            {isHindi ? "राजपत्र / आदेश संदर्भ:" : "Gazette / Order Ref:"}{" "}
            <strong className="text-gov-text font-semibold">
              {policy.source_document_identifier || reference}
            </strong>
          </span>
        </div>
      </div>

      {/* Citizen Action Links: View policy details and View official source */}
      <div className="pt-2 border-t border-gray-100 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center space-x-1.5 text-xs text-gov-secondary">
          <ShieldCheck className="w-3.5 h-3.5 text-success" aria-hidden="true" />
          <span>{isHindi ? "आधिकारिक वैधानिक नियम" : "Official Statutory Policy"}</span>
        </div>

        <div className="flex items-center space-x-3">
          <Link
            href={`/schemes/${policy.scheme_code}`}
            className="inline-flex items-center space-x-1 text-xs font-bold text-primary hover:text-primary-dark hover:underline focus-visible:ring-2 focus-visible:ring-primary rounded p-1"
          >
            <span>[ {t("claims.view_policy_details")} ]</span>
            <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
          </Link>

          {policy.source_url && (
            <a
              href={policy.source_url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`${t("claims.view_official_source")} — ${policy.source_title} (${t(
                "a11y.external_link"
              )})`}
              className="inline-flex items-center space-x-1 text-xs font-semibold text-gov-secondary hover:text-gov-text focus-visible:ring-2 focus-visible:ring-primary rounded p-1"
            >
              <span>[ {t("claims.view_official_source")} ]</span>
              <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
};
