"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  History,
  Search,
  Calendar,
  Shield,
  CheckCircle2,
  Clock,
  ArrowRight,
  FileCheck,
} from "lucide-react";
import { getEvaluationTrace } from "../../api/evaluations";
import { Breadcrumbs } from "../../components/layout/Breadcrumbs";
import { PageHeader } from "../../components/layout/PageHeader";
import { StatusBadge } from "../../components/common/StatusBadge";
import { LoadingState, ErrorState } from "../../components/common/FeedbackStates";
import { useLanguage } from "../../context/LanguageContext";
import { getFriendlyFieldTitle, formatCitizenValue } from "../../utils/claimPresentation";
import { EligibilityResult } from "../../types/enums";

interface RecentAssessment {
  id: string;
  scheme_code: string;
  policy_version_code: string;
  evaluation_date: string;
  overall_result: EligibilityResult;
  created_at: string;
  reasons_en: string[];
  reasons_hi: string[];
  facts_snapshot?: Record<string, any>;
}

export default function AuditHistoryPage() {
  const { t, isHindi } = useLanguage();
  const [evaluationIdInput, setEvaluationIdInput] = useState<string>("");
  const [activeQueryId, setActiveQueryId] = useState<string>("");
  const [recentAssessments, setRecentAssessments] = useState<RecentAssessment[]>([]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        const stored = sessionStorage.getItem("ym_recent_assessments");
        if (stored) {
          setRecentAssessments(JSON.parse(stored));
        }
      } catch {
        // ignore storage read issues
      }
    }
  }, []);

  const {
    data: persistedTrace,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["evaluation-trace", activeQueryId],
    queryFn: () => getEvaluationTrace(activeQueryId),
    enabled: !!activeQueryId,
    retry: false,
  });

  const handleLookup = (e: React.FormEvent) => {
    e.preventDefault();
    if (evaluationIdInput.trim()) {
      setActiveQueryId(evaluationIdInput.trim());
    }
  };

  return (
    <div className="gov-container py-6 space-y-8">
      <Breadcrumbs
        items={[
          {
            label: t("nav.audit_history"),
          },
        ]}
      />

      <PageHeader
        title={t("audit_page.citizen_title")}
        subtitle={t("audit_page.citizen_subtitle")}
      />

      {/* Recent Assessments Section (Session-based, no UUID required) */}
      <section className="space-y-4" aria-labelledby="recent-assessments-heading">
        <div className="flex items-center justify-between border-b border-gov-border pb-2">
          <h2
            id="recent-assessments-heading"
            className="text-base font-bold text-primary-dark flex items-center space-x-2"
          >
            <History className="w-4 h-4 text-primary" aria-hidden="true" />
            <span>{t("audit_page.recent_assessments_title")}</span>
          </h2>
          <span className="text-xs text-gov-secondary font-medium">
            {recentAssessments.length > 0
              ? `${recentAssessments.length} ${isHindi ? "मूल्यांकन उपलब्ध" : "records in session"}`
              : ""}
          </span>
        </div>

        {recentAssessments.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {recentAssessments.map((rec) => {
              const reason = isHindi
                ? rec.reasons_hi?.[0] || t(`results.${rec.overall_result}_desc`)
                : rec.reasons_en?.[0] || t(`results.${rec.overall_result}_desc`);

              return (
                <div
                  key={rec.id}
                  className="bg-white rounded-xl border border-gov-border p-5 shadow-xs hover:shadow-md transition-shadow space-y-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-xs font-bold text-primary-dark tracking-wide">
                        {rec.scheme_code === "PM_KISAN"
                          ? "PM-KISAN"
                          : rec.scheme_code === "SSY"
                          ? isHindi
                            ? "सुकन्या समृद्धि योजना"
                            : "Sukanya Samriddhi Yojana"
                          : rec.scheme_code}
                      </span>
                      <div className="text-xs text-gov-secondary">
                        {t("audit_page.policy_version_label")}{" "}
                        <span className="font-semibold text-gov-text">{rec.policy_version_code}</span>
                      </div>
                    </div>
                    <StatusBadge status={rec.overall_result} size="sm" />
                  </div>

                  <p className="text-xs text-gov-secondary line-clamp-2 leading-relaxed">{reason}</p>

                  <div className="flex items-center justify-between text-xs text-gov-secondary pt-2 border-t border-gray-100">
                    <span className="flex items-center space-x-1">
                      <Calendar className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
                      <span>{rec.evaluation_date}</span>
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setActiveQueryId(rec.id);
                      }}
                      className="text-xs font-bold text-primary hover:text-primary-dark underline focus-visible:ring-2 focus-visible:ring-primary rounded p-0.5"
                    >
                      {isHindi ? "विस्तृत विवरण देखें" : "View full details"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gov-border p-8 text-center text-xs text-gov-secondary max-w-xl mx-auto space-y-3">
            <FileCheck className="w-10 h-10 text-gray-300 mx-auto" aria-hidden="true" />
            <p className="font-medium text-gov-text text-sm">
              {t("audit_page.no_recent_assessments")}
            </p>
            <div>
              <Link
                href="/eligibility"
                className="inline-flex items-center space-x-1.5 px-4 py-2 bg-primary hover:bg-primary-dark text-white rounded-md font-bold text-xs shadow-xs transition-colors"
              >
                <span>{t("schemes.check_eligibility")}</span>
                <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
              </Link>
            </div>
          </div>
        )}
      </section>

      {/* Optional Reference Lookup Section */}
      <section className="space-y-3" aria-labelledby="lookup-heading">
        <h2 id="lookup-heading" className="text-sm font-bold text-gov-text flex items-center space-x-2">
          <Search className="w-4 h-4 text-primary" aria-hidden="true" />
          <span>{t("audit_page.lookup_by_ref")}</span>
        </h2>

        <form
          onSubmit={handleLookup}
          className="bg-white p-5 rounded-xl border border-gov-border shadow-xs space-y-3"
          role="search"
        >
          <div>
            <label
              htmlFor="eval-ref-input"
              className="block text-xs font-bold text-gov-text uppercase tracking-wider mb-1.5"
            >
              {t("audit_page.ref_input_label")}
            </label>
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                id="eval-ref-input"
                type="text"
                value={evaluationIdInput}
                onChange={(e) => setEvaluationIdInput(e.target.value)}
                placeholder={t("audit_page.ref_input_placeholder")}
                className="flex-grow font-sans text-xs p-2.5 border border-gov-border rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-primary min-h-[40px]"
              />
              <button
                type="submit"
                className="px-5 py-2.5 bg-primary hover:bg-primary-dark text-white rounded-md text-xs font-bold shadow-xs transition-colors flex items-center justify-center space-x-1.5 flex-shrink-0 min-h-[40px] focus-visible:ring-2 focus-visible:ring-primary"
              >
                <Search className="w-3.5 h-3.5" aria-hidden="true" />
                <span>{t("audit_page.search_btn")}</span>
              </button>
            </div>
          </div>
        </form>
      </section>

      {/* Persisted Trace Details Viewer */}
      <div aria-live="polite">
        {isLoading ? (
          <LoadingState message={t("common.loading")} />
        ) : error ? (
          <ErrorState
            title={t("audit_page.record_not_found")}
            message={(error as Error)?.message || t("audit_page.record_not_found_desc")}
            onRetry={refetch}
          />
        ) : persistedTrace ? (
          <div className="bg-white rounded-xl border border-gov-border p-6 sm:p-8 shadow-gov-card space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-100 pb-5">
              <div>
                <span className="text-xs font-bold text-gov-secondary tracking-wide uppercase">
                  {t("audit_page.persisted_record_title")}
                </span>
                <h2 className="text-xl font-bold text-primary-dark mt-0.5">
                  {persistedTrace.scheme_code} — {persistedTrace.policy_version_code}
                </h2>
                <div className="text-xs text-gov-secondary mt-1">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-primary-50 text-primary-dark border border-primary-100">
                    {isHindi ? "सत्र मूल्यांकन रिकॉर्ड" : "Session Assessment Record"}
                  </span>
                </div>
              </div>

              <StatusBadge status={persistedTrace.result_state} size="lg" />
            </div>

            {/* Assessment Date vs Execution Timestamp */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="bg-gov-bg p-3.5 rounded-lg border border-gov-border">
                <div className="text-gov-secondary mb-1 flex items-center">
                  <Calendar className="w-3.5 h-3.5 mr-1 text-primary" aria-hidden="true" />
                  <span>{t("audit_page.assessment_date_label")}</span>
                </div>
                <span className="font-bold text-gov-text text-sm">{persistedTrace.evaluation_date}</span>
                <div className="text-[11px] text-gov-secondary mt-1">
                  {isHindi
                    ? "इस तिथि पर प्रभावी वैधानिक नियमों का उपयोग किया गया।"
                    : "Statutory rules effective on this date were applied."}
                </div>
              </div>

              <div className="bg-gov-bg p-3.5 rounded-lg border border-gov-border">
                <div className="text-gov-secondary mb-1 flex items-center">
                  <Clock className="w-3.5 h-3.5 mr-1 text-primary" aria-hidden="true" />
                  <span>{isHindi ? "गणना निष्पादन समय:" : "Calculation Execution Time:"}</span>
                </div>
                <span className="font-semibold text-gov-text">
                  {new Date(persistedTrace.created_at).toLocaleString(isHindi ? "hi-IN" : "en-IN", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
                <div className="text-[11px] text-success-700 flex items-center mt-1">
                  <CheckCircle2 className="w-3 h-3 mr-1 text-success flex-shrink-0" aria-hidden="true" />
                  <span>{isHindi ? "अपरिवर्तनीय ऑडिट रिकॉर्ड" : "Immutable evaluation record"}</span>
                </div>
              </div>
            </div>

            {/* Assessment Summary Section */}
            <div className="bg-primary-50/50 rounded-lg p-5 border border-primary-100 space-y-2">
              <h3 className="text-xs font-bold text-primary-dark uppercase tracking-wider flex items-center space-x-1.5">
                <Shield className="w-4 h-4 text-primary" aria-hidden="true" />
                <span>{t("audit_page.summary_title")}</span>
              </h3>
              <p className="text-xs text-gov-secondary leading-relaxed">
                {t(`results.${persistedTrace.result_state}_desc`)}
              </p>
            </div>

            {/* Facts Assessed Snapshot in Plain Language */}
            {persistedTrace.input_snapshot_json && (
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-primary-dark">
                  {t("audit_page.facts_recorded_title")}
                </h3>
                <div className="bg-gov-bg rounded-lg p-4 border border-gov-border text-xs">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
                    {Object.entries(persistedTrace.input_snapshot_json).flatMap(([groupKey, groupVal]) => {
                      if (typeof groupVal === "object" && groupVal !== null) {
                        return Object.entries(groupVal).map(([k, v]) => {
                          const fullKey = `${groupKey}.${k}`;
                          const formatted = formatCitizenValue(v, fullKey, isHindi);
                          return (
                            <div
                              key={fullKey}
                              className="flex justify-between items-center py-1.5 border-b border-gray-200/60"
                            >
                              <span className="text-gov-secondary font-medium">
                                {getFriendlyFieldTitle(fullKey, isHindi)}
                              </span>
                              <span className="font-semibold text-gov-text">
                                {formatted.text}
                              </span>
                            </div>
                          );
                        });
                      }
                      const formatted = formatCitizenValue(groupVal, groupKey, isHindi);
                      return (
                        <div
                          key={groupKey}
                          className="flex justify-between items-center py-1.5 border-b border-gray-200/60"
                        >
                          <span className="text-gov-secondary font-medium">
                            {getFriendlyFieldTitle(groupKey, isHindi)}
                          </span>
                          <span className="font-semibold text-gov-text">{formatted.text}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* Policy Link */}
            <div className="pt-3 border-t border-gray-100 flex justify-end">
              <Link
                href={`/schemes/${persistedTrace.scheme_code}`}
                className="inline-flex items-center space-x-1 text-xs font-bold text-primary hover:text-primary-dark hover:underline"
              >
                <span>{t("audit_page.view_policy_cta")}</span>
                <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
              </Link>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
