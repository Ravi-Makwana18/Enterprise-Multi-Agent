import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { clearSession, createAuthHeaders, getStoredSession, saveSession } from './session'

// ─── SVG Icon components ─────────────────────────────────────────────
const Icon = {
  Dashboard: () => (
    <svg className="nav-icon" viewBox="0 0 20 20" fill="currentColor">
      <path d="M2 10a8 8 0 018-8v8h8a8 8 0 11-16 0z" />
      <path d="M12 2.252A8.014 8.014 0 0117.748 8H12V2.252z" />
    </svg>
  ),
  Chat: () => (
    <svg className="nav-icon" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
    </svg>
  ),
  Ticket: () => (
    <svg className="nav-icon" viewBox="0 0 20 20" fill="currentColor">
      <path d="M2 6a2 2 0 012-2h12a2 2 0 012 2v2a2 2 0 100 4v2a2 2 0 01-2 2H4a2 2 0 01-2-2v-2a2 2 0 100-4V6z" />
    </svg>
  ),
  Review: () => (
    <svg className="nav-icon" viewBox="0 0 20 20" fill="currentColor">
      <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
      <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
    </svg>
  ),
  Workflow: () => (
    <svg className="nav-icon" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
    </svg>
  ),
  Logout: () => (
    <svg className="nav-icon" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M3 3a1 1 0 00-1 1v12a1 1 0 102 0V4a1 1 0 00-1-1zm10.293 9.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L14.586 9H7a1 1 0 100 2h7.586l-1.293 1.293z" clipRule="evenodd" />
    </svg>
  ),
  Send: () => (
    <svg style={{ width: 16, height: 16 }} viewBox="0 0 20 20" fill="currentColor">
      <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
    </svg>
  ),
  Collapse: () => (
    <svg style={{ width: 16, height: 16 }} viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
    </svg>
  ),
  Expand: () => (
    <svg style={{ width: 16, height: 16 }} viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
    </svg>
  ),
  Plus: () => (
    <svg style={{ width: 16, height: 16 }} viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
    </svg>
  ),
  Trash: () => (
    <svg style={{ width: 13, height: 13 }} viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
    </svg>
  ),
  MessageBubble: () => (
    <svg style={{ width: 14, height: 14, flexShrink: 0 }} viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7z" clipRule="evenodd" />
    </svg>
  ),
}

// ─── Nav tab definitions (with icons) ────────────────────────────────
const NAV_TABS_ADMIN = [
  { id: 'dashboard',  label: 'Dashboard',        icon: Icon.Dashboard },
  { id: 'chat',       label: 'AI Assistant',      icon: Icon.Chat },
  { id: 'tickets',    label: 'Tickets',           icon: Icon.Ticket },
  { id: 'reviews',    label: 'Reviews',           icon: Icon.Review },
  { id: 'workflow',   label: 'Workflow History',  icon: Icon.Workflow },
]
const NAV_TABS_USER = [
  { id: 'dashboard',  label: 'Dashboard',   icon: Icon.Dashboard },
  { id: 'chat',       label: 'AI Assistant', icon: Icon.Chat },
  { id: 'tickets',    label: 'Tickets',      icon: Icon.Ticket },
  { id: 'reviews',    label: 'Reviews',      icon: Icon.Review },
]

// ─── Metric card icons / colors ───────────────────────────────────────
const METRIC_CONFIG = [
  { label: 'Open Tickets',     emoji: '🎫', gradient: 'linear-gradient(135deg,rgba(99,102,241,.18),rgba(99,102,241,.08))' },
  { label: 'Review Items',     emoji: '📋', gradient: 'linear-gradient(135deg,rgba(6,182,212,.18),rgba(6,182,212,.08))'  },
  { label: 'Security Checks',  emoji: '🔒', gradient: 'linear-gradient(135deg,rgba(245,158,11,.18),rgba(245,158,11,.08))'},
  { label: 'Workflow States',  emoji: '⚙️', gradient: 'linear-gradient(135deg,rgba(16,185,129,.18),rgba(16,185,129,.08))'},
]


// ─── Form defaults ────────────────────────────────────────────────────
const defaultTicketForm   = { summary: '', category: 'general', priority: 'normal', requester: '', assignee: '' }
const defaultReviewForm   = { title: '', reviewer: '', status: 'pending', content: '' }
const defaultApprovalForm = { title: '', reviewer: '', decision: 'approved', comments: '' }

// ─── Helpers ──────────────────────────────────────────────────────────
function formatPayload(value) {
  if (!value) return 'No data returned.'
  if (typeof value === 'string') return value
  try { return JSON.stringify(value, null, 2) } catch { return String(value) }
}

function safeArray(value) {
  return Array.isArray(value) ? value : []
}

function extractErrorMessage(error) {
  if (error instanceof Error && error.message) return error.message
  return 'Something went wrong while contacting the service.'
}

