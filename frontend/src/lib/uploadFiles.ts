const TABLE_STEMS: Record<string, string> = {
  customers: "customers",
  customer: "customers",
  users: "customers",
  transactions: "transactions",
  transaction: "transactions",
  payments: "transactions",
  subscriptions: "subscriptions",
  subscription: "subscriptions",
  revenue_events: "revenue_events",
  events: "revenue_events",
  revenueevents: "revenue_events",
  intervention_history: "intervention_history",
  interventions: "intervention_history",
  actions: "intervention_history",
}

export const REQUIRED_TABLES = [
  "customers",
  "transactions",
  "subscriptions",
  "revenue_events",
  "intervention_history",
] as const

export type RequiredTable = (typeof REQUIRED_TABLES)[number]

function basename(file: File): string {
  const relative = (file as File & { webkitRelativePath?: string }).webkitRelativePath
  const raw = relative || file.name
  return raw.replace(/\\/g, "/").split("/").pop() || file.name
}

export function tableFromFile(file: File): RequiredTable | "zip" | null {
  const name = basename(file).toLowerCase()
  if (name.endsWith(".zip")) return "zip"
  const stem = name.replace(/\.(csv|xlsx)$/i, "").replace(/-/g, "_").replace(/ /g, "_")
  const table = TABLE_STEMS[stem]
  return (table as RequiredTable | undefined) ?? null
}

export function prepareUploadFiles(files: File[]): { send: File[]; found: Set<string>; isZip: boolean } {
  const found = new Set<string>()
  const send: File[] = []
  let isZip = false
  for (const file of files) {
    const kind = tableFromFile(file)
    if (kind === "zip") {
      isZip = true
      send.push(file)
      continue
    }
    if (!kind) continue
    found.add(kind)
    send.push(file)
  }
  return { send, found, isZip }
}

export function missingTables(found: Set<string>): string[] {
  return REQUIRED_TABLES.filter((name) => !found.has(name))
}
