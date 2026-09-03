import { type FormEvent, useMemo, useState } from "react"
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom"

import { BrandMark } from "@/components/BrandMark"
import { Button } from "@/components/ui/button"
import { DEMO_LOGIN, isDemoAuthenticated, loginDemo } from "@/lib/session"

export function LoginPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = params.get("next") || "/app"
  const [email, setEmail] = useState(DEMO_LOGIN.email)
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)

  const safeNext = useMemo(() => (next.startsWith("/app") ? next : "/app"), [next])

  if (isDemoAuthenticated()) {
    return <Navigate to={safeNext} replace />
  }

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!loginDemo(email, password)) {
      setError("Those credentials are not the demo pair. Use the values shown on this page.")
      return
    }
    navigate(safeNext, { replace: true })
  }

  return (
    <div className="grid min-h-svh bg-background lg:grid-cols-2">
      <aside className="relative hidden overflow-hidden bg-primary px-12 py-10 text-primary-foreground lg:flex lg:flex-col">
        <BrandMark inverted />
        <div className="relative z-10 my-auto max-w-md">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-white/55">
            Merchant demo
          </p>
          <h1 className="mt-4 text-4xl font-semibold leading-tight tracking-tight">
            Open the recovery book. Same dataset. Same queue.
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-white/70">
            This is not real authentication. It unlocks the local console on the seeded merchant
            book — including EVT_000861 — so you can walk ingest → predict → rank → agent without
            standing up accounts.
          </p>
          <dl className="mt-10 grid gap-5 text-sm">
            <div>
              <dt className="text-[11px] uppercase tracking-wide text-white/50">After login</dt>
              <dd className="mt-1 font-medium">Overview · /app · data/demo</dd>
            </div>
            <div>
              <dt className="text-[11px] uppercase tracking-wide text-white/50">Lead event</dt>
              <dd className="mt-1 font-medium">EVT_000861 · HIGH · ERV ₹2,714.55</dd>
            </div>
          </dl>
        </div>
        <p className="relative z-10 text-xs text-white/45">Simulated execution · file-first MVP</p>
        <div className="pointer-events-none absolute -right-24 -top-24 size-80 rotate-45 rounded-[32px] bg-white/10" />
        <div className="pointer-events-none absolute -bottom-16 -left-10 size-56 rotate-45 rounded-[28px] bg-white/5" />
      </aside>

      <div className="flex flex-col px-6 py-8 sm:px-10">
        <div className="lg:hidden">
          <BrandMark />
        </div>
        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-10">
          <p className="text-xs font-medium text-muted-foreground">
            <Link to="/" className="hover:text-foreground">
              ← Back to product
            </Link>
          </p>
          <h2 className="mt-6 text-2xl font-semibold tracking-tight">Sign in to the console</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Use the demo pair. After login you land on the live Overview for the current API
            dataset.
          </p>

          <div className="mt-6 rounded-xl border border-border bg-card p-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Demo credentials
            </p>
            <p className="mt-2 font-mono text-sm">{DEMO_LOGIN.email}</p>
            <p className="font-mono text-sm">{DEMO_LOGIN.password}</p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => {
                setEmail(DEMO_LOGIN.email)
                setPassword(DEMO_LOGIN.password)
                setError(null)
              }}
            >
              Fill demo credentials
            </Button>
          </div>

          <form className="mt-6 space-y-4" onSubmit={onSubmit}>
            <label className="grid gap-1.5 text-sm">
              <span className="text-muted-foreground">Email</span>
              <input
                className="h-11 rounded-md border border-input bg-card px-3 outline-none ring-ring focus:ring-2"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <label className="grid gap-1.5 text-sm">
              <span className="text-muted-foreground">Password</span>
              <input
                className="h-11 rounded-md border border-input bg-card px-3 outline-none ring-ring focus:ring-2"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            <Button type="submit" className="h-11 w-full">
              Enter the recovery console
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
