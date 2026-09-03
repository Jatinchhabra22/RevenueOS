import { apiGet } from "./client"
import type { OpportunityListResponse, OpportunityQuery } from "./types"

export function fetchOpportunities(query: OpportunityQuery = {}): Promise<OpportunityListResponse> {
  const params = new URLSearchParams()
  if (query.priority) params.set("priority", query.priority)
  if (query.status) params.set("status", query.status)
  if (query.minimum_amount != null) params.set("minimum_amount", String(query.minimum_amount))
  if (query.limit != null) params.set("limit", String(query.limit))
  if (query.offset != null) params.set("offset", String(query.offset))
  const suffix = params.toString() ? `?${params.toString()}` : ""
  return apiGet<OpportunityListResponse>(`/api/v1/opportunities${suffix}`)
}
