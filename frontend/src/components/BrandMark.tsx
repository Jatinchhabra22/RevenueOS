import { Link } from "react-router-dom"

import { cn } from "@/lib/utils"

export function BrandMark({
  to = "/",
  compact = false,
  inverted = false,
}: {
  to?: string
  compact?: boolean
  inverted?: boolean
}) {
  return (
    <Link to={to} className="group flex items-center gap-2.5">
      <span
        className={cn(
          "relative flex size-8 shrink-0 items-center justify-center",
          inverted && "opacity-95",
        )}
        aria-hidden
      >
        <span
          className={cn(
            "absolute inset-[2px] rotate-45 rounded-[5px]",
            inverted ? "bg-white" : "bg-primary",
          )}
        />
        <span
          className={cn(
            "relative text-[11px] font-bold leading-none",
            inverted ? "text-primary" : "text-primary-foreground",
          )}
        >
          R
        </span>
      </span>
      <span className="min-w-0">
        <span
          className={cn(
            "block text-[13px] font-semibold leading-none tracking-tight",
            inverted ? "text-white" : "text-foreground",
          )}
        >
          RevenueOS
        </span>
        {compact ? null : (
          <span
            className={cn(
              "mt-1 block text-[11px] leading-none",
              inverted ? "text-white/70" : "text-muted-foreground",
            )}
          >
            Recovery Orchestrator
          </span>
        )}
      </span>
    </Link>
  )
}
