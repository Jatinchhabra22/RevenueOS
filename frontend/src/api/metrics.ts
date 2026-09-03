import { apiGet } from "./client"
import type {
  ActionEffectivenessResponse,
  MetricsDashboardResponse,
  MetricsOverviewResponse,
  OutcomeMetricsResponse,
} from "./types"

export function fetchMetricsOverview(): Promise<MetricsOverviewResponse> {
  return apiGet<MetricsOverviewResponse>("/api/v1/metrics/overview")
}

export function fetchMetricsDashboard(): Promise<MetricsDashboardResponse> {
  return apiGet<MetricsDashboardResponse>("/api/v1/metrics/dashboard")
}

export function fetchOutcomeMetrics(): Promise<OutcomeMetricsResponse> {
  return apiGet<OutcomeMetricsResponse>("/api/v1/metrics/outcomes")
}

export function fetchActionEffectiveness(actionType?: string): Promise<ActionEffectivenessResponse> {
  const query = actionType ? `?action_type=${encodeURIComponent(actionType)}` : ""
  return apiGet<ActionEffectivenessResponse>(`/api/v1/metrics/actions${query}`)
}
