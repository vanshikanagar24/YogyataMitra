"use client";

import React from "react";
import { BookOpen, ShieldCheck, Hash, FileText, Calendar, Building, ExternalLink } from "lucide-react";
import { useCase } from "../CaseContext";

export default function CasePolicyPage() {
  const { caseData, loading } = useCase();

  if (loading || !caseData) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500 text-sm">
        Loading statutory policy provenance...
      </div>
    );
  }

  const prov = caseData.policy_provenance;

  if (!prov) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500 text-xs">
        Policy provenance is unavailable for this case. Run an evaluation to link the statutory policy version.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Integrity Verification Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 tracking-tight">
                Statutory Policy Provenance & Gazette Authority
              </h2>
              <p className="text-xs text-slate-500">
                Authoritative statutory foundation applied to this eligibility evaluation.
              </p>
            </div>
          </div>

          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-green-100 text-green-800 border border-green-200 self-start sm:self-auto">
            <ShieldCheck className="w-4 h-4 text-green-600" />
            <span>STATUTORY SOURCE VERIFIED</span>
          </span>
        </div>

        {/* Cryptographic Hash Showcase */}
        <div className="p-4 bg-slate-900 text-white rounded-xl space-y-2">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
            <Hash className="w-4 h-4 text-blue-400" />
            <span>Canonical SHA-256 Rule Content Hash</span>
          </div>
          <div className="font-mono text-xs text-blue-300 break-all select-all bg-slate-950 p-2.5 rounded-lg border border-slate-800">
            {prov.content_sha256}
          </div>
          <p className="text-[11px] text-slate-400">
            Cryptographic guarantee: The statutory policy rules and AST definitions cannot be mutated by reviewers or administrative personnel. All determinations are strictly grounded in this hash.
          </p>
        </div>

        {/* Gazette Citations & Ministry */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 text-xs">
          <div className="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div className="flex items-center space-x-2 text-slate-700 font-bold uppercase tracking-wider">
              <FileText className="w-4 h-4 text-slate-500" />
              <span>Official Statutory Citation</span>
            </div>
            <div className="text-sm font-semibold text-slate-900">
              {prov.official_citation}
            </div>
            <div className="text-slate-600">
              <span className="font-medium text-slate-500">Gazette Reference: </span>
              <span className="font-mono">{prov.gazette_reference}</span>
            </div>
          </div>

          <div className="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div className="flex items-center space-x-2 text-slate-700 font-bold uppercase tracking-wider">
              <Building className="w-4 h-4 text-slate-500" />
              <span>Issuing Authority & Ministry</span>
            </div>
            <div className="text-sm font-semibold text-slate-900">
              {prov.issuing_authority}
            </div>
            <div className="text-slate-600">
              <span className="font-medium text-slate-500">Scheme Designation: </span>
              <span>{prov.scheme_name} ({prov.scheme_code})</span>
            </div>
          </div>
        </div>

        {/* Validity Period & Version Details */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs pt-2">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-slate-500 block">Policy Version Code:</span>
            <span className="font-mono font-bold text-slate-900 text-sm">
              {prov.policy_version}
            </span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-slate-500 block">Statutory Validity:</span>
            <span className="font-semibold text-slate-900 text-xs">
              {prov.effective_from} to {prov.effective_to || "Present (Current Active)"}
            </span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-slate-500 block">Rule Definitions in Set:</span>
            <span className="font-bold text-slate-900 text-sm">
              {prov.rule_definitions_count} statutory rules
            </span>
          </div>
        </div>

        {/* Phase I: Official Document & Source Binding Chain */}
        <div className="mt-4 pt-4 border-t border-slate-200 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-1.5">
              <FileText className="w-4 h-4 text-primary" />
              <span>Official Source Document Binding</span>
            </h3>
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
              Provenance: {prov.provenance_completeness || "COMPLETE"}
            </span>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <span className="font-semibold text-slate-900">
                Document: {prov.document_title || prov.official_citation}
              </span>
              {prov.document_version && (
                <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-200 text-slate-800 self-start sm:self-auto">
                  Edition: {prov.document_version}
                </span>
              )}
            </div>

            <div className="text-slate-600 flex flex-wrap gap-x-4 gap-y-1 text-[11px]">
              <span><strong>Issuing Authority:</strong> {prov.issuing_authority}</span>
              {prov.gazette_reference && <span><strong>Reference:</strong> {prov.gazette_reference}</span>}
            </div>

            {prov.official_source_url && (
              <div className="pt-1">
                <a
                  href={prov.official_source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center space-x-1 text-primary hover:text-primary-dark font-medium underline text-[11px]"
                >
                  <span>Verify at Official Government Portal</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            )}
          </div>

          {/* Traceable Entitlement Chain */}
          <div className="p-3 bg-slate-100 rounded-lg text-[11px] text-slate-600">
            <span className="font-semibold text-slate-700 block mb-1">Audit-Grade Traceable Chain:</span>
            <div className="font-mono text-[10px] text-slate-800 flex flex-wrap items-center gap-1.5">
              <span className="px-1.5 py-0.5 bg-white rounded border">Decision</span>
              <span>→</span>
              <span className="px-1.5 py-0.5 bg-white rounded border">EvaluationTrace</span>
              <span>→</span>
              <span className="px-1.5 py-0.5 bg-white rounded border">Structured Rule</span>
              <span>→</span>
              <span className="px-1.5 py-0.5 bg-white rounded border">{prov.policy_version}</span>
              <span>→</span>
              <span className="px-1.5 py-0.5 bg-white rounded border">{prov.document_version || "Source Document"}</span>
              <span>→</span>
              <span className="px-1.5 py-0.5 bg-white rounded border">Official Portal</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
