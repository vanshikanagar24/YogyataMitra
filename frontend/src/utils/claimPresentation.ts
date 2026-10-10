/**
 * Citizen UI Presentation Utilities for Claims, Evidence, and Values.
 * Converts internal backend identifiers into respectful, accessible, localized citizen language.
 */

import { getFriendlyRuleTitle } from "./rulePresentation";

export interface ClaimPresentation {
  title: string;
  question: string;
  formattedValue: string;
  sourceLabel: string;
  statusLabel: string;
  isPositive: boolean;
}

interface ClaimMetadata {
  titleEn: string;
  titleHi: string;
  questionEn: string;
  questionHi: string;
}

const CLAIM_METADATA_MAP: Record<string, ClaimMetadata> = {
  "family.owns_cultivable_land": {
    titleEn: "Cultivable Land Ownership",
    titleHi: "कृषि योग्य भूमि का स्वामित्व",
    questionEn: "Does your family own cultivable agricultural land?",
    questionHi: "क्या आपके परिवार के पास कृषि योग्य भूमि का स्वामित्व है?",
  },
  "family.is_institutional_landholder": {
    titleEn: "Institutional Landholder Status",
    titleHi: "संस्थागत भूमि धारक स्थिति",
    questionEn: "Is any agricultural land held in the name of an institution or organization?",
    questionHi: "क्या भूमि किसी संस्था या संगठन के नाम पर दर्ज है?",
  },
  "family.has_income_tax_payer": {
    titleEn: "Income Tax Assessment Status",
    titleHi: "आयकर निर्धारण स्थिति",
    questionEn: "Did any family member pay income tax in the last assessment year?",
    questionHi: "क्या परिवार के किसी सदस्य ने पिछले निर्धारण वर्ष में आयकर का भुगतान किया है?",
  },
  "family.is_nri": {
    titleEn: "Non-Resident Indian (NRI) Status",
    titleHi: "अनिवासी भारतीय (NRI) स्थिति",
    questionEn: "Is any landholding family member a Non-Resident Indian (NRI)?",
    questionHi: "क्या परिवार का कोई भूमिधारक अनिवासी भारतीय (NRI) है?",
  },
  "family.has_constitutional_post_holder": {
    titleEn: "Constitutional Post Holder",
    titleHi: "संवैधानिक पद धारक",
    questionEn: "Does any family member hold or have held constitutional posts?",
    questionHi: "क्या परिवार का कोई सदस्य संवैधानिक पद पर है या रहा है?",
  },
  "family.has_government_employee": {
    titleEn: "Government Employment Status",
    titleHi: "सरकारी सेवा स्थिति",
    questionEn: "Does any family member serve as a regular government employee?",
    questionHi: "क्या परिवार का कोई सदस्य नियमित सरकारी सेवा में कार्यरत है?",
  },
  "family.has_pensioner_above_threshold": {
    titleEn: "Pension Above Threshold (₹10,000/mo)",
    titleHi: "निर्धारित सीमा से अधिक पेंशन (₹10,000/माह)",
    questionEn: "Does any retired family member receive a monthly pension of ₹10,000 or more?",
    questionHi: "क्या परिवार का कोई सेवानिवृत्त सदस्य ₹10,000 या अधिक मासिक पेंशन प्राप्त करता है?",
  },
  "family.has_professional": {
    titleEn: "Registered Professional",
    titleHi: "पंजीकृत पेशेवर (डॉक्टर, इंजीनियर, सीए, वकील)",
    questionEn: "Is any family member a registered doctor, engineer, CA, or lawyer?",
    questionHi: "क्या परिवार का कोई सदस्य पंजीकृत डॉक्टर, इंजीनियर, सीए या वकील है?",
  },
  "land.total_area_hectares": {
    titleEn: "Total Cultivable Land Area",
    titleHi: "कुल कृषि भूमि क्षेत्रफल",
    questionEn: "What is the total cultivable land area owned by the family?",
    questionHi: "परिवार के स्वामित्व वाली कुल कृषि भूमि का क्षेत्रफल क्या है?",
  },
  "beneficiary.gender": {
    titleEn: "Beneficiary Gender",
    titleHi: "बालिका का लिंग",
    questionEn: "What is the gender of the child?",
    questionHi: "बालिका का लिंग क्या है?",
  },
  "beneficiary.date_of_birth": {
    titleEn: "Date of Birth",
    titleHi: "जन्म तिथि",
    questionEn: "What is the date of birth of the girl child?",
    questionHi: "बालिका की जन्म तिथि क्या है?",
  },
  "beneficiary.is_indian_resident": {
    titleEn: "Indian Residential Status",
    titleHi: "भारतीय निवासी स्थिति",
    questionEn: "Is the girl child a resident citizen of India?",
    questionHi: "क्या बालिका भारत की निवासी नागरिक है?",
  },
  "family.is_natural_guardian": {
    titleEn: "Guardian Status",
    titleHi: "अभिभावक स्थिति",
    questionEn: "Is the account being opened by the natural or legal guardian?",
    questionHi: "क्या खाता प्राकृतिक या कानूनी अभिभावक द्वारा खोला जा रहा है?",
  },
  "family.active_ssy_accounts_count": {
    titleEn: "Active SSY Accounts in Family",
    titleHi: "परिवार में सक्रिय सुकन्या समृद्धि खाते",
    questionEn: "How many active SSY accounts already exist in the family?",
    questionHi: "परिवार में पहले से कितने सुकन्या समृद्धि खाते सक्रिय हैं?",
  },
  "account.opening_date": {
    titleEn: "Account Opening Application Date",
    titleHi: "खाता खोलने की प्रस्तावित तिथि",
    questionEn: "What is the intended application date for opening the account?",
    questionHi: "खाता खोलने की प्रस्तावित तिथि क्या है?",
  },
  "land.acquisition_mode": {
    titleEn: "Land Acquisition Mode",
    titleHi: "भूमि अधिग्रहण की विधि",
    questionEn: "How was the agricultural land acquired (e.g. inheritance or purchase)?",
    questionHi: "कृषि भूमि का स्वामित्व किस माध्यम से प्राप्त हुआ (विरासत अथवा खरीद)?",
  },
  "land.previous_owner_deceased": {
    titleEn: "Previous Landowner Status",
    titleHi: "पूर्व भूमिधारक स्थिति",
    questionEn: "Has the previous landowner passed away (inheritance case)?",
    questionHi: "क्या पूर्व भूमिधारक का देहांत हो चुका है (विरासत का मामला)?",
  },
  "land.transferred_after_cutoff": {
    titleEn: "Land Transferred After Cutoff Date",
    titleHi: "कट-ऑफ तिथि के बाद भूमि हस्तांतरण",
    questionEn: "Was the land transferred after the statutory cutoff date (01-Feb-2019)?",
    questionHi: "क्या भूमि 1 फरवरी 2019 की निर्धारित कट-ऑफ तिथि के बाद हस्तांतरित हुई थी?",
  },
  "land.acquired_via_succession": {
    titleEn: "Acquisition via Inheritance / Succession",
    titleHi: "उत्तराधिकार / विरासत द्वारा अधिग्रहण",
    questionEn: "Was the land acquired strictly via legal succession or inheritance?",
    questionHi: "क्या भूमि का स्वामित्व कानूनी उत्तराधिकार या विरासत द्वारा प्राप्त हुआ था?",
  },
  family: {
    titleEn: "Family Details",
    titleHi: "पारिवारिक विवरण",
    questionEn: "Family Details",
    questionHi: "पारिवारिक विवरण",
  },
  guardian: {
    titleEn: "Guardian Details",
    titleHi: "अभिभावक विवरण",
    questionEn: "Guardian Information",
    questionHi: "अभिभावक विवरण",
  },
  beneficiary: {
    titleEn: "Beneficiary Details",
    titleHi: "लाभार्थी विवरण",
    questionEn: "Beneficiary Information",
    questionHi: "बालिका / लाभार्थी विवरण",
  },
  account: {
    titleEn: "Bank / Post Office Account Details",
    titleHi: "बैंक / डाकघर खाता विवरण",
    questionEn: "Account Information",
    questionHi: "खाता संबंधी विवरण",
  },
  land: {
    titleEn: "Land Ownership Details",
    titleHi: "भूमि स्वामित्व विवरण",
    questionEn: "Land Details",
    questionHi: "भूमि विवरण",
  },
  applicant: {
    titleEn: "Applicant Details",
    titleHi: "आवेदक विवरण",
    questionEn: "Applicant Information",
    questionHi: "आवेदक विवरण",
  },
  "guardian.is_natural_guardian": {
    titleEn: "Natural Guardian",
    titleHi: "प्राकृतिक अभिभावक",
    questionEn: "Is the account being opened by the natural guardian?",
    questionHi: "क्या खाता प्राकृतिक अभिभावक द्वारा खोला जा रहा है?",
  },
  "guardian.is_court_appointed_legal_guardian": {
    titleEn: "Court Appointed Legal Guardian",
    titleHi: "न्यायालय द्वारा नियुक्त कानूनी अभिभावक",
    questionEn: "Is the guardian appointed by a court of law?",
    questionHi: "क्या अभिभावक न्यायालय द्वारा नियुक्त है?",
  },
  "family.has_multiple_birth_exception": {
    titleEn: "Multiple Birth Exception (Twins / Triplets)",
    titleHi: "बहु-जन्म अपवाद (जुड़वां / तिड़वां)",
    questionEn: "Does the family have a multiple birth exception?",
    questionHi: "क्या परिवार में जुड़वां/तिड़वां बालिका अपवाद लागू है?",
  },
};

