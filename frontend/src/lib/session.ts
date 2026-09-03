const SESSION_KEY = "revenueos.demo.session"

export const DEMO_LOGIN = {
  email: "demo@revenueos",
  password: "RevenueOS-Demo",
}

export function isDemoAuthenticated(): boolean {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return false
    const parsed = JSON.parse(raw) as { email?: string }
    return parsed.email === DEMO_LOGIN.email
  } catch {
    return false
  }
}

export function loginDemo(email: string, password: string): boolean {
  const emailOk = email.trim().toLowerCase() === DEMO_LOGIN.email
  const passwordOk = password === DEMO_LOGIN.password
  if (!emailOk || !passwordOk) return false
  localStorage.setItem(
    SESSION_KEY,
    JSON.stringify({ email: DEMO_LOGIN.email, at: new Date().toISOString(), kind: "demo" }),
  )
  return true
}

export function logoutDemo(): void {
  localStorage.removeItem(SESSION_KEY)
}
