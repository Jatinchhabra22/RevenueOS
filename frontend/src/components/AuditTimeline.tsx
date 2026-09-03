import type { AuditEntry } from "@/api/types"
import { formatDate, humanize } from "@/lib/format"

const STAGE_ORDER = [
  "assemble_context",
  "diagnose_event",
  "get_predictions",
  "assess_revenue_risk",
  "generate_candidate_actions",
  "select_action",
  "validate_guardrails",
  "execute_action",
  "monitor_result",
]

const STAGE_LABELS: Record<string, string> = {
  assemble_context: "Context",
  diagnose_event: "Diagnosis",
  get_predictions: "Prediction",
  assess_revenue_risk: "Risk",
  generate_candidate_actions: "Candidates",
  select_action: "Decision",
  validate_guardrails: "Guardrail",
  execute_action: "Execution",
  monitor_result: "Outcome",
}

export function AuditTimeline({ entries }: { entries: AuditEntry[] }) {
  const byStage = new Map<string, AuditEntry>()
  for (const entry of entries) {
    if (STAGE_ORDER.includes(entry.stage)) {
      byStage.set(entry.stage, entry)
    }
  }
  const visible = STAGE_ORDER.map((stage) => byStage.get(stage)).filter(
    (entry): entry is AuditEntry => Boolean(entry),
  )
  if (!visible.length) {
    return <p className="text-sm text-muted-foreground">No audit trail yet.</p>
  }
  return (
    <ol className="space-y-0">
      {visible.map((entry, index) => (
        <li key={`${entry.stage}-${entry.timestamp}-${index}`} className="flex gap-3">
          <div className="flex flex-col items-center">
            <span className="mt-1 size-2.5 rounded-full bg-primary" />
            {index < visible.length - 1 ? <span className="w-px flex-1 bg-border" /> : null}
          </div>
          <div className="pb-5">
            <p className="text-sm font-medium">{STAGE_LABELS[entry.stage] ?? humanize(entry.stage)}</p>
            <p className="text-sm text-muted-foreground">{entry.reason}</p>
            <p className="mt-1 text-[11px] text-muted-foreground">{formatDate(entry.timestamp)}</p>
          </div>
        </li>
      ))}
    </ol>
  )
}
