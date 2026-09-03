export type HealthResponse = {
  status: string
  service: string
}

export type AgentHealthResponse = {
  configured_mode: string
  llm_available: boolean
  provider: string | null
  model: string | null
  fallback_available: boolean
  ollama_reachable: boolean
  ollama_model: string | null
  ollama_model_present: boolean
}

export type DatasetSummary = {
  dataset_id: string
  source: string
  customer_count: number
  transaction_count: number
  subscription_count: number
  revenue_event_count: number
  intervention_count: number
  open_event_count: number
  recovered_event_count: number
  validation_status: "ok" | "failed"
  validation_errors: string[]
  validation_warnings: string[]
}

export type PriorityCategory = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"

export type OpportunityItem = {
  event_id: string
  customer_id: string
  amount_at_risk: number
  recovery_probability: number
  churn_probability: number
  expected_recovery_value: number
  priority_score: number
  priority_category: string
  failure_reason: string | null
  payment_method: string | null
  event_type: string | null
  urgency: string | null
  customer_ltv: number | null
  status: string | null
  recoverability?: string | null
  pursue?: boolean | null
}

export type OpportunityListResponse = {
  items: OpportunityItem[]
  total: number
  limit: number
  offset: number
}

export type OpportunityQuery = {
  priority?: PriorityCategory
  status?: string
  minimum_amount?: number
  limit?: number
  offset?: number
}

export type Customer = {
  customer_id: string
  merchant_id: string
  signup_date?: string | null
  customer_segment?: string | null
  tenure_days?: number | null
  total_orders?: number | null
  total_spend?: number | null
  avg_order_value?: number | null
  payment_success_rate?: number | null
  previous_failures?: number | null
  previous_recoveries?: number | null
  engagement_score?: number | null
  activity_trend?: string | null
  customer_ltv?: number | null
  last_activity_date?: string | null
}

export type Subscription = {
  subscription_id: string
  customer_id: string
  merchant_id: string
  subscription_start_date: string
  subscription_status: string
  recurring_amount: number
  billing_frequency: string
  successful_cycles?: number | null
  failed_cycles?: number | null
  next_billing_date?: string | null
}

export type Transaction = {
  transaction_id: string
  customer_id: string
  merchant_id: string
  transaction_timestamp: string
  amount: number
  currency: string
  payment_method?: string | null
  transaction_status: string
  failure_reason?: string | null
  attempt_number?: number | null
}

export type Intervention = {
  intervention_id: string
  event_id: string
  customer_id: string
  action_type: string
  action_timestamp: string
  attempt_number: number
  outcome: string
  amount_recovered?: number | null
}

export type RevenueEvent = {
  event_id: string
  event_timestamp: string
  merchant_id: string
  customer_id: string
  event_type: string
  amount_at_risk: number
  payment_method?: string | null
  failure_reason?: string | null
  attempt_number?: number | null
  urgency?: string | null
  event_status: string
}

export type RecoveryPrediction = {
  probability: number
  recoverability: string
  model_type: string
  model_version: string
  fallback: boolean
  contributing_factors: string[]
}

export type ChurnPrediction = {
  probability: number
  risk_category: string
  model_type: string
  model_version: string
  fallback: boolean
  contributing_factors: string[]
}

export type RiskAssessment = {
  event_id: string
  customer_id: string
  amount_at_risk: number
  recovery_probability: number
  churn_probability: number
  customer_ltv: number | null
  urgency: string
  expected_recovery_value: number
  priority_score: number
  priority_category: string
  contributing_factors: string[]
}

export type RecoverabilityAssessment = {
  classification: string
  pursue: boolean
  statement: string
  reason: string
  reason_codes: string[]
  recovery_probability: number | null
  expected_recovery_value: number | null
  amount_at_risk: number | null
}

export type EventDetailResponse = {
  event: RevenueEvent
  customer: Customer | null
  subscription: Subscription | null
  related_transaction: Transaction | null
  recent_transactions: Transaction[]
  previous_interventions: Intervention[]
  recovery_prediction: RecoveryPrediction
  churn_prediction: ChurnPrediction
  risk_assessment: RiskAssessment
  recoverability?: RecoverabilityAssessment | null
  status: string
}

