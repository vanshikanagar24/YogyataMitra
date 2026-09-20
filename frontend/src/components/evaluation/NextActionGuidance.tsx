"use client";

import React from "react";
import Link from "next/link";
import {
  ExternalLink,
  ArrowRight,
  CheckCircle2,
  FileCheck,
  Building,
  HelpCircle,
  FileWarning,
} from "lucide-react";
import { EligibilityResult } from "../../types/enums";
import { useLanguage } from "../../context/LanguageContext";
import { getFriendlyFieldTitle } from "../../utils/claimPresentation";

interface NextActionGuidanceProps {
  overall_result: EligibilityResult;
  scheme_code: string;
  missing_fields?: string[];
  onCompleteInformation?: () => void;
  onReviewDocuments?: () => void;
}

export const NextActionGuidance: React.FC<NextActionGuidanceProps> = ({
  overall_result,
  scheme_code,
  missing_fields,
  onCompleteInformation,
  onReviewDocuments,
}) => {
  const { isHindi, t } = useLanguage();

  const isPmKisan = scheme_code === "PM_KISAN";
  const isSSY = scheme_code === "SSY";

  if (overall_result === EligibilityResult.ELIGIBLE) {
    return (
      <div className="bg-green-50/70 border border-green-200 rounded-xl p-6 space-y-4">
        <div className="flex items-start space-x-3">
          <CheckCircle2 className="w-5 h-5 text-success-700 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <h3 className="text-base font-bold text-success-900">
              {t("next_actions.eligible_heading")}
            </h3>
            <p className="text-xs text-gov-secondary mt-1 leading-relaxed">
              {t("next_actions.eligible_desc")}
            </p>
          </div>
        </div>

        {/* Statutory Document Guidance */}
        <div className="bg-white/90 rounded-lg p-3.5 border border-green-200 text-xs flex items-start space-x-2 text-gov-text">
          <FileCheck className="w-4 h-4 text-success-700 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <p className="leading-relaxed">
            {t("next_actions.document_guidance")}
          </p>
        </div>

        {/* Action Link & Offline Note */}
        {isSSY ? (
          <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <a
              href="https://www.indiapost.gov.in/Financial/Pages/Content/Sukanya-Samriddhi-Account.aspx"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-2 px-5 py-2.5 bg-success-700 hover:bg-success-800 text-white rounded-md text-xs font-bold shadow-xs transition-colors focus-visible:ring-2 focus-visible:ring-success-700 min-h-[38px]"
            >
              <span>{t("next_actions.ssy_info_cta")}</span>
              <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
            </a>
            <span className="text-xs text-gov-secondary max-w-md">
              {t("next_actions.ssy_offline_note")}
            </span>
          </div>
        ) : (
          <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <a
              href={isPmKisan ? "https://pmkisan.gov.in" : "https://www.india.gov.in"}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-2 px-5 py-2.5 bg-success-700 hover:bg-success-800 text-white rounded-md text-xs font-bold shadow-xs transition-colors focus-visible:ring-2 focus-visible:ring-success-700 min-h-[38px]"
            >
              <span>{t("next_actions.eligible_cta")}</span>
              <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
            </a>
            <span className="text-xs text-gov-secondary">
              {t("next_actions.eligible_offline")}
            </span>
          </div>
        )}
      </div>
    );
  }

  if (overall_result === EligibilityResult.INELIGIBLE) {
    return (
      <div className="bg-red-50/70 border border-red-200 rounded-xl p-6 space-y-4">
        <div className="flex items-start space-x-3">
          <FileWarning className="w-5 h-5 text-danger-700 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <h3 className="text-base font-bold text-danger-900">
              {t("next_actions.ineligible_heading")}
            </h3>
            <p className="text-xs text-gov-secondary mt-1 leading-relaxed">
              {t("next_actions.ineligible_desc")}
            </p>
          </div>
        </div>

        <div className="pt-2 flex items-center space-x-3">
          <Link
            href="/schemes"
            className="inline-flex items-center space-x-2 px-5 py-2.5 bg-primary hover:bg-primary-dark text-white rounded-md text-xs font-bold shadow-xs transition-colors focus-visible:ring-2 focus-visible:ring-primary min-h-[38px]"
          >
            <span>{t("next_actions.ineligible_cta")}</span>
            <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
          </Link>
        </div>
      </div>
    );
  }

  if (overall_result === EligibilityResult.INSUFFICIENT_INFORMATION) {
    return (
      <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-6 space-y-4">
        <div className="flex items-start space-x-3">
          <HelpCircle className="w-5 h-5 text-warning-700 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <h3 className="text-base font-bold text-amber-900">
              {t("next_actions.insufficient_heading")}
            </h3>
            <p className="text-xs text-gov-secondary mt-1 leading-relaxed">
              {t("next_actions.insufficient_desc")}
            </p>
          </div>
        </div>

        {missing_fields && missing_fields.length > 0 && (
          <div className="bg-white rounded-lg p-3 border border-amber-200 text-xs">
            <span className="font-bold text-gov-text block mb-1.5">
              {isHindi ? "आवश्यक अपूर्ण विवरण:" : "Required Missing Information:"}
            </span>
            <div className="flex flex-wrap gap-1.5">
              {missing_fields.map((f, idx) => (
                <span key={idx} className="bg-amber-100 text-amber-900 font-semibold px-2 py-0.5 rounded">
                  {getFriendlyFieldTitle(f, isHindi)}
                </span>
              ))}
            </div>
          </div>
        )}

        {onCompleteInformation && (
          <div className="pt-2">
            <button
              type="button"
              onClick={onCompleteInformation}
              className="inline-flex items-center space-x-2 px-5 py-2.5 bg-warning-700 hover:bg-warning-800 text-white rounded-md text-xs font-bold shadow-xs transition-colors focus-visible:ring-2 focus-visible:ring-warning-700 min-h-[38px]"
            >
              <span>{t("next_actions.insufficient_cta")}</span>
              <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          </div>
        )}
      </div>
    );
  }

  if (overall_result === EligibilityResult.VERIFICATION_REQUIRED) {
    return (
      <div className="bg-blue-50/70 border border-blue-200 rounded-xl p-6 space-y-4">
        <div className="flex items-start space-x-3">
          <FileCheck className="w-5 h-5 text-info flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <h3 className="text-base font-bold text-blue-900">
              {t("next_actions.verification_heading")}
            </h3>
            <p className="text-xs text-gov-secondary mt-1 leading-relaxed">
              {t("next_actions.verification_desc")}
            </p>
          </div>
        </div>

        {/* Verification Disclaimer */}
        <div className="bg-white/80 rounded-lg p-3 border border-blue-200 text-xs text-gov-secondary leading-relaxed">
          {t("next_actions.verification_disclaimer")}
        </div>

        {onReviewDocuments && (
          <div className="pt-2">
            <button
              type="button"
              onClick={onReviewDocuments}
              className="inline-flex items-center space-x-2 px-5 py-2.5 bg-primary hover:bg-primary-dark text-white rounded-md text-xs font-bold shadow-xs transition-colors focus-visible:ring-2 focus-visible:ring-primary min-h-[38px]"
            >
              <span>{t("next_actions.verification_cta")}</span>
              <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          </div>
        )}
      </div>
    );
  }

  // MANUAL_REVIEW_REQUIRED or default
  return (
    <div className="bg-purple-50/70 border border-purple-200 rounded-xl p-6 space-y-4">
      <div className="flex items-start space-x-3">
        <Building className="w-5 h-5 text-purple-700 flex-shrink-0 mt-0.5" aria-hidden="true" />
        <div>
          <h3 className="text-base font-bold text-purple-900">
            {t("next_actions.manual_heading")}
          </h3>
          <p className="text-xs text-gov-secondary mt-1 leading-relaxed">
            {t("next_actions.manual_desc")}
          </p>
        </div>
      </div>

      <div className="pt-2">
        <a
          href="https://locator.csccloud.in/"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center space-x-2 px-5 py-2.5 bg-purple-700 hover:bg-purple-800 text-white rounded-md text-xs font-bold shadow-xs transition-colors focus-visible:ring-2 focus-visible:ring-purple-700 min-h-[38px]"
        >
          <span>{t("next_actions.csc_locator_cta")}</span>
          <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
        </a>
      </div>
    </div>
  );
};
