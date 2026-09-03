import { cn } from "@/lib/utils"
import { formatPct } from "@/lib/format"

export function ProbabilityBar({
  value,
  label,
  tone = "recovery",
}: {
  value: number
  label?: string
  tone?: "recovery" | "churn"
}) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)))
  return (
    <div className="min-w-24">
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums">{formatPct(value)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div
          className={cn(
            "h-full rounded-full",
            tone === "churn" ? "bg-amber-700/80" : "bg-primary",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export function RiskIndicator({
  recovery,
  churn,
}: {
  recovery: number
  churn: number
}) {
  return (
    <div className="grid gap-2">
      <ProbabilityBar value={recovery} label="Recovery" tone="recovery" />
      <ProbabilityBar value={churn} label="Churn" tone="churn" />
    </div>
  )
}
