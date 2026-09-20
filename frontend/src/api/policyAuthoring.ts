/**
 * Policy Authoring API Client (Phase 16).
 *
 * Provides typed endpoints for controlled policy draft lifecycle,
 * static validation, deterministic compilation, test generation/execution,
 * policy diffing, and supervisory review transitions.
 */

import { apiClient } from "./client";
import { getAuthHeaders } from "./officer";
import {
  CompilationResponse,
  DraftTransitionPayload,
  PolicyDiffResponse,
  PolicyDraftCreatePayload,
  PolicyDraftDetail,
  PolicyDraftListResponse,
  PolicyDraftTestCase,
  PolicyDraftTestCreateRequest,
  PolicyDraftUpdatePayload,
  TestRunSummaryResponse,
  ValidationReportResponse,
} from "@/types/policyAuthoring";

export const policyAuthoringApi = {
  /**
   * List policy drafts with filtering and aggregated metrics.
   */
  listDrafts: (
    params?: { status?: string; scheme?: string; search?: string },
    token?: string | null
  ) => {
    const query = new URLSearchParams();
    if (params?.status && params.status !== "ALL") query.set("status", params.status);
    if (params?.scheme && params.scheme !== "ALL") query.set("scheme", params.scheme);
    if (params?.search) query.set("search", params.search);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return apiClient.get<PolicyDraftListResponse>(`/officer/policy-authoring/drafts${qs}`, {
      headers: getAuthHeaders(token),
    });
  },

  /**
   * Fetch full draft dossier including audit events, revisions, and test cases.
   */
  getDraft: (id: string, token?: string | null) =>
    apiClient.get<PolicyDraftDetail>(`/officer/policy-authoring/drafts/${encodeURIComponent(id)}`, {
      headers: getAuthHeaders(token),
    }),

  /**
   * Create a new policy draft.
   */
  createDraft: (payload: PolicyDraftCreatePayload, token?: string | null) =>
    apiClient.post<PolicyDraftDetail>("/officer/policy-authoring/drafts", payload, {
      headers: getAuthHeaders(token),
    }),

  /**
   * Update draft metadata or authored rule AST.
   */
  updateDraft: (id: string, payload: PolicyDraftUpdatePayload, token?: string | null) =>
    apiClient.patch<PolicyDraftDetail>(
      `/officer/policy-authoring/drafts/${encodeURIComponent(id)}`,
      payload,
      { headers: getAuthHeaders(token) }
    ),

  /**
   * Import an approved discovery candidate into an existing draft.
   */
  importCandidate: (id: string, candidateId: string, token?: string | null) =>
    apiClient.post<PolicyDraftDetail>(
      `/officer/policy-authoring/drafts/${encodeURIComponent(id)}/import-candidate`,
      { candidate_id: candidateId },
      { headers: getAuthHeaders(token) }
    ),

  /**
   * Run deterministic static AST validation against authored rules.
   */
  validateDraft: (id: string, token?: string | null) =>
    apiClient.post<ValidationReportResponse>(
      `/officer/policy-authoring/drafts/${encodeURIComponent(id)}/validate`,
      {},
      { headers: getAuthHeaders(token) }
    ),

  /**
   * Compile authored rules into canonical JSON and compute SHA-256 rule hash.
   */
  compileDraft: (id: string, token?: string | null) =>
    apiClient.post<CompilationResponse>(
      `/officer/policy-authoring/drafts/${encodeURIComponent(id)}/compile`,
      {},
      { headers: getAuthHeaders(token) }
    ),

  /**
   * Auto-generate boundary and Strong Kleene UNKNOWN test cases.
   */
  generateTests: (id: string, token?: string | null) =>
    apiClient.post<PolicyDraftTestCase[]>(
      `/officer/policy-authoring/drafts/${encodeURIComponent(id)}/generate-tests`,
      {},
      { headers: getAuthHeaders(token) }
    ),

  /**
   * Retrieve all test cases associated with the draft.
   */
  listTests: (id: string, token?: string | null) =>
    apiClient.get<PolicyDraftTestCase[]>(
      `/officer/policy-authoring/drafts/${encodeURIComponent(id)}/tests`,
      { headers: getAuthHeaders(token) }
    ),

  /**
   * Add a manual human-authored test case.
   */
  addTest: (id: string, payload: PolicyDraftTestCreateRequest, token?: string | null) =>
    apiClient.post<PolicyDraftTestCase>(
      `/officer/policy-authoring/drafts/${encodeURIComponent(id)}/tests`,
      payload,
      { headers: getAuthHeaders(token) }
    ),

  /**
   * Execute test suite against deterministic evaluator and statutory baselines.
   */
  runTests: (id: string, token?: string | null) =>
    apiClient.post<TestRunSummaryResponse>(
      `/officer/policy-authoring/drafts/${encodeURIComponent(id)}/test`,
      {},
      { headers: getAuthHeaders(token) }
    ),

  /**
   * Compute structural and bilingual policy diff against parent baseline.
   */
  getDiff: (id: string, token?: string | null) =>
    apiClient.get<PolicyDiffResponse>(
      `/officer/policy-authoring/drafts/${encodeURIComponent(id)}/diff`,
      { headers: getAuthHeaders(token) }
    ),

  /**
   * Transition policy draft lifecycle state with mandatory substantive justification.
   */
  transitionDraft: (id: string, payload: DraftTransitionPayload, token?: string | null) =>
    apiClient.post<PolicyDraftDetail>(
      `/officer/policy-authoring/drafts/${encodeURIComponent(id)}/transitions`,
      payload,
      { headers: getAuthHeaders(token) }
    ),

  /**
   * Fetch complete revision history and immutable audit trail.
   */
  getHistory: (id: string, token?: string | null) =>
    apiClient.get<{
      revisions: Array<any>;
      audit_events: Array<any>;
      total_revisions: number;
      total_audit_events: number;
    }>(`/officer/policy-authoring/drafts/${encodeURIComponent(id)}/history`, {
      headers: getAuthHeaders(token),
    }),
};
