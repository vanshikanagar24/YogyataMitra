import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { PolicyFormField } from "../../src/components/forms/PolicyFormField";
import { PolicyFormSection } from "../../src/components/forms/PolicyFormSection";
import { PolicyFormRenderer } from "../../src/components/forms/PolicyFormRenderer";
import {
  OFFICIAL_SCHEME_SOURCES,
  OFFICIAL_SCHEME_TITLES,
  getOfficialSourceUrl,
  getOfficialSourceTitle,
} from "../../src/utils/officialSources";
import {
  SchemeRequirementsResponse,
  SchemeRequirementField,
  FormSectionDefinition,
} from "../../src/types/citizen";

describe("Phase H: Ten Target Government Schemes Architecture", () => {
  const TARGET_10_SCHEMES = [
    "PM_KISAN",
    "SSY",
    "PM_KMY",
    "PMUY",
    "PM_VISHWAKARMA",
    "PMAY_G",
    "PMAY_U_2_0",
    "PM_SVANIDHI",
    "PMMVY",
    "IGNOAPS",
  ];

  describe("1. Official Statutory Scheme Sources & Provenance", () => {
    it("provides canonical official portal URLs for all 10 target schemes", () => {
      TARGET_10_SCHEMES.forEach((schemeCode) => {
        const url = getOfficialSourceUrl(schemeCode);
        expect(url).toBeTruthy();
        expect(url.startsWith("https://")).toBe(true);
        expect(OFFICIAL_SCHEME_SOURCES[schemeCode]).toBe(url);
      });
    });

    it("provides bilingual official statutory titles for all 10 target schemes", () => {
      TARGET_10_SCHEMES.forEach((schemeCode) => {
        const titleEn = getOfficialSourceTitle(schemeCode, false);
        const titleHi = getOfficialSourceTitle(schemeCode, true);
        expect(titleEn).toBeTruthy();
        expect(titleHi).toBeTruthy();
        expect(OFFICIAL_SCHEME_TITLES[schemeCode].en).toBe(titleEn);
        expect(OFFICIAL_SCHEME_TITLES[schemeCode].hi).toBe(titleHi);
      });
    });

    it("falls back gracefully for unregistered scheme codes", () => {
      const fallbackUrl = "https://example.gov.in/default";
      const fallbackTitle = "Custom Statutory Guidelines";
      expect(getOfficialSourceUrl("UNKNOWN_SCHEME", fallbackUrl)).toBe(fallbackUrl);
      expect(getOfficialSourceTitle("UNKNOWN_SCHEME", false, fallbackTitle)).toBe(fallbackTitle);
    });
  });

  describe("2. Generic Form Rendering for New Phase H Welfare Schemes", () => {
    it("renders PM_KMY form fields (farmer age, landholding, pension exclusion)", () => {
      const pmKmyRequirements: SchemeRequirementsResponse = {
        scheme_code: "PM_KMY",
        policy_version_id: "test-v1-kmy",
        policy_version_code: "v1.0-2019",
        sections: [
          {
            section_key: "sec_applicant",
            title_en: "Farmer Demographic Criteria",
            title_hi: "किसान जनसांख्यिकीय मानदंड",
            description_en: "Age must be between 18 and 40 years",
            display_order: 1,
          },
          {
            section_key: "sec_land",
            title_en: "Landholding Specifications",
            title_hi: "भूमि जोत विनिर्देश",
            description_en: "Small and marginal farmers up to 2.0 hectares",
            display_order: 2,
          },
        ],
        fields: [
          {
            field_key: "applicant.age",
            section_key: "sec_applicant",
            field_type: "integer",
            label_en: "Applicant Age at Enrollment",
            label_hi: "नामांकन के समय आवेदक की आयु",
            required: true,
            min_value: 18,
            max_value: 40,
            display_order: 1,
          },
          {
            field_key: "land.total_land_area_hectares",
            section_key: "sec_land",
            field_type: "decimal",
            label_en: "Cultivable Landholding (Hectares)",
            label_hi: "कृषि योग्य भूमि जोत (हेक्टेयर)",
            required: true,
            min_value: 0.01,
            max_value: 2.0,
            step: 0.01,
            display_order: 2,
            associated_evidence_type: "LAND_RECORD",
          },
        ],
        evidence_types: [
          {
            evidence_type: "AADHAAR",
            label_en: "Aadhaar Card",
            label_hi: "आधार कार्ड",
            mandatory: true,
          },
          {
            evidence_type: "LAND_RECORD",
            label_en: "Record of Rights (RoR)",
            label_hi: "जमाबंदी / खतौनी",
            mandatory: true,
          },
        ],
      };

      const mockChange = jest.fn();
      render(
        <PolicyFormRenderer
          requirements={pmKmyRequirements}
          facts={{ "applicant.age": 28, "land.total_land_area_hectares": 1.2 }}
          onChange={mockChange}
        />
      );

      expect(screen.getByText("Farmer Demographic Criteria")).toBeInTheDocument();
      expect(screen.getByText("किसान जनसांख्यिकीय मानदंड")).toBeInTheDocument();
      expect(screen.getByText("Applicant Age at Enrollment")).toBeInTheDocument();
      expect(screen.getByText("Cultivable Landholding (Hectares)")).toBeInTheDocument();
      expect(screen.getByText(/Requires Evidence: LAND_RECORD/)).toBeInTheDocument();
    });

    it("renders PMUY form fields with boolean connection check and evidence badge", () => {
      const pmuyRequirements: SchemeRequirementsResponse = {
        scheme_code: "PMUY",
        policy_version_id: "test-v2-pmuy",
        policy_version_code: "v2.0-2021",
        sections: [
          {
            section_key: "sec_household",
            title_en: "Household Energy Status",
            title_hi: "पारिवारिक ऊर्जा स्थिति",
            description_en: "No active LPG connection",
            display_order: 1,
          },
        ],
        fields: [
          {
            field_key: "household.has_existing_lpg",
            section_key: "sec_household",
            field_type: "boolean",
            label_en: "Does any member of the household have an existing LPG connection?",
            label_hi: "क्या परिवार के किसी सदस्य के पास पूर्व से एलपीजी कनेक्शन है?",
            required: true,
            display_order: 1,
          },
        ],
        evidence_types: [
          {
            evidence_type: "RATION_CARD",
            label_en: "Ration Card",
            label_hi: "राशन कार्ड",
            mandatory: true,
          },
        ],
      };

      const mockChange = jest.fn();
      render(
        <PolicyFormRenderer
          requirements={pmuyRequirements}
          facts={{ "household.has_existing_lpg": false }}
          onChange={mockChange}
        />
      );

      expect(screen.getByText("Household Energy Status")).toBeInTheDocument();
      expect(
        screen.getByText("Does any member of the household have an existing LPG connection?")
      ).toBeInTheDocument();
      expect(
        screen.getByText("क्या परिवार के किसी सदस्य के पास पूर्व से एलपीजी कनेक्शन है?")
      ).toBeInTheDocument();

      const yesBtn = screen.getByText("Yes / हाँ");
      fireEvent.click(yesBtn);
      expect(mockChange).toHaveBeenCalledWith("household.has_existing_lpg", true);
    });

    it("renders PM_VISHWAKARMA trade select and artisan declaration", () => {
      const vishwakarmaRequirements: SchemeRequirementsResponse = {
        scheme_code: "PM_VISHWAKARMA",
        policy_version_id: "test-v1-vishwa",
        policy_version_code: "v1.0-2023",
        sections: [
          {
            section_key: "sec_trade",
            title_en: "Traditional Artisan Trade",
            title_hi: "पारंपरिक शिल्प एवं व्यवसाय",
            description_en: "One of 18 eligible traditional trades",
            display_order: 1,
          },
        ],
        fields: [
          {
            field_key: "trade.trade_name",
            section_key: "sec_trade",
            field_type: "select",
            label_en: "Designated Trade Name",
            label_hi: "निर्दिष्ट शिल्प / व्यवसाय",
            required: true,
            display_order: 1,
            options: [
              { value: "Carpenter (Suthar)", label_en: "Carpenter (Suthar)", label_hi: "सुथार / बढ़ई" },
              { value: "Blacksmith (Lohar)", label_en: "Blacksmith (Lohar)", label_hi: "लोहार" },
              { value: "Potter (Kumhaar)", label_en: "Potter (Kumhaar)", label_hi: "कुम्हार" },
            ],
          },
        ],
        evidence_types: [
          {
            evidence_type: "ARTISAN_ID_OR_DECLARATION",
            label_en: "Artisan Certificate / Trade Proof",
            label_hi: "कारीगर पहचान पत्र / व्यवसाय प्रमाण",
            mandatory: true,
          },
        ],
      };

      const mockChange = jest.fn();
      render(
        <PolicyFormRenderer
          requirements={vishwakarmaRequirements}
          facts={{ "trade.trade_name": "Carpenter (Suthar)" }}
          onChange={mockChange}
        />
      );

      expect(screen.getByText("Traditional Artisan Trade")).toBeInTheDocument();
      expect(screen.getByText("Designated Trade Name")).toBeInTheDocument();
      const combobox = screen.getByRole("combobox") as HTMLSelectElement;
      expect(combobox.value).toBe("Carpenter (Suthar)");

      fireEvent.change(combobox, { target: { value: "Blacksmith (Lohar)" } });
      expect(mockChange).toHaveBeenCalledWith("trade.trade_name", "Blacksmith (Lohar)");
    });

    it("renders PMAY_U_2_0 income boundary fields and evaluates cross-field visibility", () => {
      const pmayURequirements: SchemeRequirementsResponse = {
        scheme_code: "PMAY_U_2_0",
        policy_version_id: "test-v1-pmayu",
        policy_version_code: "v1.0-2024",
        sections: [
          {
            section_key: "sec_income",
            title_en: "Household Income Specification",
            title_hi: "पारिवारिक आय विनिर्देश",
            description_en: "EWS, LIG, and MIG income thresholds",
            display_order: 1,
          },
        ],
        fields: [
          {
            field_key: "family.annual_income",
            section_key: "sec_income",
            field_type: "decimal",
            label_en: "Total Annual Household Income (INR)",
            label_hi: "कुल वार्षिक पारिवारिक आय (रुपये)",
            required: true,
            min_value: 0.0,
            max_value: 900000.0,
            display_order: 1,
          },
        ],
        evidence_types: [
          {
            evidence_type: "INCOME_CERTIFICATE",
            label_en: "Income Certificate",
            label_hi: "आय प्रमाण पत्र",
            mandatory: true,
          },
        ],
      };

      const mockChange = jest.fn();
      render(
        <PolicyFormRenderer
          requirements={pmayURequirements}
          facts={{ "family.annual_income": 300000.0 }}
          onChange={mockChange}
        />
      );

      expect(screen.getByText("Household Income Specification")).toBeInTheDocument();
      expect(screen.getByText("Total Annual Household Income (INR)")).toBeInTheDocument();
    });

    it("renders IGNOAPS age input and BPL status selection", () => {
      const ignoapsRequirements: SchemeRequirementsResponse = {
        scheme_code: "IGNOAPS",
        policy_version_id: "test-v1-ignoaps",
        policy_version_code: "v1.0-2011",
        sections: [
          {
            section_key: "sec_age_bpl",
            title_en: "Senior Citizen BPL Entitlement",
            title_hi: "वरिष्ठ नागरिक बीपीएल पात्रता",
            description_en: "Age 60+ and BPL household",
            display_order: 1,
          },
        ],
        fields: [
          {
            field_key: "applicant.age",
            section_key: "sec_age_bpl",
            field_type: "integer",
            label_en: "Age of Senior Citizen",
            label_hi: "वरिष्ठ नागरिक की आयु",
            required: true,
            min_value: 60,
            max_value: 125,
            display_order: 1,
          },
          {
            field_key: "family.is_bpl",
            section_key: "sec_age_bpl",
            field_type: "boolean",
            label_en: "Does the applicant belong to a Below Poverty Line (BPL) household?",
            label_hi: "क्या आवेदक गरीबी रेखा से नीचे (बीपीएल) परिवार से संबंधित है?",
            required: true,
            display_order: 2,
          },
        ],
        evidence_types: [
          {
            evidence_type: "AGE_PROOF",
            label_en: "Age Proof Document",
            label_hi: "आयु प्रमाण पत्र",
            mandatory: true,
          },
          {
            evidence_type: "BPL_CARD_OR_CERTIFICATE",
            label_en: "BPL Card / Certificate",
            label_hi: "बीपीएल कार्ड / प्रमाण पत्र",
            mandatory: true,
          },
        ],
      };

      const mockChange = jest.fn();
      render(
        <PolicyFormRenderer
          requirements={ignoapsRequirements}
          facts={{ "applicant.age": 68, "family.is_bpl": true }}
          onChange={mockChange}
        />
      );

      expect(screen.getByText("Senior Citizen BPL Entitlement")).toBeInTheDocument();
      expect(screen.getByText("Age of Senior Citizen")).toBeInTheDocument();
      expect(
        screen.getByText("Does the applicant belong to a Below Poverty Line (BPL) household?")
      ).toBeInTheDocument();
    });
  });
});
