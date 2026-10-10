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
import { useAuth } from "../../../context/AuthContext";
import { getOfficialSourceUrl, getOfficialSourceTitle } from "../../../utils/officialSources";

const SCHEME_CRITERIA_MAP: Record<
  string,
  { who_for_en: string; who_for_hi: string; criteria_en: string; criteria_hi: string }
> = {
  PM_KISAN: {
    who_for_en:
      "Eligible landholding farmer families with cultivable land, subject to the applicable scheme exclusions.",
    who_for_hi:
      "खेती योग्य भूमि वाले पात्र किसान परिवार, बशर्ते वे योजना बहिष्करणों के अंतर्गत न आते हों।",
    criteria_en:
      "Ownership of cultivable land by the farmer family, subject to scheme exclusions (including institutional landholders, constitutional post holders, government employees/pensioners with pension >= ₹10,000, income tax payees, professionals, and post-cutoff transfers without inheritance).",
    criteria_hi:
      "किसान परिवार के पास खेती योग्य भूमि का स्वामित्व, योजना बहिष्करणों के अधीन (संस्थागत भूधारक, संवैधानिक पदधारक, ₹10,000 से अधिक पेंशन वाले सरकारी कर्मचारी/पेंशनभोगी, आयकर दाता, पेशेवर, और उत्तराधिकार के बिना कट-ऑफ के बाद हस्तांतरण)।",
  },
  SSY: {
    who_for_en:
      "Parents or legal guardians opening an account in the name of an Indian resident girl child from birth up to age 10.",
    who_for_hi:
      "माता-पिता या कानूनी अभिभावक जो जन्म से 10 वर्ष तक की भारतीय निवासी बालिका के नाम पर खाता खोलते हैं।",
    criteria_en:
      "Beneficiary must be a girl child; age must not exceed 10 years at account opening; maximum two accounts per family (with statutory multiple-birth exceptions); natural or court-appointed legal guardian required.",
    criteria_hi:
      "लाभार्थी बालिका होनी चाहिए; खाता खोलते समय आयु 10 वर्ष से अधिक नहीं होनी चाहिए; प्रति परिवार अधिकतम दो खाते (वैधानिक बहु-जन्म अपवादों के साथ); प्राकृतिक या कानूनी अभिभावक आवश्यक।",
  },
  PM_KMY: {
    who_for_en:
      "Small and Marginal Farmers (SMF) possessing cultivable land up to 2 hectares in State/UT land records.",
    who_for_hi:
      "छोटे और सीमांत किसान (एसएमएफ) जिनके पास राज्य/केंद्र शासित प्रदेश के भूमि अभिलेखों में 2 हेक्टेयर तक कृषि योग्य भूमि है।",
    criteria_en:
      "Entry age between 18 and 40 years; cultivable landholding up to 2.0 hectares; not covered under other statutory social security schemes (NPS, ESIC, EPFO, PM-SYM).",
    criteria_hi:
      "प्रवेश आयु 18 से 40 वर्ष के बीच; 2.0 हेक्टेयर तक कृषि योग्य भूमि; अन्य वैधानिक सामाजिक सुरक्षा योजनाओं (NPS, ESIC, EPFO, PM-SYM) के अंतर्गत कवर न हों।",
  },
  PMUY: {
    who_for_en:
      "Adult women from eligible deprived / BPL households without an existing LPG connection.",
    who_for_hi:
      "पात्र वंचित/बीपीएल परिवारों की वयस्क महिलाएं जिनके घर में कोई पूर्व एलपीजी कनेक्शन नहीं है।",
    criteria_en:
      "Applicant must be an adult female (18+); belonging to eligible deprivation category (SECC, SC/ST, PMAY, AAY, most backward classes); no existing active LPG connection in the household.",
    criteria_hi:
      "आवेदक वयस्क महिला (18+) होनी चाहिए; पात्र वंचित श्रेणी (SECC, SC/ST, PMAY, AAY, अत्यंत पिछड़ा वर्ग) से संबंधित; परिवार में कोई सक्रिय एलपीजी कनेक्शन न हो।",
  },
  PM_VISHWAKARMA: {
    who_for_en:
      "Traditional artisans and craftspeople working with their hands and tools in 18 notified family-based trades.",
    who_for_hi:
      "18 अधिसूचित पारिवारिक पारंपरिक शिल्पों में अपने हाथों और औजारों से काम करने वाले कारीगर और शिल्पकार।",
    criteria_en:
      "Engaged in one of 18 notified artisan trades; minimum age 18 years; strictly one beneficiary per family; no similar government credit assistance availed in the last 5 years.",
    criteria_hi:
      "18 अधिसूचित पारंपरिक शिल्पों में से किसी एक में कार्यरत; न्यूनतम आयु 18 वर्ष; प्रति परिवार केवल एक लाभार्थी; पिछले 5 वर्षों में समान सरकारी ऋण सहायता न ली हो।",
  },
  PMAY_G: {
    who_for_en:
      "Rural houseless families or households living in zero, one, or two-room houses with kutcha wall and kutcha roof.",
    who_for_hi:
      "ग्रामीण बेघर परिवार या कच्चे कमरे वाले जर्जर अस्थायी घरों में रहने वाले परिवार।",
    criteria_en:
      "Must reside in rural area; houseless or living in kutcha house; listed under SECC 2011 deprivation criteria or verified Awaas+ list; must not own a pucca house anywhere in India.",
    criteria_hi:
      "ग्रामीण क्षेत्र में निवास; बेघर या कच्चे मकान में रहने वाले; SECC 2011 या आवास+ सूची में शामिल; भारत में कहीं भी पक्का मकान न हो।",
  },
  PMAY_U_2_0: {
    who_for_en:
      "Economically Weaker Section (EWS), Low Income Group (LIG), and Middle Income Group (MIG) families living in statutory urban areas.",
    who_for_hi:
      "वैधानिक शहरी क्षेत्रों में रहने वाले आर्थिक रूप से कमजोर वर्ग (EWS), निम्न आय वर्ग (LIG), और मध्यम आय वर्ग (MIG) के परिवार।",
    criteria_en:
      "Resident of statutory town/urban agglomeration; family must not own a pucca house anywhere in India; annual household income within statutory limits (EWS ≤ ₹3 Lakh, LIG ≤ ₹6 Lakh, MIG ≤ ₹9 Lakh).",
    criteria_hi:
      "वैधानिक शहर/शहरी क्षेत्र का निवासी; परिवार के पास भारत में कहीं भी पक्का मकान न हो; वार्षिक पारिवारिक आय वैधानिक सीमा के भीतर (EWS ≤ ₹3 लाख, LIG ≤ ₹6 लाख, MIG ≤ ₹9 लाख)।",
  },
  PM_SVANIDHI: {
    who_for_en:
      "Urban street vendors engaged in vending of goods or services in urban areas on or before statutory cutoff dates.",
    who_for_hi:
      "वैधानिक कट-ऑफ तिथि पर या उससे पहले शहरी क्षेत्रों में वस्तुओं या सेवाओं की बिक्री करने वाले स्ट्रीट वेंडर।",
    criteria_en:
      "Urban street vendor with Certificate of Vending (CoV) / Identity Card issued by ULB/Town Vending Committee, or Letter of Recommendation (LOR); minimum age 18 years.",
    criteria_hi:
      "शहरी स्थानीय निकाय/टाउन वेंडिंग कमेटी द्वारा जारी वेंडिंग प्रमाण पत्र (CoV)/पहचान पत्र, या अनुशंसा पत्र (LOR) धारक स्ट्रीट वेंडर; न्यूनतम आयु 18 वर्ष।",
  },
  PMMVY: {
    who_for_en:
      "Pregnant Women and Lactating Mothers (PW&LM) under Mission Shakti for maternity support and nutrition.",
    who_for_hi:
      "मातृत्व सहायता और पोषण के लिए मिशन शक्ति के अंतर्गत गर्भवती महिलाएं और स्तनपान कराने वाली माताएं (PW&LM)।",
    criteria_en:
      "Pregnant woman or lactating mother; eligible for first live birth, or second child if girl child; registered at Anganwadi/Health facility with MCP card; not regular government/PSU employee.",
    criteria_hi:
      "गर्भवती महिला या स्तनपान कराने वाली माता; पहले जीवित बच्चे के लिए, या बालिका होने पर दूसरे बच्चे के लिए पात्र; एमसीपी कार्ड के साथ आंगनवाड़ी/स्वास्थ्य केंद्र में पंजीकृत; नियमित सरकारी/पीएसयू कर्मचारी न हों।",
  },
  IGNOAPS: {
    who_for_en:
      "Elderly Indian citizens living below the poverty line (BPL) under the National Social Assistance Programme (NSAP).",
    who_for_hi:
      "राष्ट्रीय सामाजिक सहायता कार्यक्रम (NSAP) के तहत गरीबी रेखा से नीचे (BPL) रहने वाले बुजुर्ग भारतीय नागरिक।",
    criteria_en:
      "Citizen aged 60 years or above; must belong to a Below Poverty Line (BPL) household verified by competent State/UT civil supplies authority.",
    criteria_hi:
      "60 वर्ष या उससे अधिक आयु के नागरिक; राज्य/केंद्र शासित प्रदेश के सक्षम नागरिक आपूर्ति प्राधिकरण द्वारा सत्यापित गरीबी रेखा से नीचे (BPL) परिवार से संबंधित हों।",
  },
};

