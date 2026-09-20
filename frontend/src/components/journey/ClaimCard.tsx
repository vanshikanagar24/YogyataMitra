"use client";

import React from "react";
import { Check, FilePlus, Sparkles, Clock, AlertCircle } from "lucide-react";
import { JourneyClaim } from "../../types/journey";
import { useLanguage } from "../../context/LanguageContext";
import { EvidenceCard } from "./EvidenceCard";
import { getClaimPresentation } from "../../utils/claimPresentation";

interface ClaimCardProps {
  claim: JourneyClaim;
  onAttachEvidence?: (claimId: string) => void;
  onVerifyEvidence?: (evidenceId: string) => void;
}

export const ClaimCard: React.FC<ClaimCardProps> = ({
  claim,
  onAttachEvidence,
  onVerifyEvidence,
}) => {
  const { isHindi, t } = useLanguage();
  const pres = getClaimPresentation(claim.claim_type, claim.value_json, isHindi);

  const getStatusBadge = () => {
    const status = (claim.status || "").toUpperCase();
    if (status === "VERIFIED") {
      return (
        <span className="inline-flex items-center space-x-1 text-xs px-2.5 py-0.5 rounded-full font-semibold bg-green-50 text-green-700 border border-green-200">
          <Check className="w-3.5 h-3.5 text-green-600" aria-hidden="true" />
          <span>{pres.statusLabel}</span>
        </span>
      );
    }
    if (status === "PENDING") {
      return (
        <span className="inline-flex items-center space-x-1 text-xs px-2.5 py-0.5 rounded-full font-medium bg-amber-50 text-amber-700 border border-amber-200">
          <Clock className="w-3.5 h-3.5 text-amber-600" aria-hidden="true" />
          <span>{pres.statusLabel}</span>
        </span>
      );
    }
    if (status === "REJECTED") {
      return (
        <span className="inline-flex items-center space-x-1 text-xs px-2.5 py-0.5 rounded-full font-medium bg-red-50 text-red-700 border border-red-200">
          <AlertCircle className="w-3.5 h-3.5 text-red-600" aria-hidden="true" />
          <span>{pres.statusLabel}</span>
        </span>
      );
    }
    // Default CLAIMED
    return (
      <span className="inline-flex items-center space-x-1 text-xs px-2.5 py-0.5 rounded-full font-medium bg-blue-50 text-blue-700 border border-blue-200">
        <Sparkles className="w-3.5 h-3.5 text-blue-600" aria-hidden="true" />
        <span>{pres.statusLabel}</span>
      </span>
    );
  };

  return (
    <div
      data-claim-type={claim.claim_type}
      className="bg-white rounded-xl border border-gov-border p-5 shadow-gov-card space-y-4 transition-shadow hover:shadow-md"
    >
      {/* Top row: Friendly title & Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-3">
        <div className="flex items-center space-x-2">
          <h3 className="text-sm font-bold text-primary-dark tracking-tight">
            {pres.title}
          </h3>
        </div>
        {getStatusBadge()}
      </div>

      {/* Middle row: Question and Answer */}
      <div className="space-y-2">
        <p className="text-xs text-gov-secondary leading-relaxed font-normal">
          {pres.question}
        </p>

        <div className="flex items-center justify-between flex-wrap gap-2 pt-1">
          <div className="flex items-center space-x-2">
            <span className="text-xs text-gov-secondary">
              {isHindi ? "प्रस्तुत उत्तर:" : "Your response:"}
            </span>
            <span
              className={`text-xs px-3 py-1 rounded-md font-bold ${
                pres.isPositive
                  ? "bg-green-100 text-green-800 border border-green-300"
                  : "bg-gray-100 text-gray-800 border border-gray-300"
              }`}
            >
              {pres.formattedValue}
            </span>
          </div>

          <span className="text-[11px] text-gov-secondary font-medium">
            {pres.sourceLabel}
          </span>
        </div>
      </div>

      {/* Attached Evidence Items */}
      {claim.evidence_items && claim.evidence_items.length > 0 ? (
        <div className="pt-3 border-t border-gray-100 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gov-secondary">
              {t("journey.attached_evidence")}
            </span>
            {onAttachEvidence && (
              <button
                type="button"
                onClick={() => onAttachEvidence(claim.id)}
                className="text-primary hover:text-primary-dark font-semibold text-xs inline-flex items-center space-x-1 focus-visible:ring-2 focus-visible:ring-primary rounded p-1 min-h-[28px]"
              >
                <FilePlus className="w-3.5 h-3.5" aria-hidden="true" />
                <span>{t("claims.add_evidence_cta")}</span>
              </button>
            )}
          </div>
          <div className="space-y-2">
            {claim.evidence_items.map((ev) => (
              <EvidenceCard
                key={ev.id}
                evidence={ev}
                onVerify={onVerifyEvidence ? () => onVerifyEvidence(ev.id) : undefined}
              />
            ))}
          </div>
        </div>
      ) : (
        <div className="pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gov-secondary">
          <span className="italic">
            {t("journey.no_evidence")}
          </span>
          {onAttachEvidence && (
            <button
              type="button"
              onClick={() => onAttachEvidence(claim.id)}
              className="text-primary hover:text-primary-dark font-semibold text-xs inline-flex items-center space-x-1 focus-visible:ring-2 focus-visible:ring-primary rounded py-1 px-2.5 bg-primary-50 hover:bg-primary-100 border border-primary-100 transition-colors min-h-[32px]"
            >
              <FilePlus className="w-3.5 h-3.5" aria-hidden="true" />
              <span>{t("claims.add_evidence_cta")}</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
};
