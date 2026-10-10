"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle, Landmark } from "lucide-react";
import { SchemeSummary } from "../../types/scheme";
import { useLanguage } from "../../context/LanguageContext";

interface SchemeCardProps {
  scheme: SchemeSummary;
}

export const SchemeCard: React.FC<SchemeCardProps> = ({ scheme }) => {
  const { isHindi, t } = useLanguage();

  const isPmKisan = scheme.scheme_code === "PM_KISAN";
  const isSSY = scheme.scheme_code === "SSY";

  const benefitText = isPmKisan
    ? t("schemes.pm_kisan_benefit")
    : isSSY
    ? t("schemes.ssy_benefit")
    : "";

  const categoryText = isPmKisan
    ? t("schemes.pm_kisan_category")
    : isSSY
    ? t("schemes.ssy_category")
    : "";

  const title = isHindi ? scheme.name_hi : scheme.name_en;
  const description = isHindi ? scheme.description_hi : scheme.description_en;

  return (
    <div className="bg-white rounded-lg border border-gov-border hover:border-primary-light transition-all shadow-gov-card hover:shadow-gov-elevated flex flex-col justify-between p-6 group">
      <div>
        {/* Category & Status Bar */}
        <div className="flex items-center justify-between gap-2 mb-3.5 flex-wrap">
          <span className="inline-flex items-center text-xs font-semibold px-2.5 py-1 rounded bg-primary-50 text-primary border border-primary-100">
            <Landmark className="w-3.5 h-3.5 mr-1 text-primary flex-shrink-0" aria-hidden="true" />
            <span>{categoryText || scheme.ministry}</span>
          </span>
          <span className="text-xs font-medium text-success-700 bg-green-50 px-2 py-0.5 rounded border border-green-200">
            {t("schemes.active_scheme_badge")}
          </span>
        </div>

        {/* Title */}
        <h3 className="text-lg font-bold text-primary-dark group-hover:text-primary transition-colors mb-2 leading-snug">
          {title}
        </h3>

        {/* Description */}
        <p className="text-xs text-gov-secondary leading-relaxed mb-4 line-clamp-3">
          {description}
        </p>

        {/* Highlight Benefit (Descriptive Presentation Only) */}
        {benefitText && (
          <div className="bg-gov-bg p-3 rounded border border-gov-border mb-5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-gov-secondary block mb-1">
              {t("schemes.indicative_benefit")}
            </span>
            <div className="flex items-center text-xs font-semibold text-primary-dark">
              <CheckCircle className="w-4 h-4 text-primary mr-1.5 flex-shrink-0" aria-hidden="true" />
              <span>{benefitText}</span>
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="pt-3 border-t border-gray-100 flex items-center justify-between gap-3 flex-wrap">
        <Link
          href={`/schemes/${scheme.scheme_code}`}
          className="text-xs font-semibold text-gov-secondary hover:text-primary-dark transition-colors inline-flex items-center focus-visible:ring-2 focus-visible:ring-primary rounded p-1"
        >
          <span>{t("schemes.view_details_action")}</span>
        </Link>

        <Link
          href={`/eligibility?scheme=${scheme.scheme_code}`}
          className="inline-flex items-center space-x-1.5 px-4 py-2 bg-primary hover:bg-primary-dark text-white rounded-md text-xs font-semibold shadow-xs transition-colors group-hover:bg-primary-dark focus-visible:ring-2 focus-visible:ring-primary min-h-[36px]"
        >
          <span>{t("schemes.check_my_eligibility")}</span>
          <ArrowRight className="w-3.5 h-3.5 ml-1" aria-hidden="true" />
        </Link>
      </div>
    </div>
  );
};
