"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useParams } from "next/navigation";
import {
  ArrowLeft,
  FileText,
  FileCheck,
  Cpu,
  BookOpen,
  ClipboardCheck,
  History,
  AlertTriangle,
  Clock,
  Shield,
} from "lucide-react";
import { CaseProvider, useCase } from "./CaseContext";

function CaseHeaderAndTabs({ children }: { children: React.ReactNode }) {
  const { caseData, loading, error, journeyId } = useCase();
  const pathname = usePathname();

  const tabs = [
    {
      id: "overview",
      label: "Overview & Claims",
      href: `/officer/cases/${journeyId}`,
      icon: FileText,
      exact: true,
      badge: caseData ? caseData.claims.length : null,
    },
    {
      id: "evidence",
      label: "Supporting Evidence",
      href: `/officer/cases/${journeyId}/evidence`,
      icon: FileCheck,
      exact: false,
      badge: caseData ? caseData.evidence_items.length : null,
    },
    {
      id: "assessment",
      label: "Automated Assessment",
      href: `/officer/cases/${journeyId}/assessment`,
      icon: Cpu,
      exact: false,
      badge: null,
    },
    {
      id: "policy",
      label: "Policy Provenance",
      href: `/officer/cases/${journeyId}/policy`,
      icon: BookOpen,
      exact: false,
      badge: null,
    },
    {
      id: "review",
      label: "Officer Determination",
      href: `/officer/cases/${journeyId}/review`,
      icon: ClipboardCheck,
      exact: false,
      badge: null,
    },
    {
      id: "history",
      label: "Audit History",
      href: `/officer/cases/${journeyId}/history`,
      icon: History,
      exact: false,
      badge: caseData ? caseData.audit_history.length : null,
    },
  ];

  const isTabActive = (href: string, exact: boolean) => {
    if (exact) {
      return pathname === href;
    }
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  const getStatusBadge = (status?: string) => {
    if (!status) return null;
    switch (status) {
      case "PENDING":
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
            Pending Review
          </span>
        );
      case "IN_REVIEW":
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-blue-100 text-blue-900 border border-blue-300">
            In Review
          </span>
        );
      case "ESCALATED":
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-purple-100 text-purple-900 border border-purple-300">
            Escalated to Supervisor
          </span>
        );
      case "CLARIFICATION_REQUIRED":
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-orange-100 text-orange-900 border border-orange-300">
            Clarification Required
          </span>
        );
      case "VERIFIED":
      case "COMPLETED":
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-green-100 text-green-900 border border-green-300">
            Verification Completed
          </span>
        );
      case "REJECTED":
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-red-100 text-red-900 border border-red-300">
            Verification Rejected
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-slate-100 text-slate-800">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-5">
      {/* Back Link */}
      <div>
        <Link
          href="/officer/queue"
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-blue-600 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Verification Queue</span>
        </Link>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start space-x-2">
          <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Case Header Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 sm:p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2.5 mb-1.5">
              <span className="font-mono text-xs font-bold bg-slate-100 text-slate-800 px-2 py-0.5 rounded border border-slate-300">
                {caseData?.citizen_ref || "Loading..."}
              </span>
              <span className="text-xs text-slate-400 font-mono">
                Journey ID: {journeyId}
              </span>
              {getStatusBadge(caseData?.review_status)}
            </div>

            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              {caseData?.scheme_name || "Scheme Case Dossier"}
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Statutory Scheme Code: <span className="font-mono font-semibold text-slate-700">{caseData?.scheme_code}</span> &bull;
              Submitted on: {caseData ? new Date(caseData.submitted_at).toLocaleDateString("en-IN", {
                year: "numeric",
                month: "long",
                day: "numeric",
              }) : "..."}
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs">
            <div>
              <span className="text-slate-500 block">Automated Engine:</span>
              <span className="font-bold text-slate-800">
                {caseData?.automated_assessment?.determination || "Undetermined"}
              </span>
            </div>
            <div className="hidden sm:block text-slate-300">|</div>
            <div>
              <span className="text-slate-500 block">Current Reviewer:</span>
              <span className="font-semibold text-slate-800">
                {caseData?.reviewer_identity !== "UNASSIGNED"
                  ? `${caseData?.reviewer_identity} (${caseData?.reviewer_role})`
                  : "Unassigned"}
              </span>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="mt-6 border-b border-slate-200 -mb-5 sm:-mb-6 overflow-x-auto">
          <nav className="flex space-x-6 min-w-max">
            {tabs.map((tab) => {
              const active = isTabActive(tab.href, tab.exact);
              const Icon = tab.icon;
              return (
                <Link
                  key={tab.id}
                  href={tab.href}
                  className={`py-3 px-1 border-b-2 text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
                    active
                      ? "border-blue-600 text-blue-600"
                      : "border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                  {tab.badge !== null && (
                    <span
                      className={`ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                        active
                          ? "bg-blue-100 text-blue-800"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {tab.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Tab Content Area */}
      <div className="pt-2">{children}</div>
    </div>
  );
}

export default function CaseLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const journeyId = params.journeyId as string;

  return (
    <CaseProvider journeyId={journeyId}>
      <CaseHeaderAndTabs>{children}</CaseHeaderAndTabs>
    </CaseProvider>
  );
}
