import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

const styles: Record<string, string> = {
  CRITICAL: "border-red-200 bg-red-50 text-red-800",
  HIGH: "border-amber-200 bg-amber-50 text-amber-900",
  MEDIUM: "border-sky-200 bg-sky-50 text-sky-900",
  LOW: "border-border bg-muted text-muted-foreground",
}

export function PriorityBadge({
  value,
  className,
}: {
  value: string
  className?: string
}) {
  const key = value.toUpperCase()
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-semibold tracking-wide uppercase",
        styles[key] ?? styles.LOW,
        className,
      )}
    >
      {key}
    </span>
  )
}

export function OutcomeBadge({ value }: { value: string }) {
  const key = value.toUpperCase()
  const tone =
    key === "RECOVERED"
      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
      : key === "BLOCKED" || key === "NOT_RECOVERED"
        ? "border-red-200 bg-red-50 text-red-800"
        : key === "PENDING"
          ? "border-amber-200 bg-amber-50 text-amber-900"
          : "border-border bg-muted text-muted-foreground"
  return (
    <span className={cn("inline-flex rounded border px-2 py-0.5 text-[11px] font-semibold uppercase", tone)}>
      {key.replaceAll("_", " ")}
    </span>
  )
}

export function StatusBadge({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex rounded border border-border bg-muted px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
      {children}
    </span>
  )
}

const recoverabilityStyles: Record<string, string> = {
  RECOVERABLE: "border-emerald-200 bg-emerald-50 text-emerald-800",
  LOW_RECOVERABILITY: "border-amber-200 bg-amber-50 text-amber-900",
  NOT_RECOVERABLE: "border-red-200 bg-red-50 text-red-800",
  ALREADY_RESOLVED: "border-border bg-muted text-muted-foreground",
  ACTION_BLOCKED: "border-red-200 bg-red-50 text-red-800",
  NEEDS_REVIEW: "border-sky-200 bg-sky-50 text-sky-900",
}

export function RecoverabilityBadge({ value }: { value: string }) {
  const key = value.toUpperCase()
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-semibold tracking-wide uppercase",
        recoverabilityStyles[key] ?? recoverabilityStyles.NEEDS_REVIEW,
      )}
    >
      {key.replaceAll("_", " ")}
    </span>
  )
}
