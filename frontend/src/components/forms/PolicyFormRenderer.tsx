"use client";

import React, { useMemo } from "react";
import {
  SchemeRequirementsResponse,
  SchemeRequirementField,
  FormSectionDefinition,
} from "@/types/citizen";
import { PolicyFormField, evaluateCondition } from "./PolicyFormField";
import { PolicyFormSection } from "./PolicyFormSection";
import { Info } from "lucide-react";

export interface PolicyFormRendererProps {
  requirements: SchemeRequirementsResponse;
  facts: Record<string, any>;
  onChange: (fieldKey: string, value: any) => void;
  errors?: Record<string, string>;
  disabled?: boolean;
}

export const PolicyFormRenderer: React.FC<PolicyFormRendererProps> = ({
  requirements,
  facts,
  onChange,
  errors = {},
  disabled = false,
}) => {
  // Sort sections by display_order
  const sortedSections = useMemo(() => {
    if (!requirements.sections || requirements.sections.length === 0) {
      return [];
    }
    return [...requirements.sections].sort((a, b) => a.display_order - b.display_order);
  }, [requirements.sections]);

  // Group fields by section_key
  const { groupedFields, unassignedFields } = useMemo(() => {
    const grouped: Record<string, SchemeRequirementField[]> = {};
    const unassigned: SchemeRequirementField[] = [];

    // Initialize groupings for declared sections
    sortedSections.forEach((s) => {
      grouped[s.section_key] = [];
    });

    // Sort fields by display_order
    const sortedFields = [...requirements.fields].sort(
      (a, b) => (a.display_order ?? 0) - (b.display_order ?? 0)
    );

    sortedFields.forEach((f) => {
      if (f.is_active === false) return; // skip inactive fields

      const key = f.section_key;
      if (key && grouped[key]) {
        grouped[key].push(f);
      } else {
        unassigned.push(f);
      }
    });

    return { groupedFields: grouped, unassignedFields: unassigned };
  }, [requirements.fields, sortedSections]);

  return (
    <div data-testid="policy-form-renderer" className="space-y-6">
      {/* If there are sections defined, render section-based layout */}
      {sortedSections.length > 0 ? (
        <>
          {sortedSections.map((section) => {
            const fields = groupedFields[section.section_key] || [];
            // Count how many fields are currently visible based on conditions
            const visibleFields = fields.filter((f) => evaluateCondition(f.condition, facts));

            return (
              <PolicyFormSection
                key={section.section_key}
                section={section}
                visibleCount={visibleFields.length}
              >
                {fields.map((field) => (
                  <PolicyFormField
                    key={field.field_key}
                    field={field}
                    value={facts[field.field_key]}
                    onChange={(val) => onChange(field.field_key, val)}
                    error={errors[field.field_key]}
                    disabled={disabled}
                    allFacts={facts}
                  />
                ))}
              </PolicyFormSection>
            );
          })}

          {/* Render any unassigned fields if they exist */}
          {unassignedFields.length > 0 && (
            <div className="space-y-4">
              {unassignedFields.map((field) => (
                <PolicyFormField
                  key={field.field_key}
                  field={field}
                  value={facts[field.field_key]}
                  onChange={(val) => onChange(field.field_key, val)}
                  error={errors[field.field_key]}
                  disabled={disabled}
                  allFacts={facts}
                />
              ))}
            </div>
          )}
        </>
      ) : (
        /* Fallback when no sections are defined: render fields directly */
        <div className="space-y-4">
          {requirements.fields
            .filter((f) => f.is_active !== false)
            .map((field) => (
              <PolicyFormField
                key={field.field_key}
                field={field}
                value={facts[field.field_key]}
                onChange={(val) => onChange(field.field_key, val)}
                error={errors[field.field_key]}
                disabled={disabled}
                allFacts={facts}
              />
            ))}
        </div>
      )}

      {/* Render Cross-Field Rules Info Note if present */}
      {requirements.cross_field_rules && requirements.cross_field_rules.length > 0 && (
        <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-200/80 text-xs text-blue-900 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-blue-700 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold block">Statutory Cross-Validation Rules</span>
            <ul className="list-disc list-inside space-y-0.5 text-blue-800">
              {requirements.cross_field_rules.map((rule) => (
                <li key={rule.rule_id}>
                  {rule.message_en} ({rule.message_hi})
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default PolicyFormRenderer;
