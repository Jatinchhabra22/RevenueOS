import { apiGet, apiPost, ApiError } from "./client"
import type { AgentActivityResponse, AgentRunRequest, AgentWorkflowResponse } from "./types"

export function runRecoveryAgent(
  eventId: string,
  request: AgentRunRequest = {},
): Promise<AgentWorkflowResponse> {
  return apiPost<AgentWorkflowResponse>(
    `/api/v1/events/${encodeURIComponent(eventId)}/agent/run`,
    request,
  )
}

export async function fetchLatestWorkflow(
  eventId: string,
): Promise<AgentWorkflowResponse | null> {
  try {
    return await apiGet<AgentWorkflowResponse>(
      `/api/v1/events/${encodeURIComponent(eventId)}/agent/latest`,
    )
  } catch (error) {
    if (error instanceof ApiError && error.code === "WORKFLOW_NOT_FOUND") {
      return null
    }
    throw error
  }
}

export function fetchAgentActivity(): Promise<AgentActivityResponse> {
  return apiGet<AgentActivityResponse>("/api/v1/agent/activity")
}
