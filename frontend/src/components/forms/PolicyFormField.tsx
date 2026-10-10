"use client";

import React from "react";
import { SchemeRequirementField, FieldCondition } from "@/types/citizen";
import { AlertCircle, HelpCircle, FileCheck } from "lucide-react";

export interface PolicyFormFieldProps {
  field: SchemeRequirementField;
  value: any;
  onChange: (value: any) => void;
  error?: string;
  disabled?: boolean;
  allFacts: Record<string, any>;
}

export function evaluateCondition(condition: FieldCondition | null | undefined, facts: Record<string, any>): boolean {
  if (!condition) return true;

  const actualRaw = facts[condition.field_key];
  const targetVal = condition.value;

  switch (condition.operator) {
    case "EQUALS":
      if (typeof targetVal === "boolean") {
        return Boolean(actualRaw) === Boolean(targetVal);
      }
      return actualRaw === targetVal;

    case "NOT_EQUALS":
      if (typeof targetVal === "boolean") {
        return Boolean(actualRaw) !== Boolean(targetVal);
      }
      return actualRaw !== targetVal;

    case "IN":
      if (Array.isArray(targetVal)) {
        return targetVal.includes(actualRaw);
      }
      return false;

    case "NOT_IN":
      if (Array.isArray(targetVal)) {
        return !targetVal.includes(actualRaw);
      }
      return true;

    case "GREATER_THAN":
      return Number(actualRaw) > Number(targetVal);

    case "LESS_THAN":
      return Number(actualRaw) < Number(targetVal);

    case "GREATER_THAN_OR_EQUAL":
      return Number(actualRaw) >= Number(targetVal);

    case "LESS_THAN_OR_EQUAL":
      return Number(actualRaw) <= Number(targetVal);

    case "IS_EMPTY":
      return actualRaw === null || actualRaw === undefined || actualRaw === "" || (Array.isArray(actualRaw) && actualRaw.length === 0);

    case "IS_NOT_EMPTY":
      return actualRaw !== null && actualRaw !== undefined && actualRaw !== "" && (!Array.isArray(actualRaw) || actualRaw.length > 0);

    default:
      return true;
  }
}

export const PolicyFormField: React.FC<PolicyFormFieldProps> = ({
  field,
  value,
  onChange,
  error,
  disabled = false,
  allFacts,
}) => {
  // Check conditional visibility
  const isVisible = evaluateCondition(field.condition, allFacts);
  if (!isVisible) {
    return null;
  }

  const fieldId = `field_${field.field_key.replace(/\./g, "_")}`;

  return (
    <div
      data-testid={`form-field-${field.field_key}`}
      className="p-5 rounded-xl border border-gray-200 hover:border-blue-300 transition-colors bg-white shadow-sm space-y-3"
    >
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="max-w-xl">
          <label htmlFor={fieldId} className="text-sm font-bold text-gray-900 block leading-snug">
            {field.label_en}
            {field.required && <span className="text-red-500 ml-1" title="Required">*</span>}
          </label>
          <span className="text-xs font-medium text-gray-600 block mt-0.5">
            {field.label_hi}
          </span>
          {field.help_text_en && (
            <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">
              {field.help_text_en}
            </p>
          )}
          {field.help_text_hi && (
            <p className="text-xs text-gray-400 mt-0.5 leading-relaxed">
              {field.help_text_hi}
            </p>
          )}
          {field.associated_evidence_type && (
            <div className="mt-2 inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-800 border border-amber-200">
              <FileCheck className="w-3 h-3 text-amber-600" />
              <span>Requires Evidence: {field.associated_evidence_type}</span>
            </div>
          )}
        </div>

        {/* Input Controls according to field_type */}
        <div className="sm:w-64 shrink-0">
          {field.field_type === "boolean" && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                id={`${fieldId}_yes`}
                disabled={disabled}
                onClick={() => onChange(true)}
                className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold border transition-colors ${
                  value === true
                    ? "bg-blue-700 text-white border-blue-700 shadow-sm"
                    : "bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100"
                } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                Yes / हाँ
              </button>
              <button
                type="button"
                id={`${fieldId}_no`}
                disabled={disabled}
                onClick={() => onChange(false)}
                className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold border transition-colors ${
                  value === false
                    ? "bg-blue-700 text-white border-blue-700 shadow-sm"
                    : "bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100"
                } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                No / नहीं
              </button>
            </div>
          )}

          {(field.field_type === "number" || field.field_type === "integer" || field.field_type === "decimal") && (
            <input
              type="number"
              id={fieldId}
              disabled={disabled}
              step={field.step ?? (field.field_type === "integer" ? "1" : "any")}
              min={field.min_value ?? undefined}
              max={field.max_value ?? undefined}
              value={value ?? ""}
              onChange={(e) => {
                const val = e.target.value;
                if (val === "") {
                  onChange("");
                } else if (field.field_type === "integer") {
                  onChange(parseInt(val, 10));
                } else {
                  onChange(parseFloat(val));
                }
              }}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 disabled:opacity-50 disabled:bg-gray-50"
              placeholder={field.field_type === "integer" ? "0" : "0.0"}
            />
          )}

          {field.field_type === "date" && (
            <input
              type="date"
              id={fieldId}
              disabled={disabled}
              min={field.min_date ?? undefined}
              max={field.max_date ?? undefined}
              value={value ?? ""}
              onChange={(e) => onChange(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 disabled:opacity-50 disabled:bg-gray-50"
            />
          )}

          {field.field_type === "select" && (
            <select
              id={fieldId}
              disabled={disabled}
              value={value ?? ""}
              onChange={(e) => onChange(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 bg-white disabled:opacity-50 disabled:bg-gray-50"
            >
              <option value="">Select an option / विकल्प चुनें</option>
              {(field.options || []).map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label_en || opt.label || opt.value}
                  {opt.label_hi ? ` (${opt.label_hi})` : ""}
                </option>
              ))}
            </select>
          )}

          {field.field_type === "radio" && (
            <div className="space-y-2">
              {(field.options || []).map((opt) => (
                <label
                  key={opt.value}
                  className="flex items-center gap-2 text-xs font-medium text-gray-800 cursor-pointer"
                >
                  <input
                    type="radio"
                    name={fieldId}
                    disabled={disabled}
                    value={opt.value}
                    checked={value === opt.value}
                    onChange={(e) => onChange(e.target.value)}
                    className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                  />
                  <span>
                    {opt.label_en || opt.label || opt.value}
                    {opt.label_hi && <span className="text-gray-500 text-[11px] ml-1">({opt.label_hi})</span>}
                  </span>
                </label>
              ))}
            </div>
          )}

          {field.field_type === "address" && (
            <textarea
              id={fieldId}
              disabled={disabled}
              rows={3}
              value={value ?? ""}
              onChange={(e) => onChange(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 disabled:opacity-50 disabled:bg-gray-50"
              placeholder="Enter address details / पता दर्ज करें"
            />
          )}

          {field.field_type === "text" && (
            <input
              type="text"
              id={fieldId}
              disabled={disabled}
              value={value ?? ""}
              onChange={(e) => onChange(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 disabled:opacity-50 disabled:bg-gray-50"
            />
          )}
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-1.5 text-xs text-red-600 mt-2 font-medium">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};
