"use client";

import React from "react";
import { FileText, ShieldCheck, CheckCircle2, Clock, XCircle } from "lucide-react";
import { JourneyEvidence } from "../../types/journey";
import { EvidenceStatus } from "../../types/enums";
import { useLanguage } from "../../context/LanguageContext";
import { getEvidencePresentation } from "../../utils/claimPresentation";

interface EvidenceCardProps {
  evidence: JourneyEvidence;
  onVerify?: () => void;
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({ evidence, onVerify }) => {
  const { isHindi, t } = useLanguage();
  const docPres = getEvidencePresentation(evidence.evidence_type, isHindi);

  const getEvidenceStatusBadge = () => {
    switch (evidence.status) {
      case EvidenceStatus.VERIFIED:
        return (
          <span className="inline-flex items-center space-x-1 text-[11px] px-2 py-0.5 rounded font-semibold bg-green-50 text-green-700 border border-green-200">
            <CheckCircle2 className="w-3 h-3 text-green-600" aria-hidden="true" />
            <span>{isHindi ? "दस्तावेज़ सत्यापित" : "Evidence Verified"}</span>
          </span>
        );
      case EvidenceStatus.REJECTED:
        return (
          <span className="inline-flex items-center space-x-1 text-[11px] px-2 py-0.5 rounded font-semibold bg-red-50 text-red-700 border border-red-200">
            <XCircle className="w-3 h-3 text-red-600" aria-hidden="true" />
            <span>{isHindi ? "दस्तावेज़ अस्वीकृत" : "Evidence Rejected"}</span>
          </span>
        );
      case EvidenceStatus.PENDING:
      default:
        return (
          <span className="inline-flex items-center space-x-1 text-[11px] px-2 py-0.5 rounded font-medium bg-amber-50 text-amber-700 border border-amber-200">
            <Clock className="w-3 h-3 text-amber-600" aria-hidden="true" />
            <span>{isHindi ? "सत्यापन लंबित" : "Verification Pending"}</span>
          </span>
        );
    }
  };

  return (
    <div className="bg-gray-50/80 rounded-lg border border-gov-border p-3 space-y-2 text-xs">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start space-x-2.5 min-w-0">
          <div className="p-1 rounded bg-white border border-gov-border text-primary mt-0.5 flex-shrink-0">
            <FileText className="w-4 h-4" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <span className="font-bold text-gov-text block truncate">
              {docPres.title}
            </span>
            <span className="text-[11px] text-gov-secondary block">
              {evidence.metadata_json?.original_filename ? (
                <>
                  <strong className="text-gov-text">{String(evidence.metadata_json.original_filename)}</strong>
                  {evidence.metadata_json.size_bytes ? ` (${(Number(evidence.metadata_json.size_bytes) / 1024).toFixed(1)} KB) • ` : " • "}
                </>
              ) : null}
              {docPres.hint}
            </span>
          </div>
        </div>
        {getEvidenceStatusBadge()}
      </div>

      {evidence.rejection_reason && (
        <div className="bg-red-50 text-danger-700 p-2 rounded border border-red-200">
          <span className="font-semibold mr-1">{t("journey.rejection_reason")}</span>
          <span>{evidence.rejection_reason}</span>
        </div>
      )}

      {/* Verification Audit Details */}
      {evidence.verification_records && evidence.verification_records.length > 0 && (
        <div className="text-[11px] text-gov-secondary pt-1 border-t border-gray-200 space-y-1">
          {evidence.verification_records.map((vr) => (
            <div key={vr.id} className="flex items-center justify-between flex-wrap gap-1">
              <span>
                {t("journey.verification_method")}{" "}
                <strong className="text-gov-text font-medium">
                  {vr.verification_method === "AUTOMATED"
                    ? isHindi
                      ? "स्वचालित रजिस्ट्री मिलान"
                      : "Automated Registry Match"
                    : vr.verification_method}
                </strong>
              </span>
              <span className="text-gray-400">
                {t("journey.verified_on")} {new Date(vr.created_at).toLocaleDateString()}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Action to Verify (if PENDING and onVerify callback passed) */}
      {evidence.status === EvidenceStatus.PENDING && onVerify && (
        <div className="pt-1 flex justify-end">
          <button
            type="button"
            onClick={onVerify}
            className="inline-flex items-center space-x-1 px-3 py-1 bg-white border border-primary text-primary hover:bg-primary-50 rounded text-xs font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-primary min-h-[32px]"
          >
            <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" />
            <span>{t("journey.simulate_verification")}</span>
          </button>
        </div>
      )}
    </div>
  );
};
