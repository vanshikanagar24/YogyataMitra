import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { PolicyFormField, evaluateCondition } from "../../src/components/forms/PolicyFormField";
import { PolicyFormSection } from "../../src/components/forms/PolicyFormSection";
import { PolicyFormRenderer } from "../../src/components/forms/PolicyFormRenderer";
import {
  SchemeRequirementsResponse,
  SchemeRequirementField,
  FormSectionDefinition,
} from "../../src/types/citizen";

describe("Phase G: Generic Policy-Driven Forms Frontend Architecture", () => {
  describe("1. Condition Evaluation Engine", () => {
    it("evaluates EQUALS operator for booleans and values", () => {
      expect(evaluateCondition({ field_key: "flag", operator: "EQUALS", value: true }, { flag: true })).toBe(true);
      expect(evaluateCondition({ field_key: "flag", operator: "EQUALS", value: true }, { flag: false })).toBe(false);
      expect(evaluateCondition({ field_key: "code", operator: "EQUALS", value: "XYZ" }, { code: "XYZ" })).toBe(true);
      expect(evaluateCondition({ field_key: "code", operator: "EQUALS", value: "XYZ" }, { code: "ABC" })).toBe(false);
    });

    it("evaluates numeric comparisons (GREATER_THAN, LESS_THAN, etc.)", () => {
      expect(evaluateCondition({ field_key: "age", operator: "GREATER_THAN", value: 18 }, { age: 25 })).toBe(true);
      expect(evaluateCondition({ field_key: "age", operator: "GREATER_THAN", value: 18 }, { age: 15 })).toBe(false);
      expect(evaluateCondition({ field_key: "count", operator: "LESS_THAN_OR_EQUAL", value: 2 }, { count: 2 })).toBe(true);
    });

    it("evaluates IN and NOT_IN operators", () => {
      expect(evaluateCondition({ field_key: "category", operator: "IN", value: ["SC", "ST"] }, { category: "SC" })).toBe(true);
      expect(evaluateCondition({ field_key: "category", operator: "IN", value: ["SC", "ST"] }, { category: "GEN" })).toBe(false);
      expect(evaluateCondition({ field_key: "category", operator: "NOT_IN", value: ["SC", "ST"] }, { category: "GEN" })).toBe(true);
    });

    it("evaluates IS_EMPTY and IS_NOT_EMPTY operators", () => {
      expect(evaluateCondition({ field_key: "opt", operator: "IS_EMPTY" }, { opt: "" })).toBe(true);
      expect(evaluateCondition({ field_key: "opt", operator: "IS_EMPTY" }, { opt: "filled" })).toBe(false);
      expect(evaluateCondition({ field_key: "opt", operator: "IS_NOT_EMPTY" }, { opt: "filled" })).toBe(true);
    });
  });

  describe("2. PolicyFormField Component", () => {
    it("renders boolean field with bilingual labels and handles value change", () => {
      const mockChange = jest.fn();
      const field: SchemeRequirementField = {
        field_key: "applicant.is_farmer",
        field_type: "boolean",
        label_en: "Are you an agricultural landowner?",
        label_hi: "क्या आप कृषि भूमिधारक हैं?",
        help_text_en: "Verify via land records.",
        help_text_hi: "भूमि रिकॉर्ड के माध्यम से सत्यापित करें।",
        required: true,
      };

      render(
        <PolicyFormField
          field={field}
          value={false}
          onChange={mockChange}
          allFacts={{}}
        />
      );

      expect(screen.getByText("Are you an agricultural landowner?")).toBeInTheDocument();
      expect(screen.getByText("क्या आप कृषि भूमिधारक हैं?")).toBeInTheDocument();
      expect(screen.getByText("Verify via land records.")).toBeInTheDocument();

      const yesBtn = screen.getByText("Yes / हाँ");
      fireEvent.click(yesBtn);
      expect(mockChange).toHaveBeenCalledWith(true);
    });

    it("renders number input with step and limits", () => {
      const mockChange = jest.fn();
      const field: SchemeRequirementField = {
        field_key: "land.area_hectares",
        field_type: "decimal",
        label_en: "Total Land Holding (Hectares)",
        label_hi: "कुल भूमि जोत (हेक्टेयर)",
        required: true,
        min_value: 0.01,
        max_value: 100.0,
        step: 0.01,
      };

      render(
        <PolicyFormField
          field={field}
          value={1.5}
          onChange={mockChange}
          allFacts={{}}
        />
      );

      const input = screen.getByPlaceholderText("0.0") as HTMLInputElement;
      expect(input.value).toBe("1.5");
      fireEvent.change(input, { target: { value: "2.5" } });
      expect(mockChange).toHaveBeenCalledWith(2.5);
    });

    it("renders date input", () => {
      const mockChange = jest.fn();
      const field: SchemeRequirementField = {
        field_key: "girl.dob",
        field_type: "date",
        label_en: "Date of Birth",
        label_hi: "जन्म तिथि",
        required: true,
      };

      render(
        <PolicyFormField
          field={field}
          value="2020-01-15"
          onChange={mockChange}
          allFacts={{}}
        />
      );

      expect(screen.getByLabelText(/Date of Birth/)).toBeInTheDocument();
    });

    it("renders select input with options", () => {
      const mockChange = jest.fn();
      const field: SchemeRequirementField = {
        field_key: "category",
        field_type: "select",
        label_en: "Social Category",
        label_hi: "सामाजिक वर्ग",
        required: true,
        options: [
          { value: "GEN", label_en: "General", label_hi: "सामान्य" },
          { value: "OBC", label_en: "Other Backward Class", label_hi: "अन्य पिछड़ा वर्ग" },
        ],
      };

      render(
        <PolicyFormField
          field={field}
          value="GEN"
          onChange={mockChange}
          allFacts={{}}
        />
      );

      const select = screen.getByRole("combobox") as HTMLSelectElement;
      expect(select.value).toBe("GEN");
      fireEvent.change(select, { target: { value: "OBC" } });
      expect(mockChange).toHaveBeenCalledWith("OBC");
    });

    it("hides conditionally controlled field when condition is unmet", () => {
      const field: SchemeRequirementField = {
        field_key: "land.transfer_details",
        field_type: "text",
        label_en: "Transfer Details",
        label_hi: "हस्तांतरण विवरण",
        required: true,
        condition: {
          field_key: "land.ownership_transferred_post_cutoff",
          operator: "EQUALS",
          value: true,
        },
      };

      const { container, rerender } = render(
        <PolicyFormField
          field={field}
          value=""
          onChange={jest.fn()}
          allFacts={{ "land.ownership_transferred_post_cutoff": false }}
        />
      );

      // Should not be in document
      expect(container.firstChild).toBeNull();

      // When condition becomes true, field appears
      rerender(
        <PolicyFormField
          field={field}
          value=""
          onChange={jest.fn()}
          allFacts={{ "land.ownership_transferred_post_cutoff": true }}
        />
      );
      expect(screen.getByText("Transfer Details")).toBeInTheDocument();
    });

    it("shows associated evidence requirement badge", () => {
      const field: SchemeRequirementField = {
        field_key: "land.record_number",
        field_type: "text",
        label_en: "Land Record Khasra",
        label_hi: "खसरा संख्या",
        required: true,
        associated_evidence_type: "LAND_RECORD",
      };

      render(
        <PolicyFormField
          field={field}
          value="123/45"
          onChange={jest.fn()}
          allFacts={{}}
        />
      );

      expect(screen.getByText(/Requires Evidence: LAND_RECORD/)).toBeInTheDocument();
    });

    it("displays error message when error prop is provided", () => {
      const field: SchemeRequirementField = {
        field_key: "tax_payer",
        field_type: "boolean",
        label_en: "Tax Payer",
        label_hi: "करदाता",
        required: true,
      };

      render(
        <PolicyFormField
          field={field}
          value={null}
          onChange={jest.fn()}
          error="This field is mandatory."
          allFacts={{}}
        />
      );

      expect(screen.getByText("This field is mandatory.")).toBeInTheDocument();
    });
  });

  describe("3. PolicyFormSection Component", () => {
    it("renders section card with English and Hindi titles", () => {
      const section: FormSectionDefinition = {
        section_key: "exclusion_criteria",
        title_en: "Exclusion & Ineligibility Checks",
        title_hi: "बहिष्करण एवं अपात्रता मानदंड",
        description_en: "Statutory checks under Section 4.1",
        display_order: 1,
      };

      render(
        <PolicyFormSection section={section} visibleCount={1}>
          <div>Child field content</div>
        </PolicyFormSection>
      );

      expect(screen.getByText("Exclusion & Ineligibility Checks")).toBeInTheDocument();
      expect(screen.getByText("बहिष्करण एवं अपात्रता मानदंड")).toBeInTheDocument();
      expect(screen.getByText("Statutory checks under Section 4.1")).toBeInTheDocument();
      expect(screen.getByText("Child field content")).toBeInTheDocument();
    });

    it("hides section when visibleCount is 0", () => {
      const section: FormSectionDefinition = {
        section_key: "conditional_section",
        title_en: "Conditional Section",
        title_hi: "सशर्त अनुभाग",
        display_order: 2,
      };

      const { container } = render(
        <PolicyFormSection section={section} visibleCount={0}>
          <div>Child field content</div>
        </PolicyFormSection>
      );

      expect(container.firstChild).toBeNull();
    });
  });

  describe("4. PolicyFormRenderer Component", () => {
    const mockRequirements: SchemeRequirementsResponse = {
      scheme_code: "PM_KISAN",
      scheme_name_en: "PM-KISAN",
      scheme_name_hi: "पीएम-किसान",
      official_url: "https://pmkisan.gov.in",
      policy_version_id: "pv-pmkisan-v3",
      policy_version_code: "v3.0-2023",
      effective_from: "2023-01-01",
      sections: [
        {
          section_key: "landholding",
          title_en: "Landholding Details",
          title_hi: "भूमि स्वामित्व विवरण",
          description_en: "Land records as of operational guidelines",
          display_order: 1,
        },
        {
          section_key: "exclusions",
          title_en: "Statutory Exclusions",
          title_hi: "सांविधिक बहिष्करण",
          display_order: 2,
        },
      ],
      fields: [
        {
          field_key: "farmer.is_institutional_landholder",
          field_type: "boolean",
          label_en: "Institutional Landholder",
          label_hi: "संस्थागत भूमिधारक",
          required: true,
          section_key: "exclusions",
          display_order: 1,
        },
        {
          field_key: "land.ownership_transferred_post_cutoff",
          field_type: "boolean",
          label_en: "Land transferred after 01-02-2019?",
          label_hi: "क्या भूमि 01-02-2019 के बाद हस्तांतरित हुई?",
          required: true,
          section_key: "landholding",
          display_order: 1,
        },
        {
          field_key: "land.acquired_via_succession",
          field_type: "boolean",
          label_en: "Acquired via succession?",
          label_hi: "क्या उत्तराधिकार द्वारा अधिग्रहित किया गया?",
          required: true,
          section_key: "landholding",
          display_order: 2,
          condition: {
            field_key: "land.ownership_transferred_post_cutoff",
            operator: "EQUALS",
            value: true,
          },
        },
      ],
      evidence_types: [
        {
          evidence_type: "LAND_RECORD",
          label_en: "Land Record (ROR)",
          label_hi: "भूमि रिकॉर्ड",
          description_en: "Valid land record",
          description_hi: "मान्य भूमि अभिलेख",
          mandatory: true,
        },
      ],
      cross_field_rules: [
        {
          rule_id: "R_LAND_SUCCESSION",
          rule_type: "CONDITIONAL_REQUIREMENT",
          primary_field: "land.acquired_via_succession",
          message_en: "Land transferred after cutoff must specify succession status.",
          message_hi: "कटऑफ के बाद हस्तांतरित भूमि पर उत्तराधिकार स्थिति आवश्यक है।",
        },
      ],
    };

    it("renders sections in order and groups fields correctly", () => {
      const mockChange = jest.fn();
      const facts = {
        "farmer.is_institutional_landholder": false,
        "land.ownership_transferred_post_cutoff": false,
      };

      render(
        <PolicyFormRenderer
          requirements={mockRequirements}
          facts={facts}
          onChange={mockChange}
        />
      );

      // Both section headers exist
      expect(screen.getByText("Landholding Details")).toBeInTheDocument();
      expect(screen.getByText("Statutory Exclusions")).toBeInTheDocument();

      // Fields in landholding
      expect(screen.getByText("Land transferred after 01-02-2019?")).toBeInTheDocument();

      // Conditional field is hidden initially because cutoff is false
      expect(screen.queryByText("Acquired via succession?")).not.toBeInTheDocument();

      // Cross field rule info note is rendered
      expect(screen.getByText(/Land transferred after cutoff must specify succession status/)).toBeInTheDocument();
    });

    it("reveals conditional field when controlling fact is updated", () => {
      const mockChange = jest.fn();
      const { rerender } = render(
        <PolicyFormRenderer
          requirements={mockRequirements}
          facts={{ "land.ownership_transferred_post_cutoff": false }}
          onChange={mockChange}
        />
      );

      expect(screen.queryByText("Acquired via succession?")).not.toBeInTheDocument();

      // User toggles cutoff to true
      rerender(
        <PolicyFormRenderer
          requirements={mockRequirements}
          facts={{ "land.ownership_transferred_post_cutoff": true }}
          onChange={mockChange}
        />
      );

      expect(screen.getByText("Acquired via succession?")).toBeInTheDocument();
    });
  });
});