/**
 * Format a raw value JSON into citizen-friendly text.
 * Strictly prevents "[object Object]" leaks under any circumstance.
 */
export function formatCitizenValue(
  val: any,
  fieldKey: string = "",
  isHindi: boolean = false
): { text: string; isPositive: boolean } {
  if (val === null || val === undefined || val === "") {
    return {
      text: isHindi ? "जानकारी उपलब्ध नहीं है" : "Not provided",
      isPositive: false,
    };
  }

  let raw = val;
  if (typeof raw === "object" && raw !== null && "value" in raw) {
    raw = raw.value;
    if (raw === null || raw === undefined || raw === "") {
      return {
        text: isHindi ? "जानकारी उपलब्ध नहीं है" : "Not provided",
        isPositive: false,
      };
    }
  }

  if (typeof raw === "boolean") {
    if (raw) {
      return { text: isHindi ? "हाँ" : "Yes", isPositive: true };
    }
    return { text: isHindi ? "नहीं" : "No", isPositive: false };
  }

  if (typeof raw === "number") {
    const keyLower = (fieldKey || "").toLowerCase();
    if (keyLower.includes("area") || keyLower.includes("hectare")) {
      return {
        text: isHindi ? `${raw} हेक्टेयर` : `${raw} Hectares`,
        isPositive: raw > 0,
      };
    }
    if (keyLower.includes("accounts_count") || keyLower.includes("active_ssy")) {
      return {
        text: isHindi ? `${raw} खाता/खाते` : `${raw} Account(s)`,
        isPositive: raw === 0,
      };
    }
    return { text: String(raw), isPositive: true };
  }

  if (typeof raw === "string") {
    const upper = raw.trim().toUpperCase();
    if (upper === "FEMALE") {
      return { text: isHindi ? "महिला (बालिका)" : "Female (Girl Child)", isPositive: true };
    }
    if (upper === "MALE") {
      return { text: isHindi ? "पुरुष" : "Male", isPositive: false };
    }
    // Date format YYYY-MM-DD
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
      const parts = raw.split("-");
      const dateObj = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
      if (!isNaN(dateObj.getTime())) {
        return {
          text: dateObj.toLocaleDateString(isHindi ? "hi-IN" : "en-IN", {
            day: "numeric",
            month: "short",
            year: "numeric",
          }),
          isPositive: true,
        };
      }
    }
    return { text: raw, isPositive: true };
  }

  // Handle Arrays
  if (Array.isArray(raw)) {
    if (raw.length === 0) {
      return { text: isHindi ? "कोई नहीं" : "None", isPositive: true };
    }
    const formattedItems = raw.map((item) => formatCitizenValue(item, fieldKey, isHindi).text);
    return { text: formattedItems.join(", "), isPositive: true };
  }

  // Handle Objects (Family, Beneficiary, Guardian, Account, Land, etc.)
  if (typeof raw === "object" && raw !== null) {
    const entries = Object.entries(raw).filter(
      ([k, v]) => v !== null && v !== undefined && k !== "_sa_instance_state"
    );
    if (entries.length === 0) {
      return {
        text: isHindi ? "जानकारी उपलब्ध नहीं है" : "Not provided",
        isPositive: false,
      };
    }

    const formattedParts = entries.map(([subKey, subVal]) => {
      const fullSubKey = fieldKey ? `${fieldKey}.${subKey}` : subKey;
      const title = getFriendlyFieldTitle(fullSubKey, isHindi);
      const formattedVal = formatCitizenValue(subVal, fullSubKey, isHindi);
      return `${title}: ${formattedVal.text}`;
    });

    return {
      text: formattedParts.join(isHindi ? " | " : " | "),
      isPositive: true,
    };
  }

  return { text: String(raw ?? ""), isPositive: true };
}

