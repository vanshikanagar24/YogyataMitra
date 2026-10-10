/**
 * Citizen Application and Journey Domain Types (Phase B).
 */

export type JourneyState =
  | "DRAFT"
  | "FACTS_COLLECTED"
  | "EVIDENCE_PENDING"
  | "VERIFICATION_IN_PROGRESS"
  | "READY_FOR_EVALUATION"
  | "EVALUATED"
  | "ACTION_REQUIRED"
  | "COMPLETED";

export type EligibilityResult =
  | "ELIGIBLE"
  | "INELIGIBLE"
  | "INSUFFICIENT_INFORMATION"
  | "VERIFICATION_REQUIRED"
  | "MANUAL_REVIEW_REQUIRED";

export type ClaimStatus =
  | "CLAIMED"
  | "PENDING"
  | "VERIFIED"
  | "REJECTED"
  | "UNKNOWN";

export type EvidenceStatus =
  | "PENDING"
  | "VERIFIED"
  | "REJECTED"
  | "CLARIFICATION_REQUIRED"
  | "UNKNOWN";

export type ClarificationStatus =
  | "OPEN"
  | "RESPONDED"
  | "UNDER_REVIEW"
  | "RESOLVED"
  | "CLOSED";

export type VerificationCompleteness =
  | "VERIFICATION_IN_PROGRESS"
  | "CLARIFICATION_REQUIRED"
  | "VERIFICATION_COMPLETE"
  | "VERIFICATION_BLOCKED";

export type VerificationStatus =
  | "PENDING"
  | "VERIFIED"
  | "REJECTED"
  | "MANUAL_REVIEW_REQUIRED"
  | "UNKNOWN";

export interface JourneyVerificationRecord {
  id: string;
  evidence_id?: string | null;
  claim_id?: string | null;
  verification_method: string;
  status: VerificationStatus;
  verified_by?: string | null;
  verified_at?: string | null;
  details_json?: Record<string, any> | null;
  created_at: string;
}

export interface JourneyEvidence {
  id: string;
  claim_id: string;
  evidence_type: string;
  storage_reference: string;
  metadata_json?: Record<string, any> | null;
  status: EvidenceStatus;
  rejection_reason?: string | null;
  submitted_at: string;
  verified_at?: string | null;
  rejected_at?: string | null;
  verification_records?: JourneyVerificationRecord[];
}

export interface JourneyClaim {
  id: string;
  journey_id?: string | null;
  citizen_id?: string | null;
  claim_type: string;
  value_json: Record<string, any>;
  source: string;
  status: ClaimStatus;
  claimed_at: string;
  updated_at?: string;
  evidence_items?: JourneyEvidence[];
}

export interface JourneyTransition {
  id: string;
  journey_id: string;
  from_state: JourneyState;
  to_state: JourneyState;
  actor: string;
  reason?: string | null;
  created_at: string;
}

export interface EvaluationSummary {
  evaluation_id: string;
  result_state: EligibilityResult;
  evaluation_date: string;
  policy_version_code?: string | null;
  rule_definition_hash?: string | null;
  reasons_en: string[];
  reasons_hi: string[];
}

export interface CitizenApplicationSummary {
  id: string;
  application_ref: string;
  scheme_id: string;
  scheme_code: string;
  scheme_name: string;
  scheme_name_hi?: string | null;
  ministry?: string | null;
  state: JourneyState;
  status_label_en: string;
  status_label_hi: string;
  created_at: string;
  updated_at: string;
  submitted_at?: string | null;
  policy_version_id?: string | null;
  policy_version_code?: string | null;
  rule_definition_hash?: string | null;
  evaluation_outcome?: EligibilityResult | null;
  claims_count: number;
  evidence_count: number;
}

export interface CitizenClarificationItem {
  id: string;
  round: number;
  evidence_id?: string | null;
  claim_id?: string | null;
  request_reason: string;
  status: ClarificationStatus;
  requested_at: string;
  response_text?: string | null;
  responded_at?: string | null;
  has_replacement_evidence: boolean;
  replacement_evidence_id?: string | null;
  replacement_evidence_name?: string | null;
  resolved_at?: string | null;
}

export interface CitizenApplicationDetail extends CitizenApplicationSummary {
  citizen_ref: string;
  citizen_name?: string | null;
  official_url?: string | null;
  claims: JourneyClaim[];
  transitions: JourneyTransition[];
  latest_evaluation?: EvaluationSummary | null;
  allowed_actions: string[];
  verification_status?: string | null;
  clarifications?: CitizenClarificationItem[];
}

export interface CitizenReplacementEvidenceInput {
  document_name: string;
  storage_reference: string;
  evidence_type?: string;
  file_size_bytes?: number;
  mime_type?: string;
  metadata_json?: Record<string, any>;
}

