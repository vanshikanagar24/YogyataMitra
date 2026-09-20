"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { listSchemes } from "../../api/schemes";
import { SchemeCard } from "../../components/schemes/SchemeCard";
import { Breadcrumbs } from "../../components/layout/Breadcrumbs";
import { PageHeader } from "../../components/layout/PageHeader";
import { ErrorState, EmptyState, SchemeCardSkeleton } from "../../components/common/FeedbackStates";
import { useLanguage } from "../../context/LanguageContext";

export default function SchemesPage() {
  const { t } = useLanguage();
  const [searchTerm, setSearchTerm] = useState("");

  const { data: schemes, isLoading, error, refetch } = useQuery({
    queryKey: ["schemes"],
    queryFn: () => listSchemes(),
  });

  const filteredSchemes = schemes?.filter((s) => {
    const q = searchTerm.toLowerCase();
    return (
      s.name_en.toLowerCase().includes(q) ||
      s.name_hi.includes(searchTerm) ||
      s.scheme_code.toLowerCase().includes(q)
    );
  });

  return (
    <div className="gov-container py-6 space-y-6">
      <Breadcrumbs
        items={[
          {
            label: t("nav.schemes"),
          },
        ]}
      />

      <PageHeader
        title={t("schemes.section_title")}
        subtitle={t("schemes.section_subtitle")}
      />

      {/* Filter & Search Bar */}
      <div className="bg-white p-4 rounded-lg border border-gov-border shadow-xs flex flex-col sm:flex-row gap-4 justify-between items-center" role="search">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-gov-secondary absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true" />
          <label htmlFor="schemes-search-filter" className="sr-only">
            {t("schemes.search_schemes_placeholder")}
          </label>
          <input
            id="schemes-search-filter"
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={t("schemes.search_schemes_placeholder")}
            className="w-full pl-9 pr-3 py-2 text-xs text-gov-text border border-gov-border rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-primary min-h-[38px]"
          />
        </div>
        <div className="text-xs text-gov-secondary font-medium">
          <span className="font-bold text-primary-dark">
            {t("schemes.supported_schemes_count", { count: filteredSchemes?.length || 0 })}
          </span>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6" aria-busy="true">
          <SchemeCardSkeleton />
          <SchemeCardSkeleton />
        </div>
      ) : error ? (
        <ErrorState
          title={t("common.error")}
          message={(error as Error)?.message}
          onRetry={refetch}
        />
      ) : filteredSchemes && filteredSchemes.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredSchemes.map((s) => (
            <SchemeCard key={s.id} scheme={s} />
          ))}
        </div>
      ) : (
        <EmptyState
          title={t("schemes.no_schemes_found")}
          description={t("schemes.no_schemes_desc")}
        />
      )}
    </div>
  );
}
