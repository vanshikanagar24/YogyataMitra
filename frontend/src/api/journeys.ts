import { apiClient } from "./client";
import {
  EvidenceVerificationRequest,
  JourneyClaim,
  JourneyClaimCreateRequest,
  JourneyCreateRequest,
  JourneyDetailResponse,
  JourneyEvaluateRequest,
  JourneyEvaluationResponse,
  JourneyEvidence,
  JourneyEvidenceCreateRequest,
  JourneyResponse,
  JourneyTransitionRecord,
  JourneyTransitionRequest,
} from "../types/journey";

export async function createJourney(request: JourneyCreateRequest): Promise<JourneyResponse> {
  return apiClient.post<JourneyResponse>("/journeys", request);
}

export async function getJourney(journeyId: string): Promise<JourneyDetailResponse> {
  return apiClient.get<JourneyDetailResponse>(`/journeys/${encodeURIComponent(journeyId)}`);
}

export async function transitionJourney(
  journeyId: string,
  request: JourneyTransitionRequest
): Promise<JourneyResponse> {
  return apiClient.post<JourneyResponse>(`/journeys/${encodeURIComponent(journeyId)}/transitions`, request);
}

export async function getJourneyHistory(journeyId: string): Promise<JourneyTransitionRecord[]> {
  return apiClient.get<JourneyTransitionRecord[]>(`/journeys/${encodeURIComponent(journeyId)}/history`);
}

export async function addJourneyClaim(
  journeyId: string,
  request: JourneyClaimCreateRequest
): Promise<JourneyClaim> {
  return apiClient.post<JourneyClaim>(`/journeys/${encodeURIComponent(journeyId)}/claims`, request);
}

export async function getJourneyClaims(journeyId: string): Promise<JourneyClaim[]> {
  return apiClient.get<JourneyClaim[]>(`/journeys/${encodeURIComponent(journeyId)}/claims`);
}

export async function addJourneyEvidence(
  journeyId: string,
  claimId: string,
  request: JourneyEvidenceCreateRequest
): Promise<JourneyEvidence> {
  return apiClient.post<JourneyEvidence>(
    `/journeys/${encodeURIComponent(journeyId)}/claims/${encodeURIComponent(claimId)}/evidence`,
    request
  );
}

export async function uploadJourneyEvidence(
  journeyId: string,
  claimId: string,
  file: File,
  evidenceType: string
): Promise<JourneyEvidence> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("evidence_type", evidenceType);

  return apiClient.upload<JourneyEvidence>(
    `/journeys/${encodeURIComponent(journeyId)}/claims/${encodeURIComponent(claimId)}/evidence/upload`,
    formData
  );
}

export async function verifyJourneyEvidence(
  journeyId: string,
  evidenceId: string,
  request: EvidenceVerificationRequest
): Promise<JourneyEvidence> {
  return apiClient.post<JourneyEvidence>(
    `/journeys/${encodeURIComponent(journeyId)}/evidence/${encodeURIComponent(evidenceId)}/verify`,
    request
  );
}

export async function evaluateJourney(
  journeyId: string,
  request: JourneyEvaluateRequest
): Promise<JourneyEvaluationResponse> {
  return apiClient.post<JourneyEvaluationResponse>(
    `/journeys/${encodeURIComponent(journeyId)}/evaluate`,
    request
  );
}
