export const SESSION_KEY = 'enterprise-agent-session'

export function getStoredSession() {
  try {
    const rawSession = window.localStorage.getItem(SESSION_KEY)
    if (!rawSession) {
      return null
    }

    const parsed = JSON.parse(rawSession)
    if (parsed && parsed.token && parsed.role) {
      return parsed
    }
  } catch (error) {
    console.warn('Unable to restore session', error)
  }

  return null
}

export function saveSession(session) {
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

export function clearSession() {
  window.localStorage.removeItem(SESSION_KEY)
}

export function createAuthHeaders(session) {
  if (!session?.token) {
    return {}
  }

  return {
    Authorization: `Bearer ${session.token}`,
  }
}
