import {
  ClaimStatus,
  EligibilityResult,
  EvidenceStatus,
  JourneyState,
  VerificationStatus,
} from "./enums";

export interface JourneyTransitionRecord {
  id: string;
  journey_id: string;
  from_state: JourneyState;
  to_state: JourneyState;
  actor: string;
  reason?: string | null;
  created_at: string;
}

export interface JourneyVerificationRecord {
  id: string;
  evidence_id?: string | null;
  claim_id?: string | null;
  verification_method: string;
  status: VerificationStatus;
  verified_by?: string | null;
  verified_at?: string | null;
  details_json?: Record<string, unknown> | null;
  created_at: string;
}

export interface JourneyEvidence {
  id: string;
  claim_id: string;
  evidence_type: string;
  storage_reference: string;
  metadata_json?: Record<string, unknown> | null;
  status: EvidenceStatus;
  rejection_reason?: string | null;
  submitted_at: string;
  verified_at?: string | null;
  rejected_at?: string | null;
  verification_records: JourneyVerificationRecord[];
}

export interface JourneyClaim {
  id: string;
  journey_id?: string | null;
  citizen_id: string;
  claim_type: string;
  value_json: Record<string, unknown>;
  source: string;
  status: ClaimStatus;
  claimed_at: string;
  updated_at: string;
  evidence_items: JourneyEvidence[];
}

export interface JourneyResponse {
  id: string;
  citizen_id: string;
  citizen_ref: string;
  scheme_id: string;
  scheme_code: string;
  state: JourneyState;
  latest_evaluation_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface JourneyDetailResponse extends JourneyResponse {
  claims: JourneyClaim[];
  transitions: JourneyTransitionRecord[];
}

export interface JourneyCreateRequest {
  citizen_ref: string;
  scheme_code: string;
  initial_facts?: Record<string, unknown> | null;
}

export interface JourneyTransitionRequest {
  target_state: JourneyState;
  actor: string;
  reason?: string | null;
}

export interface JourneyClaimCreateRequest {
  claim_type: string;
  value_json: Record<string, unknown>;
  source?: string;
}

export interface JourneyEvidenceCreateRequest {
  evidence_type: string;
  storage_reference: string;
  metadata_json?: Record<string, unknown> | null;
}

export interface EvidenceVerificationRequest {
  status: EvidenceStatus;
  verification_method: string;
  verified_by: string;
  details_json?: Record<string, unknown> | null;
  rejection_reason?: string | null;
}

export interface JourneyEvaluateRequest {
  evaluation_date?: string | null;
  policy_version_code?: string | null;
  facts_override?: Record<string, unknown> | null;
}

export interface JourneyEvaluationResponse {
  journey_id: string;
  journey_state: JourneyState;
  evaluation_id: string;
  result_state: EligibilityResult;
  is_eligible?: boolean | null;
  scheme_code: string;
  policy_version_code: string;
  evaluation_date: string;
  missing_facts: string[];
  disqualifying_factors: Record<string, unknown>[];
  pending_evidence_count: number;
  unverified_evidence_count: number;
  action_items: string[];
}
