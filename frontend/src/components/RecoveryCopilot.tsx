import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react"
import { LoaderCircle, Lock, Sparkles } from "lucide-react"

import { askRecoveryCopilot } from "@/api/copilot"
import type { CopilotAskResponse } from "@/api/types"
import { errorMessage } from "@/lib/format"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

const QUICK_QUESTIONS = [
  "Why was this action selected?",
  "Why is this event high risk?",
  "Why was the action blocked?",
  "What happened during execution?",
  "What should happen next?",
]

const EMPHASIS =
  /\*\*(.+?)\*\*|₹[\d,]+(?:\.\d+)?|\b\d+(?:\.\d+)?%|\b(?:payment_method_update|retry_now|retry_later|generate_payment_link|send_email|retention_offer|stop_recovery)\b|\bEVT_[A-Z0-9]+\b|\bCUS_[A-Z0-9]+\b|\b(?:CRITICAL|HIGH|MEDIUM|LOW)\b|\b(?:ALLOW|BLOCK)\b|\b(?:RECOVERED|NOT_RECOVERED|PENDING|NO_ACTION|WAITING_FOR_CUSTOMER|WAIT_FOR_CUSTOMER|ESCALATE_TO_MERCHANT|STOP_RECOVERY)\b/gi

export function RecoveryCopilot({ eventId }: { eventId: string }) {
  const [question, setQuestion] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CopilotAskResponse | null>(null)
  const requestId = useRef(0)

  useEffect(() => {
    requestId.current += 1
    setQuestion("")
    setError(null)
    setResult(null)
    setLoading(false)
  }, [eventId])

  const chooseQuestion = (next: string) => {
    setQuestion(next)
    setError(null)
    setResult(null)
  }

  const submit = async () => {
    const trimmed = question.trim()
    if (!trimmed) {
      setError("Enter a question, or pick one of the prompts below.")
      return
    }
    const current = requestId.current + 1
    requestId.current = current
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const next = await askRecoveryCopilot({ event_id: eventId, question: trimmed })
      if (requestId.current !== current) return
      setResult(next)
    } catch (err) {
      if (requestId.current !== current) return
      setResult(null)
      setError(errorMessage(err))
    } finally {
      if (requestId.current === current) setLoading(false)
    }
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault()
      void submit()
    }
  }

  return (
    <Card className="overflow-hidden border-primary/20 shadow-sm">
      <CardHeader className="border-b bg-gradient-to-r from-primary/10 via-card to-card">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Sparkles className="size-4" />
            </span>
            <div>
              <CardTitle className="text-base">Ask Recovery Copilot</CardTitle>
              <CardDescription className="mt-1 max-w-xl">
                Read-only explanation for this event. Choose a prompt, then click Ask Copilot.
                Nothing is executed.
              </CardDescription>
            </div>
          </div>
          <span className="inline-flex items-center gap-1 rounded-full border border-primary/20 bg-primary/5 px-2.5 py-1 text-[11px] font-medium text-primary">
            <Lock className="size-3" />
            Read-only
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-5">
        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Suggested questions
          </p>
          <div className="flex flex-wrap gap-2">
            {QUICK_QUESTIONS.map((item) => {
              const selected = question === item
              return (
                <button
                  key={item}
                  type="button"
                  disabled={loading}
                  onClick={() => chooseQuestion(item)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-left text-xs font-medium transition-colors disabled:opacity-50",
                    selected
                      ? "border-primary bg-primary text-primary-foreground shadow-sm"
                      : "border-border bg-background text-foreground hover:border-primary/40 hover:bg-accent",
                  )}
                >
                  {item}
                </button>
              )
            })}
          </div>
        </div>

        <label className="block space-y-2">
          <span className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Your question
          </span>
          <textarea
            value={question}
            onChange={(event) => {
              setQuestion(event.target.value)
              if (result) setResult(null)
              if (error) setError(null)
            }}
            onKeyDown={onKeyDown}
            rows={3}
            maxLength={800}
            disabled={loading}
            placeholder="Ask why this action was selected, why risk is high, or what happened during execution…"
            className="min-h-[96px] w-full resize-y rounded-lg border border-input bg-muted/30 px-3.5 py-3 text-sm leading-6 outline-none transition-colors placeholder:text-muted-foreground/80 focus-visible:border-primary focus-visible:bg-background focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
          />
        </label>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">⌘ / Ctrl + Enter to ask</p>
          <Button type="button" disabled={loading} onClick={() => void submit()}>
            {loading ? (
              <>
                <LoaderCircle className="size-4 animate-spin" />
                Asking Copilot…
              </>
            ) : (
              <>
                <Sparkles className="size-4" />
                Ask Copilot
              </>
            )}
          </Button>
        </div>

        {error ? (
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        {loading ? (
          <div className="rounded-xl border border-dashed border-primary/25 bg-primary/5 px-5 py-8 text-center">
            <LoaderCircle className="mx-auto size-5 animate-spin text-primary" />
            <p className="mt-3 text-sm font-medium">Writing an explanation from this event’s context…</p>
            <p className="mt-1 text-xs text-muted-foreground">The Copilot is not running a recovery action.</p>
          </div>
        ) : result ? (
          <CopilotAnswerPanel result={result} />
        ) : (
          <div className="rounded-xl border border-dashed border-border bg-muted/20 px-5 py-8 text-center">
            <p className="text-sm font-medium text-foreground">No answer yet</p>
            <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
              Pick a suggested question or type your own, then click Ask Copilot. The previous
              explanation is cleared whenever you change the question.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function CopilotAnswerPanel({ result }: { result: CopilotAskResponse }) {
  const providerLabel = result.fallback_used
    ? "Deterministic fallback"
    : result.provider === "ollama"
      ? "Local LLM"
      : result.provider || "LLM"
  const blocks = result.answer
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean)

  return (
    <div className="overflow-hidden rounded-xl border border-primary/15 bg-gradient-to-b from-primary/10 to-card shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-primary/10 px-5 py-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Explanation</p>
          <p className="mt-0.5 text-xs text-muted-foreground">Based on this event’s workflow context</p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="rounded-full bg-background/80 px-2.5 py-0.5 text-[11px] font-semibold text-foreground ring-1 ring-border">
            {providerLabel}
            {result.model ? ` · ${result.model}` : ""}
          </span>
          <span
            className={cn(
              "rounded-full px-2.5 py-0.5 text-[11px] font-semibold ring-1",
              result.fallback_used
                ? "bg-amber-50 text-amber-900 ring-amber-200"
                : "bg-emerald-50 text-emerald-800 ring-emerald-200",
            )}
          >
            {result.fallback_used ? "Fallback" : "Live model"}
          </span>
        </div>
      </div>

      <div className="space-y-3 px-5 py-4">
        {blocks.map((block, index) => (
          <AnswerBlock key={`${index}-${block.slice(0, 24)}`} text={block} lead={index === 0} />
        ))}
      </div>

      {result.sources.length ? (
        <div className="flex flex-wrap gap-1.5 border-t border-primary/10 bg-background/50 px-5 py-3">
          {result.sources.map((source) => (
            <span
              key={source}
              className="rounded-full bg-background px-2 py-0.5 text-[11px] font-medium text-muted-foreground ring-1 ring-border"
            >
              {source.replaceAll("_", " ")}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function AnswerBlock({ text, lead }: { text: string; lead: boolean }) {
  const facts = /^facts:\s*/i.test(text)
  // Strip any leading "Facts:" prefix the fallback might still emit
  const body = facts ? text.replace(/^facts:\s*/i, "") : text
  // Split on semicolons that appear between sentences (legacy fallback guard)
  const sentences = body
    .split(/;\s*/)
    .map((s) => s.trim())
    .filter(Boolean)
  const unified = sentences.join(" ")

  return (
    <div
      className={cn(
        facts && "rounded-lg border border-border/80 bg-background/70 px-3.5 py-3",
      )}
    >
      {facts ? (
        <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Key facts
        </p>
      ) : null}
      <p
        className={cn(
          "text-sm leading-7 text-foreground/90",
          lead && !facts && "text-[15px] leading-8",
        )}
      >
        {emphasize(unified, lead && !facts)}
      </p>
    </div>
  )
}

function emphasize(text: string, emphasizeFirstSentence: boolean): ReactNode[] {
  const match = emphasizeFirstSentence ? text.match(/^(.+?[.!?])(\s+[\s\S]*)?$/) : null
  if (match) {
    return [
      <strong key="lead" className="font-semibold text-foreground">
        {highlightTokens(match[1])}
      </strong>,
      match[2] ? <span key="rest"> {highlightTokens(match[2].trimStart())}</span> : null,
    ]
  }
  return highlightTokens(text)
}

function highlightTokens(text: string): ReactNode[] {
  const nodes: ReactNode[] = []
  const pattern = new RegExp(EMPHASIS.source, "gi")
  let cursor = 0
  let index = 0
  let match: RegExpExecArray | null
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > cursor) {
      nodes.push(text.slice(cursor, match.index))
    }
    // match[1] is set when the **bold** pattern matched — use inner text
    const label = match[1] !== undefined ? match[1] : match[0]
    nodes.push(
      <strong key={`h-${index}`} className="font-semibold text-foreground">
        {label}
      </strong>,
    )
    index += 1
    cursor = match.index + match[0].length
  }
  if (cursor < text.length) nodes.push(text.slice(cursor))
  return nodes
}