export interface CitizenClarificationRespondPayload {
  response_text: string;
  replacement_evidence?: CitizenReplacementEvidenceInput | null;
}

export interface CitizenClarificationListResponse {
  application_id: string;
  application_ref: string;
  scheme_code: string;
  scheme_name: string;
  verification_status: string;
  clarifications: CitizenClarificationItem[];
}

export interface CitizenVerificationStatusResponse {
  application_id: string;
  application_ref: string;
  scheme_code: string;
  scheme_name: string;
  verification_status: string;
  total_evidence_count: number;
  verified_evidence_count: number;
  pending_evidence_count: number;
  clarification_required_count: number;
  rejected_evidence_count: number;
  open_clarification_count: number;
}

export interface CitizenDashboardStats {
  total_applications: number;
  in_progress_count: number;
  evaluated_count: number;
  action_required_count: number;
  recent_applications: CitizenApplicationSummary[];
}

export interface CitizenApplicationCreatePayload {
  scheme_code: string;
  initial_facts?: Record<string, any>;
}

export interface CitizenEvidenceSubmission {
  evidence_type: string;
  storage_reference: string;
  document_name?: string | null;
  metadata_json?: Record<string, any> | null;
}

export interface CitizenApplicationDraftUpdatePayload {
  facts?: Record<string, any> | null;
  evidence_items?: CitizenEvidenceSubmission[] | null;
}

export interface CitizenApplicationSubmitPayload {
  facts: Record<string, any>;
  evidence_items?: CitizenEvidenceSubmission[] | null;
  declaration_confirmed: boolean;
}

export interface FieldCondition {
  field_key: string;
  operator: "EQUALS" | "NOT_EQUALS" | "IN" | "NOT_IN" | "GREATER_THAN" | "LESS_THAN" | "GREATER_THAN_OR_EQUAL" | "LESS_THAN_OR_EQUAL" | "IS_EMPTY" | "IS_NOT_EMPTY";
  value?: any;
}

export interface FormSectionDefinition {
  section_key: string;
  title_en: string;
  title_hi: string;
  description_en?: string | null;
  description_hi?: string | null;
  display_order: number;
}

export interface CrossFieldRule {
  rule_id: string;
  rule_type: string;
  primary_field: string;
  secondary_field?: string | null;
  operator?: string | null;
  parameters?: Record<string, any> | null;
  message_en: string;
  message_hi: string;
}

export interface SchemeRequirementField {
  field_key: string;
  field_type: "boolean" | "number" | "integer" | "decimal" | "date" | "text" | "select" | "radio" | "multi_select" | "address" | string;
  label_en: string;
  label_hi: string;
  help_text_en?: string | null;
  help_text_hi?: string | null;
  required: boolean;
  options?: Array<{ value: string; label?: string; label_en?: string; label_hi?: string }> | null;
  default_value?: any;
  claim_type?: string | null;
  section_key?: string;
  display_order?: number;
  min_value?: number | null;
  max_value?: number | null;
  min_date?: string | null;
  max_date?: string | null;
  step?: number | null;
  validation_message_en?: string | null;
  validation_message_hi?: string | null;
  associated_evidence_type?: string | null;
  condition?: FieldCondition | null;
  is_active?: boolean;
}

export interface SchemeRequirementEvidence {
  evidence_type: string;
  label_en: string;
  label_hi: string;
  description_en: string;
  description_hi: string;
  mandatory: boolean;
  allowed_extensions?: string[];
  max_size_mb?: number;
  associated_field_keys?: string[];
}

export interface SchemeRequirementsResponse {
  scheme_code: string;
  scheme_name_en: string;
  scheme_name_hi: string;
  ministry?: string | null;
  official_url: string;
  policy_version_id: string;
  policy_version_code: string;
  effective_from: string;
  rule_definition_hash?: string | null;
  sections?: FormSectionDefinition[];
  fields: SchemeRequirementField[];
  evidence_types: SchemeRequirementEvidence[];
  cross_field_rules?: CrossFieldRule[];
}

export interface AvailableSchemeSummary {
  id: string;
  scheme_code: string;
  name_en: string;
  name_hi: string;
  description_en: string;
  description_hi: string;
  ministry?: string | null;
  official_url: string;
  status: string;
  created_at: string;
}

export interface CitizenDecisionResponse {
  application_id: string;
  application_ref: string;
  scheme_code: string;
  scheme_name_en: string;
  scheme_name_hi: string;
  is_evaluated: boolean;
  outcome: string;
  policy_version_code?: string | null;
  evaluated_at?: string | null;
  reasons_en: string[];
  reasons_hi: string[];
  passed_conditions: string[];
  failed_conditions: string[];
  missing_information: string[];
  unverified_requirements: string[];
  statutory_disclaimer_en: string;
  statutory_disclaimer_hi: string;
}
