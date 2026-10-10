import { apiClient } from "./client";

export interface SchemeProvenanceData {
  scheme_code: string;
  scheme_name_en: string;
  scheme_name_hi: string;
  ministry?: string;
  official_url: string;
  sources: Array<{
    id: string;
    publisher_name: string;
    publisher_type: string;
    official_domain: string;
    canonical_url: string;
  }>;
  documents: Array<{
    id: string;
    document_title: string;
    document_type: string;
    issuing_authority: string;
    reference_number?: string;
    official_url: string;
    versions: Array<{
      id: string;
      version_label: string;
      document_hash?: string;
      hash_algorithm: string;
      status: string;
      completeness: string;
      content_reference?: string;
      byte_size?: number;
    }>;
  }>;
  policy_versions: Array<{
    policy_version_id: string;
    version_code: string;
    effective_from: string;
    effective_to?: string;
    canonical_rule_hash?: string;
    source_title: string;
    source_url: string;
    bound_documents: Array<{
      document_title: string;
      version_label: string;
      reference_number?: string;
      official_url: string;
      binding_type: string;
      citation?: string;
      document_hash?: string;
      hash_algorithm: string;
      completeness: string;
    }>;
    rule_provenance_count: number;
  }>;
}

export async function getSchemeProvenance(schemeCode: string): Promise<SchemeProvenanceData> {
  return apiClient.get<SchemeProvenanceData>(`/provenance/schemes/${encodeURIComponent(schemeCode)}`);
}

export async function getPolicyProvenance(policyVersionId: string): Promise<any> {
  return apiClient.get(`/provenance/policies/${encodeURIComponent(policyVersionId)}`);
}

export async function getRuleProvenance(policyVersionId: string, ruleId: string): Promise<any> {
  return apiClient.get(`/provenance/rules/${encodeURIComponent(policyVersionId)}/${encodeURIComponent(ruleId)}`);
}
