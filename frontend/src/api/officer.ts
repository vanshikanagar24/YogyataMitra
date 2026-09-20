/**
 * Officer Verification Portal API client bindings (Phase 14).
 */

import { apiClient } from "./client";
import {
  OfficerAuditEvent,
  OfficerCaseDetail,
  OfficerCaseReviewPayload,
  OfficerEvidence,
  OfficerEvidenceVerifyPayload,
  OfficerLoginResponse,
  OfficerProfile,
  OfficerQueueListResponse,
} from "@/types/officer";

export function getAuthHeaders(token?: string | null): Record<string, string> {
  const activeToken =
    token ||
    (typeof window !== "undefined"
      ? localStorage.getItem("yogyatamitra_officer_token")
      : null);

  return activeToken ? { Authorization: `Bearer ${activeToken}` } : {};
}

export const officerApi = {
  login: (credentials: { email: string; password: string }) =>
    apiClient.post<OfficerLoginResponse>("/officer/auth/login", credentials),

  getProfile: (token?: string | null) =>
    apiClient.get<OfficerProfile>("/officer/auth/me", {
      headers: getAuthHeaders(token),
    }),

  getQueue: (
    params?: { status?: string; scheme?: string },
    token?: string | null
  ) => {
    const query = new URLSearchParams();
    if (params?.status && params.status !== "ALL") query.set("status", params.status);
    if (params?.scheme && params.scheme !== "ALL") query.set("scheme", params.scheme);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return apiClient.get<OfficerQueueListResponse>(`/officer/queue${qs}`, {
      headers: getAuthHeaders(token),
    });
  },

  getCaseDetail: (journeyId: string, token?: string | null) =>
    apiClient.get<OfficerCaseDetail>(`/officer/cases/${journeyId}`, {
      headers: getAuthHeaders(token),
    }),

  verifyEvidence: (
    journeyId: string,
    evidenceId: string,
    payload: OfficerEvidenceVerifyPayload,
    token?: string | null
  ) =>
    apiClient.post<OfficerEvidence>(
      `/officer/cases/${journeyId}/evidence/${evidenceId}/verify`,
      payload,
      { headers: getAuthHeaders(token) }
    ),

  reviewCase: (
    journeyId: string,
    payload: OfficerCaseReviewPayload,
    token?: string | null
  ) =>
    apiClient.post<OfficerCaseDetail>(
      `/officer/cases/${journeyId}/review`,
      payload,
      { headers: getAuthHeaders(token) }
    ),

  getAuditTrail: (journeyId: string, token?: string | null) =>
    apiClient.get<OfficerAuditEvent[]>(
      `/officer/cases/${journeyId}/audit-trail`,
      { headers: getAuthHeaders(token) }
    ),
};
