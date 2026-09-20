"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Scale, Info, History } from "lucide-react";
import { listSchemePolicies } from "../../api/policies";
import { Breadcrumbs } from "../../components/layout/Breadcrumbs";
import { PageHeader } from "../../components/layout/PageHeader";
import { PolicyVersionCard } from "../../components/policy/PolicyVersionCard";
import { ErrorState, TableSkeleton } from "../../components/common/FeedbackStates";
import { useLanguage } from "../../context/LanguageContext";

export default function PolicyVerificationPage() {
  const { isHindi, t } = useLanguage();
  const [selectedScheme, setSelectedScheme] = useState<string>("PM_KISAN");

  const { data: policies, isLoading, error, refetch } = useQuery({
    queryKey: ["scheme-policies", selectedScheme],
    queryFn: () => listSchemePolicies(selectedScheme),
  });

  // Split into current policy (index 0) and historical policies (index > 0)
  const currentPolicy = policies && policies.length > 0 ? policies[0] : null;
  const historicalPolicies = policies && policies.length > 1 ? policies.slice(1) : [];

  return (
    <div className="gov-container py-6 space-y-8">
      <Breadcrumbs
        items={[
          {
            label: t("nav.policy_verification"),
          },
        ]}
      />

      <PageHeader
        title={t("policy_page.title")}
        subtitle={t("policy_page.subtitle")}
      />

      {/* Statutory Assessment Date Notice */}
      <div className="bg-primary-50/70 border border-primary-200 rounded-xl p-5 shadow-xs flex items-start space-x-3">
        <Info className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" aria-hidden="true" />
        <div className="space-y-1 text-xs">
          <h2 className="font-bold text-primary-dark text-sm">
            {t("policy_page.statutory_assessment_notice")}
          </h2>
          <p className="text-gov-secondary leading-relaxed">
            {t("policy_page.statutory_assessment_notice_desc")}
          </p>
        </div>
      </div>

      {/* Scheme Tab Switcher */}
      <div className="flex space-x-2 border-b border-gov-border pb-2" role="tablist" aria-label="Scheme Policy Tabs">
        <button
          type="button"
          role="tab"
          aria-selected={selectedScheme === "PM_KISAN"}
          onClick={() => setSelectedScheme("PM_KISAN")}
          className={`px-4 py-2.5 rounded-md text-xs font-bold transition-colors min-h-[38px] focus-visible:ring-2 focus-visible:ring-primary ${
            selectedScheme === "PM_KISAN"
              ? "bg-primary-dark text-white"
              : "bg-white text-gov-secondary hover:text-gov-text border border-gov-border"
          }`}
        >
          {t("schemes.pm_kisan")}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={selectedScheme === "SSY"}
          onClick={() => setSelectedScheme("SSY")}
          className={`px-4 py-2.5 rounded-md text-xs font-bold transition-colors min-h-[38px] focus-visible:ring-2 focus-visible:ring-primary ${
            selectedScheme === "SSY"
              ? "bg-primary-dark text-white"
              : "bg-white text-gov-secondary hover:text-gov-text border border-gov-border"
          }`}
        >
          {t("schemes.ssy")}
        </button>
      </div>

      {/* Policy Content */}
      {isLoading ? (
        <TableSkeleton rows={3} />
      ) : error ? (
        <ErrorState
          title={t("common.error")}
          message={(error as Error)?.message}
          onRetry={refetch}
        />
      ) : (
        <div className="space-y-8">
          {/* Current Effective Policy Section */}
          {currentPolicy && (
            <section className="space-y-3" aria-labelledby="current-policy-heading">
              <div className="border-b border-gray-100 pb-2">
                <h2 id="current-policy-heading" className="text-base font-bold text-primary-dark flex items-center space-x-2">
                  <Scale className="w-4 h-4 text-primary" aria-hidden="true" />
                  <span>{t("policy_page.current_version_heading")}</span>
                </h2>
              </div>
              <PolicyVersionCard policy={currentPolicy} index={0} />
            </section>
          )}

          {/* Historical Policy Versions & Timeline Section */}
          {historicalPolicies.length > 0 && (
            <section className="space-y-4" aria-labelledby="history-policy-heading">
              <div className="border-b border-gray-100 pb-2">
                <h2 id="history-policy-heading" className="text-base font-bold text-gov-text flex items-center space-x-2">
                  <History className="w-4 h-4 text-primary" aria-hidden="true" />
                  <span>{t("policy_page.history_timeline_heading")}</span>
                </h2>
                <p className="text-xs text-gov-secondary mt-0.5">
                  {t("policy_page.history_timeline_desc")}
                </p>
              </div>

              <div className="space-y-4">
                {historicalPolicies.map((policy, idx) => (
                  <PolicyVersionCard key={policy.id} policy={policy} index={idx + 1} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
