export type ApiErrorBody = {
  error: {
    code: string
    message: string
  }
}

export class ApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(code: string, message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.code = code
    this.status = status
  }
}

export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
)

async function parseError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as ApiErrorBody
    if (body?.error?.code) {
      return new ApiError(body.error.code, body.error.message, response.status)
    }
  } catch {
    /* fall through */
  }
  return new ApiError("HTTP_ERROR", `Request failed with status ${response.status}`, response.status)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}${path}`, init)
  } catch {
    throw new ApiError(
      "NETWORK_ERROR",
      "Cannot reach the API. Start the backend with uvicorn on port 8000.",
      0,
    )
  }
  if (!response.ok) {
    throw await parseError(response)
  }
  try {
    return (await response.json()) as T
  } catch {
    throw new ApiError("INVALID_RESPONSE", "The API returned an unreadable response.", response.status)
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  return request<T>(path)
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  })
}

export async function apiUpload<T>(path: string, files: File[]): Promise<T> {
  const form = new FormData()
  for (const file of files) {
    form.append("files", file)
  }
  return request<T>(path, { method: "POST", body: form })
}
