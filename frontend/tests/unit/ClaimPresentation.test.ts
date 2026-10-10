import {
  formatCitizenValue,
  getFriendlyFieldTitle,
  sanitizeCitizenMessage,
  getClaimPresentation,
} from "../../src/utils/claimPresentation";

describe("Claim Presentation & Safe Formatting (Elimination of [object Object])", () => {
  test("formats primitive values correctly without [object Object]", () => {
    expect(formatCitizenValue(true, "family.owns_cultivable_land", false).text).toBe("Yes");
    expect(formatCitizenValue(false, "family.owns_cultivable_land", false).text).toBe("No");
    expect(formatCitizenValue(true, "family.owns_cultivable_land", true).text).toBe("हाँ");
    expect(formatCitizenValue(false, "family.owns_cultivable_land", true).text).toBe("नहीं");
    expect(formatCitizenValue(2.5, "land.total_area_hectares", false).text).toBe("2.5 Hectares");
    expect(formatCitizenValue(0, "family.active_ssy_accounts_count", false).text).toBe("0 Account(s)");
  });

  test("handles null, undefined, empty object, and empty string gracefully", () => {
    expect(formatCitizenValue(null, "any.field", false).text).toBe("Not provided");
    expect(formatCitizenValue(undefined, "any.field", false).text).toBe("Not provided");
    expect(formatCitizenValue("", "any.field", false).text).toBe("Not provided");
    expect(formatCitizenValue({}, "any.field", false).text).toBe("Not provided");
    expect(formatCitizenValue(null, "any.field", true).text).toBe("जानकारी उपलब्ध नहीं है");
    expect(formatCitizenValue({}, "any.field", true).text).toBe("जानकारी उपलब्ध नहीं है");
  });

  test("unwraps { value: ... } object wrappers without producing [object Object]", () => {
    expect(formatCitizenValue({ value: true }, "family.owns_cultivable_land", false).text).toBe("Yes");
    expect(formatCitizenValue({ value: "FEMALE" }, "beneficiary.gender", false).text).toBe("Female (Girl Child)");
    expect(formatCitizenValue({ value: "FEMALE" }, "beneficiary.gender", true).text).toBe("महिला (बालिका)");
    expect(formatCitizenValue({ value: null }, "family.owns_cultivable_land", false).text).toBe("Not provided");
  });

  test("recursively formats composite objects (Family, Guardian, Beneficiary) without [object Object]", () => {
    const ssyGuardianObj = {
      is_natural_guardian: true,
      is_court_appointed_legal_guardian: false,
    };
    const formattedEn = formatCitizenValue(ssyGuardianObj, "guardian", false).text;
    expect(formattedEn).not.toContain("[object Object]");
    expect(formattedEn).toContain("Natural Guardian: Yes");
    expect(formattedEn).toContain("Court Appointed Legal Guardian: No");

    const formattedHi = formatCitizenValue(ssyGuardianObj, "guardian", true).text;
    expect(formattedHi).not.toContain("[object Object]");
    expect(formattedHi).toContain("प्राकृतिक अभिभावक: हाँ");
    expect(formattedHi).toContain("न्यायालय द्वारा नियुक्त कानूनी अभिभावक: नहीं");
  });

  test("recursively formats family fact objects without [object Object]", () => {
    const pmKisanFamilyObj = {
      owns_cultivable_land: true,
      has_income_tax_payer: false,
    };
    const formatted = formatCitizenValue(pmKisanFamilyObj, "family", false).text;
    expect(formatted).not.toContain("[object Object]");
    expect(formatted).toContain("Cultivable Land Ownership: Yes");
    expect(formatted).toContain("Income Tax Assessment Status: No");
  });

  test("formats arrays cleanly without [object Object]", () => {
    expect(formatCitizenValue([], "items", false).text).toBe("None");
    expect(formatCitizenValue([], "items", true).text).toBe("कोई नहीं");
    const arr = [true, false];
    const formatted = formatCitizenValue(arr, "flags", false).text;
    expect(formatted).toBe("Yes, No");
  });

  test("getClaimPresentation never produces [object Object]", () => {
    const pres = getClaimPresentation("family", { owns_cultivable_land: true }, false);
    expect(pres.formattedValue).not.toContain("[object Object]");
    expect(pres.formattedValue).toContain("Yes");

    const presSSY = getClaimPresentation("beneficiary", { gender: "FEMALE", date_of_birth: "2016-06-10" }, false);
    expect(presSSY.formattedValue).not.toContain("[object Object]");
    expect(presSSY.formattedValue).toContain("Female (Girl Child)");
  });

  test("getFriendlyFieldTitle handles top-level and nested keys", () => {
    expect(getFriendlyFieldTitle("family", false)).toBe("Family Details");
    expect(getFriendlyFieldTitle("family", true)).toBe("पारिवारिक विवरण");
    expect(getFriendlyFieldTitle("guardian", false)).toBe("Guardian Details");
    expect(getFriendlyFieldTitle("guardian", true)).toBe("अभिभावक विवरण");
    expect(getFriendlyFieldTitle("beneficiary", false)).toBe("Beneficiary Details");
    expect(getFriendlyFieldTitle("beneficiary", true)).toBe("लाभार्थी विवरण");
    expect(getFriendlyFieldTitle("account", false)).toBe("Bank / Post Office Account Details");
  });
});
