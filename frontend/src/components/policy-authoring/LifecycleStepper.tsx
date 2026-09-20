"use client";

import React from "react";
import { Check, Clock, AlertCircle, ShieldCheck } from "lucide-react";
import { PolicyDraftLifecycleStatus } from "@/types/policyAuthoring";

interface LifecycleStepperProps {
  currentStatus: PolicyDraftLifecycleStatus | string;
}

const ORDERED_STEPS: Array<{ key: PolicyDraftLifecycleStatus; label: string; number: number }> = [
  { key: "DRAFT_CREATION", label: "Draft Creation", number: 1 },
  { key: "CANDIDATE_IMPORTED", label: "Candidate Import", number: 2 },
  { key: "HUMAN_EDITING", label: "Human Editing", number: 3 },
  { key: "AST_VALIDATED", label: "AST Validated", number: 4 },
  { key: "COMPILED", label: "Compiled & Hashed", number: 5 },
  { key: "TEST_GENERATED", label: "Tests Generated", number: 6 },
  { key: "REGRESSION_VALIDATED", label: "Regression Validated", number: 7 },
  { key: "REVIEW_PENDING", label: "Review Pending", number: 8 },
  { key: "REVISED", label: "Revision Requested", number: 9 },
  { key: "STAGED", label: "Staged (Quarantine)", number: 10 },
];

export function LifecycleStepper({ currentStatus }: LifecycleStepperProps) {
  const currentIndex = ORDERED_STEPS.findIndex((s) => s.key === currentStatus);
  const isStaged = currentStatus === "STAGED";
  const isRevised = currentStatus === "REVISED";

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Statutory Policy Authoring Lifecycle (Controlled Quarantine Pipeline)
        </h3>
        {isStaged && (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-bold bg-purple-100 text-purple-900 border border-purple-300">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>STAGED — NOT ACTIVE</span>
          </span>
        )}
      </div>

      <div className="overflow-x-auto pb-2">
        <div className="flex items-center min-w-[760px] justify-between relative">
          {ORDERED_STEPS.map((step, idx) => {
            const isCurrent = step.key === currentStatus;
            const isCompleted =
              !isRevised && currentIndex > idx;
            const isPast = currentIndex >= idx;

            let circleBg = "bg-slate-100 text-slate-400 border-slate-300";
            if (isCurrent) {
              circleBg = isRevised
                ? "bg-amber-500 text-white border-amber-600 ring-4 ring-amber-100"
                : isStaged
                ? "bg-purple-700 text-white border-purple-800 ring-4 ring-purple-100"
                : "bg-blue-600 text-white border-blue-700 ring-4 ring-blue-100";
            } else if (isCompleted) {
              circleBg = "bg-emerald-600 text-white border-emerald-700";
            }

            return (
              <div key={step.key} className="flex flex-col items-center relative z-10 flex-1">
                {/* Step Connector Line */}
                {idx > 0 && (
                  <div
                    className={`absolute top-4 -left-1/2 w-full h-0.5 -z-10 ${
                      idx <= currentIndex ? "bg-emerald-500" : "bg-slate-200"
                    }`}
                  />
                )}

                {/* Circle icon */}
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border transition-colors shadow-sm ${circleBg}`}
                >
                  {isCompleted ? (
                    <Check className="w-4 h-4" />
                  ) : isCurrent ? (
                    isRevised ? (
                      <AlertCircle className="w-4 h-4" />
                    ) : (
                      <Clock className="w-4 h-4" />
                    )
                  ) : (
                    <span>{step.number}</span>
                  )}
                </div>

                {/* Label */}
                <div className="mt-2 text-center">
                  <span
                    className={`text-[11px] block leading-tight font-medium ${
                      isCurrent
                        ? "text-slate-900 font-bold"
                        : isCompleted
                        ? "text-slate-700 font-semibold"
                        : "text-slate-400"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
