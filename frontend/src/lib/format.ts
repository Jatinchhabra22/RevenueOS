export function formatInr(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—"
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`
}

export function formatInrCompact(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—"
  if (Math.abs(value) >= 100_000) {
    return `₹${(value / 100_000).toLocaleString("en-IN", { maximumFractionDigits: 2 })}L`
  }
  return formatInr(value)
}

export function formatPct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—"
  return `${Math.round(value * 100)}%`
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function humanize(value: string | null | undefined): string {
  if (!value) return "—"
  return value.replaceAll("_", " ")
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return "Something went wrong."
}
