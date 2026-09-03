import { useEffect, useMemo, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { LoaderCircle } from "lucide-react"

import { fetchLatestWorkflow, runRecoveryAgent } from "@/api/agent"
import { ApiError } from "@/api/client"
import { fetchEventDetail } from "@/api/events"
import type { AgentWorkflowResponse, EventDetailResponse } from "@/api/types"
import {
  AgentModeBadge,
  DiagnosisPanel,
  RecoveredBanner,
  ReflectionPanel,
  StrategyPanel,
  WorkflowStageList,
} from "@/components/AgentWorkflow"
import { RecoveryCopilot } from "@/components/RecoveryCopilot"
import { ActionCard } from "@/components/ActionCard"
import { AuditTimeline } from "@/components/AuditTimeline"
import { GuardrailPanel } from "@/components/GuardrailResult"
import { PriorityBadge, OutcomeBadge, StatusBadge, RecoverabilityBadge } from "@/components/PriorityBadge"
import { RiskIndicator } from "@/components/ProbabilityBar"
import { ErrorState, LoadingState } from "@/components/States"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useWorkspace } from "@/hooks/useWorkspace"
import { rememberWorkflow } from "@/lib/activity"
import { errorMessage, formatDate, formatInr, formatPct, humanize } from "@/lib/format"

const RUN_STEPS = ["Waiting for the live LangGraph workflow to finish on the API."]

