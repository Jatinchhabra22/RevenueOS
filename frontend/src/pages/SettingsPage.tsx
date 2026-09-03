import { useEffect, useState } from "react"

import { fetchAgentHealth } from "@/api/health"
import type { AgentHealthResponse } from "@/api/types"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useWorkspace } from "@/hooks/useWorkspace"
import { apiBaseUrl } from "@/api/client"

export function SettingsPage() {
  const { health, summary, error } = useWorkspace()
  const connected = health?.status === "healthy"
  const [agent, setAgent] = useState<AgentHealthResponse | null>(null)

  useEffect(() => {
    void fetchAgentHealth()
      .then(setAgent)
      .catch(() => setAgent(null))
  }, [])

  return (
    <div className="max-w-2xl space-y-4">
      <div>
        <h2 className="text-lg font-semibold">System status</h2>
        <p className="text-sm text-muted-foreground">
          Configuration is environment-driven. There is no account management in this MVP.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Connection</CardTitle>
          <CardDescription>API base {apiBaseUrl}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <Row label="API" value={connected ? "Connected" : error ?? "Offline"} />
          <Row label="Service" value={health?.service ?? "—"} />
          <Row label="Active dataset" value={summary?.source ?? "—"} />
          <Row label="Dataset ID" value={summary?.dataset_id ?? "—"} />
          <Row label="Configured mode" value={agent?.configured_mode ?? "—"} />
          <Row label="LLM available" value={agent ? (agent.llm_available ? "Yes" : "No") : "—"} />
          <Row label="Provider" value={agent?.provider ?? "none"} />
          <Row label="Model" value={agent?.model ?? "—"} />
          <Row label="Ollama reachable" value={agent ? (agent.ollama_reachable ? "Yes" : "No") : "—"} />
          <Row label="Fallback" value={agent?.fallback_available ? "Available" : "—"} />
          <Row label="Access" value="Demo login only (browser session). Not production auth." />
        </CardContent>
      </Card>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border py-2 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  )
}
