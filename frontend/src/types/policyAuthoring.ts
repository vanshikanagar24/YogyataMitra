/**
 * Type definitions for Controlled Policy Authoring & Compilation (Phase 16).
 *
 * Implements the full typed schema for:
 * - 10-state policy draft lifecycle
 * - Static AST validation and structural findings
 * - Deterministic compilation and canonical SHA-256 rule hashing
 * - Test generation, manual test authoring, and test execution
 * - Statutory regression verification against 6 permanently frozen canonical policy hashes
 * - Structural and bilingual policy diffing
 * - Supervisory review determination and immutable audit logging
 */

export type PolicyDraftLifecycleStatus =
  | "DRAFT"
  | "AUTHORING"
  | "VALIDATING"
  | "TESTING"
  | "PENDING_REVIEW"
  | "IN_REVIEW"
  | "REJECTED"
  | "NEEDS_CLARIFICATION"
  | "ARCHIVED"
  | "DRAFT_CREATION"
  | "CANDIDATE_IMPORTED"
  | "HUMAN_EDITING"
  | "AST_VALIDATED"
  | "COMPILED"
  | "TEST_GENERATED"
  | "REGRESSION_VALIDATED"
  | "REVIEW_PENDING"
  | "REVISED"
  | "STAGED";

export type PolicyDraftValidationStatus = "PENDING" | "VALID" | "INVALID";

export type PolicyDraftTestStatus = "PENDING" | "PASSED" | "FAILED";

export type PolicyDraftTestType =
  | "BOUNDARY"
  | "STRONG_KLEENE_UNKNOWN"
  | "STATUTORY_REGRESSION"
  | "MANUAL_HUMAN";

export interface ValidationFinding {
  code: string;
  message: string;
  rule_id?: string | null;
  field_path?: string | null;
}

export interface ValidationReportResponse {
  is_valid: boolean;
  errors: ValidationFinding[];
  warnings: ValidationFinding[];
  info: ValidationFinding[];
  rule_count: number;
  validated_at: string;
}

export interface CompilationResponse {
  is_compiled: boolean;
  rule_hash: string;
  canonical_rules_json: Record<string, any>;
  compiled_at: string;
}

export interface PolicyDraftTestCase {
  id: string;
  draft_id: string;
  name: string;
  description?: string | null;
  test_type: PolicyDraftTestType | string;
  facts_json: Record<string, any>;
  expected_result: "ELIGIBLE" | "INELIGIBLE" | "UNKNOWN" | string;
  actual_result?: "ELIGIBLE" | "INELIGIBLE" | "UNKNOWN" | string | null;
  status: PolicyDraftTestStatus | string;
  execution_notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PolicyDraftTestCreateRequest {
  name: string;
  description?: string;
  test_type?: string;
  facts_json: Record<string, any>;
  expected_result: "ELIGIBLE" | "INELIGIBLE" | "UNKNOWN";
}

export interface TestRunSummaryResponse {
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  test_status: PolicyDraftTestStatus | string;
  executed_at: string;
  results: PolicyDraftTestCase[];
}

export interface PolicyRuleDiffItem {
  rule_id: string;
  diff_type: "ADDED" | "REMOVED" | "MODIFIED";
  description_en?: string | null;
  description_hi?: string | null;
  old_value?: any;
  new_value?: any;
  human_explanation: string;
}

export interface PolicyDiffResponse {
  parent_version_code?: string | null;
  parent_rule_hash?: string | null;
  draft_rule_hash?: string | null;
  added_rules: PolicyRuleDiffItem[];
  removed_rules: PolicyRuleDiffItem[];
  modified_rules: PolicyRuleDiffItem[];
  metadata_changes: Array<Record<string, any>>;
  human_summary: string;
}

export interface PolicyDraftAuditEvent {
  id: string;
  draft_id: string;
  actor_identity: string;
  actor_role: string;
  previous_status?: string | null;
  new_status: string;
  action: string;
  reason: string;
  details_json?: Record<string, any> | null;
  created_at: string;
}

export interface PolicyDraftRevision {
  id: string;
  draft_id: string;
  revision_number: number;
  author_id: string;
  author_role: string;
  change_summary?: string | null;
  previous_rule_hash?: string | null;
  new_rule_hash?: string | null;
  created_at: string;
}

export interface PolicyDraftItem {
  id: string;
  scheme_id: string;
  scheme_code: string | null;
  scheme_name: string | null;
  policy_title: string;
  description: string;
  lifecycle_status: PolicyDraftLifecycleStatus;
  source_candidate_id?: string | null;

  // Provenance
  source_url?: string | null;
  source_title?: string | null;
  source_publisher?: string | null;
  source_document_identifier?: string | null;
  source_publication_date?: string | null;
  source_effective_date?: string | null;
  source_retrieved_at?: string | null;
  source_excerpt?: string | null;
  provenance_status?: string | null;
  adversarial_flag_detected?: boolean;
  candidate_type?: string | null;

  // AST and Rules
  authored_rules_json: Record<string, any>;
  canonical_rules_json?: Record<string, any> | null;
  rule_hash?: string | null;
  schema_version: string;
  compiler_version: string;

  // Temporality
  effective_from?: string | null;
  effective_to?: string | null;

  // Parent baseline
  parent_policy_version_id?: string | null;
  change_summary?: string | null;

  // Verification
  validation_status: PolicyDraftValidationStatus;
  validation_details_json?: Record<string, any> | null;
  test_status: PolicyDraftTestStatus;
  test_summary_json?: Record<string, any> | null;

  // Authorship and Audit
  author_id: string;
  author_role: string;
  created_at: string;
  updated_at: string;
  submitted_at?: string | null;
  reviewed_at?: string | null;
  reviewed_by?: string | null;
  reviewed_by_role?: string | null;
  reviewer_reason?: string | null;
  staged_at?: string | null;
  staged_by?: string | null;
  staged_by_role?: string | null;
}

export interface PolicyDraftDetail extends PolicyDraftItem {
  audit_events: PolicyDraftAuditEvent[];
  revisions: PolicyDraftRevision[];
  tests: PolicyDraftTestCase[];
}

export interface PolicyDraftQueueMetrics {
  total_drafts: number;
  draft_status_count: number;
  authoring: number;
  validating: number;
  testing: number;
  pending_review: number;
  in_review: number;
  needs_clarification: number;
  staged: number;
  archived: number;
}

export interface PolicyDraftListResponse {
  drafts: PolicyDraftItem[];
  total: number;
  metrics: PolicyDraftQueueMetrics;
}

export interface PolicyDraftCreatePayload {
  scheme_code: string;
  policy_title: string;
  description: string;
  source_candidate_id?: string;
  effective_from?: string;
  effective_to?: string;
  parent_policy_version_id?: string;
  authored_rules_json?: Record<string, any>;
}

export interface PolicyDraftUpdatePayload {
  policy_title?: string;
  description?: string;
  effective_from?: string;
  effective_to?: string;
  authored_rules_json?: Record<string, any>;
  change_summary?: string;
}

export interface DraftTransitionPayload {
  action: string;
  reason: string;
  notes?: string;
}
