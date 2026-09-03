import { apiGet } from "./client"
import type { EventDetailResponse } from "./types"

export function fetchEventDetail(eventId: string): Promise<EventDetailResponse> {
  return apiGet<EventDetailResponse>(`/api/v1/events/${encodeURIComponent(eventId)}`)
}
