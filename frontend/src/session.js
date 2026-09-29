export const SESSION_KEY = 'enterprise-agent-session'

export const DEFAULT_SESSION = {
  token: 'user-demo-token',
  role: 'user',
  username: 'Alice Smith',
  employee_id: 'EMP-101',
}

export function getStoredSession() {
  try {
    const rawSession = window.localStorage.getItem(SESSION_KEY)
    if (!rawSession) {
      return DEFAULT_SESSION
    }

    const parsed = JSON.parse(rawSession)
    if (parsed && parsed.token && parsed.role) {
      return parsed
    }
  } catch (error) {
    console.warn('Unable to restore session', error)
  }

  return DEFAULT_SESSION
}

export function saveSession(session) {
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

export function clearSession() {
  window.localStorage.removeItem(SESSION_KEY)
}

export function createAuthHeaders(session) {
  const effective = (session && session.token) ? session : DEFAULT_SESSION
  const headers = {
    Authorization: `Bearer ${effective.token}`,
  }

  if (effective.employee_id) {
    headers['X-Employee-Id'] = effective.employee_id
  } else if (effective.role === 'user') {
    headers['X-Employee-Id'] = 'EMP-101'
  }

  return headers
}

export function getUserChatStorageKey(session) {
  if (!session) return null
  if (session.employee_id) {
    return `enterprise_chat_history_${session.employee_id.toUpperCase().trim()}`
  }
  if (session.role === 'admin') {
    return 'enterprise_chat_history_ADMIN'
  }
  return `enterprise_chat_history_${(session.username || 'user').toLowerCase().trim()}`
}

export function loadUserChatSessions(session) {
  const key = getUserChatStorageKey(session)
  if (!key) return []
  try {
    const raw = window.localStorage.getItem(key)
    return raw ? JSON.parse(raw) : []
  } catch (err) {
    console.warn('Unable to load chat sessions', err)
    return []
  }
}

export function saveUserChatSessions(session, sessions) {
  const key = getUserChatStorageKey(session)
  if (!key) return
  try {
    window.localStorage.setItem(key, JSON.stringify(sessions || []))
  } catch (err) {
    console.warn('Unable to save chat sessions', err)
  }
}

