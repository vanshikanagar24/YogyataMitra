"use client";

import React from "react";
import Link from "next/link";
import { ShieldCheck, Check, ArrowRight } from "lucide-react";
import { useLanguage } from "../../context/LanguageContext";

export const TrustCard: React.FC = () => {
  const { t } = useLanguage();

  return (
    <div className="bg-white/95 backdrop-blur-xs rounded-lg p-5 sm:p-6 shadow-gov-elevated border border-gov-border max-w-sm w-full text-gov-text">
      <div className="flex items-center space-x-3 mb-3.5">
        <div className="w-10 h-10 rounded-full bg-primary-50 border border-primary-100 flex items-center justify-center text-primary">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-base font-bold text-primary-dark leading-tight">
            {t("hero.trust_card_title")}
          </h3>
          <span className="text-xs text-gov-secondary">
            {t("brand.portal_tag")}
          </span>
        </div>
      </div>

      <ul className="space-y-2 text-xs font-medium text-gov-text border-t border-b border-gray-100 py-3 mb-4">
        <li className="flex items-center space-x-2 text-gov-secondary">
          <Check className="w-4 h-4 text-success flex-shrink-0" />
          <span>{t("hero.trust_card_p1")}</span>
        </li>
        <li className="flex items-center space-x-2 text-gov-secondary">
          <Check className="w-4 h-4 text-success flex-shrink-0" />
          <span>{t("hero.trust_card_p2")}</span>
        </li>
        <li className="flex items-center space-x-2 text-gov-secondary">
          <Check className="w-4 h-4 text-success flex-shrink-0" />
          <span>{t("hero.trust_card_p3")}</span>
        </li>
      </ul>

      <Link
        href="/policy-verification"
        className="inline-flex items-center text-xs font-bold text-primary hover:text-primary-light transition-colors group"
      >
        <span>{t("hero.trust_card_cta")}</span>
        <ArrowRight className="w-3.5 h-3.5 ml-1 group-hover:translate-x-0.5 transition-transform" />
      </Link>
    </div>
  );
};
