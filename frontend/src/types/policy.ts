export interface PolicyVersionSummary {
  version_code: string;
  effective_from: string;
  effective_to: string | null;
  rule_definition_hash: string | null;
}

export interface PolicyVersionDetail {
  id: string;
  scheme_code: string;
  version_code: string;
  effective_from: string;
  effective_to: string | null;
  source_url: string;
  source_title: string;
  source_document_identifier: string | null;
  rule_definition_hash: string | null;
  ruleset_schema_version: string | null;
  ruleset_version: string | null;
  created_at: string;
}
