import { useEffect, useMemo, useState } from "react"

import { fetchOpportunities } from "@/api/opportunities"
import type { OpportunityItem, PriorityCategory } from "@/api/types"
import { OpportunityTable } from "@/components/OpportunityTable"
import { ErrorState, LoadingState } from "@/components/States"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { errorMessage } from "@/lib/format"

const PAGE_SIZE = 25

export function OpportunitiesPage() {
  const [priority, setPriority] = useState<PriorityCategory | "">("")
  const [status, setStatus] = useState("open")
  const [minimumAmount, setMinimumAmount] = useState("")
  const [search, setSearch] = useState("")
  const [offset, setOffset] = useState(0)
  const [total, setTotal] = useState(0)
  const [items, setItems] = useState<OpportunityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    const min = minimumAmount.trim() ? Number(minimumAmount) : undefined
    fetchOpportunities({
      status,
      priority: priority || undefined,
      minimum_amount: min != null && !Number.isNaN(min) ? min : undefined,
      limit: 200,
      offset: 0,
    })
      .then((result) => {
        if (cancelled) return
        setItems(result.items)
        setTotal(result.total)
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
  }, [priority, status, minimumAmount])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return items
    return items.filter(
      (item) =>
        item.event_id.toLowerCase().includes(q) || item.customer_id.toLowerCase().includes(q),
    )
  }, [items, search])

  const page = filtered.slice(offset, offset + PAGE_SIZE)
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pageIndex = Math.floor(offset / PAGE_SIZE)

  useEffect(() => {
    setOffset(0)
  }, [priority, status, minimumAmount, search])

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">Recovery queue</h2>
        <p className="text-sm text-muted-foreground">
          Each row is an open revenue event ranked by expected recovery value — why it deserves attention
          before you inspect the decision trail.
        </p>
      </div>

      <Card className="flex flex-wrap items-end gap-3 p-4">
        <label className="grid gap-1 text-xs font-medium">
          Search
          <input
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            placeholder="Event or customer"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <label className="grid gap-1 text-xs font-medium">
          Priority
          <select
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            value={priority}
            onChange={(event) => setPriority(event.target.value as PriorityCategory | "")}
          >
            <option value="">All</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </label>
        <label className="grid gap-1 text-xs font-medium">
          Status
          <select
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="open">Open</option>
            <option value="all">All</option>
          </select>
        </label>
        <label className="grid gap-1 text-xs font-medium">
          Minimum amount (₹)
          <input
            className="h-9 w-36 rounded-md border border-input bg-background px-3 text-sm"
            inputMode="numeric"
            placeholder="0"
            value={minimumAmount}
            onChange={(event) => setMinimumAmount(event.target.value)}
          />
        </label>
      </Card>

      <p className="text-xs text-muted-foreground">
        Showing {page.length} of {filtered.length} loaded rows
        {total > items.length ? ` (${total} match API filters)` : ""}.
      </p>

      <Card>
        {error ? (
          <div className="p-4">
            <ErrorState message={error} />
          </div>
        ) : loading ? (
          <div className="p-4">
            <LoadingState label="Loading recovery queue…" />
          </div>
        ) : (
          <OpportunityTable items={page} highlightFirst={offset === 0 && !search && !priority} />
        )}
        <div className="flex items-center justify-between border-t border-border px-4 py-3">
          <p className="text-xs text-muted-foreground">
            Page {pageIndex + 1} of {pageCount}
          </p>
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Previous
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={offset + PAGE_SIZE >= filtered.length}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
