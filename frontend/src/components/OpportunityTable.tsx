import { Link } from "react-router-dom"

import type { OpportunityItem } from "@/api/types"
import { PriorityBadge, StatusBadge } from "@/components/PriorityBadge"
import { ProbabilityBar } from "@/components/ProbabilityBar"
import { formatInr, humanize } from "@/lib/format"
import { cn } from "@/lib/utils"

export function OpportunityTable({
  items,
  highlightFirst = false,
  emptyLabel = "No opportunities match the current filters.",
}: {
  items: OpportunityItem[]
  highlightFirst?: boolean
  emptyLabel?: string
}) {
  if (!items.length) {
    return (
      <div className="px-4 py-10 text-center text-sm text-muted-foreground">{emptyLabel}</div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[860px] text-left text-sm">
        <thead className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-4 py-3 font-medium">Priority</th>
            <th className="px-4 py-3 font-medium">Event</th>
            <th className="px-4 py-3 font-medium">Customer</th>
            <th className="px-4 py-3 font-medium">Amount at risk</th>
            <th className="px-4 py-3 font-medium">Recovery</th>
            <th className="px-4 py-3 font-medium">Churn</th>
            <th className="px-4 py-3 font-medium">Expected recovery</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Action</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr
              key={item.event_id}
              className={cn(
                "border-b border-border last:border-0 hover:bg-muted/40",
                highlightFirst && index === 0 && "bg-amber-50/70",
              )}
            >
              <td className="px-4 py-3">
                <PriorityBadge value={item.priority_category} />
              </td>
              <td className="px-4 py-3">
                <Link className="font-medium text-foreground hover:underline" to={`/app/events/${item.event_id}`}>
                  {item.event_id}
                </Link>
                <p className="text-xs text-muted-foreground">{humanize(item.failure_reason)}</p>
              </td>
              <td className="px-4 py-3 font-mono text-xs">{item.customer_id}</td>
              <td className="px-4 py-3 tabular-nums">{formatInr(item.amount_at_risk)}</td>
              <td className="px-4 py-3 w-36">
                <ProbabilityBar value={item.recovery_probability} />
              </td>
              <td className="px-4 py-3 w-36">
                <ProbabilityBar value={item.churn_probability} tone="churn" />
              </td>
              <td className="px-4 py-3 font-medium tabular-nums">
                {formatInr(item.expected_recovery_value)}
              </td>
              <td className="px-4 py-3">
                <StatusBadge>{item.status ?? "unknown"}</StatusBadge>
              </td>
              <td className="px-4 py-3">
                <Link
                  to={`/app/events/${item.event_id}`}
                  className="text-xs font-medium text-primary hover:underline"
                >
                  Inspect
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