/**
 * Maps technical status code to citizen status label.
 */
export function getCitizenStatusLabel(status: string, isHindi: boolean): string {
  const norm = (status || "").toUpperCase();
  switch (norm) {
    case "CLAIMED":
      return isHindi ? "जानकारी दी गई" : "Information provided";
    case "PENDING":
      return isHindi ? "सत्यापन लंबित" : "Verification pending";
    case "VERIFIED":
      return isHindi ? "सत्यापित" : "Verified";
    case "REJECTED":
      return isHindi ? "सत्यापन सफल नहीं हुआ" : "Verification unsuccessful";
    case "UNKNOWN":
      return isHindi ? "जानकारी उपलब्ध नहीं है" : "Information unavailable";
    default:
      return norm.replace(/_/g, " ");
  }
}

/**
 * Maps technical source code to citizen source label.
 */
export function getCitizenSourceLabel(source: string, isHindi: boolean): string {
  const norm = (source || "").toUpperCase();
  switch (norm) {
    case "SELF_DECLARATION":
      return isHindi ? "स्रोत: आपके द्वारा दी गई जानकारी" : "Source: Information you provided";
    case "OFFICIAL_REGISTRY":
      return isHindi ? "स्रोत: आधिकारिक सरकारी रजिस्ट्री" : "Source: Official Government Registry";
    case "THIRD_PARTY_API":
      return isHindi ? "स्रोत: सरकारी सत्यापन प्रणाली" : "Source: Government API Verification";
    default:
      return isHindi ? `स्रोत: ${source}` : `Source: ${source}`;
  }
}