export type Diagnosis = {
  primary_issue: string
  recoverability_reason: string
  churn_concern: string
  customer_context: string
  recommended_strategy: string
  issue_category: string
  event_summary: string
  key_factors: string[]
  risk_notes: string[]
  source: "llm" | "fallback"
}

export type CandidateAction = {
  action_id: string
  action_type: string
  eligibility: boolean
  expected_effect: string
  friction: string
  estimated_cost: string
  rationale: string
  required_inputs: string[]
}

export type ActionDecision = {
  selected_action_id: string
  selected_action_type: string
  reason: string
  confidence: number
  alternative_considered: string | null
  source: "llm" | "fallback"
  informed_by_observations?: number | null
  historical_note?: string | null
}

export type GuardrailResult = {
  allowed: boolean
  status: "ALLOW" | "BLOCK"
  reason: string
  violations: string[]
  reason_codes?: string[]
}

export type ToolResult = {
  action_id: string
  action_type: string
  execution_id: string
  status: string
  timestamp: string
  message: string
}

export type RecoveryOutcome = {
  outcome: string
  action_type: string
  execution_status: string
  amount_recovered: number
  remaining_amount_at_risk: number
  customer_impact: string
  timestamp: string
  explanation: string
}

export type AuditEntry = {
  timestamp: string
  stage: string
  decision: string
  reason: string
  metadata: Record<string, unknown>
}

export type AgentTraceEvent = {
  trace_id: string
  workflow_id: string
  iteration: number
  agent: string
  event_type: string
  timestamp: string
  status: string
  summary: string
  tool_name?: string | null
  decision?: string | null
  fallback_used?: boolean
}

export type InvestigationResult = {
  facts_found: string[]
  important_signals: string[]
  missing_information: string[]
  anomalies: string[]
  evidence_summary: string
  confidence: number
  source: "llm" | "fallback"
  tools_used: string[]
}

export type CustomerAnalysis = {
  customer_value_band: string
  churn_risk: string
  relationship_strength: string
  contact_sensitivity: string
  recovery_sensitivity: string
  recommended_tone: string
  key_customer_signals: string[]
  summary: string
  source: "llm" | "fallback"
  ml_churn_probability?: number | null
}

export type RecoveryStrategy = {
  recommended_action: string
  alternative_action?: string | null
  reasoning_summary: string
  expected_effect: string
  customer_impact: string
  confidence: number
  source: "llm" | "fallback"
}

export type ReflectionResult = {
  outcome_interpretation: string
  strategy_assessment: string
  new_information: string
  recommended_next_step: string
  avoid_actions: string[]
  confidence: number
  summary: string
  source: "llm" | "fallback"
}

export type AgentWorkflowResponse = {
  workflow_id: string
  event_id: string
  diagnosis: Diagnosis
  recovery_prediction: RecoveryPrediction
  churn_prediction: ChurnPrediction
  risk_assessment: RiskAssessment
  candidate_actions: CandidateAction[]
  selected_action: CandidateAction
  decision: ActionDecision
  guardrail_result: GuardrailResult
  execution_result: ToolResult | null
  outcome: RecoveryOutcome | null
  final_decision: string
  status: string
  used_llm: boolean
  dry_run: boolean
  audit_trail: AuditEntry[]
  agent_mode?: string
  provider?: string | null
  model?: string | null
  fallback_used?: boolean
  iterations?: number
  current_stage?: string | null
  workflow_status?: string | null
  terminal_reason?: string | null
  investigation?: InvestigationResult | null
  customer_analysis?: CustomerAnalysis | null
  strategy?: RecoveryStrategy | null
  reflection?: ReflectionResult | null
  agent_trace?: AgentTraceEvent[]
  iteration_history?: Record<string, unknown>[]
  llm_call_count?: number
  recoverability?: RecoverabilityAssessment | null
}

export type AgentRunRequest = {
  force_recompute?: boolean
  dry_run?: boolean
}