async function requestJson(url, options = {}, session) {
  if (!url.startsWith('/api/')) throw new Error('Invalid request path.')
  const headers = {
    ...(options.headers || {}),
    ...createAuthHeaders(session),
  }
  if (!(options.body instanceof FormData) && options.body !== undefined && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }
  const response = await fetch(url, { ...options, headers })
  const contentType = response.headers.get('content-type') || ''
  let payload = null
  if (contentType.includes('application/json')) {
    payload = await response.json()
  } else if (response.status !== 204) {
    payload = await response.text()
  }
  if (!response.ok) {
    const message =
      payload && typeof payload === 'object'
        ? payload?.error?.message || payload?.detail?.error?.message || payload?.detail || 'Request failed.'
        : 'Request failed.'
    throw new Error(message)
  }
  return payload
}

function AgentResponse({ reply }) {
  const data = reply.response || {};
  const message = data.message || data.content || data.blog_content || data.revised_content || data.summary || data.result || null;
  const issues = Array.isArray(data.issues) ? data.issues : [];
  const recommendations = Array.isArray(data.recommendations) ? data.recommendations : [];
  const ticketId = data.ticket_id || data.id || null;
  const score = reply.score ?? data.score ?? null;
  const riskLevel = data.risk_level || null;
  const requiresHumanReview = data.requires_human_review || false;
  const isBlog = !!data.blog_content;

  return (
    <div className="agent-response">
      {message && <p className="agent-message">{message}</p>}
      {ticketId && (
        <div className="agent-meta-row">
          <span className="meta-label">Ticket ID</span>
          <span className="meta-value">{ticketId}</span>
        </div>
      )}
      {score !== null && (
        <div className="agent-meta-row">
          <span className="meta-label">Confidence</span>
          <span className="meta-value">{score} / 100</span>
        </div>
      )}
      {riskLevel && (
        <div className="agent-meta-row">
          <span className="meta-label">Risk Level</span>
          <span className={`status-badge ${riskLevel === 'low' ? 'success' : riskLevel === 'medium' ? 'neutral' : 'danger'}`}>{riskLevel}</span>
        </div>
      )}
      {requiresHumanReview && (
        <div className="agent-alert">⚠ Human review required before acting on this response.</div>
      )}
      {!isBlog && issues.length > 0 && (
        <div className="agent-section">
          <p className="agent-section-title">Issues found</p>
          <ul className="agent-list">{issues.map((item, i) => <li key={i}>{item}</li>)}</ul>
        </div>
      )}
      {!isBlog && recommendations.length > 0 && (
        <div className="agent-section">
          <p className="agent-section-title">Recommendations</p>
          <ul className="agent-list">{recommendations.map((item, i) => <li key={i}>{item}</li>)}</ul>
        </div>
      )}
      {!message && !ticketId && issues.length === 0 && recommendations.length === 0 && (
        <pre className="agent-raw">{formatPayload(data)}</pre>
      )}
    </div>
  );
}

