"use client";

import React from "react";
import { FormSectionDefinition } from "@/types/citizen";
import { Layers } from "lucide-react";

export interface PolicyFormSectionProps {
  section: FormSectionDefinition;
  children: React.ReactNode;
  visibleCount?: number;
}

export const PolicyFormSection: React.FC<PolicyFormSectionProps> = ({
  section,
  children,
  visibleCount,
}) => {
  // If there are no visible fields in this section, don't render an empty section box
  if (visibleCount !== undefined && visibleCount === 0) {
    return null;
  }

  return (
    <section
      data-testid={`form-section-${section.section_key}`}
      className="bg-slate-50/70 rounded-2xl border border-slate-200/80 p-5 sm:p-6 mb-6 shadow-sm"
    >
      <div className="border-b border-slate-200 pb-3 mb-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="p-1 rounded-md bg-blue-100 text-blue-800">
              <Layers className="w-4 h-4" />
            </span>
            <h3 className="text-base font-bold text-gray-900 tracking-tight">
              {section.title_en}
            </h3>
          </div>
          {section.title_hi && (
            <span className="text-xs font-semibold text-gray-600 bg-white px-2.5 py-1 rounded-md border border-slate-200">
              {section.title_hi}
            </span>
          )}
        </div>
        {section.description_en && (
          <p className="text-xs text-gray-500 mt-1 leading-relaxed">
            {section.description_en}
          </p>
        )}
      </div>

      <div className="space-y-4">
        {children}
      </div>
    </section>
  );
};
