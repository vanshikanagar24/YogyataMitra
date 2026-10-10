/**
 * Officer Verification Portal API client bindings (Phase 14).
 */

import { apiClient } from "./client";
import {
  OfficerAssessment,
  OfficerAssignment,
  OfficerAssignmentPayload,
  OfficerAuditEvent,
  OfficerCaseDetail,
  OfficerCaseReviewPayload,
  OfficerClarificationItem,
  OfficerClarificationRequestPayload,
  OfficerDashboardStats,
  OfficerEvidence,
  OfficerEvidenceVerifyPayload,
  OfficerLoginResponse,
  OfficerProfile,
  OfficerQueueListResponse,
  OfficerReassignmentPayload,
  OfficerVerificationHistoryResponse,
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

  getDashboardStats: (token?: string | null) =>
    apiClient.get<OfficerDashboardStats>("/officer/dashboard/stats", {
      headers: getAuthHeaders(token),
    }),

  getQueue: (
    params?: {
      status?: string;
      scheme?: string;
      sla?: string;
      assigned_to_me?: boolean;
      unassigned?: boolean;
    },
    token?: string | null
  ) => {
    const query = new URLSearchParams();
    if (params?.status && params.status !== "ALL") query.set("status", params.status);
    if (params?.scheme && params.scheme !== "ALL") query.set("scheme", params.scheme);
    if (params?.sla && params.sla !== "ALL") query.set("sla", params.sla);
    if (params?.assigned_to_me) query.set("assigned_to_me", "true");
    if (params?.unassigned) query.set("unassigned", "true");
    const qs = query.toString() ? `?${query.toString()}` : "";
    return apiClient.get<OfficerQueueListResponse>(`/officer/queue${qs}`, {
      headers: getAuthHeaders(token),
    });
  },

  assignCase: (
    journeyId: string,
    payload: OfficerAssignmentPayload,
    token?: string | null
  ) =>
    apiClient.post<OfficerAssignment>(
      `/officer/cases/${journeyId}/assign`,
      payload,
      { headers: getAuthHeaders(token) }
    ),

  reassignCase: (
    journeyId: string,
    payload: OfficerReassignmentPayload,
    token?: string | null
  ) =>
    apiClient.post<OfficerAssignment>(
      `/officer/cases/${journeyId}/reassign`,
      payload,
      { headers: getAuthHeaders(token) }
    ),

  autoAssignCase: (journeyId: string, token?: string | null) =>
    apiClient.post<OfficerAssignment>(
      `/officer/cases/${journeyId}/auto-assign`,
      {},
      { headers: getAuthHeaders(token) }
    ),

  getAssignments: (journeyId: string, token?: string | null) =>
    apiClient.get<OfficerAssignment[]>(
      `/officer/cases/${journeyId}/assignments`,
      { headers: getAuthHeaders(token) }
    ),


  getCaseDetail: (journeyId: string, token?: string | null) =>
    apiClient.get<OfficerCaseDetail>(`/officer/cases/${journeyId}`, {
      headers: getAuthHeaders(token),
    }),

  getEvidence: (journeyId: string, token?: string | null) =>
    apiClient.get<OfficerEvidence[]>(
      `/officer/cases/${journeyId}/evidence`,
      { headers: getAuthHeaders(token) }
    ),

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

  requestClarification: (
    journeyId: string,
    evidenceId: string,
    payload: OfficerClarificationRequestPayload,
    token?: string | null
  ) =>
    apiClient.post<OfficerClarificationItem>(
      `/officer/cases/${journeyId}/evidence/${evidenceId}/clarification`,
      payload,
      { headers: getAuthHeaders(token) }
    ),

  getVerificationHistory: (journeyId: string, token?: string | null) =>
    apiClient.get<OfficerVerificationHistoryResponse>(
      `/officer/cases/${journeyId}/verification-history`,
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

  evaluateCase: (
    journeyId: string,
    payload?: { notes?: string },
    token?: string | null
  ) =>
    apiClient.post<OfficerAssessment>(
      `/officer/cases/${journeyId}/evaluate`,
      payload || {},
      { headers: getAuthHeaders(token) }
    ),

  getEvaluation: (journeyId: string, token?: string | null) =>
    apiClient.get<OfficerAssessment>(
      `/officer/cases/${journeyId}/evaluation`,
      { headers: getAuthHeaders(token) }
    ),

  getEvaluationHistory: (journeyId: string, token?: string | null) =>
    apiClient.get<OfficerAssessment[]>(
      `/officer/cases/${journeyId}/evaluation/history`,
      { headers: getAuthHeaders(token) }
    ),
};
