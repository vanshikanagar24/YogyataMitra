/**
 * Types and Interfaces for Policy Transparency, Provenance,
 * and the Citizen vs. Future Auditor Architectural Boundary.
 *
 * Adheres strictly to the architectural boundary documented in
 * docs/auditor_data_boundary.md:
 * - Citizen view models expose plain-language descriptions, official sources,
 *   timelines, and actionable guidance without internal database keys or crypto hashes.
 * - Auditor models expose immutable cryptographic hashes, AST ruleset structures,
 *   evaluation traces, and exact statutory rule nodes.
 */

import { EligibilityResult } from "./enums";

export type PolicyTimelineStatus = "CURRENT" | "PREVIOUS" | "EARLIER";

export interface CitizenPolicySummary {
  scheme_code: string;
  version_code: string;
  effective_from: string;
  effective_to: string | null;
  source_title: string;
  source_url: string;
  source_document_identifier?: string | null;
  timeline_status: PolicyTimelineStatus;
  timeline_label_en: string;
  timeline_label_hi: string;
  summary_en: string;
  summary_hi: string;
  is_current: boolean;
}

export interface CitizenEvaluationExplanation {
  result_state: EligibilityResult;
  result_title: string;
  why_result: string;
  satisfied_criteria: string[];
  blockers: Array<{
    title: string;
    message: string;
  }>;
  missing_information: string[];
  recommended_actions: string[];
  statutory_source_title: string;
  statutory_version_code: string;
  effective_period: string;
  assessment_date: string;
}

export interface AuditPolicyDetails {
  id: string;
  scheme_code: string;
  version_code: string;
  effective_from: string;
  effective_to: string | null;
  rule_definition_hash: string;
  ruleset_schema_version: string | null;
  ruleset_version: string | null;
  source_url: string;
  source_title: string;
  source_document_identifier: string | null;
  rules_count?: number;
  created_at: string;
}

export interface AuditEvaluationDetails {
  id: string;
  evaluation_date: string; // Statutory assessment date determining policy version applied
  created_at: string; // Execution timestamp when calculation ran
  scheme_code: string;
  policy_version_code: string;
  result_state: EligibilityResult;
  input_snapshot_json: Record<string, any>;
  rule_definition_hash: string;
  ast_trace?: any;
}

export interface AuditEvidenceDetails {
  claim_id?: string;
  claim_type: string;
  status: string;
  source: string;
  evidence_type?: string;
  verified_at?: string;
}

export interface AuditTraceDetails {
  evaluation_id: string;
  policy_version_code: string;
  rule_definition_hash: string;
  canonical_trace_hash?: string;
  ast_nodes_evaluated?: number;
  evaluation_timestamp: string;
  assessment_date: string;
}
