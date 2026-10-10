/**
 * Canonical Government of India Official Scheme Sources
 *
 * Provides verified and working official source documents and portals
 * for statutory welfare schemes in YogyataMitra.
 */

export const OFFICIAL_SCHEME_SOURCES: Record<string, string> = {
  PM_KISAN:
    "https://pmkisan.gov.in/Documents/RevisedPM-KISANOperationalGuidelines%28English%29.pdf",
  SSY: "https://dea.gov.in/index.php/budget-division/sukanya-samriddhi-account",
  PM_KMY: "https://pmkmy.gov.in/",
  PMUY: "https://www.pmuy.gov.in/",
  PM_VISHWAKARMA: "https://pmvishwakarma.gov.in/",
  PMAY_G: "https://pmayg.dord.gov.in/",
  PMAY_U_2_0: "https://pmay-urban.gov.in/",
  PM_SVANIDHI: "https://pmsvanidhi.mohua.gov.in/",
  PMMVY: "https://pmmvy.wcd.gov.in/",
  IGNOAPS: "https://nsap.nic.in/",
};

export const OFFICIAL_SCHEME_TITLES: Record<string, { en: string; hi: string }> = {
  PM_KISAN: {
    en: "Revised PM-KISAN Operational Guidelines (Government of India)",
    hi: "संशोधित पीएम-किसान परिचालन दिशानिर्देश (भारत सरकार)",
  },
  SSY: {
    en: "Sukanya Samriddhi Account — Department of Economic Affairs, Ministry of Finance",
    hi: "सुकन्या समृद्धि खाता — आर्थिक कार्य विभाग, वित्त मंत्रालय",
  },
  PM_KMY: {
    en: "Pradhan Mantri Kisan Maandhan Yojana Operational Guidelines (Ministry of Agriculture & Farmers Welfare)",
    hi: "प्रधानमंत्री किसान मानधन योजना परिचालन दिशानिर्देश (कृषि एवं किसान कल्याण मंत्रालय)",
  },
  PMUY: {
    en: "Pradhan Mantri Ujjwala Yojana 2.0 Guidelines (Ministry of Petroleum & Natural Gas)",
    hi: "प्रधानमंत्री उज्ज्वला योजना 2.0 दिशानिर्देश (पेट्रोलियम और प्राकृतिक गैस मंत्रालय)",
  },
  PM_VISHWAKARMA: {
    en: "PM Vishwakarma Scheme Guidelines (Ministry of Micro, Small and Medium Enterprises)",
    hi: "पीएम विश्वकर्मा योजना दिशानिर्देश (सूक्ष्म, लघु और मध्यम उद्यम मंत्रालय)",
  },
  PMAY_G: {
    en: "Pradhan Mantri Awaas Yojana - Gramin Framework for Implementation (Ministry of Rural Development)",
    hi: "प्रधानमंत्री आवास योजना - ग्रामीण कार्यान्वयन रूपरेखा (ग्रामीण विकास मंत्रालय)",
  },
  PMAY_U_2_0: {
    en: "Pradhan Mantri Awas Yojana - Urban 2.0 Guidelines (Ministry of Housing and Urban Affairs)",
    hi: "प्रधानमंत्री आवास योजना - शहरी 2.0 दिशानिर्देश (आवासन और शहरी कार्य मंत्रालय)",
  },
  PM_SVANIDHI: {
    en: "PM Street Vendor's AtmaNirbhar Nidhi Guidelines (Ministry of Housing and Urban Affairs)",
    hi: "पीएम स्ट्रीट वेंडर्स आत्मनिर्भर निधि दिशानिर्देश (आवासन और शहरी कार्य मंत्रालय)",
  },
  PMMVY: {
    en: "Pradhan Mantri Matru Vandana Yojana Guidelines - Mission Shakti (Ministry of Women and Child Development)",
    hi: "प्रधानमंत्री मातृ वंदना योजना दिशानिर्देश - मिशन शक्ति (महिला एवं बाल विकास मंत्रालय)",
  },
  IGNOAPS: {
    en: "Indira Gandhi National Old Age Pension Scheme Guidelines (National Social Assistance Programme, MoRD)",
    hi: "इंदिरा गांधी राष्ट्रीय वृद्धावस्था पेंशन योजना दिशानिर्देश (राष्ट्रीय सामाजिक सहायता कार्यक्रम, ग्रामीण विकास मंत्रालय)",
  },
};

/**
 * Returns the verified canonical official source URL for a given scheme.
 * Resolves to the verified GoI document/portal link for PM_KISAN and SSY.
 * Falls back to provided sourceUrl if unknown scheme.
 */
export function getOfficialSourceUrl(
  schemeCode?: string | null,
  fallbackUrl?: string | null
): string {
  if (!schemeCode) return fallbackUrl || "";
  const code = schemeCode.trim().toUpperCase();
  if (OFFICIAL_SCHEME_SOURCES[code]) {
    return OFFICIAL_SCHEME_SOURCES[code];
  }
  return fallbackUrl || "";
}

/**
 * Returns the verified official source title for a given scheme.
 */
export function getOfficialSourceTitle(
  schemeCode?: string | null,
  isHindi: boolean = false,
  fallbackTitle?: string | null
): string {
  if (!schemeCode) return fallbackTitle || "Official Statutory Guidelines";
  const code = schemeCode.trim().toUpperCase();
  const entry = OFFICIAL_SCHEME_TITLES[code];
  if (entry) {
    return isHindi ? entry.hi : entry.en;
  }
  return fallbackTitle || "Official Statutory Guidelines";
}
