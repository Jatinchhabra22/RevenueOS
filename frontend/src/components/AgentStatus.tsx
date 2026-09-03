import { cn } from "@/lib/utils"

export function AgentStatus({
  connected,
  llmUsed,
}: {
  connected: boolean
  llmUsed?: boolean | null
}) {
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="inline-flex items-center gap-1.5">
        <span
          className={cn(
            "size-1.5 rounded-full",
            connected ? "bg-emerald-600" : "bg-destructive",
          )}
        />
        {connected ? "API connected" : "API offline"}
      </span>
      {llmUsed != null ? (
        <span className="text-muted-foreground">
          {llmUsed ? "Local LLM" : "Deterministic fallback"}
        </span>
      ) : (
        <span className="text-muted-foreground">Agent ready</span>
      )}
    </div>
  )
}
