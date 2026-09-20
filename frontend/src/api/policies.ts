import { apiClient } from "./client";
import { PolicyVersionDetail } from "../types/policy";

export async function listSchemePolicies(schemeCode: string): Promise<PolicyVersionDetail[]> {
  return apiClient.get<PolicyVersionDetail[]>(`/schemes/${encodeURIComponent(schemeCode)}/policies`);
}

export async function getPolicyVersion(schemeCode: string, versionCode: string): Promise<PolicyVersionDetail> {
  return apiClient.get<PolicyVersionDetail[]>(
    `/schemes/${encodeURIComponent(schemeCode)}/policies/${encodeURIComponent(versionCode)}`
  ).then((res: any) => (Array.isArray(res) ? res[0] : res));
}
