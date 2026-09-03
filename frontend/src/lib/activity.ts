import type { AgentWorkflowResponse } from "@/api/types"

const KEY = "rro.recent-workflows"

export type RecentWorkflow = {
  workflow_id: string
  event_id: string
  customer_id: string
  selected_action: string
  guardrail: string
  outcome: string
  timestamp: string
}

export function rememberWorkflow(workflow: AgentWorkflowResponse, customerId?: string): void {
  const entry: RecentWorkflow = {
    workflow_id: workflow.workflow_id,
    event_id: workflow.event_id,
    customer_id: customerId || workflow.risk_assessment.customer_id,
    selected_action: workflow.selected_action.action_type,
    guardrail: workflow.guardrail_result.status,
    outcome: workflow.outcome?.outcome ?? workflow.status,
    timestamp: workflow.outcome?.timestamp ?? workflow.execution_result?.timestamp ?? new Date().toISOString(),
  }
  const existing = listRememberedWorkflows().filter((item) => item.workflow_id !== entry.workflow_id)
  const next = [entry, ...existing].slice(0, 50)
  localStorage.setItem(KEY, JSON.stringify(next))
}

export function listRememberedWorkflows(): RecentWorkflow[] {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as RecentWorkflow[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}
