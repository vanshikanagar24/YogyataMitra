"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search, ArrowRight, ChevronRight, Landmark, ShieldCheck, FileCheck, Scale, History } from "lucide-react";
import { useLanguage } from "../context/LanguageContext";
import { useAuth } from "../context/AuthContext";
import { TrustCard } from "../components/common/TrustCard";
import { SchemeCard } from "../components/schemes/SchemeCard";
import { useQuery } from "@tanstack/react-query";
import { listSchemes } from "../api/schemes";
import { ErrorState, SchemeCardSkeleton } from "../components/common/FeedbackStates";

export default function HomePage() {
  const { t } = useLanguage();
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");

  const { data: schemes, isLoading, error, refetch } = useQuery({
    queryKey: ["schemes"],
    queryFn: () => listSchemes(),
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      router.push("/schemes");
      return;
    }
    const q = searchQuery.toLowerCase();
    if (q.includes("kisan") || q.includes("किसान")) {
      router.push("/schemes/PM_KISAN");
    } else if (q.includes("sukanya") || q.includes("सुकन्या") || q.includes("ssy")) {
      router.push("/schemes/SSY");
    } else {
      router.push(`/schemes?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const { isAuthenticated, role } = useAuth();
  const checkEligibilityHref =
    isAuthenticated && role === "CITIZEN"
      ? "/eligibility"
      : "/citizen/login?redirect=/eligibility";

  return (
    <div className="space-y-12 sm:space-y-16">
      {/* Hero Section */}
      <section className="relative bg-primary-dark overflow-hidden min-h-[480px] sm:min-h-[520px] flex items-center" aria-label="Hero">
        {/* Background Image with Dark Navy Gradient Overlay */}
        <div className="absolute inset-0 z-0">
          <img
            src="/images/parliament_hero.jpg"
            alt="Sansad Bhavan - Parliament of India in New Delhi"
            className="w-full h-full object-cover object-center"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-navy-900/95 via-navy-900/85 to-navy-900/40" />
        </div>

        <div className="gov-container relative z-10 py-12 sm:py-16 w-full">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            {/* Left Col: Headlines, Search, Chips */}
            <div className="lg:col-span-8 space-y-6 text-white">
              <div className="inline-flex items-center space-x-2 text-xs font-semibold px-3 py-1 rounded bg-white/10 border border-white/20 text-blue-200 tracking-wide">
                <Landmark className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
                <span>{t("hero.eyebrow")}</span>
              </div>

              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight leading-tight">
                {t("hero.heading_part1")}{" "}
                <span className="text-amber-300">{t("hero.heading_highlight")}</span>
              </h1>

              <p className="text-sm sm:text-base text-gray-200 max-w-2xl leading-relaxed font-normal">
                {t("hero.subtitle")}
              </p>

              {/* Primary & Secondary Citizen Action CTAs */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
                <Link
                  href={checkEligibilityHref}
                  className="inline-flex items-center justify-center space-x-2 px-6 py-3.5 bg-amber-400 hover:bg-amber-300 text-navy-900 rounded-lg text-sm font-extrabold shadow-md transition-all hover:scale-[1.01] focus-visible:ring-2 focus-visible:ring-white min-h-[48px] text-center"
                >
                  <span>{t("hero.check_eligibility_cta")}</span>
                  <ArrowRight className="w-4 h-4" aria-hidden="true" />
                </Link>

                <Link
                  href="/schemes"
                  className="inline-flex items-center justify-center space-x-2 px-5 py-3.5 bg-white/15 hover:bg-white/25 text-white border border-white/30 rounded-lg text-sm font-bold backdrop-blur-xs transition-colors focus-visible:ring-2 focus-visible:ring-white min-h-[48px] text-center"
                >
                  <span>{t("hero.explore_schemes_cta")}</span>
                </Link>
              </div>

              {/* Compact Auxiliary Search */}
              <div className="pt-2 max-w-xl">
                <p className="text-xs text-gray-300 mb-1.5 font-medium">
                  {t("hero.search_heading")}
                </p>
                <form onSubmit={handleSearch} role="search">
                  <div className="relative flex items-center bg-white/10 hover:bg-white/15 focus-within:bg-white border border-white/20 focus-within:border-white rounded-lg p-1 transition-all group">
                    <Search className="w-4 h-4 text-gray-300 group-focus-within:text-gov-secondary ml-2.5 flex-shrink-0" aria-hidden="true" />
                    <label htmlFor="hero-search-input" className="sr-only">
                      {t("hero.search_placeholder")}
                    </label>
                    <input
                      id="hero-search-input"
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder={t("hero.search_placeholder")}
                      className="w-full px-2.5 py-1.5 text-xs text-white group-focus-within:text-gov-text bg-transparent focus:outline-none placeholder-gray-300 group-focus-within:placeholder-gray-400 min-h-[36px]"
                    />
                    <button
                      type="submit"
                      className="px-3.5 py-1.5 bg-primary hover:bg-primary-dark text-white rounded text-xs font-semibold shadow-xs transition-colors flex items-center space-x-1 flex-shrink-0 min-h-[32px] focus-visible:ring-2 focus-visible:ring-primary"
                    >
                      <span>{t("hero.search_button")}</span>
                    </button>
                  </div>
                </form>
              </div>

              {/* Supported Schemes Direct Access Chips */}
              <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                <span className="text-gray-300 font-medium">{t("hero.popular_searches")}</span>
                <Link
                  href="/schemes/PM_KISAN"
                  className="px-3 py-1.5 rounded-full bg-white/15 hover:bg-white/25 text-white border border-white/20 transition-colors font-medium min-h-[32px] inline-flex items-center focus-visible:ring-2 focus-visible:ring-primary"
                >
                  {t("schemes.pm_kisan")}
                </Link>
                <Link
                  href="/schemes/SSY"
                  className="px-3 py-1.5 rounded-full bg-white/15 hover:bg-white/25 text-white border border-white/20 transition-colors font-medium min-h-[32px] inline-flex items-center focus-visible:ring-2 focus-visible:ring-primary"
                >
                  {t("schemes.ssy")}
                </Link>
              </div>
            </div>

            {/* Right Col: Floating Trust Card */}
            <div className="lg:col-span-4 flex justify-center lg:justify-end">
              <TrustCard />
            </div>
          </div>
        </div>
      </section>

      {/* Popular Schemes Section */}
      <section className="gov-container" aria-labelledby="popular-schemes-heading">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-8 gap-4">
          <div>
            <h2 id="popular-schemes-heading" className="text-2xl sm:text-3xl font-bold text-primary-dark tracking-tight">
              {t("schemes.section_title")}
            </h2>
            <p className="text-sm text-gov-secondary mt-1 max-w-2xl">
              {t("schemes.section_subtitle")}
            </p>
          </div>
          <Link
            href="/schemes"
            className="inline-flex items-center text-xs font-bold text-primary hover:text-primary-dark transition-colors focus-visible:ring-2 focus-visible:ring-primary rounded p-1 min-h-[36px]"
          >
            <span>{t("schemes.view_all")}</span>
            <ChevronRight className="w-4 h-4 ml-0.5" aria-hidden="true" />
          </Link>
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
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {schemes?.map((s) => (
              <SchemeCard key={s.id} scheme={s} />
            ))}
          </div>
        )}
      </section>

      {/* How YogyataMitra Works */}
      <section className="bg-white border-y border-gov-border py-12 sm:py-16" aria-labelledby="how-it-works-heading">
        <div className="gov-container">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 id="how-it-works-heading" className="text-2xl sm:text-3xl font-bold text-primary-dark tracking-tight">
              {t("how_it_works.title")}
            </h2>
            <p className="text-sm text-gov-secondary mt-2">
              {t("how_it_works.subtitle")}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-gov-bg p-6 rounded-lg border border-gov-border space-y-2">
              <div className="w-8 h-8 rounded-full bg-primary-50 text-primary font-bold flex items-center justify-center text-sm border border-primary-100">
                1
              </div>
              <h3 className="font-bold text-sm text-gov-text pt-2">
                {t("how_it_works.step1_title")}
              </h3>
              <p className="text-xs text-gov-secondary leading-relaxed">
                {t("how_it_works.step1_desc")}
              </p>
            </div>

            <div className="bg-gov-bg p-6 rounded-lg border border-gov-border space-y-2">
              <div className="w-8 h-8 rounded-full bg-primary-50 text-primary font-bold flex items-center justify-center text-sm border border-primary-100">
                2
              </div>
              <h3 className="font-bold text-sm text-gov-text pt-2">
                {t("how_it_works.step2_title")}
              </h3>
              <p className="text-xs text-gov-secondary leading-relaxed">
                {t("how_it_works.step2_desc")}
              </p>
            </div>

            <div className="bg-gov-bg p-6 rounded-lg border border-gov-border space-y-2">
              <div className="w-8 h-8 rounded-full bg-primary-50 text-primary font-bold flex items-center justify-center text-sm border border-primary-100">
                3
              </div>
              <h3 className="font-bold text-sm text-gov-text pt-2">
                {t("how_it_works.step3_title")}
              </h3>
              <p className="text-xs text-gov-secondary leading-relaxed">
                {t("how_it_works.step3_desc")}
              </p>
            </div>

            <div className="bg-gov-bg p-6 rounded-lg border border-gov-border space-y-2">
              <div className="w-8 h-8 rounded-full bg-primary-50 text-primary font-bold flex items-center justify-center text-sm border border-primary-100">
                4
              </div>
              <h3 className="font-bold text-sm text-gov-text pt-2">
                {t("how_it_works.step4_title")}
              </h3>
              <p className="text-xs text-gov-secondary leading-relaxed">
                {t("how_it_works.step4_desc")}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Institutional Commitment / Trust Pillars */}
      <section className="gov-container pb-8" aria-labelledby="institutional-commitment-heading">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 id="institutional-commitment-heading" className="text-2xl sm:text-3xl font-bold text-primary-dark tracking-tight">
            {t("trust.section_title")}
          </h2>
          <p className="text-sm text-gov-secondary mt-2">
            {t("trust.section_subtitle")}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-white p-6 rounded-lg border border-gov-border shadow-gov-card space-y-3">
            <div className="w-10 h-10 rounded-md bg-blue-50 text-primary flex items-center justify-center border border-blue-100">
              <ShieldCheck className="w-5 h-5" aria-hidden="true" />
            </div>
            <h3 className="font-bold text-base text-gov-text">
              {t("trust.pillar1_title")}
            </h3>
            <p className="text-xs text-gov-secondary leading-relaxed">
              {t("trust.pillar1_desc")}
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg border border-gov-border shadow-gov-card space-y-3">
            <div className="w-10 h-10 rounded-md bg-blue-50 text-primary flex items-center justify-center border border-blue-100">
              <FileCheck className="w-5 h-5" aria-hidden="true" />
            </div>
            <h3 className="font-bold text-base text-gov-text">
              {t("trust.pillar2_title")}
            </h3>
            <p className="text-xs text-gov-secondary leading-relaxed">
              {t("trust.pillar2_desc")}
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg border border-gov-border shadow-gov-card space-y-3">
            <div className="w-10 h-10 rounded-md bg-blue-50 text-primary flex items-center justify-center border border-blue-100">
              <Scale className="w-5 h-5" aria-hidden="true" />
            </div>
            <h3 className="font-bold text-base text-gov-text">
              {t("trust.pillar3_title")}
            </h3>
            <p className="text-xs text-gov-secondary leading-relaxed">
              {t("trust.pillar3_desc")}
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg border border-gov-border shadow-gov-card space-y-3">
            <div className="w-10 h-10 rounded-md bg-blue-50 text-primary flex items-center justify-center border border-blue-100">
              <History className="w-5 h-5" aria-hidden="true" />
            </div>
            <h3 className="font-bold text-base text-gov-text">
              {t("trust.pillar4_title")}
            </h3>
            <p className="text-xs text-gov-secondary leading-relaxed">
              {t("trust.pillar4_desc")}
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
