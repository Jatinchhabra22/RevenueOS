import { BrowserRouter, Navigate, Route, Routes, useParams } from "react-router-dom"

import { AppShell } from "@/components/layout/AppShell"
import { RequireDemoAuth } from "@/components/RequireDemoAuth"
import { WorkspaceProvider } from "@/hooks/useWorkspace"
import { AgentActivityPage } from "@/pages/AgentActivityPage"
import { DataPage } from "@/pages/DataPage"
import { EventDetailPage } from "@/pages/EventDetailPage"
import { HomePage } from "@/pages/HomePage"
import { LoginPage } from "@/pages/LoginPage"
import { OpportunitiesPage } from "@/pages/OpportunitiesPage"
import { OverviewPage } from "@/pages/OverviewPage"
import { SettingsPage } from "@/pages/SettingsPage"

export default function App() {
  return (
    <BrowserRouter>
      <WorkspaceProvider>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/opportunities" element={<Navigate to="/app/opportunities" replace />} />
          <Route path="/activity" element={<Navigate to="/app/activity" replace />} />
          <Route path="/data" element={<Navigate to="/app/data" replace />} />
          <Route path="/settings" element={<Navigate to="/app/settings" replace />} />
          <Route path="/events/:eventId" element={<LegacyEventRedirect />} />
          <Route element={<RequireDemoAuth />}>
            <Route element={<AppShell />}>
              <Route path="/app" element={<OverviewPage />} />
              <Route path="/app/opportunities" element={<OpportunitiesPage />} />
              <Route path="/app/events/:eventId" element={<EventDetailPage />} />
              <Route path="/app/activity" element={<AgentActivityPage />} />
              <Route path="/app/data" element={<DataPage />} />
              <Route path="/app/settings" element={<SettingsPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </WorkspaceProvider>
    </BrowserRouter>
  )
}

function LegacyEventRedirect() {
  const { eventId } = useParams()
  return <Navigate to={`/app/events/${eventId ?? ""}`} replace />
}