/**
 * Returns full presentation metadata for a claim.
 */
export function getClaimPresentation(
  claimType: string,
  valueJson: any,
  isHindi: boolean
): ClaimPresentation {
  const meta = CLAIM_METADATA_MAP[claimType] || {
    titleEn: claimType.split(".").pop()?.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()) || claimType,
    titleHi: claimType.split(".").pop()?.replace(/_/g, " ") || claimType,
    questionEn: `Assertion regarding ${claimType.replace(/_/g, " ")}:`,
    questionHi: `${claimType.replace(/_/g, " ")} संबंधी जानकारी:`,
  };

  const formatted = formatCitizenValue(valueJson, claimType, isHindi);

  return {
    title: isHindi ? meta.titleHi : meta.titleEn,
    question: isHindi ? meta.questionHi : meta.questionEn,
    formattedValue: formatted.text,
    sourceLabel: getCitizenSourceLabel("SELF_DECLARATION", isHindi),
    statusLabel: getCitizenStatusLabel("CLAIMED", isHindi),
    isPositive: formatted.isPositive,
  };
}

/**
 * Returns citizen friendly document name for evidence types.
 */
export function getEvidencePresentation(
  evidenceType: string,
  isHindi: boolean
): { title: string; hint: string } {
  const norm = (evidenceType || "").toUpperCase();
  switch (norm) {
    case "LAND_RECORD_7_12":
      return {
        title: isHindi
          ? "भूमि स्वामित्व अभिलेख (खतौनी / खसरा / 7-12)"
          : "Land Ownership Record (Khatauni / Khasra / 7-12)",
        hint: isHindi ? "आधिकारिक राजस्व विभाग अभिलेख" : "Official Revenue Department Record",
      };
    case "BIRTH_CERTIFICATE":
      return {
        title: isHindi
          ? "जन्म प्रमाण पत्र (पंजीयक द्वारा जारी)"
          : "Birth Certificate (Issued by Registrar)",
        hint: isHindi ? "नागरिक पंजीकरण प्रणाली दस्तावेज़" : "Civil Registration System Document",
      };
    case "ITR_ACKNOWLEDGEMENT":
      return {
        title: isHindi
          ? "आयकर रिटर्न (ITR-V) पावती"
          : "Income Tax Return (ITR-V) Acknowledgement",
        hint: isHindi ? "केंद्रीय प्रत्यक्ष कर बोर्ड अभिलेख" : "Income Tax Department Assessment",
      };
    case "SUPPORTING_AFFIDAVIT":
      return {
        title: isHindi
          ? "शपथ पत्र (स्वप्रमाणित / नोटरी)"
          : "Supporting Sworn Affidavit",
        hint: isHindi ? "सत्यापित शपथ पत्र" : "Attested Declaration",
      };
    default:
      return {
        title: isHindi ? "सहायक दस्तावेज़ साक्ष्य" : "Supporting Document Artifact",
        hint: isHindi ? "सत्यापित दस्तावेज़" : "Uploaded verification document",
      };
  }
}

