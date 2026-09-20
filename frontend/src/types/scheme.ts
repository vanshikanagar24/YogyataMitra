import { SchemeStatus } from "./enums";
import { PolicyVersionSummary } from "./policy";

export interface SchemeSummary {
  id: string;
  scheme_code: string;
  name_en: string;
  name_hi: string;
  description_en: string;
  description_hi: string;
  ministry?: string | null;
  official_url: string;
  status: SchemeStatus;
  created_at: string;
}

export interface SchemeDetail extends SchemeSummary {
  updated_at: string;
  policy_versions: PolicyVersionSummary[];
}
