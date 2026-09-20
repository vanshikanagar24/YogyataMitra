"use client";

import React from "react";
import { Clock, User, ArrowRight } from "lucide-react";
import { JourneyTransitionRecord } from "../../types/journey";
import { useLanguage } from "../../context/LanguageContext";

interface AuditTimelineProps {
  transitions: JourneyTransitionRecord[];
}

export const AuditTimeline: React.FC<AuditTimelineProps> = ({ transitions }) => {
  const { t } = useLanguage();

  if (!transitions || transitions.length === 0) {
    return (
      <div className="p-4 text-center text-xs text-gov-secondary">
        {t("journey.no_transitions")}
      </div>
    );
  }

  return (
    <div className="relative border-l-2 border-primary-100 ml-4 pl-4 space-y-5 my-4">
      {transitions.map((tr, idx) => (
        <div key={tr.id || idx} className="relative group">
          {/* Dot */}
          <div className="absolute -left-[23px] top-1 w-3 h-3 rounded-full bg-primary ring-4 ring-white" aria-hidden="true" />

          <div className="text-xs space-y-1">
            <div className="flex items-center space-x-2 flex-wrap gap-1">
              <span className="font-mono font-bold text-primary-dark bg-gray-100 px-1.5 py-0.5 rounded">
                {tr.from_state}
              </span>
              <ArrowRight className="w-3 h-3 text-gov-secondary" aria-hidden="true" />
              <span className="font-mono font-bold text-primary bg-primary-50 px-1.5 py-0.5 rounded border border-primary-100">
                {tr.to_state}
              </span>
            </div>

            <div className="flex items-center space-x-3 text-gov-secondary pt-0.5 flex-wrap gap-1">
              <span className="flex items-center">
                <User className="w-3 h-3 mr-1" aria-hidden="true" />
                {tr.actor}
              </span>
              <span className="flex items-center">
                <Clock className="w-3 h-3 mr-1" aria-hidden="true" />
                {new Date(tr.created_at).toLocaleString()}
              </span>
            </div>

            {tr.reason && (
              <p className="text-gov-text bg-gray-50 p-2 rounded border border-gray-100 mt-1 italic">
                "{tr.reason}"
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
