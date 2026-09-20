"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  FileText,
  Sliders,
  CheckCircle,
  FlaskConical,
  GitCompare,
  ShieldCheck,
} from "lucide-react";

interface DraftSubNavProps {
  draftId: string;
}

export function DraftSubNav({ draftId }: DraftSubNavProps) {
  const pathname = usePathname();

  const basePath = `/officer/policy-authoring/${draftId}`;

  const tabs = [
    {
      name: "Overview",
      href: basePath,
      icon: FileText,
      exact: true,
    },
    {
      name: "Rule Builder",
      href: `${basePath}/rules`,
      icon: Sliders,
    },
    {
      name: "AST Validation",
      href: `${basePath}/validation`,
      icon: CheckCircle,
    },
    {
      name: "Test Suite & Regression",
      href: `${basePath}/tests`,
      icon: FlaskConical,
    },
    {
      name: "Policy Diff",
      href: `${basePath}/diff`,
      icon: GitCompare,
    },
    {
      name: "Supervisory Review",
      href: `${basePath}/review`,
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="border-b border-slate-200 bg-white shadow-sm rounded-t-lg">
      <nav className="flex space-x-1 sm:space-x-4 px-4 overflow-x-auto" aria-label="Tabs">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = tab.exact
            ? pathname === tab.href
            : pathname?.startsWith(tab.href);

          return (
            <Link
              key={tab.name}
              href={tab.href}
              className={`flex items-center space-x-2 py-3 px-3 border-b-2 text-xs sm:text-sm font-medium whitespace-nowrap transition-colors ${
                isActive
                  ? "border-blue-600 text-blue-600 font-semibold"
                  : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-blue-600" : "text-slate-400"}`} />
              <span>{tab.name}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
