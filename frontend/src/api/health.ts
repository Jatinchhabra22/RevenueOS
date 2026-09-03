import { apiGet } from "./client"
import type { AgentHealthResponse, HealthResponse } from "./types"

export function fetchHealth(): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/api/v1/health")
}

export function fetchAgentHealth(): Promise<AgentHealthResponse> {
  return apiGet<AgentHealthResponse>("/api/v1/agent/health")
}