export function EventDetailPage() {
  const { eventId = "" } = useParams()
  const { refresh } = useWorkspace()
  const [detail, setDetail] = useState<EventDetailResponse | null>(null)
  const [workflow, setWorkflow] = useState<AgentWorkflowResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setNotFound(false)
    setWorkflow(null)
    Promise.all([fetchEventDetail(eventId), fetchLatestWorkflow(eventId)])
      .then(([nextDetail, nextWorkflow]) => {
        if (cancelled) return
        setDetail(nextDetail)
        setWorkflow(nextWorkflow)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        if (err instanceof ApiError && err.code === "EVENT_NOT_FOUND") {
          setNotFound(true)
        } else {
          setError(errorMessage(err))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [eventId])

  const risk = detail?.risk_assessment
  const customer = detail?.customer

  const run = async () => {
    setRunning(true)
    setRunError(null)
    setConfirming(false)
    try {
      const result = await runRecoveryAgent(eventId, { force_recompute: false })
      setWorkflow(result)
      rememberWorkflow(result, detail?.event.customer_id)
      await refresh()
    } catch (err) {
      setRunError(errorMessage(err))
    } finally {
      setRunning(false)
    }
  }

  const selectedId = workflow?.selected_action.action_id

  const headerWhy = useMemo(() => {
    if (!risk) return ""
    return `${formatInr(risk.amount_at_risk)} at risk · ${formatPct(risk.recovery_probability)} recovery · ${formatPct(risk.churn_probability)} churn`
  }, [risk])

  if (loading) return <LoadingState label="Loading event context…" />
  if (notFound) {
    return (
      <ErrorState
        title="Event not found"
        message={`Revenue event ${eventId} was not found in the active dataset.`}
      />
    )
  }
  if (error || !detail || !risk) {
    return <ErrorState message={error ?? "Event could not be loaded."} />
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs text-muted-foreground">
            <Link to="/app/opportunities" className="hover:underline">
              Opportunities
            </Link>
            <span> / {detail.event.event_id}</span>
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-semibold">{detail.event.event_id}</h2>
            <PriorityBadge value={risk.priority_category} />
            <StatusBadge>{detail.status}</StatusBadge>
          </div>
          <p className="mt-1 max-w-xl text-sm text-muted-foreground">
            {detail.event.customer_id} · {humanize(detail.event.failure_reason)} · {headerWhy}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          {!confirming && !running ? (
            <Button type="button" onClick={() => setConfirming(true)}>
              Run recovery agent
            </Button>
          ) : null}
        </div>
      </div>

      {confirming ? (
        <Card className="border-primary/30">
          <CardHeader>
            <CardTitle>Run recovery agent?</CardTitle>
            <CardDescription>
              The agent will diagnose this event, choose one eligible action, validate guardrails,
              and execute a simulated intervention. No live payment call is made.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex gap-2">
            <Button type="button" onClick={() => void run()}>
              Confirm run
            </Button>
            <Button type="button" variant="outline" onClick={() => setConfirming(false)}>
              Cancel
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {running ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <LoaderCircle className="size-4 animate-spin" />
              Recovery agent running
            </CardTitle>
            <CardDescription>Waiting for the live API workflow to finish.</CardDescription>
          </CardHeader>
          <CardContent>
            <ol className="space-y-2 text-sm text-muted-foreground">
              {RUN_STEPS.map((step) => (
                <li key={step}>→ {step}</li>
              ))}
            </ol>
          </CardContent>
        </Card>
      ) : null}

      {runError ? <ErrorState title="Agent execution failed" message={runError} /> : null}

      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
        1. What happened → 2. Why it matters → 3. What AI thinks → 4. What it did
      </p>

      <div className="grid gap-4 md:grid-cols-4">
        <Card className="p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">1 · Amount at risk</p>
          <p className="mt-1 text-xl font-semibold tabular-nums">{formatInr(risk.amount_at_risk)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">2 · Expected recovery</p>
          <p className="mt-1 text-xl font-semibold tabular-nums">
            {formatInr(risk.expected_recovery_value)}
          </p>
        </Card>
        <Card className="p-4 md:col-span-2">
          <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Probabilities</p>
          <RiskIndicator recovery={risk.recovery_probability} churn={risk.churn_probability} />
        </Card>
      </div>

      {detail.recoverability ? (
        <Card className="border-primary/20 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Recoverability
            </p>
            <RecoverabilityBadge value={detail.recoverability.classification} />
          </div>
          <p className="mt-2 text-sm font-medium">{detail.recoverability.statement}</p>
          <p className="mt-1 text-sm text-muted-foreground">{detail.recoverability.reason}</p>
          <p className="mt-2 text-xs text-muted-foreground">
            At risk {formatInr(detail.recoverability.amount_at_risk)} · recovery{" "}
            {formatPct(detail.recoverability.recovery_probability)} · ERV{" "}
            {formatInr(detail.recoverability.expected_recovery_value)}.{" "}
            {detail.recoverability.pursue
              ? "Intervention is justified if an eligible action passes guardrails."
              : "No recovery action should be executed from these signals."}
          </p>
        </Card>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>2 · Why it matters</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 text-sm">
            <Info label="LTV" value={formatInr(customer?.customer_ltv ?? risk.customer_ltv)} />
            <Info label="Tenure" value={customer?.tenure_days != null ? `${customer.tenure_days} days` : "—"} />
            <Info label="Engagement" value={humanize(customer?.activity_trend)} />
            <Info
              label="Payment success"
              value={customer?.payment_success_rate != null ? formatPct(customer.payment_success_rate) : "—"}
            />
            <Info label="Previous failures" value={String(customer?.previous_failures ?? "—")} />
            <Info
              label="Subscription"
              value={
                detail.subscription
                  ? `${humanize(detail.subscription.subscription_status)} · ${formatInr(detail.subscription.recurring_amount)}`
                  : "None"
              }
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>1 · What happened</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 text-sm">
            <Info label="Type" value={humanize(detail.event.event_type)} />
            <Info label="Payment method" value={humanize(detail.event.payment_method)} />
            <Info label="Attempt" value={String(detail.event.attempt_number ?? "—")} />
            <Info label="Urgency" value={humanize(detail.event.urgency)} />
            <Info label="Timestamp" value={formatDate(detail.event.event_timestamp)} />
            <Info label="Score" value={risk.priority_score.toFixed(1)} />
          </CardContent>
        </Card>
      </div>

      {!workflow ? (
        <EmptyAgent />
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <AgentModeBadge workflow={workflow} />
            <p className="text-xs text-muted-foreground">
              {workflow.iterations ?? 1} iteration{(workflow.iterations ?? 1) === 1 ? "" : "s"} ·{" "}
              {workflow.workflow_status || workflow.status}
            </p>
          </div>
          <RecoveredBanner workflow={workflow} />
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>AI recovery workflow</CardTitle>
                <CardDescription>Stages recorded by the live backend run.</CardDescription>
              </CardHeader>
              <CardContent>
                <WorkflowStageList workflow={workflow} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Diagnosis</CardTitle>
                <CardDescription>
                  Source: {workflow.diagnosis.source === "llm" ? "LLM" : "deterministic fallback"}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <DiagnosisPanel workflow={workflow} />
              </CardContent>
            </Card>
          </div>
          <Card>
            <CardHeader>
              <CardTitle>3 · AI diagnosis</CardTitle>
              <CardDescription>
                Workflow {workflow.workflow_id}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <Info label="Primary issue" value={workflow.diagnosis.primary_issue} />
              <Info label="Recoverability" value={workflow.diagnosis.recoverability_reason} />
              <Info label="Churn concern" value={workflow.diagnosis.churn_concern} />
              <Info label="Recommended strategy" value={workflow.diagnosis.recommended_strategy} />
            </CardContent>
          </Card>

          <section className="space-y-3">
            <h3 className="text-sm font-semibold">4 · Actions considered</h3>
            <div className="grid gap-3 md:grid-cols-2">
              {workflow.candidate_actions.map((action) => (
                <ActionCard
                  key={action.action_id}
                  action={action}
                  selected={action.action_id === selectedId}
                />
              ))}
            </div>
            <p className="text-sm">
              <span className="font-medium">5 · Chose {humanize(workflow.selected_action.action_type)}.</span>{" "}
              <span className="text-muted-foreground">{workflow.decision.reason}</span>
            </p>
            <StrategyPanel workflow={workflow} />
          </section>

          <div className="grid gap-4 lg:grid-cols-2">
            <GuardrailPanel result={workflow.guardrail_result} />
            <Card className="p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                7 · Execution
              </p>
              {workflow.execution_result ? (
                <dl className="mt-2 space-y-2 text-sm">
                  <Info label="Action" value={humanize(workflow.execution_result.action_type)} />
                  <Info label="Execution ID" value={workflow.execution_result.execution_id} />
                  <Info label="Status" value={workflow.execution_result.status} />
                  <Info label="Timestamp" value={formatDate(workflow.execution_result.timestamp)} />
                  <p className="text-muted-foreground">{workflow.execution_result.message}</p>
                </dl>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">No execution — blocked or skipped.</p>
              )}
            </Card>
          </div>

          <Card className="p-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Reflection
            </p>
            <ReflectionPanel workflow={workflow} />
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                8 · Outcome
              </p>
              {workflow.outcome ? <OutcomeBadge value={workflow.outcome.outcome} /> : null}
            </div>
            {workflow.outcome ? (
              <div className="mt-3 grid gap-3 sm:grid-cols-3 text-sm">
                <Info label="Amount recovered" value={formatInr(workflow.outcome.amount_recovered)} />
                <Info
                  label="Remaining at risk"
                  value={formatInr(workflow.outcome.remaining_amount_at_risk)}
                />
                <Info label="Final decision" value={workflow.final_decision} />
                <p className="sm:col-span-3 text-muted-foreground">{workflow.outcome.explanation}</p>
              </div>
            ) : (
              <p className="mt-2 text-sm text-muted-foreground">Outcome not recorded.</p>
            )}
          </Card>

          {workflow.outcome ? (
            <Card className="p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Expected vs observed
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                One execution does not validate or invalidate the recovery model. Compare in aggregate on Overview.
              </p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
                <Info label="Recovery probability" value={formatPct(workflow.recovery_prediction.probability)} />
                <Info label="Agent outcome" value={workflow.outcome.outcome} />
                <Info label="Expected recovery" value={formatInr(workflow.risk_assessment.expected_recovery_value)} />
                <Info label="Observed recovery" value={formatInr(workflow.outcome.amount_recovered)} />
              </div>
              {workflow.decision.historical_note && (workflow.decision.informed_by_observations ?? 0) > 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">{workflow.decision.historical_note}</p>
              ) : null}
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>9 · Audit timeline</CardTitle>
              <CardDescription>
                Context → Diagnosis → Prediction → Risk → Decision → Guardrail → Execution → Outcome
              </CardDescription>
            </CardHeader>
            <CardContent>
              <AuditTimeline entries={workflow.audit_trail} />
            </CardContent>
          </Card>
        </>
      )}

      <RecoveryCopilot eventId={eventId} />
    </div>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  )
}

function EmptyAgent() {
  return (
    <Card className="p-5">
      <p className="text-sm font-medium">Agent has not run on this event</p>
      <p className="mt-1 text-sm text-muted-foreground">
        Predictions and ranking are already available. Run the recovery agent to generate a diagnosis,
        choose an intervention, and record a simulated outcome.
      </p>
    </Card>
  )
}