export default function SchemeDetailPage() {
  const params = useParams();
  const schemeCode = (params.schemeCode as string)?.toUpperCase();
  const { isHindi, t } = useLanguage();
  const { isAuthenticated, role } = useAuth();

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
  const officialSourceUrl = getOfficialSourceUrl(scheme.scheme_code, scheme.official_url);
  const officialSourceTitle = getOfficialSourceTitle(scheme.scheme_code, isHindi, scheme.ministry);

  const checkEligibilityHref =
    isAuthenticated && role === "CITIZEN"
      ? `/eligibility?scheme=${scheme.scheme_code}`
      : `/citizen/login?redirect=${encodeURIComponent(`/eligibility?scheme=${scheme.scheme_code}`)}`;

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
              href={checkEligibilityHref}
              className="inline-flex items-center justify-center space-x-2 px-6 py-3 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm font-bold shadow-xs transition-colors text-center focus-visible:ring-2 focus-visible:ring-primary min-h-[44px]"
            >
              <span>{t("scheme_detail.check_my_eligibility")}</span>
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>

            {officialSourceUrl && (
              <a
                href={officialSourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`${t("claims.view_official_source")} — ${officialSourceTitle} (${t("a11y.external_link")})`}
                className="inline-flex items-center justify-center space-x-1.5 px-4 py-2.5 bg-white border border-gov-border hover:bg-gray-50 text-gov-text rounded-lg text-xs font-semibold transition-colors text-center focus-visible:ring-2 focus-visible:ring-primary min-h-[38px] shadow-xs"
              >
                <span>[ {t("claims.view_official_source")} ]</span>
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
              {SCHEME_CRITERIA_MAP[schemeCode]
                ? (isHindi ? SCHEME_CRITERIA_MAP[schemeCode].who_for_hi : SCHEME_CRITERIA_MAP[schemeCode].who_for_en)
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
              {SCHEME_CRITERIA_MAP[schemeCode]
                ? (isHindi ? SCHEME_CRITERIA_MAP[schemeCode].criteria_hi : SCHEME_CRITERIA_MAP[schemeCode].criteria_en)
                : description}
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
