import { apiPost } from "./client"
import type { CopilotAskRequest, CopilotAskResponse } from "./types"

export function askRecoveryCopilot(payload: CopilotAskRequest): Promise<CopilotAskResponse> {
  return apiPost<CopilotAskResponse>("/api/v1/copilot/ask", payload)
}
