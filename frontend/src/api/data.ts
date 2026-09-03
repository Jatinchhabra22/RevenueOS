import { apiGet, apiUpload } from "./client"
import type { DatasetSummary } from "./types"

export function fetchDatasetSummary(): Promise<DatasetSummary> {
  return apiGet<DatasetSummary>("/api/v1/data/summary")
}

export function uploadDataset(files: File[]): Promise<DatasetSummary> {
  return apiUpload<DatasetSummary>("/api/v1/data/upload", files)
}