export type AgentActivityItem = {
  workflow_id: string
  event_id: string
  customer_id: string
  selected_action: string
  guardrail_status: string
  outcome: string | null
  execution_status: string | null
  timestamp: string | null
  amount_recovered: number
  dry_run: boolean
  priority_category?: string | null
  amount_at_risk?: number | null
  expected_recovery_value?: number | null
  agent_mode?: string | null
  iterations?: number | null
  provider?: string | null
}

export type AgentActivityResponse = {
  items: AgentActivityItem[]
  total: number
}

export type MetricsOverviewResponse = {
  dataset: {
    open_event_count: number
    recovered_event_count: number
    revenue_event_count: number
  }
  opportunities: {
    open_opportunities: number
    revenue_at_risk: number
    expected_recoverable_revenue: number
    critical_count: number
    high_count: number
    medium_count: number
    low_count: number
    average_recovery_probability: number | null
    average_churn_probability: number | null
    priority_breakdown: {
      priority_category: string
      count: number
      revenue_at_risk: number
      expected_recoverable_revenue: number
    }[]
  }
  agent_executions: {
    workflow_count: number
    recovered_outcomes: number
    not_recovered_outcomes: number
    pending_outcomes: number
    blocked_outcomes: number
    no_action_outcomes: number
    simulated_amount_recovered: number
  }
}

export type OutcomeMetricsResponse = {
  source: "agent_workflows"
  disclaimer: string
  executions: number
  successful_recoveries: number
  unsuccessful_recoveries: number
  pending_outcomes: number
  blocked_actions: number
  no_action_outcomes: number
  recovery_rate: number | null
  total_amount_recovered: number
  total_amount_attempted: number
  average_recovered_amount: number | null
  expected_recovery_sum: number
  observed_recovery_sum: number
  missing_amount_recovered_count: number
  top_performing_action: string | null
}

export type ActionEffectivenessRow = {
  action_type: string
  execution_count: number
  recovered_count: number
  recovery_rate: number | null
  amount_recovered: number
  average_recovered_amount: number | null
  average_recovery_probability: number | null
  expected_recovery_value: number
  observed_recovery: number
  observed_vs_expected: number | null
  low_sample_size: boolean
  sample_quality: string
}

export type ActionEffectivenessResponse = {
  source: "agent_workflows"
  disclaimer: string
  items: ActionEffectivenessRow[]
}

export type CopilotAskRequest = {
  event_id: string
  question: string
}

export type CopilotAskResponse = {
  event_id: string
  question: string
  answer: string
  sources: string[]
  provider: string | null
  model: string | null
  fallback_used: boolean
}

export type NamedCountAmount = {
  key: string
  count: number
  amount: number
  expected_recoverable_value: number
}

export type MetricsDashboardResponse = {
  funnel: {
    revenue_at_risk: number
    predicted_recoverable_value: number
    revenue_targeted: number | null
    actual_recovered: number | null
    revenue_targeted_available: boolean
    actual_recovered_available: boolean
  }
  risk_by_level: NamedCountAmount[]
  recoverability: NamedCountAmount[]
  outcomes: NamedCountAmount[]
  failure_reasons: NamedCountAmount[]
  predicted_vs_actual: {
    key: string
    predicted_recoverable_value: number
    actual_recovered: number
    executions: number
  }[]
  predicted_vs_actual_grouping: string
  actions: {
    action_type: string
    observed_recovery_rate: number | null
    execution_count: number
    amount_recovered: number
    recovered_count: number
    low_sample_size: boolean
    sample_quality: string
    confidence_label: string
  }[]
  activity_trend: {
    date: string
    recovery_attempts: number
    successful_recoveries: number
    amount_recovered: number
  }[]
  activity_trend_available: boolean
  activity_trend_reason: string | null
  top_opportunities: {
    event_id: string
    customer_id: string
    amount_at_risk: number
    expected_recovery_value: number
    priority_score: number
    priority_category: string
    recoverability: string | null
    failure_reason: string | null
  }[]
  kpis: Record<string, number | null>
  disclaimer: string
}
