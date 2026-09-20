/**
 * Centralized Statutory Rule Presentation & Plain-Language Mapping.
 * Translates internal rule IDs, AST codes, and statutory policy definitions
 * into citizen-friendly language in both English and Hindi.
 *
 * Invariant: Never leak raw rule IDs, field paths, or dot notation into citizen views.
 */

import { PolicyTimelineStatus } from "../types/audit";

export interface RulePresentationMeta {
  titleEn: string;
  titleHi: string;
  explanationEn: string;
  explanationHi: string;
}

export const RULE_PRESENTATION_MAP: Record<string, RulePresentationMeta> = {
  // PM-KISAN Exclusion Rules
  "PMKISAN-EXCL-CONSTITUTIONAL": {
    titleEn: "Constitutional Post Exclusion",
    titleHi: "संवैधानिक पद धारक बहिष्करण",
    explanationEn: "Holders of constitutional posts are excluded from benefits under scheme guidelines.",
    explanationHi: "संवैधानिक पद धारक योजना के दिशानिर्देशों के तहत लाभ के पात्र नहीं हैं।",
  },
  "PMKISAN-EXCL-GOVT-EMPLOYEE": {
    titleEn: "Government Employment Exclusion",
    titleHi: "सरकारी सेवा बहिष्करण",
    explanationEn: "Regular serving or retired officers and employees of central/state government and PSUs are excluded.",
    explanationHi: "केंद्र/राज्य सरकार एवं सार्वजनिक उपक्रमों के नियमित सेवारत अथवा सेवानिवृत्त कर्मचारी योजना के तहत बहिष्कृत हैं।",
  },
  "PMKISAN-EXCL-INCOME-TAX": {
    titleEn: "Income Tax Payer Exclusion",
    titleHi: "आयकर दाता बहिष्करण",
    explanationEn: "Individuals or family members who paid income tax in the last assessment year are excluded from benefits.",
    explanationHi: "पिछले निर्धारण वर्ष में आयकर का भुगतान करने वाले व्यक्ति या उनके परिवार के सदस्य योजना से बहिष्कृत हैं।",
  },
  "PMKISAN-EXCL-INSTITUTIONAL": {
    titleEn: "Institutional Landholder Exclusion",
    titleHi: "संस्थागत भूमि धारक बहिष्करण",
    explanationEn: "Institutional landholders are not eligible for benefits under scheme guidelines.",
    explanationHi: "संस्थागत भूमि धारक योजना के दिशानिर्देशों के तहत लाभ के पात्र नहीं हैं।",
  },
  "PMKISAN-EXCL-NRI": {
    titleEn: "Non-Resident Indian (NRI) Exclusion",
    titleHi: "अनिवासी भारतीय (NRI) बहिष्करण",
    explanationEn: "The scheme does not apply to families falling under the applicable NRI exclusion.",
    explanationHi: "यह योजना लागू अनिवासी भारतीय (NRI) बहिष्करण श्रेणी के अंतर्गत आने वाले परिवारों पर लागू नहीं होती है।",
  },
  "PMKISAN-EXCL-PENSIONER": {
    titleEn: "High Pensioner Exclusion (₹10,000+/month)",
    titleHi: "उच्च पेंशनभोगी बहिष्करण (₹10,000+/माह)",
    explanationEn: "Retired individuals receiving a monthly pension of ₹10,000 or more are excluded.",
    explanationHi: "₹10,000 या अधिक मासिक पेंशन प्राप्त करने वाले सेवानिवृत्त व्यक्ति योजना से बहिष्कृत हैं।",
  },
  "PMKISAN-EXCL-PROFESSIONAL": {
    titleEn: "Registered Professional Exclusion",
    titleHi: "पंजीकृत पेशेवर बहिष्करण",
    explanationEn: "Registered doctors, engineers, lawyers, and chartered accountants are excluded.",
    explanationHi: "पंजीकृत डॉक्टर, इंजीनियर, वकील और चार्टर्ड एकाउंटेंट योजना से बहिष्कृत हैं।",
  },
  "PMKISAN-EXCL-PUBLIC-REPRESENTATIVE": {
    titleEn: "Elected Public Representative Exclusion",
    titleHi: "निर्वाचित जन-प्रतिनिधि बहिष्करण",
    explanationEn: "Former or sitting members of Parliament, State Legislatures, Mayors, and District Panchayat Chairpersons are excluded.",
    explanationHi: "संसद, राज्य विधानसभाओं के पूर्व या वर्तमान सदस्य, महापौर तथा जिला पंचायत अध्यक्ष योजना से बहिष्कृत हैं।",
  },

  // PM-KISAN Land Rules
  "PMKISAN-HIST-LAND-CEILING-2HA": {
    titleEn: "Landholding Ceiling (Up to 2.0 Hectares)",
    titleHi: "भूमि सीमा (अधिकतम 2.0 हेक्टेयर)",
    explanationEn: "Under original 2018 guidelines, cultivable landholding was limited to a maximum of 2.0 hectares.",
    explanationHi: "मूल 2018 दिशानिर्देशों के तहत, कृषि योग्य भूमि स्वामित्व अधिकतम 2.0 हेक्टेयर तक सीमित था।",
  },
  "PMKISAN-LAND-CULTIVABLE": {
    titleEn: "Cultivable Agricultural Land Ownership",
    titleHi: "कृषि योग्य भूमि का स्वामित्व",
    explanationEn: "The family must own cultivable agricultural land as per official revenue land records.",
    explanationHi: "आधिकारिक राजस्व अभिलेखों के अनुसार परिवार के पास कृषि योग्य भूमि का स्वामित्व होना अनिवार्य है।",
  },
  "PMKISAN-LAND-CUTOFF-2019": {
    titleEn: "Land Ownership Cutoff (01-Feb-2019) or Inheritance",
    titleHi: "भूमि कट-ऑफ तिथि (01-फरवरी-2019) अथवा विरासत",
    explanationEn: "Landholding must be owned on or before the statutory cutoff date of 01-Feb-2019, or acquired post-cutoff via inheritance/succession.",
    explanationHi: "भूमि स्वामित्व 1 फरवरी 2019 की निर्धारित कट-ऑफ तिथि को या उससे पूर्व होना चाहिए, अथवा कट-ऑफ के बाद केवल उत्तराधिकार/विरासत द्वारा प्राप्त होना चाहिए।",
  },
  "PMKISAN-LAND-OWNED-PRE-CUTOFF": {
    titleEn: "Land Owned On or Before Cutoff",
    titleHi: "कट-ऑफ तिथि से पूर्व भूमि स्वामित्व",
    explanationEn: "Land was registered and owned on or before 01-Feb-2019.",
    explanationHi: "कृषि भूमि का स्वामित्व 1 फरवरी 2019 को या उससे पहले दर्ज था।",
  },
  "PMKISAN-LAND-POST-CUTOFF-FLAG": {
    titleEn: "Land Acquired After Cutoff Date",
    titleHi: "कट-ऑफ तिथि के बाद भूमि अधिग्रहण",
    explanationEn: "Land was transferred or acquired after 01-Feb-2019.",
    explanationHi: "कृषि भूमि का हस्तांतरण या अधिग्रहण 1 फरवरी 2019 के बाद हुआ।",
  },
  "PMKISAN-LAND-PREV-OWNER-DECEASED": {
    titleEn: "Previous Landowner Deceased Status",
    titleHi: "पूर्व भूमिधारक के देहांत की स्थिति",
    explanationEn: "The previous landowner is deceased, supporting inheritance eligibility.",
    explanationHi: "पूर्व भूमिधारक का देहांत हो चुका है, जो विरासत के आधार पर पात्रता का समर्थन करता है।",
  },
  "PMKISAN-LAND-ACQUISITION-SUCCESSION": {
    titleEn: "Acquisition via Legal Succession",
    titleHi: "कानूनी उत्तराधिकार द्वारा अधिग्रहण",
    explanationEn: "Land ownership was acquired through legal succession or inheritance.",
    explanationHi: "भूमि का स्वामित्व कानूनी उत्तराधिकार अथवा विरासत के माध्यम से प्राप्त हुआ।",
  },
  "PMKISAN-LAND-QUALIFYING-SUCCESSION": {
    titleEn: "Qualifying Inheritance Exception",
    titleHi: "मान्य उत्तराधिकार छूट",
    explanationEn: "Land transferred after cutoff qualifies under the statutory succession exception.",
    explanationHi: "कट-ऑफ तिथि के बाद हस्तांतरित भूमि वैधानिक उत्तराधिकार छूट के अंतर्गत मान्य है।",
  },

  // PM-KISAN Policy Roots
  "PMKISAN-V1-ROOT": {
    titleEn: "PM-KISAN 2018 Statutory Criteria",
    titleHi: "पीएम-किसान 2018 वैधानिक मानदंड",
    explanationEn: "Statutory eligibility criteria under PM-KISAN 2018 Guidelines (Small & Marginal Farmers).",
    explanationHi: "पीएम-किसान 2018 दिशानिर्देशों (लघु एवं सीमांत किसान) के तहत वैधानिक पात्रता मानदंड।",
  },
  "PMKISAN-V2-ROOT": {
    titleEn: "PM-KISAN 2019 Statutory Criteria",
    titleHi: "पीएम-किसान 2019 वैधानिक मानदंड",
    explanationEn: "Statutory eligibility criteria under PM-KISAN 2019 Revised Guidelines (Universal Expansion).",
    explanationHi: "पीएम-किसान 2019 संशोधित दिशानिर्देशों (सार्वभौमिक विस्तार) के तहत वैधानिक पात्रता मानदंड।",
  },
  "PMKISAN-V3-ROOT": {
    titleEn: "PM-KISAN 2023 Statutory Criteria",
    titleHi: "पीएम-किसान 2023 वैधानिक मानदंड",
    explanationEn: "Statutory eligibility criteria under PM-KISAN 2023 Operational Guidelines.",
    explanationHi: "पीएम-किसान 2023 परिचालन दिशानिर्देशों के तहत वैधानिक पात्रता मानदंड।",
  },

  // Sukanya Samriddhi Yojana (SSY) Rules
  "SSY-AGE-LIMIT-10": {
    titleEn: "Girl Child Age Limit (Under 10 Years)",
    titleHi: "बालिका की आयु सीमा (10 वर्ष से कम)",
    explanationEn: "The girl child must not have attained 10 years of age on the date of account opening.",
    explanationHi: "खाता खोलने की तिथि पर बालिका की आयु 10 वर्ष से अधिक नहीं होनी चाहिए।",
  },
  "SSY-BENEFICIARY-GENDER": {
    titleEn: "Beneficiary Gender (Girl Child)",
    titleHi: "लाभार्थी का लिंग (बालिका)",
    explanationEn: "The account beneficiary must be a girl child.",
    explanationHi: "योजना की लाभार्थी केवल बालिका होनी चाहिए।",
  },
  "SSY-BENEFICIARY-RESIDENT": {
    titleEn: "Indian Resident Citizen Status",
    titleHi: "भारतीय निवासी नागरिक स्थिति",
    explanationEn: "The girl child must be a resident citizen of India.",
    explanationHi: "बालिका भारत की निवासी नागरिक होनी चाहिए।",
  },
  "SSY-FAMILY-ACCOUNT-LIMIT": {
    titleEn: "Family Account Limit (Maximum Two)",
    titleHi: "परिवार में खाता सीमा (अधिकतम दो)",
    explanationEn: "A family can open a maximum of two SSY accounts, with exceptions for multiple births.",
    explanationHi: "एक परिवार में अधिकतम दो सुकन्या समृद्धि खाते खोले जा सकते हैं, जिसमें जुड़वां/तिड़वां जन्म की स्थिति में छूट प्राप्त है।",
  },
  "SSY-FAMILY-ACCOUNTS-UNDER-TWO": {
    titleEn: "Active Accounts Count Below Threshold",
    titleHi: "सक्रिय खातों की संख्या सीमा के भीतर",
    explanationEn: "Existing active SSY accounts in the family must be fewer than two.",
    explanationHi: "परिवार में पहले से सक्रिय सुकन्या समृद्धि खातों की संख्या दो से कम होनी चाहिए।",
  },
  "SSY-GUARDIAN-ELIGIBILITY": {
    titleEn: "Authorized Guardian Requirement",
    titleHi: "अधिकृत अभिभावक की अनिवार्यता",
    explanationEn: "The account must be opened and operated by the natural or legal guardian.",
    explanationHi: "खाता केवल प्राकृतिक या कानूनी अभिभावक द्वारा खोला एवं संचालित किया जाना चाहिए।",
  },
  "SSY-LEGAL-GUARDIAN": {
    titleEn: "Court-Appointed Legal Guardian",
    titleHi: "न्यायालय द्वारा नियुक्त कानूनी अभिभावक",
    explanationEn: "Account is opened by the court-appointed legal guardian.",
    explanationHi: "खाता न्यायालय द्वारा नियुक्त कानूनी अभिभावक द्वारा खोला जा रहा है।",
  },
  "SSY-NATURAL-GUARDIAN": {
    titleEn: "Natural Guardian (Parents)",
    titleHi: "प्राकृतिक अभिभावक (माता या पिता)",
    explanationEn: "Account is opened by the biological or adoptive parents as natural guardians.",
    explanationHi: "खाता प्राकृतिक अभिभावक (माता या पिता) द्वारा खोला जा रहा है।",
  },
  "SSY-MULTIPLE-BIRTH-EXCEPTION": {
    titleEn: "Multiple Birth Exception (Twins / Triplets)",
    titleHi: "जुड़वां / तिड़वां जन्म की विशेष छूट",
    explanationEn: "Permitted multiple-birth exception (twins or triplets) verified by official hospital records.",
    explanationHi: "अस्पताल अभिलेखों द्वारा सत्यापित जुड़वां अथवा तिड़वां बालिकाओं के जन्म की विशेष छूट।",
  },
  "SSY-ONE-ACCOUNT-PER-CHILD": {
    titleEn: "Single Account per Girl Child",
    titleHi: "प्रति बालिका केवल एक खाता",
    explanationEn: "Only one account may be opened in the name of a girl child across all banks and post offices.",
    explanationHi: "किसी भी बैंक या डाकघर में एक बालिका के नाम पर केवल एक ही खाता खोला जा सकता है।",
  },
  "SSY-V1-ROOT": {
    titleEn: "SSY 2016 Statutory Rules",
    titleHi: "सुकन्या समृद्धि नियम 2016",
    explanationEn: "Statutory eligibility criteria under Sukanya Samriddhi Account Rules, 2016.",
    explanationHi: "सुकन्या समृद्धि खाता नियम, 2016 के तहत वैधानिक पात्रता मानदंड।",
  },
  "SSY-V2-ROOT": {
    titleEn: "SSY 2019 Statutory Scheme",
    titleHi: "सुकन्या समृद्धि योजना 2019",
    explanationEn: "Statutory eligibility criteria under Sukanya Samriddhi Account Scheme, 2019.",
    explanationHi: "सुकन्या समृद्धि खाता योजना, 2019 के तहत वैधानिक पात्रता मानदंड।",
  },
  "SSY-V3-ROOT": {
    titleEn: "SSY 2024 Consolidated Scheme",
    titleHi: "सुकन्या समृद्धि समेकित योजना 2024",
    explanationEn: "Statutory eligibility criteria under Sukanya Samriddhi Account Scheme, 2019 (2024 Amendments).",
    explanationHi: "सुकन्या समृद्धि खाता योजना, 2019 (2024 संशोधन) के तहत वैधानिक पात्रता मानदंड।",
  },
};