/**
 * Returns citizen-friendly title for a field path in explainability views.
 */
export function getFriendlyFieldTitle(fieldPath: string, isHindi: boolean): string {
  if (!fieldPath) return "";
  const meta = CLAIM_METADATA_MAP[fieldPath];
  if (meta) {
    return isHindi ? meta.titleHi : meta.titleEn;
  }
  const lastPart = fieldPath.split(".").pop() || fieldPath;
  const directMatch =
    CLAIM_METADATA_MAP[`family.${lastPart}`] ||
    CLAIM_METADATA_MAP[`beneficiary.${lastPart}`] ||
    CLAIM_METADATA_MAP[`guardian.${lastPart}`] ||
    CLAIM_METADATA_MAP[`land.${lastPart}`] ||
    CLAIM_METADATA_MAP[`account.${lastPart}`] ||
    CLAIM_METADATA_MAP[lastPart];
  if (directMatch) {
    return isHindi ? directMatch.titleHi : directMatch.titleEn;
  }
  const clean = lastPart.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
  return clean || fieldPath;
}

/**
 * Sanitizes backend-generated messages to eliminate any raw dot-notation keys
 * or technical identifiers, replacing them with citizen-friendly equivalents.
 */
export function sanitizeCitizenMessage(message: string, isHindi: boolean): string {
  if (!message) return "";

  let sanitized = message;

  // Replace raw 'land.acquisition_mode'
  sanitized = sanitized.replace(/'land\.acquisition_mode'/g, isHindi ? "भूमि अधिग्रहण की विधि" : "how the land was acquired");
  sanitized = sanitized.replace(/land\.acquisition_mode/g, isHindi ? "भूमि अधिग्रहण की विधि" : "land acquisition details");

  // Replace raw 'land.previous_owner_deceased'
  sanitized = sanitized.replace(/'land\.previous_owner_deceased'/g, isHindi ? "पूर्व भूमिधारक के देहांत की स्थिति" : "whether the previous landowner is deceased");
  sanitized = sanitized.replace(/land\.previous_owner_deceased/g, isHindi ? "पूर्व भूमिधारक स्थिति" : "previous owner status");

  // Replace raw 'family.has_income_tax_payer'
  sanitized = sanitized.replace(/'family\.has_income_tax_payer'/g, isHindi ? "आयकर भुगतान विवरण" : "income tax assessment status");
  sanitized = sanitized.replace(/family\.has_income_tax_payer/g, isHindi ? "आयकर भुगतान स्थिति" : "income tax status");

  // Replace raw 'family.owns_cultivable_land'
  sanitized = sanitized.replace(/'family\.owns_cultivable_land'/g, isHindi ? "कृषि योग्य भूमि का स्वामित्व" : "cultivable land ownership");
  sanitized = sanitized.replace(/family\.owns_cultivable_land/g, isHindi ? "कृषि भूमि स्वामित्व" : "cultivable land ownership");

  // Replace raw 'family.is_institutional_landholder'
  sanitized = sanitized.replace(/'family\.is_institutional_landholder'/g, isHindi ? "संस्थागत भूमि धारक स्थिति" : "institutional landholder status");
  sanitized = sanitized.replace(/family\.is_institutional_landholder/g, isHindi ? "संस्थागत भूमि धारक" : "institutional landholder status");

  // Replace generic "Required information 'X' is missing" pattern if any other dot notation remains
  sanitized = sanitized.replace(/Required information '([\w.]+)' is missing\./g, (_, key) => {
    const fieldName = getFriendlyFieldTitle(key, false);
    return `Required information regarding ${fieldName.toLowerCase()} is missing.`;
  });
  sanitized = sanitized.replace(/आवश्यक जानकारी '([\w.]+)' अनुपलब्ध है।/g, (_, key) => {
    const fieldName = getFriendlyFieldTitle(key, true);
    return `आवश्यक जानकारी (${fieldName}) अनुपलब्ध है।`;
  });

  // Replace raw rule IDs if present in messages
  sanitized = sanitized.replace(/PMKISAN-[A-Z0-9-]+/g, (match) => getFriendlyRuleTitle(match, isHindi));
  sanitized = sanitized.replace(/SSY-[A-Z0-9-]+/g, (match) => getFriendlyRuleTitle(match, isHindi));

  return sanitized;
}
