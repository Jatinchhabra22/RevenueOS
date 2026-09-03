import { Check } from "lucide-react"

import type { CandidateAction } from "@/api/types"
import { humanize } from "@/lib/format"
import { cn } from "@/lib/utils"

export function ActionCard({
  action,
  selected = false,
}: {
  action: CandidateAction
  selected?: boolean
}) {
  return (
    <div
      className={cn(
        "rounded-lg border p-4",
        selected ? "border-primary bg-primary/5" : "border-border bg-card",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">{humanize(action.action_type)}</p>
          <p className="mt-1 text-xs text-muted-foreground">{action.rationale}</p>
        </div>
        {selected ? (
          <span className="inline-flex items-center gap-1 rounded border border-primary/30 bg-primary/10 px-2 py-0.5 text-[11px] font-semibold uppercase text-primary">
            <Check className="size-3" />
            Selected
          </span>
        ) : null}
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div>
          <dt className="text-muted-foreground">Eligibility</dt>
          <dd className="font-medium">{action.eligibility ? "Eligible" : "Not eligible"}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Expected effect</dt>
          <dd className="font-medium">{humanize(action.expected_effect)}</dd>
        </div>
      </dl>
    </div>
  )
}
