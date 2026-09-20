"use client";

import React from "react";
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  HelpCircle,
  FileText,
  Clock,
  Check,
  Sparkles,
} from "lucide-react";
import {
  EligibilityResult,
  EvidenceStatus,
  JourneyState,
  ClaimStatus,
} from "../../types/enums";
import { useLanguage } from "../../context/LanguageContext";

interface StatusBadgeProps {
  status: EligibilityResult | EvidenceStatus | JourneyState | ClaimStatus | string;
  size?: "sm" | "md" | "lg";
  showIcon?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = "md",
  showIcon = true,
}) => {
  const { t, isHindi } = useLanguage();

  const sizeClasses = {
    sm: "text-xs px-2 py-0.5",
    md: "text-xs sm:text-sm px-2.5 py-1",
    lg: "text-sm sm:text-base px-3 py-1.5 font-semibold",
  }[size];

  // Eligibility Results
  if (status === EligibilityResult.ELIGIBLE) {
    return (
      <span className={`inline-flex items-center space-x-1.5 rounded-md font-semibold bg-success-50 text-success-700 border border-green-200 ${sizeClasses}`}>
        {showIcon && <CheckCircle2 className="w-4 h-4 text-success-700 flex-shrink-0" aria-hidden="true" />}
        <span>{t("results.ELIGIBLE")}</span>
      </span>
    );
  }

  if (status === EligibilityResult.INELIGIBLE) {
    return (
      <span className={`inline-flex items-center space-x-1.5 rounded-md font-semibold bg-danger-50 text-danger-700 border border-red-200 ${sizeClasses}`}>
        {showIcon && <XCircle className="w-4 h-4 text-danger-700 flex-shrink-0" aria-hidden="true" />}
        <span>{t("results.INELIGIBLE")}</span>
      </span>
    );
  }

  if (status === EligibilityResult.INSUFFICIENT_INFORMATION) {
    return (
      <span className={`inline-flex items-center space-x-1.5 rounded-md font-semibold bg-warning-50 text-warning-700 border border-amber-200 ${sizeClasses}`}>
        {showIcon && <HelpCircle className="w-4 h-4 text-warning-700 flex-shrink-0" aria-hidden="true" />}
        <span>{t("results.INSUFFICIENT_INFORMATION")}</span>
      </span>
    );
  }

  if (status === EligibilityResult.VERIFICATION_REQUIRED) {
    return (
      <span className={`inline-flex items-center space-x-1.5 rounded-md font-semibold bg-info-50 text-info-700 border border-blue-200 ${sizeClasses}`}>
        {showIcon && <FileText className="w-4 h-4 text-info-700 flex-shrink-0" aria-hidden="true" />}
        <span>{t("results.VERIFICATION_REQUIRED")}</span>
      </span>
    );
  }

  if (status === EligibilityResult.MANUAL_REVIEW_REQUIRED) {
    return (
      <span className={`inline-flex items-center space-x-1.5 rounded-md font-semibold bg-purple-50 text-purple-700 border border-purple-200 ${sizeClasses}`}>
        {showIcon && <AlertCircle className="w-4 h-4 text-purple-700 flex-shrink-0" aria-hidden="true" />}
        <span>{t("results.MANUAL_REVIEW_REQUIRED")}</span>
      </span>
    );
  }

  // Evidence Status
  if (status === EvidenceStatus.VERIFIED) {
    return (
      <span className={`inline-flex items-center space-x-1.5 rounded-md font-medium bg-green-50 text-green-700 border border-green-200 ${sizeClasses}`}>
        {showIcon && <Check className="w-3.5 h-3.5" aria-hidden="true" />}
        <span>{isHindi ? "दस्तावेज़ सत्यापित" : t("journey.status_verified")}</span>
      </span>
    );
  }

  if (status === EvidenceStatus.REJECTED) {
    return (
      <span className={`inline-flex items-center space-x-1.5 rounded-md font-medium bg-red-50 text-red-700 border border-red-200 ${sizeClasses}`}>
        {showIcon && <XCircle className="w-3.5 h-3.5" aria-hidden="true" />}
        <span>{isHindi ? "दस्तावेज़ अस्वीकृत" : t("journey.status_rejected")}</span>
      </span>
    );
  }

  if (status === EvidenceStatus.PENDING) {
    return (
      <span className={`inline-flex items-center space-x-1.5 rounded-md font-medium bg-amber-50 text-amber-700 border border-amber-200 ${sizeClasses}`}>
        {showIcon && <Clock className="w-3.5 h-3.5" aria-hidden="true" />}
        <span>{t("journey.status_pending")}</span>
      </span>
    );
  }

  // Claim Statuses
  const strStatus = String(status).toUpperCase();
  if (strStatus === "CLAIMED") {
    return (
      <span className={`inline-flex items-center space-x-1.5 rounded-md font-medium bg-blue-50 text-blue-700 border border-blue-200 ${sizeClasses}`}>
        {showIcon && <Sparkles className="w-3.5 h-3.5 text-blue-600" aria-hidden="true" />}
        <span>{isHindi ? "जानकारी दी गई" : "Information provided"}</span>
      </span>
    );
  }

  if (strStatus === "UNKNOWN") {
    return (
      <span className={`inline-flex items-center space-x-1.5 rounded-md font-medium bg-gray-100 text-gray-700 border border-gray-200 ${sizeClasses}`}>
        {showIcon && <HelpCircle className="w-3.5 h-3.5 text-gray-500" aria-hidden="true" />}
        <span>{isHindi ? "जानकारी उपलब्ध नहीं है" : "Information unavailable"}</span>
      </span>
    );
  }

  // Journey States
  const journeyStateMap: Record<string, { en: string; hi: string }> = {
    FACTS_COLLECTED: { en: "Facts Collected", hi: "तथ्य एकत्रित" },
    CLAIMS_REGISTERED: { en: "Claims Registered", hi: "दावे पंजीकृत" },
    EVIDENCE_ATTACHED: { en: "Evidence Attached", hi: "साक्ष्य संलग्न" },
    EVIDENCE_VERIFIED: { en: "Evidence Verified", hi: "साक्ष्य सत्यापित" },
    EVALUATION_COMPLETED: { en: "Evaluation Completed", hi: "मूल्यांकन संपन्न" },
  };

  if (journeyStateMap[strStatus]) {
    return (
      <span className={`inline-flex items-center space-x-1.5 rounded-md font-medium bg-gray-100 text-gray-800 border border-gray-200 ${sizeClasses}`}>
        <span>{isHindi ? journeyStateMap[strStatus].hi : journeyStateMap[strStatus].en}</span>
      </span>
    );
  }

  // Default fallback
  return (
    <span className={`inline-flex items-center space-x-1.5 rounded-md font-medium bg-gray-100 text-gray-800 border border-gray-200 ${sizeClasses}`}>
      <span>{strStatus.replace(/_/g, " ")}</span>
    </span>
  );
};
