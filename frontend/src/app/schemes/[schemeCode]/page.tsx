"use client";

import React from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  ExternalLink,
  Users,
  CheckSquare,
  ShieldCheck,
  AlertCircle,
} from "lucide-react";
import { getScheme } from "../../../api/schemes";
import { listSchemePolicies } from "../../../api/policies";
import { Breadcrumbs } from "../../../components/layout/Breadcrumbs";
import { PolicyVersionCard } from "../../../components/policy/PolicyVersionCard";
import { ErrorState, TableSkeleton } from "../../../components/common/FeedbackStates";
import { useLanguage } from "../../../context/LanguageContext";

export default function SchemeDetailPage() {
  const params = useParams();
  const schemeCode = (params.schemeCode as string)?.toUpperCase();
  const { isHindi, t } = useLanguage();

  const {
    data: scheme,
    isLoading: schemeLoading,
    error: schemeError,
    refetch: refetchScheme,
  } = useQuery({
    queryKey: ["scheme", schemeCode],
    queryFn: () => getScheme(schemeCode),
    enabled: !!schemeCode,
  });

  const { data: policies, isLoading: policiesLoading } = useQuery({
    queryKey: ["scheme-policies", schemeCode],
    queryFn: () => listSchemePolicies(schemeCode),
    enabled: !!schemeCode,
  });

  if (schemeLoading) {
    return (
      <div className="gov-container py-12 space-y-6" aria-busy="true">
        <TableSkeleton rows={2} />
      </div>
    );
  }

  if (schemeError || !scheme) {
    return (
      <div className="gov-container py-12">
        <ErrorState
          title={t("scheme_detail.scheme_not_found")}
          message={(schemeError as Error)?.message}
          onRetry={refetchScheme}
        />
      </div>
    );
  }

  const title = isHindi ? scheme.name_hi : scheme.name_en;
  const description = isHindi ? scheme.description_hi : scheme.description_en;

  return (
    <div className="gov-container py-6 space-y-8">
      <Breadcrumbs
        items={[
          { label: t("nav.schemes"), href: "/schemes" },
          { label: scheme.scheme_code },
        ]}
      />

      {/* Main Header & Direct CTA Banner */}
      <div className="bg-white rounded-xl border border-gov-border p-6 sm:p-8 shadow-gov-card space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-gray-100">
          <div className="space-y-2">
            <div className="flex items-center space-x-2 text-xs font-semibold flex-wrap gap-1">
              <span className="px-2.5 py-1 rounded bg-primary-50 text-primary border border-primary-100">
                {scheme.ministry || (isHindi ? "भारत सरकार" : "Government of India")}
              </span>
              <span className="px-2 py-0.5 rounded bg-green-50 text-green-700 border border-green-200">
                {t("schemes.active_scheme_badge")}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-primary-dark tracking-tight">
              {title}
            </h1>
            <p className="text-xs sm:text-sm text-gov-secondary max-w-3xl leading-relaxed">
              {description}
            </p>
          </div>

          <div className="flex flex-col sm:flex-row md:flex-col gap-3 flex-shrink-0">
            <Link
              href={`/eligibility?scheme=${scheme.scheme_code}`}
              className="inline-flex items-center justify-center space-x-2 px-6 py-3 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm font-bold shadow-xs transition-colors text-center focus-visible:ring-2 focus-visible:ring-primary min-h-[44px]"
            >
              <span>{t("scheme_detail.check_my_eligibility")}</span>
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>

            {scheme.official_url && (
              <a
                href={scheme.official_url}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`${t("schemes.official_portal")} (${t("a11y.external_link")})`}
                className="inline-flex items-center justify-center space-x-1.5 px-4 py-2 bg-white border border-gov-border hover:bg-gray-50 text-gov-text rounded-lg text-xs font-medium transition-colors text-center focus-visible:ring-2 focus-visible:ring-primary min-h-[38px]"
              >
                <span>{t("schemes.official_portal")}</span>
                <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
              </a>
            )}
          </div>
        </div>

        {/* Citizen Information Sections */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-2">
          {/* Who this scheme is for */}
          <div className="bg-primary-50/50 p-4 rounded-lg border border-primary-100 space-y-2">
            <h2 className="font-bold text-primary-dark text-sm flex items-center space-x-2">
              <Users className="w-4 h-4 text-primary flex-shrink-0" aria-hidden="true" />
              <span>{t("scheme_detail.who_intended_for_title")}</span>
            </h2>
            <p className="text-gov-secondary leading-relaxed">
              {schemeCode === "PM_KISAN"
                ? t("scheme_detail.pm_kisan_who_for")
                : schemeCode === "SSY"
                ? t("scheme_detail.ssy_who_for")
                : description}
            </p>
          </div>

          {/* Key eligibility criteria */}
          <div className="bg-primary-50/50 p-4 rounded-lg border border-primary-100 space-y-2">
            <h2 className="font-bold text-primary-dark text-sm flex items-center space-x-2">
              <CheckSquare className="w-4 h-4 text-primary flex-shrink-0" aria-hidden="true" />
              <span>{t("scheme_detail.key_criteria_title")}</span>
            </h2>
            <p className="text-gov-secondary leading-relaxed">
              {schemeCode === "PM_KISAN"
                ? t("scheme_detail.pm_kisan_key_criteria")
                : schemeCode === "SSY"
                ? t("scheme_detail.ssy_key_criteria")
                : ""}
            </p>
          </div>

          {/* What YogyataMitra assesses */}
          <div className="bg-gov-bg p-4 rounded-lg border border-gov-border space-y-2">
            <h2 className="font-bold text-gov-text text-sm flex items-center space-x-2">
              <ShieldCheck className="w-4 h-4 text-success-700 flex-shrink-0" aria-hidden="true" />
              <span>{t("scheme_detail.what_assesses_title")}</span>
            </h2>
            <p className="text-gov-secondary leading-relaxed">
              {t("scheme_detail.what_assesses_desc")}
            </p>
          </div>

          {/* What YogyataMitra cannot guarantee */}
          <div className="bg-gov-bg p-4 rounded-lg border border-gov-border space-y-2">
            <h2 className="font-bold text-gov-text text-sm flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-warning-700 flex-shrink-0" aria-hidden="true" />
              <span>{t("scheme_detail.what_cannot_guarantee_title")}</span>
            </h2>
            <p className="text-gov-secondary leading-relaxed">
              {t("scheme_detail.what_cannot_guarantee_desc")}
            </p>
          </div>
        </div>
      </div>

      {/* Statutory Policy Versions & Provenance */}
      <section className="space-y-4" aria-labelledby="policy-versions-heading">
        <div>
          <h2 id="policy-versions-heading" className="text-xl font-bold text-primary-dark tracking-tight">
            {t("scheme_detail.policy_versions_title")}
          </h2>
          <p className="text-xs text-gov-secondary mt-1">
            {t("scheme_detail.policy_versions_subtitle")}
          </p>
        </div>

        {policiesLoading ? (
          <TableSkeleton rows={3} />
        ) : policies && policies.length > 0 ? (
          <div className="space-y-3">
            {policies.map((p) => (
              <PolicyVersionCard key={p.id} policy={p} />
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}
