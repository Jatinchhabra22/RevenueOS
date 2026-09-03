import type { AgentWorkflowResponse } from "@/api/types"
import { formatInr, formatPct, humanize } from "@/lib/format"

const STAGES = [
  { key: "supervisor", label: "Supervisor" },
  { key: "investigate_context", label: "Investigation" },
  { key: "diagnose_event", label: "Diagnosis" },
  { key: "analyze_customer", label: "Customer analysis" },
  { key: "select_action", label: "Strategy" },
  { key: "validate_guardrails", label: "Guardrail" },
  { key: "execute_action", label: "Execution" },
  { key: "monitor_result", label: "Observation" },
  { key: "reflect_outcome", label: "Reflection" },
] as const

export function AgentModeBadge({ workflow }: { workflow: AgentWorkflowResponse }) {
  const fallback = workflow.fallback_used === true || workflow.agent_mode === "deterministic_fallback"
  const label = fallback
    ? "Deterministic Fallback"
    : workflow.provider === "ollama" || workflow.agent_mode === "ollama"
      ? "Local LLM"
      : "LLM"
  const model = workflow.model ? ` · ${workflow.model}` : ""
  return (
    <p className="text-xs font-medium">
      Agent mode: {label}
      {model}
      {workflow.provider ? ` · ${workflow.provider}` : ""}
      {` · fallback ${fallback ? "true" : "false"}`}
    </p>
  )
}

export function WorkflowStageList({ workflow }: { workflow: AgentWorkflowResponse }) {
  const stages = new Set((workflow.audit_trail ?? []).map((entry) => entry.stage))
  return (
    <ol className="space-y-2 text-sm">
      {STAGES.map((stage) => {
        const done = stages.has(stage.key)
        return (
          <li key={stage.key} className="flex items-center gap-2">
            <span className={done ? "text-emerald-700" : "text-muted-foreground"}>{done ? "✓" : "○"}</span>
            <span className={done ? "text-foreground" : "text-muted-foreground"}>{stage.label}</span>
          </li>
        )
      })}
    </ol>
  )
}

export function RecoveredBanner({ workflow }: { workflow: AgentWorkflowResponse }) {
  const amount = workflow.outcome?.amount_recovered ?? 0
  if (workflow.outcome?.outcome !== "RECOVERED" || amount <= 0) return null
  const actions = (workflow.iteration_history ?? [])
    .map((row) => humanize(String(row.action_type ?? "")))
    .filter(Boolean)
  return (
    <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-800">Recovered</p>
      <p className="mt-1 text-3xl font-semibold tabular-nums text-emerald-900">{formatInr(amount)}</p>
      <p className="mt-2 text-sm text-emerald-900">
        Workflow RECOVERED · {workflow.iterations} iteration{workflow.iterations === 1 ? "" : "s"}
        {actions.length ? ` · ${actions.join(" → ")}` : ""}
      </p>
    </div>
  )
}

export function DiagnosisPanel({ workflow }: { workflow: AgentWorkflowResponse }) {
  const diagnosis = workflow.diagnosis
  const investigation = workflow.investigation
  return (
    <div className="space-y-3 text-sm">
      <p>
        <span className="text-muted-foreground">Likely cause · </span>
        {diagnosis.primary_issue}
      </p>
      {investigation?.facts_found?.length ? (
        <ul className="list-disc space-y-1 pl-4 text-muted-foreground">
          {investigation.facts_found.slice(0, 4).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
      <p className="text-muted-foreground">
        Confidence {formatPct(investigation?.confidence ?? diagnosis.source === "llm" ? 0.7 : 0.55)}
      </p>
    </div>
  )
}

export function StrategyPanel({ workflow }: { workflow: AgentWorkflowResponse }) {
  const strategy = workflow.strategy
  return (
    <div className="space-y-2 text-sm">
      <p>
        <span className="font-medium">Recommended · </span>
        {humanize(strategy?.recommended_action || workflow.selected_action.action_type)}
      </p>
      {strategy?.alternative_action ? (
        <p className="text-muted-foreground">Alternative · {humanize(strategy.alternative_action)}</p>
      ) : null}
      <p className="text-muted-foreground">{strategy?.reasoning_summary || workflow.decision.reason}</p>
    </div>
  )
}

export function ReflectionPanel({ workflow }: { workflow: AgentWorkflowResponse }) {
  const reflection = workflow.reflection
  if (!reflection) {
    return <p className="text-sm text-muted-foreground">No reflection recorded (blocked before execution).</p>
  }
  return (
    <div className="space-y-2 text-sm">
      <p>
        <span className="font-medium">Outcome · </span>
        {workflow.outcome?.outcome ?? "—"}
      </p>
      <p className="text-muted-foreground">{reflection.outcome_interpretation}</p>
      <p>
        <span className="font-medium">Next · </span>
        {humanize(reflection.recommended_next_step)}
      </p>
      {(workflow.iteration_history ?? []).length > 0 ? (
        <ol className="mt-2 space-y-1 text-muted-foreground">
          {(workflow.iteration_history ?? []).map((row, index) => (
            <li key={`${row.iteration}-${index}`}>
              Iteration {String(row.iteration ?? index + 1)} → {humanize(String(row.action_type ?? "—"))} →{" "}
              {String(row.outcome ?? "—")}
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  )
}
