/**
 * Citizen Authentication API client bindings (Phase A).
 */

import { apiClient } from "./client";
import {
  CitizenAuthResponse,
  CitizenLoginPayload,
  CitizenProfile,
  CitizenSignupPayload,
} from "@/types/auth";

import {
  CitizenApplicationCreatePayload,
  CitizenApplicationDetail,
  CitizenApplicationSummary,
  CitizenDashboardStats,
  CitizenDecisionResponse,
} from "@/types/citizen";

export function getCitizenAuthHeaders(token?: string | null): Record<string, string> {
  const activeToken =
    token ||
    (typeof window !== "undefined"
      ? localStorage.getItem("yogyatamitra_citizen_token")
      : null);

  return activeToken ? { Authorization: `Bearer ${activeToken}` } : {};
}

export const citizenApi = {
  // Phase A: Authentication & Profile
  signup: (payload: CitizenSignupPayload) =>
    apiClient.post<CitizenAuthResponse>("/citizen/auth/signup", payload),

  login: (payload: CitizenLoginPayload) =>
    apiClient.post<CitizenAuthResponse>("/citizen/auth/login", payload),

  getProfile: (token?: string | null) =>
    apiClient.get<CitizenProfile>("/citizen/auth/me", {
      headers: getCitizenAuthHeaders(token),
    }),

  // Phase B: Applications & Dashboard
  getApplications: (token?: string | null) =>
    apiClient.get<CitizenApplicationSummary[]>("/citizen/applications", {
      headers: getCitizenAuthHeaders(token),
    }),

  getApplicationDetail: (applicationId: string, token?: string | null) =>
    apiClient.get<CitizenApplicationDetail>(`/citizen/applications/${applicationId}`, {
      headers: getCitizenAuthHeaders(token),
    }),

  getDashboardStats: (token?: string | null) =>
    apiClient.get<CitizenDashboardStats>("/citizen/dashboard/stats", {
      headers: getCitizenAuthHeaders(token),
    }),

  createApplication: (payload: CitizenApplicationCreatePayload, token?: string | null) =>
    apiClient.post<CitizenApplicationSummary>("/citizen/applications", payload, {
      headers: getCitizenAuthHeaders(token),
    }),

  // Phase C: Schemes, Requirements, Draft Saving, and Submission
  getAvailableSchemes: (token?: string | null) =>
    apiClient.get<import("@/types/citizen").AvailableSchemeSummary[]>("/citizen/schemes", {
      headers: getCitizenAuthHeaders(token),
    }),

  getSchemeRequirements: (schemeCode: string, token?: string | null) =>
    apiClient.get<import("@/types/citizen").SchemeRequirementsResponse>(
      `/citizen/schemes/${schemeCode}/requirements`,
      { headers: getCitizenAuthHeaders(token) }
    ),

  updateDraft: (
    applicationId: string,
    payload: import("@/types/citizen").CitizenApplicationDraftUpdatePayload,
    token?: string | null
  ) =>
    apiClient.put<CitizenApplicationDetail>(
      `/citizen/applications/${applicationId}/draft`,
      payload,
      { headers: getCitizenAuthHeaders(token) }
    ),

  submitApplication: (
    applicationId: string,
    payload: import("@/types/citizen").CitizenApplicationSubmitPayload,
    token?: string | null
  ) =>
    apiClient.post<CitizenApplicationDetail>(
      `/citizen/applications/${applicationId}/submit`,
      payload,
      { headers: getCitizenAuthHeaders(token) }
    ),

  // Phase E: Evidence Clarification Workflow
  getClarifications: (applicationId: string, token?: string | null) =>
    apiClient.get<import("@/types/citizen").CitizenClarificationListResponse>(
      `/citizen/applications/${applicationId}/clarifications`,
      { headers: getCitizenAuthHeaders(token) }
    ),

  respondClarification: (
    applicationId: string,
    clarificationId: string,
    payload: import("@/types/citizen").CitizenClarificationRespondPayload,
    token?: string | null
  ) =>
    apiClient.post<import("@/types/citizen").CitizenClarificationItem>(
      `/citizen/applications/${applicationId}/clarifications/${clarificationId}/respond`,
      payload,
      { headers: getCitizenAuthHeaders(token) }
    ),

  getVerificationStatus: (applicationId: string, token?: string | null) =>
    apiClient.get<import("@/types/citizen").CitizenVerificationStatusResponse>(
      `/citizen/applications/${applicationId}/verification-status`,
      { headers: getCitizenAuthHeaders(token) }
    ),

  getDecision: (applicationId: string, token?: string | null) =>
    apiClient.get<CitizenDecisionResponse>(
      `/citizen/applications/${applicationId}/decision`,
      { headers: getCitizenAuthHeaders(token) }
    ),
};
