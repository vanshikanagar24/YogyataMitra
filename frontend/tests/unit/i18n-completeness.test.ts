import en from "../../src/i18n/locales/en.json";
import hi from "../../src/i18n/locales/hi.json";

function getLeafKeys(obj: Record<string, any>, prefix = ""): Record<string, string> {
  const result: Record<string, string> = {};
  for (const key of Object.keys(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    const value = obj[key];
    if (typeof value === "object" && value !== null && !Array.isArray(value)) {
      Object.assign(result, getLeafKeys(value, fullKey));
    } else {
      result[fullKey] = String(value);
    }
  }
  return result;
}

describe("i18n Translation Completeness & Parity", () => {
  const enLeaves = getLeafKeys(en);
  const hiLeaves = getLeafKeys(hi);

  test("en.json and hi.json have identical key counts", () => {
    const enKeyCount = Object.keys(enLeaves).length;
    const hiKeyCount = Object.keys(hiLeaves).length;
    expect(enKeyCount).toBe(hiKeyCount);
  });

  test("every key in en.json exists in hi.json", () => {
    const hiKeySet = new Set(Object.keys(hiLeaves));
    const missingInHi = Object.keys(enLeaves).filter((k) => !hiKeySet.has(k));
    expect(missingInHi).toEqual([]);
  });

  test("every key in hi.json exists in en.json", () => {
    const enKeySet = new Set(Object.keys(enLeaves));
    const missingInEn = Object.keys(hiLeaves).filter((k) => !enKeySet.has(k));
    expect(missingInEn).toEqual([]);
  });

  test("no translation values are empty or whitespace only", () => {
    for (const [k, v] of Object.entries(enLeaves)) {
      expect(v.trim().length).toBeGreaterThan(0);
    }
    for (const [k, v] of Object.entries(hiLeaves)) {
      expect(v.trim().length).toBeGreaterThan(0);
    }
  });

  test("interpolation tokens match between en.json and hi.json", () => {
    const tokenRegex = /\{([^}]+)\}/g;
    for (const key of Object.keys(enLeaves)) {
      const enTokens = (enLeaves[key].match(tokenRegex) || []).sort();
      const hiTokens = (hiLeaves[key].match(tokenRegex) || []).sort();
      expect(hiTokens).toEqual(enTokens);
    }
  });
});
