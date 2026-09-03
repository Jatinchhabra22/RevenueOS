import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"

import { fetchAgentActivity } from "@/api/agent"
import type { AgentActivityItem } from "@/api/types"
import { PriorityBadge, OutcomeBadge } from "@/components/PriorityBadge"
import { ErrorState, EmptyState, LoadingState } from "@/components/States"
import { Card } from "@/components/ui/card"
import { useWorkspace } from "@/hooks/useWorkspace"
import { errorMessage, formatDate, formatInr, humanize } from "@/lib/format"

export function AgentActivityPage() {
  const { epoch } = useWorkspace()
  const [rows, setRows] = useState<AgentActivityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [outcomeFilter, setOutcomeFilter] = useState("")

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchAgentActivity()
      .then((result) => {
        if (!cancelled) setRows(result.items)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(errorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [epoch])

  const visible = useMemo(() => {
    if (!outcomeFilter) return rows
    return rows.filter((row) => row.outcome === outcomeFilter)
  }, [rows, outcomeFilter])

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">What the recovery system has done</h2>
        <p className="text-sm text-muted-foreground">
          Persisted simulated workflows. Click an event to inspect the full decision trail.
        </p>
      </div>

      <label className="grid w-48 gap-1 text-xs font-medium">
        Outcome
        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={outcomeFilter}
          onChange={(event) => setOutcomeFilter(event.target.value)}
        >
          <option value="">All</option>
          <option value="RECOVERED">RECOVERED</option>
          <option value="NOT_RECOVERED">NOT_RECOVERED</option>
          <option value="PENDING">PENDING</option>
          <option value="BLOCKED">BLOCKED</option>
          <option value="NO_ACTION">NO_ACTION</option>
        </select>
      </label>

      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState label="Loading agent activity…" /> : null}
      {!loading && !error && visible.length === 0 ? (
        <EmptyState
          title="No agent activity yet"
          description="Run the recovery agent from an event to populate this feed."
        />
      ) : null}

      {!loading && visible.length > 0 ? (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[800px] text-left text-sm">
            <thead className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">Workflow</th>
                <th className="px-4 py-3 font-medium">Event</th>
                <th className="px-4 py-3 font-medium">Action</th>
                <th className="px-4 py-3 font-medium">Priority</th>
                <th className="px-4 py-3 font-medium">Guardrail</th>
                <th className="px-4 py-3 font-medium">Outcome</th>
                <th className="px-4 py-3 font-medium">Recovered</th>
                <th className="px-4 py-3 font-medium">Mode</th>
                <th className="px-4 py-3 font-medium">Iterations</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr key={row.workflow_id} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 font-mono text-xs">{row.workflow_id}</td>
                  <td className="px-4 py-3">
                    <Link className="font-medium hover:underline" to={`/app/events/${row.event_id}`}>
                      {row.event_id}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{humanize(row.selected_action)}</td>
                  <td className="px-4 py-3">
                    {row.priority_category ? <PriorityBadge value={row.priority_category} /> : "—"}
                  </td>
                  <td className="px-4 py-3">{row.guardrail_status}</td>
                  <td className="px-4 py-3">
                    {row.outcome ? <OutcomeBadge value={row.outcome} /> : "—"}
                  </td>
                  <td className="px-4 py-3 tabular-nums">{formatInr(row.amount_recovered)}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{formatDate(row.timestamp)}</td>
                  <td className="px-4 py-3 text-xs">{row.agent_mode ?? "—"}</td>
                  <td className="px-4 py-3 tabular-nums">{row.iterations ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
    </div>
  )
}
