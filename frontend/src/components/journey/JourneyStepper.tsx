"use client";

import React from "react";
import { Check } from "lucide-react";
import { useLanguage } from "../../context/LanguageContext";

export type StepId = "facts" | "claims" | "evaluation" | "result";

interface JourneyStepperProps {
  currentStep: StepId;
  onSelectStep?: (step: StepId) => void;
}

export const JourneyStepper: React.FC<JourneyStepperProps> = ({ currentStep, onSelectStep }) => {
  const { t } = useLanguage();

  const steps: { id: StepId; labelKey: string }[] = [
    { id: "facts", labelKey: "journey.step_facts" },
    { id: "claims", labelKey: "journey.step_claims" },
    { id: "evaluation", labelKey: "journey.step_evaluation" },
    { id: "result", labelKey: "journey.step_result" },
  ];

  const stepOrder = steps.map((s) => s.id);
  const currentIndex = Math.max(0, stepOrder.indexOf(currentStep));

  return (
    <div className="w-full py-4 mb-6 space-y-3">
      {/* Visible Step Counter & Honest Progress Indicator */}
      <div className="flex items-center justify-between text-xs text-gov-secondary font-semibold px-1">
        <span className="text-primary-dark font-bold text-sm">
          {t("journey.step_counter", { current: currentIndex + 1, total: 4 })}
        </span>
        <span className="font-medium">
          {t(steps[currentIndex]?.labelKey || "journey.step_facts")}
        </span>
      </div>

      <nav aria-label="Journey Progress">
        <ol className="flex items-center justify-between w-full relative">
          {/* Connector Bar */}
          <div className="absolute top-1/2 left-0 w-full -translate-y-1/2 h-0.5 bg-gov-border z-0 hidden sm:block" />

          {steps.map((step, idx) => {
            const isCompleted = idx < currentIndex;
            const isCurrent = idx === currentIndex;
            const isClickable = idx <= currentIndex && onSelectStep;

            return (
              <li
                key={step.id}
                className="relative z-10 flex flex-col items-center flex-1 text-center"
              >
                <button
                  type="button"
                  disabled={!isClickable}
                  onClick={() => isClickable && onSelectStep && onSelectStep(step.id)}
                  className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                    isCompleted
                      ? "bg-primary text-white shadow-xs cursor-pointer"
                      : isCurrent
                      ? "bg-primary-dark text-white ring-4 ring-primary-100 shadow-sm cursor-default"
                      : "bg-white text-gov-secondary border border-gov-border cursor-not-allowed"
                  }`}
                  aria-current={isCurrent ? "step" : undefined}
                >
                  {isCompleted ? <Check className="w-4 h-4" /> : idx + 1}
                </button>
                <span
                  className={`mt-2 text-xs hidden sm:block max-w-[110px] leading-tight ${
                    isCurrent
                      ? "font-bold text-primary-dark"
                      : isCompleted
                      ? "font-medium text-gov-text"
                      : "text-gov-secondary"
                  }`}
                >
                  {t(step.labelKey)}
                </span>
              </li>
            );
          })}
        </ol>
      </nav>
    </div>
  );
};
