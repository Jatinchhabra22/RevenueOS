import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { IndianRupee, ShieldAlert, Sparkles, Target } from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { fetchMetricsDashboard } from "@/api/metrics"
import { fetchOpportunities } from "@/api/opportunities"
import type { MetricsDashboardResponse, OpportunityItem } from "@/api/types"
import { MetricCard } from "@/components/MetricCard"
import { OpportunityTable } from "@/components/OpportunityTable"
import { EmptyState, ErrorState, LoadingState } from "@/components/States"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useWorkspace } from "@/hooks/useWorkspace"
import { errorMessage, formatInr, formatInrCompact, formatPct, humanize } from "@/lib/format"

const NAVY = "#1e3a5f"
const SLATE = "#64748b"
const GREEN = "#047857"
const GRID = "var(--border)"

export function OverviewPage() {
  const { summary, error, refresh, epoch } = useWorkspace()
  const [dashboard, setDashboard] = useState<MetricsDashboardResponse | null>(null)
  const [items, setItems] = useState<OpportunityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [pageError, setPageError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setPageError(null)
    Promise.all([fetchMetricsDashboard(), fetchOpportunities({ status: "open", limit: 8, offset: 0 })])
      .then(([nextDashboard, queue]) => {
        if (cancelled) return
        setDashboard(nextDashboard)
        setItems(queue.items)
      })
      .catch((err: unknown) => {
        if (!cancelled) setPageError(errorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [epoch, summary?.dataset_id])

  const funnelData = useMemo(() => {
    if (!dashboard) return []
    const funnel = dashboard.funnel
    return [
      { name: "Revenue at risk", value: funnel.revenue_at_risk, available: true },
      { name: "Predicted recoverable", value: funnel.predicted_recoverable_value, available: true },
      {
        name: "Targeted for intervention",
        value: funnel.revenue_targeted,
        available: funnel.revenue_targeted_available,
      },
      {
        name: "Actually recovered",
        value: funnel.actual_recovered,
        available: funnel.actual_recovered_available,
      },
    ]
  }, [dashboard])

  if (error && !summary) {
    return <ErrorState message={error} onRetry={() => void refresh()} />
  }
  if (pageError) {
    return <ErrorState message={pageError} onRetry={() => void refresh()} />
  }
  if (loading || !dashboard || !summary) {
    return <LoadingState label="Loading merchant overview…" />
  }

  const kpis = dashboard.kpis
  const observedRate = kpis.observed_event_recovery_rate
  const coverage = kpis.recoverability_coverage

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
          Risk ≠ predicted recovery ≠ actual recovery
        </p>
        <h2 className="mt-1 text-lg font-semibold">Which revenue is realistically worth pursuing?</h2>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          The agent estimates recoverability and expected value, then may take no action. Dataset labels
          are not observed recovery.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Revenue at risk"
          value={formatInrCompact(kpis.revenue_at_risk)}
          hint="Open events only — unpaid amount, not a recovery forecast"
          icon={IndianRupee}
          tone="emphasis"
        />
        <MetricCard
          label="Expected recoverable value"
          value={formatInrCompact(kpis.expected_recoverable_value)}
          hint="Predicted: amount at risk × recovery probability"
          icon={Sparkles}
        />
        <MetricCard
          label="Actual recovered"
          value={
            dashboard.funnel.actual_recovered_available
              ? formatInrCompact(kpis.actual_recovered)
              : "Unavailable"
          }
          hint={
            dashboard.funnel.actual_recovered_available
              ? "Observed from simulated agent workflows"
              : "No agent workflows persisted yet"
          }
          icon={Target}
        />
        <MetricCard
          label="Observed event recovery rate"
          value={formatPct(observedRate ?? null)}
          hint="Recovered ÷ (recovered + not recovered) among agent outcomes. Not amount at risk."
          icon={ShieldAlert}
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Recoverability coverage"
          value={formatPct(coverage ?? null)}
          hint="Share of open events classified RECOVERABLE"
        />
        <MetricCard
          label="High / critical events"
          value={String(kpis.high_critical_events ?? 0)}
          hint="Priority score, not recoverability"
        />
        <MetricCard
          label="No-action open events"
          value={String(kpis.no_action_open_events ?? 0)}
          hint="Intervention not justified from current signals"
        />
        <MetricCard
          label="Blocked actions"
          value={String(kpis.blocked_actions ?? 0)}
          hint="Observed agent guardrail blocks"
        />
      </div>

      <ChartCard
        title="Revenue recovery funnel"
        description="At-risk amount is not the same as predicted recoverable value or money actually recovered."
      >
        <ChartOrEmpty
          empty={!funnelData.some((row) => row.available && (row.value ?? 0) > 0)}
          label="No open-book amounts to chart."
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={funnelData} layout="vertical" margin={{ left: 28, right: 16 }}>
              <CartesianGrid horizontal={false} stroke={GRID} />
              <XAxis type="number" tickFormatter={(v: number) => formatInrCompact(v)} tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="name" width={170} tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(value, _name, item) => {
                  const available = (item?.payload as { available?: boolean } | undefined)?.available
                  if (!available) return ["Unavailable", ""]
                  return [formatInr(Number(value ?? 0)), ""]
                }}
              />
              <Bar dataKey="value" fill={NAVY} radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartOrEmpty>
      </ChartCard>

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartCard
          title="Events by risk level"
          description="Count of open events. Amounts are on the adjacent chart so units stay separate."
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={dashboard.risk_by_level}>
              <CartesianGrid vertical={false} stroke={GRID} />
              <XAxis dataKey="key" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" name="Events" fill={NAVY} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard
          title="Amount at risk by risk level"
          description="Rupees at risk for open events in each priority band."
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={dashboard.risk_by_level}>
              <CartesianGrid vertical={false} stroke={GRID} />
              <XAxis dataKey="key" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={(v: number) => formatInrCompact(v)} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(value) => formatInr(Number(value ?? 0))} />
              <Bar dataKey="amount" name="At risk" fill={SLATE} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <ChartCard
        title="Recoverability distribution"
        description="The agent does not treat every event as recoverable. Already-resolved counts come from dataset event status."
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={dashboard.recoverability} layout="vertical" margin={{ left: 16 }}>
            <CartesianGrid horizontal={false} stroke={GRID} />
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="key" width={150} tickFormatter={(v: string) => humanize(v)} tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(value, name) =>
                name === "count" ? [value, "Events"] : [formatInr(Number(value ?? 0)), "Amount at risk"]
              }
              labelFormatter={(label) => humanize(String(label))}
            />
            <Bar dataKey="count" name="count" fill={NAVY} radius={[0, 3, 3, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Recovery performance by action"
        description="Observed event recovery rate among resolved attempts. A 100% rate on a handful of executions is not a statistical claim."
        flush
      >
        {dashboard.actions.length === 0 ? (
          <EmptyState
            title="No action outcomes yet"
            description="Run the recovery agent on an event to record simulated outcomes."
          />
        ) : (
          <div className="space-y-4">
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={dashboard.actions.map((row) => ({
                    action: humanize(row.action_type),
                    rate: row.observed_recovery_rate == null ? null : Math.round(row.observed_recovery_rate * 100),
                    executions: row.execution_count,
                    recovered: row.amount_recovered,
                    confidence: row.confidence_label,
                    lowSample: row.low_sample_size,
                  }))}
                  layout="vertical"
                  margin={{ left: 20 }}
                >
                  <CartesianGrid horizontal={false} stroke={GRID} />
                  <XAxis type="number" domain={[0, 100]} tickFormatter={(v: number) => `${v}%`} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="action" width={140} tick={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={(value) => [`${value ?? "—"}%`, "Observed recovery rate"]}
                    labelFormatter={(label, payload) => {
                      const row = payload?.[0]?.payload as {
                        executions?: number
                        confidence?: string
                        recovered?: number
                      }
                      return `${label} · ${row?.executions ?? 0} executions · ${row?.confidence ?? ""}`
                    }}
                  />
                  <Bar dataKey="rate" fill={NAVY} radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="pb-2 font-medium">Action</th>
                    <th className="pb-2 font-medium">Observed rate</th>
                    <th className="pb-2 font-medium">Executions</th>
                    <th className="pb-2 font-medium">Amount recovered</th>
                    <th className="pb-2 font-medium">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.actions.map((row) => (
                    <tr key={row.action_type} className="border-t border-border">
                      <td className="py-2">{humanize(row.action_type)}</td>
                      <td className="py-2 tabular-nums">{formatPct(row.observed_recovery_rate)}</td>
                      <td className="py-2 tabular-nums">{row.execution_count}</td>
                      <td className="py-2 tabular-nums">{formatInr(row.amount_recovered)}</td>
                      <td className="py-2 text-xs text-muted-foreground">{row.confidence_label}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </ChartCard>

      <ChartCard
        title="Revenue at risk by failure reason"
        description="Where open-book revenue loss is concentrated."
      >
        {dashboard.failure_reasons.length === 0 ? (
          <EmptyState title="No failure reasons" description="The active dataset has no open events." />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={dashboard.failure_reasons} layout="vertical" margin={{ left: 12 }}>
              <CartesianGrid horizontal={false} stroke={GRID} />
              <XAxis type="number" tickFormatter={(v: number) => formatInrCompact(v)} tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="key" width={130} tickFormatter={(v: string) => humanize(v)} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(value) => formatInr(Number(value ?? 0))} labelFormatter={(label) => humanize(String(label))} />
              <Bar dataKey="amount" name="At risk" fill={NAVY} radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </ChartCard>

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartCard
          title="Predicted vs actual recovery"
          description={`Grouped by ${dashboard.predicted_vs_actual_grouping}. Predicted is model ERV on those workflows; actual is observed recovered amount.`}
        >
          {dashboard.predicted_vs_actual.length === 0 ? (
            <EmptyState
              title="No workflow comparisons yet"
              description="Predicted vs actual appears after agent runs are persisted."
            />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dashboard.predicted_vs_actual}>
                <CartesianGrid vertical={false} stroke={GRID} />
                <XAxis dataKey="key" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={(v: number) => formatInrCompact(v)} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(value) => formatInr(Number(value ?? 0))} />
                <Legend />
                <Bar dataKey="predicted_recoverable_value" name="Predicted ERV" fill={SLATE} radius={[3, 3, 0, 0]} />
                <Bar dataKey="actual_recovered" name="Actual recovered" fill={GREEN} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
        <ChartCard
          title="Workflow outcome distribution"
          description="Includes no-action and blocked results so execution is not assumed."
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={dashboard.outcomes} layout="vertical" margin={{ left: 8 }}>
              <CartesianGrid horizontal={false} stroke={GRID} />
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="key" width={120} tickFormatter={(v: string) => humanize(v)} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill={NAVY} radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <ChartCard
        title="Recent recovery activity"
        description="Attempts, successes, and rupees recovered from persisted workflow timestamps."
      >
        {dashboard.activity_trend_available ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={dashboard.activity_trend}>
              <CartesianGrid stroke={GRID} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="left" allowDecimals={false} tick={{ fontSize: 11 }} />
              <YAxis yAxisId="right" orientation="right" tickFormatter={(v: number) => formatInrCompact(v)} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="recovery_attempts" name="Attempts" stroke={NAVY} dot={false} />
              <Line yAxisId="left" type="monotone" dataKey="successful_recoveries" name="Recovered events" stroke={GREEN} dot={false} />
              <Line yAxisId="right" type="monotone" dataKey="amount_recovered" name="Amount recovered" stroke={SLATE} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <EmptyState
            title="Not enough history for a trend"
            description={dashboard.activity_trend_reason || "Need at least two dated workflow days."}
          />
        )}
      </ChartCard>

      <ChartCard
        title="Top recovery opportunities"
        description="Ranked by existing priority / expected recoverable value. Financial context is shown with each event."
        flush
      >
        {dashboard.top_opportunities.length === 0 ? (
          <EmptyState title="No open opportunities" description="Upload or generate a dataset with open events." />
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dashboard.top_opportunities} layout="vertical" margin={{ left: 8 }}>
                <CartesianGrid horizontal={false} stroke={GRID} />
                <XAxis type="number" tickFormatter={(v: number) => formatInrCompact(v)} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="event_id" width={100} tick={{ fontSize: 10 }} />
                <Tooltip
                  formatter={(value, name) => [formatInr(Number(value ?? 0)), name === "expected_recovery_value" ? "ERV" : "At risk"]}
                  labelFormatter={(label, payload) => {
                    const row = payload?.[0]?.payload as MetricsDashboardResponse["top_opportunities"][number]
                    return `${label} · ${row?.customer_id ?? ""} · ${row?.priority_category ?? ""}`
                  }}
                />
                <Legend />
                <Bar dataKey="amount_at_risk" name="At risk" fill={SLATE} radius={[0, 3, 3, 0]} />
                <Bar dataKey="expected_recovery_value" name="ERV" fill={NAVY} radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </ChartCard>

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-3">
          <div>
            <CardTitle>Opportunity queue</CardTitle>
            <CardDescription>Highest expected recovery first. Open an event to inspect recoverability vs risk.</CardDescription>
          </div>
          <Link to="/app/opportunities" className="shrink-0 text-sm font-medium text-primary hover:underline">
            Open queue
          </Link>
        </CardHeader>
        <CardContent className="px-0 pb-0">
          <OpportunityTable items={items} highlightFirst emptyLabel="No open opportunities in this dataset." />
        </CardContent>
      </Card>
    </div>
  )
}

function ChartCard({
  title,
  description,
  children,
  flush = false,
}: {
  title: string
  description: string
  children: React.ReactNode
  flush?: boolean
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className={flush ? "space-y-4" : "h-64"}>{children}</CardContent>
    </Card>
  )
}

function ChartOrEmpty({
  empty,
  label,
  children,
}: {
  empty: boolean
  label: string
  children: React.ReactNode
}) {
  if (empty) {
    return <p className="text-sm text-muted-foreground">{label}</p>
  }
  return children
}
