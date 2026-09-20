import { apiClient } from "./client";
import {
  EvaluationRequest,
  EvaluationResponse,
  PersistedEvaluationResponse,
} from "../types/evaluation";

export async function evaluateEligibility(request: EvaluationRequest): Promise<EvaluationResponse> {
  return apiClient.post<EvaluationResponse>("/evaluations", request);
}

export async function getEvaluationTrace(evaluationId: string): Promise<PersistedEvaluationResponse> {
  return apiClient.get<PersistedEvaluationResponse>(`/evaluations/${encodeURIComponent(evaluationId)}`);
}
