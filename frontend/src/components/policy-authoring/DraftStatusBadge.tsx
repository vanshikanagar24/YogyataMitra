"use client";

import React from "react";
import {
  PolicyDraftLifecycleStatus,
  PolicyDraftValidationStatus,
  PolicyDraftTestStatus,
} from "@/types/policyAuthoring";

interface StatusBadgeProps {
  status: PolicyDraftLifecycleStatus | string;
  className?: string;
}

export function DraftStatusBadge({ status, className = "" }: StatusBadgeProps) {
  const getBadgeStyle = (s: string) => {
    switch (s) {
      case "DRAFT_CREATION":
        return "bg-slate-100 text-slate-800 border-slate-300";
      case "CANDIDATE_IMPORTED":
        return "bg-cyan-100 text-cyan-800 border-cyan-300";
      case "HUMAN_EDITING":
        return "bg-blue-100 text-blue-800 border-blue-300";
      case "AST_VALIDATED":
        return "bg-teal-100 text-teal-800 border-teal-300";
      case "COMPILED":
        return "bg-indigo-100 text-indigo-800 border-indigo-300";
      case "TEST_GENERATED":
        return "bg-sky-100 text-sky-800 border-sky-300";
      case "REGRESSION_VALIDATED":
        return "bg-emerald-100 text-emerald-800 border-emerald-300";
      case "REVIEW_PENDING":
        return "bg-amber-100 text-amber-800 border-amber-300";
      case "REVISED":
        return "bg-orange-100 text-orange-800 border-orange-300";
      case "STAGED":
        return "bg-purple-100 text-purple-900 border-purple-400 font-semibold";
      default:
        return "bg-slate-100 text-slate-700 border-slate-200";
    }
  };

  const getLabel = (s: string) => {
    switch (s) {
      case "DRAFT_CREATION":
        return "Draft Creation";
      case "CANDIDATE_IMPORTED":
        return "Candidate Imported";
      case "HUMAN_EDITING":
        return "Human Editing";
      case "AST_VALIDATED":
        return "AST Validated";
      case "COMPILED":
        return "Compiled";
      case "TEST_GENERATED":
        return "Tests Generated";
      case "REGRESSION_VALIDATED":
        return "Regression Validated";
      case "REVIEW_PENDING":
        return "Review Pending";
      case "REVISED":
        return "Revised";
      case "STAGED":
        return "Staged (Non-Active)";
      default:
        return s;
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getBadgeStyle(
        status
      )} ${className}`}
    >
      {getLabel(status)}
    </span>
  );
}

export function ValidationStatusBadge({
  status,
}: {
  status: PolicyDraftValidationStatus | string;
}) {
  switch (status) {
    case "VALID":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
          AST VALID
        </span>
      );
    case "INVALID":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-300">
          AST INVALID
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-300">
          NOT VALIDATED
        </span>
      );
  }
}

export function TestStatusBadge({
  status,
}: {
  status: PolicyDraftTestStatus | string;
}) {
  switch (status) {
    case "PASSED":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
          TESTS PASSED
        </span>
      );
    case "FAILED":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-300">
          TESTS FAILED
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-300">
          TESTS PENDING
        </span>
      );
  }
}
