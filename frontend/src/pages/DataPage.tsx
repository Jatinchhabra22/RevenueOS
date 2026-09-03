import { useMemo, useState, type InputHTMLAttributes } from "react"

import { uploadDataset } from "@/api/data"
import { ErrorState } from "@/components/States"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useWorkspace } from "@/hooks/useWorkspace"
import { errorMessage } from "@/lib/format"
import { REQUIRED_TABLES, missingTables, prepareUploadFiles } from "@/lib/uploadFiles"

export function DataPage() {
  const { summary, refresh, error: workspaceError } = useWorkspace()
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const prepared = useMemo(() => prepareUploadFiles(files), [files])
  const missing = prepared.isZip ? [] : missingTables(prepared.found)

  const onUpload = async () => {
    if (!prepared.send.length) {
      setError(
        "Choose a pack folder, a zip, or the five CSV files: customers, transactions, subscriptions, revenue_events, intervention_history.",
      )
      return
    }
    if (!prepared.isZip && !prepared.found.has("revenue_events")) {
      setError(
        `A revenue_events.csv (or .xlsx) file is required. You selected: ${
          files.map((file) => file.name).join(", ") || "nothing"
        }. Open data/upload-tests/tiny_40_customers and select all five CSVs, or use “Choose folder”.`,
      )
      return
    }
    setUploading(true)
    setError(null)
    setMessage(null)
    try {
      const result = await uploadDataset(prepared.send)
      setMessage(
        `Uploaded ${result.dataset_id}. Validation ${result.validation_status}. ` +
          `${result.customer_count} customers · ${result.revenue_event_count} events · ${result.open_event_count} open.`,
      )
      await refresh()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">Merchant data</h2>
        <p className="text-sm text-muted-foreground">
          Uploads replace the running book (not the files in data/demo). Easiest path: choose a
          whole pack folder such as data/upload-tests/tiny_40_customers, or zip that folder.
        </p>
      </div>

      {workspaceError && !summary ? <ErrorState message={workspaceError} onRetry={() => void refresh()} /> : null}

      {summary ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Active dataset" value={summary.source} />
          <Stat label="Customers" value={String(summary.customer_count)} />
          <Stat label="Transactions" value={String(summary.transaction_count)} />
          <Stat label="Subscriptions" value={String(summary.subscription_count)} />
          <Stat label="Revenue events" value={String(summary.revenue_event_count)} />
          <Stat label="Interventions" value={String(summary.intervention_count)} />
          <Stat label="Open events" value={String(summary.open_event_count)} />
          <Stat
            label="Validation"
            value={summary.validation_status === "ok" ? "OK" : "Failed"}
          />
        </div>
      ) : null}

      {summary?.validation_errors.length ? (
        <ErrorState title="Dataset validation issues" message={summary.validation_errors.join("; ")} />
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Upload a merchant pack</CardTitle>
          <CardDescription>
            Required tables: customers, transactions, subscriptions, revenue_events,
            intervention_history. Sidecar files like metadata.json are ignored. 25 MB max per file.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="grid gap-1.5 text-sm">
              <span className="font-medium">Choose folder</span>
              <input
                type="file"
                className="text-sm"
                multiple
                {...({ webkitdirectory: true, directory: true } as InputHTMLAttributes<HTMLInputElement>)}
                onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
              />
            </label>
            <label className="grid gap-1.5 text-sm">
              <span className="font-medium">Or files / zip</span>
              <input
                type="file"
                className="text-sm"
                multiple
                accept=".csv,.xlsx,.zip,application/zip,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"
                onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
              />
            </label>
          </div>

          <ul className="grid gap-1 text-sm sm:grid-cols-2">
            {REQUIRED_TABLES.map((table) => {
              const ok = prepared.isZip || prepared.found.has(table)
              return (
                <li key={table} className={ok ? "text-emerald-800" : "text-muted-foreground"}>
                  {ok ? "✓" : "○"} {table}.csv
                </li>
              )
            })}
          </ul>

          {files.length ? (
            <p className="text-xs text-muted-foreground">
              {files.length} selected
              {prepared.isZip ? " (zip)" : ` · ${prepared.send.length} table files`}
              {missing.length ? ` · still need ${missing.join(", ")}` : ""}
            </p>
          ) : null}

          <Button type="button" disabled={uploading} onClick={() => void onUpload()}>
            {uploading ? "Uploading…" : "Upload and validate"}
          </Button>
          {message ? <p className="text-sm text-emerald-800">{message}</p> : null}
          {error ? <ErrorState title="Upload failed" message={error} /> : null}
        </CardContent>
      </Card>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card className="p-4">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </Card>
  )
}
