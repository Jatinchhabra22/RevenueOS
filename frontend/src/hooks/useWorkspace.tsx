import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react"

import { fetchDatasetSummary } from "@/api/data"
import { fetchHealth } from "@/api/health"
import type { DatasetSummary, HealthResponse } from "@/api/types"
import { errorMessage } from "@/lib/format"

type WorkspaceValue = {
  health: HealthResponse | null
  summary: DatasetSummary | null
  error: string | null
  refreshing: boolean
  epoch: number
  refresh: () => Promise<void>
}

const WorkspaceContext = createContext<WorkspaceValue | null>(null)

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [summary, setSummary] = useState<DatasetSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [epoch, setEpoch] = useState(0)

  const refresh = useCallback(async () => {
    setRefreshing(true)
    setError(null)
    try {
      const [nextHealth, nextSummary] = await Promise.all([fetchHealth(), fetchDatasetSummary()])
      setHealth(nextHealth)
      setSummary(nextSummary)
      setEpoch((value) => value + 1)
    } catch (err) {
      setHealth(null)
      setError(errorMessage(err))
    } finally {
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const value = useMemo(
    () => ({ health, summary, error, refreshing, epoch, refresh }),
    [health, summary, error, refreshing, epoch, refresh],
  )

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
}

export function useWorkspace(): WorkspaceValue {
  const value = useContext(WorkspaceContext)
  if (!value) {
    throw new Error("useWorkspace must be used within WorkspaceProvider")
  }
  return value
}
