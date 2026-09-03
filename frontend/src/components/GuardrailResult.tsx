import type { GuardrailResult } from "@/api/types"
import { cn } from "@/lib/utils"

export function GuardrailPanel({ result }: { result: GuardrailResult }) {
  const allowed = result.allowed
  return (
    <div
      className={cn(
        "rounded-lg border p-4",
        allowed ? "border-emerald-200 bg-emerald-50/60" : "border-red-200 bg-red-50/70",
      )}
    >
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        6 · Guardrail
      </p>
      <p className={cn("mt-1 text-lg font-semibold", allowed ? "text-emerald-800" : "text-red-800")}>
        {result.status}
      </p>
      <p className="mt-2 text-sm">{result.reason}</p>
      {result.reason_codes?.length ? (
        <p className="mt-2 text-xs text-muted-foreground">{result.reason_codes.join(" · ")}</p>
      ) : null}
      {result.violations.length ? (
        <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-red-800">
          {result.violations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
