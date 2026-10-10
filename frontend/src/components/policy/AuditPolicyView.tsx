"use client";

import React from "react";
import { ShieldAlert, Hash, FileCode, Database, ExternalLink } from "lucide-react";
import { AuditPolicyDetails } from "../../types/audit";
import { getOfficialSourceUrl } from "../../utils/officialSources";

interface AuditPolicyViewProps {
  policy: AuditPolicyDetails;
}

/**
 * Audit Policy View Component.
 * Architectural Foundation for Future Authorized Auditor Portal.
 *
 * Strictly separated from CitizenPolicyView:
 * Renders technical cryptographic hashes, AST schema versions,
 * and database keys required by statutory audit and integrity verification.
 */
export const AuditPolicyView: React.FC<AuditPolicyViewProps> = ({ policy }) => {
  return (
    <div
      data-testid="audit-policy-view"
      className="bg-slate-900 text-slate-100 rounded-xl border border-slate-700 p-6 space-y-5 font-mono text-xs shadow-lg"
    >
      {/* Auditor Warning Banner */}
      <div className="flex items-center space-x-2 text-amber-400 bg-amber-950/60 border border-amber-800/80 px-3.5 py-2 rounded-md font-sans text-xs">
        <ShieldAlert className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
        <span className="font-bold tracking-wide uppercase">
          Internal Statutory Audit Record — Authorized Auditor Inspection Layer
        </span>
      </div>

      {/* Metadata Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div>
          <span className="text-slate-400 text-[11px] uppercase tracking-wider">Scheme / Version</span>
          <h3 className="text-base font-bold text-white font-sans">
            {policy.scheme_code} — {policy.version_code}
          </h3>
        </div>
        <div className="text-right">
          <span className="text-slate-400 text-[11px] uppercase tracking-wider">Effective Window</span>
          <div className="text-slate-200">
            {policy.effective_from} → {policy.effective_to || "OPEN-ENDED"}
          </div>
        </div>
      </div>

      {/* Cryptographic Hash Verification Block */}
      <div className="bg-slate-950 p-3.5 rounded border border-slate-800 space-y-1.5">
        <div className="flex items-center space-x-1.5 text-emerald-400 font-bold">
          <Hash className="w-3.5 h-3.5" aria-hidden="true" />
          <span>CANONICAL RULE DEFINITION HASH (SHA-256)</span>
        </div>
        <div
          data-testid="audit-rule-hash"
          className="text-[11px] text-slate-300 break-all select-all font-mono bg-slate-900/80 p-2 rounded border border-slate-800"
        >
          {policy.rule_definition_hash}
        </div>
      </div>

      {/* AST & Ruleset Schema Identifiers */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[11px]">
        <div className="bg-slate-950/60 p-3 rounded border border-slate-800">
          <div className="text-slate-400 flex items-center space-x-1 mb-1">
            <FileCode className="w-3.5 h-3.5 text-cyan-400" aria-hidden="true" />
            <span>Ruleset Version</span>
          </div>
          <span className="text-slate-200 font-semibold">{policy.ruleset_version || "1.0.0"}</span>
          <span className="text-slate-500 ml-2">(Schema {policy.ruleset_schema_version || "1.0"})</span>
        </div>

        <div className="bg-slate-950/60 p-3 rounded border border-slate-800">
          <div className="text-slate-400 flex items-center space-x-1 mb-1">
            <Database className="w-3.5 h-3.5 text-indigo-400" aria-hidden="true" />
            <span>Internal Entity ID</span>
          </div>
          <span className="text-slate-300 break-all select-all">{policy.id}</span>
        </div>
      </div>

      {/* Statutory Document Citations */}
      <div className="border-t border-slate-800 pt-3 space-y-1 text-[11px]">
        <div className="text-slate-400">Statutory Citation:</div>
        <div className="text-slate-200 font-sans">{policy.source_title}</div>
        {policy.source_document_identifier && (
          <div className="text-slate-400">
            Document ID: <span className="text-slate-200">{policy.source_document_identifier}</span>
          </div>
        )}
        {getOfficialSourceUrl(policy.scheme_code, policy.source_url) && (
          <div className="pt-1">
            <a
              href={getOfficialSourceUrl(policy.scheme_code, policy.source_url)}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`Verify Official Source Document (${policy.scheme_code})`}
              className="inline-flex items-center space-x-1 text-cyan-400 hover:text-cyan-300 hover:underline"
            >
              <span>Verify Official Source Document</span>
              <ExternalLink className="w-3 h-3 ml-0.5" aria-hidden="true" />
            </a>
          </div>
        )}
      </div>
    </div>
  );
};
