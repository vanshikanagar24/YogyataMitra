import { apiClient } from "./client";
import { SchemeDetail, SchemeSummary } from "../types/scheme";
import { SchemeStatus } from "../types/enums";

export async function listSchemes(statusFilter?: SchemeStatus): Promise<SchemeSummary[]> {
  const query = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : "";
  return apiClient.get<SchemeSummary[]>(`/schemes${query}`);
}

export async function getScheme(schemeCode: string): Promise<SchemeDetail> {
  return apiClient.get<SchemeDetail>(`/schemes/${encodeURIComponent(schemeCode)}`);
}