// ─── Live clock ───────────────────────────────────────────────────────
function LiveClock() {
  const [time, setTime] = useState(new Date())
  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return (
    <span className="system-time">
      {time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
    </span>
  )
}

// ─── App ──────────────────────────────────────────────────────────────
function App() {
  const [session, setSession]       = useState(getStoredSession())
  const [activeView, setActiveView] = useState('dashboard')
  const [loginForm, setLoginForm]   = useState({ role: 'user', token: 'user-demo-token' })
  const [authError, setAuthError]   = useState('')

  const [overview, setOverview] = useState({ tickets: [], reviews: [], securityChecks: [], workflows: [] })
  const [overviewState, setOverviewState] = useState({ loading: false, error: '' })

  const [chatInput, setChatInput] = useState('')
  const [chatState, setChatState] = useState({ loading: false, error: '', messages: [] })

  const [sidebarExpanded, setSidebarExpanded] = useState(() => {
    try {
      const saved = localStorage.getItem('enterprise_sidebar_expanded')
      return saved !== null ? saved === 'true' : true
    } catch {
      return true
    }
  })

  const [chatSessions, setChatSessions] = useState(() => {
    try {
      const saved = localStorage.getItem('enterprise_agent_chat_sessions')
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })
  const [activeSessionId, setActiveSessionId] = useState(null)

  function toggleSidebar() {
    setSidebarExpanded((prev) => {
      const next = !prev
      try { localStorage.setItem('enterprise_sidebar_expanded', String(next)) } catch {}
      return next
    })
  }

  function handleNewChat() {
    setActiveSessionId(null)
    setChatState({ loading: false, error: '', messages: [] })
    setChatInput('')
    setActiveView('chat')
  }

  function handleSelectSession(sessionItem) {
    setActiveSessionId(sessionItem.id)
    setChatState({ loading: false, error: '', messages: sessionItem.messages || [] })
    setChatInput('')
    setActiveView('chat')
  }

  function handleDeleteSession(e, sessionId) {
    e.stopPropagation()
    setChatSessions((prev) => {
      const filtered = prev.filter((s) => s.id !== sessionId)
      try { localStorage.setItem('enterprise_agent_chat_sessions', JSON.stringify(filtered)) } catch {}
      return filtered
    })
    if (activeSessionId === sessionId) {
      setActiveSessionId(null)
      setChatState({ loading: false, error: '', messages: [] })
    }
  }

  const [ticketForm, setTicketForm]     = useState(defaultTicketForm)
  const [ticketState, setTicketState]   = useState({ loading: false, error: '', success: '' })

  const [reviewForm, setReviewForm]     = useState(defaultReviewForm)
  const [reviewState, setReviewState]   = useState({ loading: false, error: '', success: '' })

  const [approvalForm, setApprovalForm]   = useState(defaultApprovalForm)
  const [approvalState, setApprovalState] = useState({ loading: false, error: '', success: '' })

  const roleTabs = useMemo(
    () => session?.role === 'admin' ? NAV_TABS_ADMIN : NAV_TABS_USER,
    [session?.role],
  )

  const dashboardSummary = useMemo(
    () => [
      { ...METRIC_CONFIG[0], value: safeArray(overview.tickets).length },
      { ...METRIC_CONFIG[1], value: safeArray(overview.reviews).length },
      { ...METRIC_CONFIG[2], value: safeArray(overview.securityChecks).length },
      { ...METRIC_CONFIG[3], value: safeArray(overview.workflows).length },
    ],
    [overview],
  )

  useEffect(() => { if (session) loadOverview() }, [session])

  async function loadOverview() {
    if (!session) return
    setOverviewState({ loading: true, error: '' })
    try {
      const [tickets, reviews, securityChecks, workflows] = await Promise.all([
        requestJson('/api/tickets', { method: 'GET' }, session),
        requestJson('/api/reviews', { method: 'GET' }, session),
        requestJson('/api/security-checks', { method: 'GET' }, session),
        session.role === 'admin' ? requestJson('/api/workflow-states', { method: 'GET' }, session) : Promise.resolve([]),
      ])
      setOverview({
        tickets: safeArray(tickets),
        reviews: safeArray(reviews),
        securityChecks: safeArray(securityChecks),
        workflows: safeArray(workflows),
      })
      setOverviewState({ loading: false, error: '' })
    } catch (error) {
      const msg = extractErrorMessage(error)
      if (msg.toLowerCase().includes('valid api token required')) {
        clearSession()
        setSession(null)
        setAuthError('Your token was invalid or expired. Please use user-demo-token or admin-demo-token.')
        return
      }
      setOverviewState({ loading: false, error: msg })
    }
  }

  async function submitChat(rawMessage) {
    const message = rawMessage.trim()
    if (!message || message.length < 3) {
      setChatState((p) => ({ ...p, loading: false, error: 'Please enter at least 3 characters.' }))
      return
    }
    setChatState((p) => ({ ...p, loading: true, error: '' }))
    try {
      const data = await requestJson('/api/chat', { method: 'POST', body: JSON.stringify({ message }) }, session)
      const newMsg = { input: message, reply: data }
      
      setChatState((p) => ({
        loading: false,
        error: '',
        messages: [newMsg, ...(p.messages || [])],
      }))
      setChatInput('')

      // Sync with chat history sessions
      setChatSessions((prevSessions) => {
        let targetId = activeSessionId
        let updated
        const existingIdx = targetId ? prevSessions.findIndex((s) => s.id === targetId) : -1
        
        if (existingIdx >= 0) {
          updated = prevSessions.map((s, idx) =>
            idx === existingIdx
              ? { ...s, messages: [newMsg, ...(s.messages || [])], updatedAt: new Date().toISOString() }
              : s
          )
        } else {
          targetId = `session_${Date.now()}`
          setActiveSessionId(targetId)
          const title = message.length > 28 ? message.slice(0, 28) + '…' : message
          const newSession = {
            id: targetId,
            title,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            messages: [newMsg],
          }
          updated = [newSession, ...prevSessions]
        }
        try {
          localStorage.setItem('enterprise_agent_chat_sessions', JSON.stringify(updated))
        } catch {}
        return updated
      })
    } catch (error) {
      setChatState((p) => ({ ...p, loading: false, error: extractErrorMessage(error) }))
    }
  }

  async function submitTicket(event) {
    event.preventDefault()
    const summary   = ticketForm.summary.trim()
    const requester = ticketForm.requester.trim()
    if (!summary || !requester) {
      setTicketState({ loading: false, error: 'Summary and requester are required.', success: '' })
      return
    }
    setTicketState({ loading: true, error: '', success: '' })
    try {
      const payload = await requestJson('/api/tickets', {
        method: 'POST',
        body: JSON.stringify({ summary, category: ticketForm.category, priority: ticketForm.priority, requester, assignee: ticketForm.assignee.trim() }),
      }, session)
      setOverview((p) => ({ ...p, tickets: [payload, ...safeArray(p.tickets)] }))
      setTicketForm(defaultTicketForm)
      setTicketState({ loading: false, error: '', success: 'Ticket created successfully.' })
    } catch (error) {
      setTicketState({ loading: false, error: extractErrorMessage(error), success: '' })
    }
  }

  async function submitReview(event) {
    event.preventDefault()
    const title    = reviewForm.title.trim()
    const reviewer = reviewForm.reviewer.trim()
    const content  = reviewForm.content.trim()
    if (!title || !reviewer || !content) {
      setReviewState({ loading: false, error: 'Title, reviewer, and content are required.', success: '' })
      return
    }
    setReviewState({ loading: true, error: '', success: '' })
    try {
      const payload = await requestJson('/api/reviews', {
        method: 'POST',
        body: JSON.stringify({ title, reviewer, status: reviewForm.status, content }),
      }, session)
      setOverview((p) => ({ ...p, reviews: [payload, ...safeArray(p.reviews)] }))
      setReviewForm(defaultReviewForm)
      setReviewState({ loading: false, error: '', success: 'Review saved and queued for approval.' })
    } catch (error) {
      setReviewState({ loading: false, error: extractErrorMessage(error), success: '' })
    }
  }

  async function submitApproval(event) {
    event.preventDefault()
    const title    = approvalForm.title.trim()
    const reviewer = approvalForm.reviewer.trim()
    const comments = approvalForm.comments.trim()
    if (!title || !reviewer || !comments) {
      setApprovalState({ loading: false, error: 'Title, reviewer, and comments are required.', success: '' })
      return
    }
    setApprovalState({ loading: true, error: '', success: '' })
    try {
      const payload = await requestJson('/api/reviews', {
        method: 'POST',
        body: JSON.stringify({ title, reviewer, status: approvalForm.decision, content: comments }),
      }, session)
      setOverview((p) => ({ ...p, reviews: [payload, ...safeArray(p.reviews)] }))
      setApprovalForm(defaultApprovalForm)
      setApprovalState({ loading: false, error: '', success: `Decision "${approvalForm.decision}" recorded.` })
    } catch (error) {
      setApprovalState({ loading: false, error: extractErrorMessage(error), success: '' })
    }
  }

  function handleLogin(event) {
    event.preventDefault()
    let token = loginForm.token.trim()
    if (!token) {
      token = `${loginForm.role}-demo-token`
    }
    const nextSession = { token, role: loginForm.role, username: `${loginForm.role}-user` }
    saveSession(nextSession)
    setSession(nextSession)
    setAuthError('')
  }

  function handleLogout() {
    clearSession()
    setSession(null)
    setActiveView('dashboard')
  }

  const renderStatusBadge = (value) => {
    const n = String(value || 'pending').toLowerCase()
    const tone =
      n.includes('approved') || n.includes('ok') || n.includes('success') ? 'success'
      : n.includes('rejected') || n.includes('error') || n.includes('fail') ? 'danger'
      : 'neutral'
    return <span className={`status-badge ${tone}`}>{value || 'pending'}</span>
  }

  const renderEmptyState = (label) => (
    <div className="empty-state">
      <span style={{ fontSize: '1.6rem', opacity: 0.4 }}>📭</span>
      <span>No {label} found yet.</span>
    </div>
  )

  // ─── Login screen ─────────────────────────────────────────────────
  if (!session) {
    return (
      <div className="login-shell">
        <div className="login-card">
          <div className="brand-block">
            <div className="brand-icon">AI</div>
            <div>
              <p className="eyebrow">Enterprise</p>
              <h1 style={{ fontSize: '1.15rem', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
                Agent Console
              </h1>
            </div>
          </div>

          <div className="login-copy">
            <h2>Secure workspace access</h2>
            <p>
              Use your role credentials to access the enterprise multi-agent platform —
              intelligent routing for HR, IT, Security, and Operations workflows.
            </p>
          </div>

          <form className="login-form" onSubmit={handleLogin}>
            <label>
              Role
              <select
                value={loginForm.role}
                onChange={(e) => {
                  const role = e.target.value
                  setLoginForm({ role, token: `${role}-demo-token` })
                }}
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
            </label>

            <label>
              Session Token
              <input
                id="session-token"
                type="text"
                value={loginForm.token}
                onChange={(e) => setLoginForm((c) => ({ ...c, token: e.target.value }))}
                placeholder="user-demo-token"
                autoComplete="off"
              />
            </label>

            {authError && <div className="alert error">{authError}</div>}

            <button type="submit" className="primary-button full-width" style={{ marginTop: 4 }}>
              Continue to workspace →
            </button>
          </form>

          <div className="demo-hint">
            <strong>Click to use demo token:</strong>{' '}
            <button
              type="button"
              className="inline-token-btn"
              onClick={() => setLoginForm({ role: 'user', token: 'user-demo-token' })}
            >
              user-demo-token
            </button>
            &nbsp;or&nbsp;
            <button
              type="button"
              className="inline-token-btn"
              onClick={() => setLoginForm({ role: 'admin', token: 'admin-demo-token' })}
            >
              admin-demo-token
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ─── Authenticated layout ─────────────────────────────────────────
  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarExpanded ? 'expanded' : 'collapsed'}`}>
        <div className="sidebar-top-row">
          <div className="brand-block" title="Enterprise Agent Console">
            <div className="brand-icon">AI</div>
            {sidebarExpanded && (
              <div className="brand-text">
                <p className="eyebrow">Enterprise</p>
                <h1 style={{ fontSize: '0.95rem', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
                  Agent Console
                </h1>
              </div>
            )}
          </div>
          <button
            type="button"
            className="sidebar-toggle-btn"
            onClick={toggleSidebar}
            title={sidebarExpanded ? 'Shrink sidebar' : 'Expand sidebar'}
            aria-label={sidebarExpanded ? 'Shrink sidebar' : 'Expand sidebar'}
          >
            {sidebarExpanded ? <Icon.Collapse /> : <Icon.Expand />}
          </button>
        </div>

        {/* New Chat Button */}
        <button
          type="button"
          className="new-chat-btn"
          onClick={handleNewChat}
          title="New Chat"
        >
          <Icon.Plus />
          {sidebarExpanded && <span>New Chat</span>}
        </button>

        {/* User Card */}
        {sidebarExpanded ? (
          <div className="sidebar-card">
            <p className="section-title">Active Session</p>
            <div className="user-pill">
              <span className="dot" />
              <div>
                <strong>{session.username}</strong>
                <small>{session.role === 'admin' ? '⚡ Administrator' : '👤 Standard User'}</small>
              </div>
            </div>
          </div>
        ) : (
          <div className="user-pill-collapsed" title={`${session.username} (${session.role})`}>
            <span className="dot" />
          </div>
        )}

        <div className="section-divider" />
        {sidebarExpanded && <p className="section-title" style={{ padding: '0 4px' }}>Navigation</p>}

        <nav className="nav-stack" aria-label="Main navigation">
          {roleTabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`nav-button ${activeView === tab.id ? 'active' : ''}`}
              onClick={() => setActiveView(tab.id)}
              title={tab.label}
            >
              <tab.icon />
              {sidebarExpanded && <span>{tab.label}</span>}
            </button>
          ))}
        </nav>

        {/* Chat History in Left Panel */}
        {sidebarExpanded && (
          <div className="sidebar-history-container">
            <div className="section-divider" />
            <div className="history-header">
              <p className="section-title" style={{ margin: 0, padding: '0 4px' }}>Chat History</p>
              {chatSessions.length > 0 && (
                <span className="history-badge">{chatSessions.length}</span>
              )}
            </div>

            <div className="history-list">
              {chatSessions.length === 0 ? (
                <div className="history-empty">No stored chats yet</div>
              ) : (
                chatSessions.map((s) => (
                  <div
                    key={s.id}
                    className={`history-item ${activeSessionId === s.id && activeView === 'chat' ? 'active' : ''}`}
                    onClick={() => handleSelectSession(s)}
                    title={s.title}
                  >
                    <Icon.MessageBubble />
                    <span className="history-text">{s.title}</span>
                    <button
                      type="button"
                      className="history-delete-btn"
                      onClick={(e) => handleDeleteSession(e, s.id)}
                      title="Delete chat"
                    >
                      <Icon.Trash />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        <div style={{ marginTop: 'auto', paddingTop: 8 }}>
          <button
            type="button"
            className="primary-button ghost full-width signout-btn"
            onClick={handleLogout}
            title="Sign out"
            style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'center' }}
          >
            <Icon.Logout />
            {sidebarExpanded && <span>Sign out</span>}
          </button>
        </div>
      </aside>

      {/* Main workspace */}
      <main className="workspace-panel">
        {/* Topbar */}
        <header className="topbar">
          <div>
            <p className="eyebrow muted">
              {session.role === 'admin' ? 'Operations Command Center' : 'Employee Workspace'} &nbsp;·&nbsp; {activeView}
            </p>
            <h2>
              {activeView === 'dashboard'  && 'System Overview'}
              {activeView === 'chat'       && 'AI Assistant'}
              {activeView === 'tickets'    && 'Support Tickets'}
              {activeView === 'reviews'    && 'Reviews & Approvals'}
              {activeView === 'workflow'   && 'Workflow History'}
            </h2>
          </div>
          <div className="topbar-actions">
            <LiveClock />
            <span className="status-pill">System Online</span>
          </div>
        </header>

        {/* ── Dashboard ── */}
        {activeView === 'dashboard' && (
          <div className="panel-stack">
            <div className="metric-grid">
              {dashboardSummary.map((stat) => (
                <div key={stat.label} className="metric-card">
                  <div className="metric-icon" style={{ background: stat.gradient }}>
                    <span style={{ fontSize: '1.1rem' }}>{stat.emoji}</span>
                  </div>
                  <span>{stat.label}</span>
                  <strong>{stat.value}</strong>
                  <div className="metric-trend">↑ Live</div>
                </div>
              ))}
            </div>

            {overviewState.loading && <div className="loading-card">Loading workspace data…</div>}
            {overviewState.error && (
              <div className="alert error">
                {overviewState.error}
                <button type="button" className="inline-button" onClick={loadOverview}>Retry</button>
              </div>
            )}

            <div className="content-grid">
              <div className="card-panel">
                <div className="card-header">
                  <h3>🎫 Open Tickets</h3>
                  <span className="status-badge neutral">{safeArray(overview.tickets).length} total</span>
                </div>
                {safeArray(overview.tickets).length ? (
                  <ul className="list-stack">
                    {overview.tickets.slice(0, 5).map((ticket) => (
                      <li key={ticket.ticket_id || ticket.id} className="list-item">
                        <div>
                          <strong>{ticket.summary || 'Untitled ticket'}</strong>
                          <small>{ticket.category || 'general'} · {ticket.requester || 'unknown'}</small>
                        </div>
                        {renderStatusBadge(ticket.status || 'open')}
                      </li>
                    ))}
                  </ul>
                ) : renderEmptyState('tickets')}
              </div>

              <div className="card-panel">
                <div className="card-header">
                  <h3>📋 Review Queue</h3>
                  <span className="status-badge neutral">{safeArray(overview.reviews).length} items</span>
                </div>
                {safeArray(overview.reviews).length ? (
                  <ul className="list-stack">
                    {overview.reviews.slice(0, 5).map((review) => (
                      <li key={review.review_id || review.id} className="list-item">
                        <div>
                          <strong>{review.title || review.summary || 'Review item'}</strong>
                          <small>{review.reviewer || 'reviewer'} · {review.status || 'pending'}</small>
                        </div>
                        {renderStatusBadge(review.status || 'pending')}
                      </li>
                    ))}
                  </ul>
                ) : renderEmptyState('reviews')}
              </div>
            </div>

            <div className="card-panel">
              <div className="card-header">
                <h3>⚙️ Workflow Status History</h3>
                <span className="status-badge neutral">{safeArray(overview.workflows).length} runs</span>
              </div>
              {safeArray(overview.workflows).length ? (
                <ul className="list-stack">
                  {overview.workflows.slice(0, 6).map((workflow) => (
                    <li key={workflow.workflow_id || workflow.id} className="list-item">
                      <div>
                        <strong>{workflow.route || workflow.type || 'workflow'}</strong>
                        <small>{workflow.workflow_id || workflow.id || 'workflow'}</small>
                      </div>
                      <div className="timeline-meta">
                        {renderStatusBadge(workflow.status || 'in_review')}
                        {Array.isArray(workflow.execution_history) && workflow.execution_history.length ? (
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            {workflow.execution_history.length} steps
                          </span>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : renderEmptyState('workflow history')}
            </div>
          </div>
        )}

        {/* ── Chat ── */}
        {activeView === 'chat' && (
          <div className="panel-stack">
            <div className="card-panel">
              <div className="card-header">
                <h3>🤖 AI Multi-Agent Assistant</h3>
                <span className="status-badge success">Ready</span>
              </div>



              <div className="chat-input-area">
                <form
                  className="form-stack"
                  onSubmit={(e) => { e.preventDefault(); submitChat(chatInput) }}
                >
                  <label style={{ textTransform: 'none', letterSpacing: 0, fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-secondary)' }}>
                    Message the enterprise agent network
                    <textarea
                      rows="4"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder="Describe your task or question — the orchestrator will route it to the right specialist agent…"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                          e.preventDefault()
                          submitChat(chatInput)
                        }
                      }}
                    />
                  </label>

                  {chatState.error && <div className="alert error">{chatState.error}</div>}

                  <div className="form-actions">
                    <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)', alignSelf: 'center' }}>
                      Ctrl+Enter to send
                    </span>
                    <button
                      type="submit"
                      className="primary-button"
                      disabled={chatState.loading}
                      style={{ display: 'flex', alignItems: 'center', gap: 8 }}
                    >
                      {chatState.loading ? (
                        'Routing request…'
                      ) : (
                        <><Icon.Send /> Send to agent</>
                      )}
                    </button>
                  </div>
                </form>
              </div>
            </div>

            <div className="card-panel">
              <div className="card-header">
                <h3>💬 Conversation</h3>
                {(chatState.messages?.length ?? 0) > 0 && (
                  <button
                    type="button"
                    className="inline-button"
                    onClick={() => {
                      setChatState((p) => ({ ...p, messages: [] }))
                      if (activeSessionId) {
                        setChatSessions((prev) => {
                          const updated = prev.filter((s) => s.id !== activeSessionId)
                          try { localStorage.setItem('enterprise_agent_chat_sessions', JSON.stringify(updated)) } catch {}
                          return updated
                        })
                        setActiveSessionId(null)
                      }
                    }}
                  >
                    Clear history
                  </button>
                )}
              </div>

              {chatState.loading && <div className="loading-card">Running enterprise workflow…</div>}

              {(chatState.messages?.length ?? 0) === 0 && !chatState.loading ? (
                renderEmptyState('messages yet — send a query above to get started')
              ) : (
                <div className="chat-history">
                  {(chatState.messages || []).map((msg, i) => (
                    <div key={i} className="chat-entry">
                      <div className="chat-user-bubble">{msg.input}</div>
                      <div className="response-card">
                        <div className="response-topline">
                          <strong>{msg.reply.route || 'workflow'}</strong>
                          {renderStatusBadge(msg.reply.approved ? 'approved' : 'in review')}
                        </div>
                        <div className="response-body">
                          <AgentResponse reply={msg.reply} />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Tickets ── */}
        {activeView === 'tickets' && (
          <div className="panel-stack">
            <div className="card-panel">
              <div className="card-header">
                <h3>🎫 Create Support Ticket</h3>
              </div>
              <div className="card-body">
                <form className="form-stack" onSubmit={submitTicket}>
                  <label>
                    Summary
                    <input
                      type="text"
                      value={ticketForm.summary}
                      onChange={(e) => setTicketForm((c) => ({ ...c, summary: e.target.value }))}
                      placeholder="e.g. Password reset for employee ID 123"
                    />
                  </label>

                  <div className="two-column-grid">
                    <label>
                      Category
                      <select
                        value={ticketForm.category}
                        onChange={(e) => setTicketForm((c) => ({ ...c, category: e.target.value }))}
                      >
                        <option value="general">General</option>
                        <option value="security">Security</option>
                        <option value="payroll">Payroll</option>
                        <option value="hr">HR</option>
                      </select>
                    </label>
                    <label>
                      Priority
                      <select
                        value={ticketForm.priority}
                        onChange={(e) => setTicketForm((c) => ({ ...c, priority: e.target.value }))}
                      >
                        <option value="low">Low</option>
                        <option value="normal">Normal</option>
                        <option value="high">High</option>
                        <option value="urgent">Urgent</option>
                      </select>
                    </label>
                  </div>

                  <div className="two-column-grid">
                    <label>
                      Requester
                      <input
                        type="text"
                        value={ticketForm.requester}
                        onChange={(e) => setTicketForm((c) => ({ ...c, requester: e.target.value }))}
                        placeholder="jane.doe@company.com"
                      />
                    </label>
                    <label>
                      Assignee
                      <input
                        type="text"
                        value={ticketForm.assignee}
                        onChange={(e) => setTicketForm((c) => ({ ...c, assignee: e.target.value }))}
                        placeholder="Ops team"
                      />
                    </label>
                  </div>

                  {ticketState.error   && <div className="alert error">{ticketState.error}</div>}
                  {ticketState.success && <div className="alert success">{ticketState.success}</div>}

                  <div className="form-actions">
                    <button type="submit" className="primary-button" disabled={ticketState.loading}>
                      {ticketState.loading ? 'Submitting…' : 'Create ticket'}
                    </button>
                  </div>
                </form>
              </div>
            </div>

            <div className="card-panel">
              <div className="card-header">
                <h3>📂 Recent Tickets</h3>
                <span className="status-badge neutral">{safeArray(overview.tickets).length}</span>
              </div>
              {safeArray(overview.tickets).length ? (
                <ul className="list-stack">
                  {overview.tickets.slice(0, 8).map((ticket) => (
                    <li key={ticket.ticket_id || ticket.id} className="list-item large-gap">
                      <div>
                        <strong>{ticket.summary || 'Untitled'}</strong>
                        <small>{ticket.requester || 'Requester missing'} · {ticket.category || 'general'} · {ticket.priority || 'normal'}</small>
                      </div>
                      {renderStatusBadge(ticket.status || 'open')}
                    </li>
                  ))}
                </ul>
              ) : renderEmptyState('tickets')}
            </div>
          </div>
        )}

        {/* ── Reviews ── */}
        {activeView === 'reviews' && (
          <div className="panel-stack">
            <div className="content-grid">
              <div className="card-panel">
                <div className="card-header">
                  <h3>📋 Save Review</h3>
                </div>
                <div className="card-body">
                  <form className="form-stack" onSubmit={submitReview}>
                    <label>
                      Review Title
                      <input
                        type="text"
                        value={reviewForm.title}
                        onChange={(e) => setReviewForm((c) => ({ ...c, title: e.target.value }))}
                        placeholder="Employee performance review"
                      />
                    </label>
                    <div className="two-column-grid">
                      <label>
                        Reviewer
                        <input
                          type="text"
                          value={reviewForm.reviewer}
                          onChange={(e) => setReviewForm((c) => ({ ...c, reviewer: e.target.value }))}
                          placeholder="HR manager"
                        />
                      </label>
                      <label>
                        Status
                        <select
                          value={reviewForm.status}
                          onChange={(e) => setReviewForm((c) => ({ ...c, status: e.target.value }))}
                        >
                          <option value="pending">Pending</option>
                          <option value="in_review">In Review</option>
                          <option value="approved">Approved</option>
                          <option value="rejected">Rejected</option>
                        </select>
                      </label>
                    </div>
                    <label>
                      Notes
                      <textarea
                        rows="4"
                        value={reviewForm.content}
                        onChange={(e) => setReviewForm((c) => ({ ...c, content: e.target.value }))}
                        placeholder="Provide objective notes, risks, and final recommendations."
                      />
                    </label>
                    {reviewState.error   && <div className="alert error">{reviewState.error}</div>}
                    {reviewState.success && <div className="alert success">{reviewState.success}</div>}
                    <div className="form-actions">
                      <button type="submit" className="primary-button" disabled={reviewState.loading}>
                        {reviewState.loading ? 'Saving…' : 'Save review'}
                      </button>
                    </div>
                  </form>
                </div>
              </div>

              <div className="card-panel">
                <div className="card-header">
                  <h3>✅ Approval Decision</h3>
                </div>
                <div className="card-body">
                  <form className="form-stack" onSubmit={submitApproval}>
                    <label>
                      Decision Title
                      <input
                        type="text"
                        value={approvalForm.title}
                        onChange={(e) => setApprovalForm((c) => ({ ...c, title: e.target.value }))}
                        placeholder="Approval for salary adjustment"
                      />
                    </label>
                    <div className="two-column-grid">
                      <label>
                        Reviewer
                        <input
                          type="text"
                          value={approvalForm.reviewer}
                          onChange={(e) => setApprovalForm((c) => ({ ...c, reviewer: e.target.value }))}
                          placeholder="Operations lead"
                        />
                      </label>
                      <label>
                        Decision
                        <select
                          value={approvalForm.decision}
                          onChange={(e) => setApprovalForm((c) => ({ ...c, decision: e.target.value }))}
                        >
                          <option value="approved">Approve ✓</option>
                          <option value="rejected">Reject ✗</option>
                          <option value="escalated">Escalate ↑</option>
                        </select>
                      </label>
                    </div>
                    <label>
                      Comments
                      <textarea
                        rows="4"
                        value={approvalForm.comments}
                        onChange={(e) => setApprovalForm((c) => ({ ...c, comments: e.target.value }))}
                        placeholder="Rationale, risk level, and any required follow-up."
                      />
                    </label>
                    {approvalState.error   && <div className="alert error">{approvalState.error}</div>}
                    {approvalState.success && <div className="alert success">{approvalState.success}</div>}
                    <div className="form-actions">
                      <button type="submit" className="primary-button" disabled={approvalState.loading}>
                        {approvalState.loading ? 'Recording…' : 'Submit decision'}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            </div>

            {/* Reviews list */}
            <div className="card-panel">
              <div className="card-header">
                <h3>📋 All Reviews</h3>
                <span className="status-badge neutral">{safeArray(overview.reviews).length}</span>
              </div>
              {safeArray(overview.reviews).length ? (
                <ul className="list-stack">
                  {overview.reviews.slice(0, 8).map((review) => (
                    <li key={review.review_id || review.id} className="list-item">
                      <div>
                        <strong>{review.title || review.summary || 'Review item'}</strong>
                        <small>{review.reviewer || 'reviewer'} · {review.status || 'pending'}</small>
                      </div>
                      {renderStatusBadge(review.status || 'pending')}
                    </li>
                  ))}
                </ul>
              ) : renderEmptyState('reviews')}
            </div>
          </div>
        )}

        {/* ── Workflow History (admin only) ── */}
        {session.role === 'admin' && activeView === 'workflow' && (
          <div className="panel-stack">
            <div className="card-panel">
              <div className="card-header">
                <h3>⚙️ Workflow Execution History</h3>
                <span className="status-badge neutral">{safeArray(overview.workflows).length} runs</span>
              </div>
              {safeArray(overview.workflows).length ? (
                <ul className="list-stack">
                  {overview.workflows.map((workflow) => (
                    <li key={workflow.workflow_id || workflow.id} className="list-item large-gap" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
                        <div>
                          <strong>{workflow.route || workflow.type || 'agent route'}</strong>
                          <small>{workflow.workflow_id || workflow.id || ''}</small>
                        </div>
                        <div className="timeline-meta">
                          {renderStatusBadge(workflow.status || 'in_review')}
                          {Array.isArray(workflow.execution_history) && workflow.execution_history.length ? (
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              {workflow.execution_history.length} steps
                            </span>
                          ) : null}
                        </div>
                      </div>
                      {workflow.execution_history ? (
                        <div className="workflow-detail">
                          <pre>{formatPayload(workflow.execution_history)}</pre>
                        </div>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : renderEmptyState('workflow history')}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
