/**
 * TypeScript definitions for Phase 14: Officer / Human Verification Portal.
 */

export interface OfficerProfile {
  id?: string;
  email: string;
  role: "OFFICER" | "SUPERVISOR" | "ADMIN" | string;
  name: string;
  designation: string;
  department: string;
}

export interface OfficerLoginResponse {
  access_token: string;
  token_type: string;
  officer_name: string;
  officer_role: string;
  designation: string;
  department: string;
  demo_environment: boolean;
  environment_notice: string;
}

export interface OfficerQueueItem {
  journey_id: string;
  citizen_ref: string;
  scheme_code: string;
  scheme_name: string;
  journey_state: string;
  submitted_at: string;
  review_status: string;
  review_decision?: string | null;
  evidence_count: number;
  verified_evidence_count: number;
  automated_eligibility?: string | null;
}

export interface OfficerQueueMetrics {
  total_cases: number;
  pending_cases: number;
  in_review_cases: number;
  escalated_cases: number;
  completed_cases: number;
}

export interface OfficerQueueListResponse {
  metrics: OfficerQueueMetrics;
  items: OfficerQueueItem[];
}

export interface OfficerClaim {
  id: string;
  claim_type: string;
  claim_label: string;
  value_json: Record<string, unknown>;
  value_display: string;
  source: string;
  status: string;
  claimed_at: string;
}

export interface OfficerVerificationRecord {
  id: string;
  method: string;
  status: string;
  verified_by?: string | null;
  verified_at?: string | null;
  details?: Record<string, unknown> | null;
}

export interface OfficerEvidence {
  id: string;
  claim_id: string;
  claim_type: string;
  evidence_type: string;
  evidence_type_label: string;
  storage_reference: string;
  metadata_json?: Record<string, unknown> | null;
  status: string;
  submitted_at: string;
  verified_at?: string | null;
  rejected_at?: string | null;
  rejection_reason?: string | null;
  verification_records: OfficerVerificationRecord[];
}

export interface OfficerAssessmentRule {
  rule_id: string;
  rule_name: string;
  description: string;
  result: "PASS" | "FAIL" | "UNKNOWN" | string;
  details?: string | null;
}

export interface OfficerAssessment {
  evaluation_id?: string | null;
  determination?: string | null;
  evaluated_at?: string | null;
  ruleset_version?: string | null;
  ruleset_hash?: string | null;
  rules_evaluated: OfficerAssessmentRule[];
  missing_facts: string[];
  disqualifiers: string[];
}

export interface OfficerPolicyProvenance {
  scheme_code: string;
  scheme_name: string;
  policy_version: string;
  ruleset_version: string;
  effective_from: string;
  effective_to?: string | null;
  content_sha256: string;
  official_citation: string;
  gazette_reference: string;
  issuing_authority: string;
  rule_definitions_count: number;
  is_statutory_source_verified: boolean;
}

export interface OfficerAuditEvent {
  id: string;
  journey_id: string;
  review_id: string;
  actor_identity: string;
  actor_role: string;
  action: string;
  previous_status?: string | null;
  new_status: string;
  reason?: string | null;
  details_json?: Record<string, unknown> | null;
  created_at: string;
}

export interface OfficerCaseDetail {
  journey_id: string;
  citizen_ref: string;
  scheme_code: string;
  scheme_name: string;
  journey_state: string;
  submitted_at: string;
  updated_at: string;
  review_status: string;
  review_decision?: string | null;
  review_notes?: string | null;
  reviewer_identity?: string | null;
  reviewer_role?: string | null;
  claims: OfficerClaim[];
  evidence_items: OfficerEvidence[];
  automated_assessment?: OfficerAssessment | null;
  policy_provenance?: OfficerPolicyProvenance | null;
  audit_history: OfficerAuditEvent[];
}

export interface OfficerEvidenceVerifyPayload {
  action: "VERIFY" | "REJECT" | "REQUEST_CLARIFICATION" | string;
  reason?: string | null;
  notes?: string | null;
}

export interface OfficerCaseReviewPayload {
  decision: "VERIFIED" | "CLARIFICATION_REQUIRED" | "REJECTED" | "ESCALATED" | "COMPLETED" | string;
  reason?: string | null;
  notes?: string | null;
}
