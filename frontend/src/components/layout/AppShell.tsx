import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom"
import {
  Activity,
  Database,
  LayoutDashboard,
  RefreshCw,
  Settings,
  Target,
} from "lucide-react"

import { AgentStatus } from "@/components/AgentStatus"
import { BrandMark } from "@/components/BrandMark"
import { Button } from "@/components/ui/button"
import { useWorkspace } from "@/hooks/useWorkspace"
import { logoutDemo } from "@/lib/session"
import { cn } from "@/lib/utils"

const NAV = [
  { to: "/app", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/app/opportunities", label: "Opportunities", icon: Target },
  { to: "/app/activity", label: "Agent Activity", icon: Activity },
  { to: "/app/data", label: "Data", icon: Database },
  { to: "/app/settings", label: "Settings", icon: Settings },
]

const TITLES: Record<string, string> = {
  "/app": "Revenue intelligence",
  "/app/opportunities": "Recovery queue",
  "/app/activity": "Agent activity",
  "/app/data": "Merchant data",
  "/app/settings": "System status",
}

export function AppShell() {
  const location = useLocation()
  const navigate = useNavigate()
  const { health, summary, refresh, refreshing, error } = useWorkspace()
  const title =
    TITLES[location.pathname] ??
    (location.pathname.startsWith("/app/events/") ? "Event investigation" : "Revenue Recovery")

  return (
    <div className="flex min-h-svh bg-background">
      <aside className="hidden w-60 shrink-0 border-r border-border bg-card md:flex md:flex-col">
        <div className="border-b border-border px-5 py-5">
          <BrandMark to="/" />
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                  isActive && "bg-accent text-foreground",
                )
              }
            >
              <item.icon className="size-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-border bg-card px-4 py-3 md:px-6">
          <div>
            <h1 className="text-base font-semibold">{title}</h1>
            <p className="text-xs text-muted-foreground">
              Dataset {summary?.source ?? "—"} · {summary?.open_event_count ?? "—"} open events
            </p>
          </div>
          <div className="flex items-center gap-4">
            <AgentStatus connected={health?.status === "healthy"} />
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void refresh()}
              disabled={refreshing}
            >
              <RefreshCw className={cn("size-3.5", refreshing && "animate-spin")} />
              Refresh
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                logoutDemo()
                navigate("/")
              }}
            >
              Sign out
            </Button>
          </div>
        </header>
        <nav className="flex gap-1 overflow-x-auto border-b border-border px-3 py-2 md:hidden">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "whitespace-nowrap rounded-md px-3 py-1.5 text-xs font-medium text-muted-foreground",
                  isActive && "bg-accent text-foreground",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <main className="flex-1 overflow-auto p-4 md:p-6">
          {error ? (
            <div className="mb-4">
              <p className="rounded-lg border border-destructive/30 bg-card px-4 py-3 text-sm">
                {error} Use Refresh after the API is available.
              </p>
            </div>
          ) : null}
          <Outlet />
        </main>
      </div>
    </div>
  )
}