/**
 * Returns citizen-friendly title for an internal rule ID.
 */
export function getFriendlyRuleTitle(ruleId: string, isHindi: boolean): string {
  const meta = RULE_PRESENTATION_MAP[ruleId];
  if (meta) {
    return isHindi ? meta.titleHi : meta.titleEn;
  }
  // Fallback: clean up ID into human title without dot notation or screams
  const cleaned = ruleId
    .replace(/^(PMKISAN|SSY|R)[-_]/i, "")
    .replace(/[-_]/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
  return cleaned;
}

/**
 * Returns plain-language explanation for an internal rule ID.
 */
export function getFriendlyRuleExplanation(ruleId: string, isHindi: boolean): string {
  const meta = RULE_PRESENTATION_MAP[ruleId];
  if (meta) {
    return isHindi ? meta.explanationHi : meta.explanationEn;
  }
  return isHindi
    ? "यह वैधानिक मानदंड योजना की आधिकारिक अधिसूचना के अनुसार निर्धारित किया गया है।"
    : "This statutory criterion is defined in accordance with the official scheme notification.";
}

/**
 * Statutory descriptions for all 6 official policy versions.
 * Derived strictly from authoritative guidelines and gazette orders.
 */
export const STATUTORY_POLICY_SUMMARIES: Record<
  string,
  { summaryEn: string; summaryHi: string; gazetteRefEn: string; gazetteRefHi: string }
> = {
  "PM_KISAN:v1.0-2018": {
    summaryEn:
      "Policy version applicable from 1 December 2018 to 31 March 2019, governing Small and Marginal Farmer families owning cultivable land up to 2.0 hectares.",
    summaryHi:
      "1 दिसंबर 2018 से 31 मार्च 2019 तक लागू नीति संस्करण, जो 2.0 हेक्टेयर तक कृषि योग्य भूमि वाले लघु एवं सीमांत किसान परिवारों पर लागू है।",
    gazetteRefEn: "Original Scheme Guidelines 2018-19 (Ministry of Agriculture and Farmers Welfare)",
    gazetteRefHi: "मूल योजना दिशानिर्देश 2018-19 (कृषि एवं किसान कल्याण मंत्रालय)",
  },
  "PM_KISAN:v2.0-2019": {
    summaryEn:
      "Policy version applicable from 1 April 2019 to 31 December 2022, governing landholding farmer families with land ownership cutoff date of 01-Feb-2019.",
    summaryHi:
      "1 अप्रैल 2019 से 31 दिसंबर 2022 तक लागू नीति संस्करण, जो 1 फरवरी 2019 की भूमि स्वामित्व कट-ऑफ तिथि के साथ भूमिधारक किसान परिवारों पर लागू है।",
    gazetteRefEn: "Cabinet Decision 31.05.2019 & Operational Guidelines (Ministry of Agriculture and Farmers Welfare)",
    gazetteRefHi: "केंद्रीय मंत्रिमंडल निर्णय 31.05.2019 एवं परिचालन दिशानिर्देश (कृषि एवं किसान कल्याण मंत्रालय)",
  },
  "PM_KISAN:v3.0-2023": {
    summaryEn:
      "Policy version applicable from 1 January 2023 onwards, governing eligible landholding farmer families.",
    summaryHi:
      "1 जनवरी 2023 से निरंतर लागू नीति संस्करण, जो पात्र भूमिधारक किसान परिवारों पर लागू है।",
    gazetteRefEn: "PM-KISAN Operational Guidelines 2023 (Ministry of Agriculture and Farmers Welfare)",
    gazetteRefHi: "पीएम-किसान परिचालन दिशानिर्देश 2023 (कृषि एवं किसान कल्याण मंत्रालय)",
  },
  "SSY:v1.0-2016": {
    summaryEn:
      "Policy version applicable from 18 March 2016 to 11 December 2019, notified under GSR 323(E) by the Department of Economic Affairs, Ministry of Finance.",
    summaryHi:
      "18 मार्च 2016 से 11 दिसंबर 2019 तक लागू नीति संस्करण, जो आर्थिक कार्य विभाग, वित्त मंत्रालय द्वारा जी.एस.आर. 323(ई) के तहत अधिसूचित है।",
    gazetteRefEn: "GSR 323(E), Department of Economic Affairs, Ministry of Finance",
    gazetteRefHi: "जी.एस.आर. 323(ई), आर्थिक कार्य विभाग, वित्त मंत्रालय",
  },
  "SSY:v2.0-2019": {
    summaryEn:
      "Policy version applicable from 12 December 2019 to 31 March 2024, notified under GSR 914(E) by the Department of Economic Affairs, Ministry of Finance.",
    summaryHi:
      "12 दिसंबर 2019 से 31 मार्च 2024 तक लागू नीति संस्करण, जो आर्थिक कार्य विभाग, वित्त मंत्रालय द्वारा जी.एस.आर. 914(ई) के तहत अधिसूचित है।",
    gazetteRefEn: "GSR 914(E), Department of Economic Affairs, Ministry of Finance",
    gazetteRefHi: "जी.एस.आर. 914(ई), आर्थिक कार्य विभाग, वित्त मंत्रालय",
  },
  "SSY:v3.0-2024": {
    summaryEn:
      "Policy version applicable from 1 April 2024 onwards, notified under GSR 914(E) as amended by Ministry of Finance DEA Order F.No. 1/3/2024-NS.",
    summaryHi:
      "1 अप्रैल 2024 से निरंतर लागू नीति संस्करण, जो वित्त मंत्रालय आर्थिक कार्य विभाग के आदेश 1/3/2024-NS द्वारा संशोधित जी.एस.आर. 914(ई) के तहत अधिसूचित है।",
    gazetteRefEn: "GSR 914(E) as amended & MoF DEA Order F.No. 1/3/2024-NS dated 21.08.2024",
    gazetteRefHi: "जी.एस.आर. 914(ई) यथा संशोधित एवं वित्त मंत्रालय आदेश 21.08.2024",
  },
};

/**
 * Returns statutory summary and reference for a policy version.
 */
export function getPolicyStatutorySummary(
  schemeCode: string,
  versionCode: string,
  isHindi: boolean
): { summary: string; reference: string } {
  const key = `${schemeCode.toUpperCase()}:${versionCode}`;
  const record = STATUTORY_POLICY_SUMMARIES[key];
  if (record) {
    return {
      summary: isHindi ? record.summaryHi : record.summaryEn,
      reference: isHindi ? record.gazetteRefHi : record.gazetteRefEn,
    };
  }
  return {
    summary: isHindi
      ? "यह संस्करण भारत सरकार द्वारा अधिसूचित आधिकारिक योजना नियमों का प्रतिनिधित्व करता है।"
      : "This version represents official scheme rules notified by the Government of India.",
    reference: isHindi ? "आधिकारिक राजपत्र आदेश" : "Official Gazette Order",
  };
}

/**
 * Determines timeline classification: CURRENT, PREVIOUS, or EARLIER.
 */
export function getPolicyTimelineStatus(
  effectiveTo: string | null,
  indexInDescendingList: number
): PolicyTimelineStatus {
  if (effectiveTo === null || indexInDescendingList === 0) {
    return "CURRENT";
  }
  if (indexInDescendingList === 1) {
    return "PREVIOUS";
  }
  return "EARLIER";
}

/**
 * Timeline badge labels.
 */
export function getTimelineStatusLabel(status: PolicyTimelineStatus, isHindi: boolean): string {
  switch (status) {
    case "CURRENT":
      return isHindi ? "वर्तमान प्रभावी नीति" : "Current Effective Policy";
    case "PREVIOUS":
      return isHindi ? "पूर्व नीति संशोधन" : "Previous Policy Revision";
    case "EARLIER":
      return isHindi ? "प्रारंभिक अधिसूचना" : "Earlier Notification";
    default:
      return status;
  }
}
