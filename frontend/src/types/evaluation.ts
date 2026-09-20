import { EligibilityResult } from "./enums";

export interface BlockerResponse {
  code: string;
  category: string;
  field_path?: string | null;
  rule_id?: string | null;
  message_en: string;
  message_hi: string;
}

export interface FamilyFacts {
  owns_cultivable_land?: boolean | null;
  total_land_area_hectares?: number | null;
  is_institutional_landholder?: boolean | null;
  has_constitutional_post_holder?: boolean | null;
  has_public_representative?: boolean | null;
  has_disqualified_government_employee?: boolean | null;
  has_pensioner_above_ten_thousand?: boolean | null;
  has_income_tax_payer?: boolean | null;
  has_registered_practicing_professional?: boolean | null;
  is_nri?: boolean | null;
  has_nri_relative?: boolean | null;
  active_ssy_accounts_count?: number | null;
  has_multiple_birth_exception?: boolean | null;
  medical_twin_triplet_certificate_available?: boolean | null;
}

export interface LandFacts {
  transferred_after_cutoff?: boolean | null;
  acquired_via_succession?: boolean | null;
  previous_owner_deceased?: boolean | null;
}

export interface BeneficiaryFacts {
  gender?: string | null;
  is_indian_resident?: boolean | null;
  date_of_birth?: string | null;
}

export interface GuardianFacts {
  is_natural_guardian?: boolean | null;
  is_court_appointed_legal_guardian?: boolean | null;
}

export interface AccountFacts {
  opening_date?: string | null;
  is_first_account_for_child?: boolean | null;
}

export interface EvaluationFacts {
  family?: FamilyFacts;
  land?: LandFacts;
  beneficiary?: BeneficiaryFacts;
  guardian?: GuardianFacts;
  account?: AccountFacts;
  [key: string]: unknown;
}

export interface EvaluationRequest {
  scheme_code: string;
  evaluation_date: string;
  facts: EvaluationFacts;
  policy_version_code?: string | null;
  citizen_id?: string | null;
  citizen_ref?: string | null;
}

export interface EvaluationResponse {
  evaluation_id: string;
  scheme_code: string;
  policy_version_code: string;
  rule_definition_hash: string;
  evaluation_date: string;
  effective_from: string;
  effective_to?: string | null;
  overall_result: EligibilityResult;
  root_truth_value: string;
  reasons_en: string[];
  reasons_hi: string[];
  missing_fields: string[];
  satisfied_rules: string[];
  failed_rules: string[];
  unknown_rules: string[];
  blockers: BlockerResponse[];
  audit_persisted: boolean;
  created_at: string;
  trace?: Record<string, unknown> | null;
}

export interface PersistedEvaluationResponse {
  id: string;
  citizen_id: string;
  scheme_id: string;
  scheme_code: string;
  policy_version_id: string;
  policy_version_code: string;
  evaluation_date: string;
  result_state: EligibilityResult;
  rule_definition_hash?: string | null;
  trace_schema_version: string;
  input_snapshot_json: Record<string, unknown>;
  trace_json: Record<string, unknown>;
  created_at: string;
}
