import { Navigate, Outlet, useLocation } from "react-router-dom"

import { isDemoAuthenticated } from "@/lib/session"

export function RequireDemoAuth() {
  const location = useLocation()
  if (!isDemoAuthenticated()) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${next}`} replace />
  }
  return <Outlet />
}
