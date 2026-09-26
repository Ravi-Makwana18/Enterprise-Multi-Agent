import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { clearSession, createAuthHeaders, getStoredSession, saveSession } from './session'

const quickPrompts = [
  'Write a blog about AI in healthcare',
  'What is my salary breakdown?',
  'Check security compliance for employee EMP001',
  'Create a support ticket for password reset',
]

const defaultTicketForm = {
  summary: '',
  category: 'general',
  priority: 'normal',
  requester: '',
  assignee: '',
}

const defaultReviewForm = {
  title: '',
  reviewer: '',
  status: 'pending',
  content: '',
}

const defaultApprovalForm = {
  title: '',
  reviewer: '',
  decision: 'approved',
  comments: '',
}

function formatPayload(value) {
  if (!value) return 'No data returned.'
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function AgentResponse({ reply }) {
  const route = (reply.route || '').toUpperCase()
  const data = reply.response || {}

  // Extract the main text content from nested response shapes
  const message =
    data.message ||
    data.content ||
    data.blog_content ||
    data.revised_content ||
    data.summary ||
    data.result ||
    null

  const issues = Array.isArray(data.issues) ? data.issues : []
  const recommendations = Array.isArray(data.recommendations) ? data.recommendations : []
  const ticketId = data.ticket_id || data.id || null
  const score = reply.score ?? data.score ?? null
  const riskLevel = data.risk_level || null
  const requiresHumanReview = data.requires_human_review || false

  return (
    <div className="agent-response">
      {/* Main message / content */}
      {message && (
        <p className="agent-message">{message}</p>
      )}

      {/* Ticket confirmation */}
      {ticketId && (
        <div className="agent-meta-row">
          <span className="meta-label">Ticket ID</span>
          <span className="meta-value">{ticketId}</span>
        </div>
      )}

      {/* Score + risk */}
      {score !== null && (
        <div className="agent-meta-row">
          <span className="meta-label">Confidence score</span>
          <span className="meta-value">{score} / 100</span>
        </div>
      )}
      {riskLevel && (
        <div className="agent-meta-row">
          <span className="meta-label">Risk level</span>
          <span className={`status-badge ${riskLevel === 'low' ? 'success' : riskLevel === 'medium' ? 'neutral' : 'danger'}`}>
            {riskLevel}
          </span>
        </div>
      )}
      {requiresHumanReview && (
        <div className="agent-alert">⚠ Human review required before acting on this response.</div>
      )}

      {/* Issues list */}
      {issues.length > 0 && (
        <div className="agent-section">
          <p className="agent-section-title">Issues found</p>
          <ul className="agent-list">
            {issues.map((item, i) => <li key={i}>{item}</li>)}
          </ul>
        </div>
      )}

      {/* Recommendations list */}
      {recommendations.length > 0 && (
        <div className="agent-section">
          <p className="agent-section-title">Recommendations</p>
          <ul className="agent-list">
            {recommendations.map((item, i) => <li key={i}>{item}</li>)}
          </ul>
        </div>
      )}

      {/* Fallback: if nothing matched, show formatted JSON */}
      {!message && !ticketId && issues.length === 0 && recommendations.length === 0 && (
        <pre className="agent-raw">{formatPayload(data)}</pre>
      )}
    </div>
  )
}

function safeArray(value) {
  return Array.isArray(value) ? value : []
}

function extractErrorMessage(error) {
  if (error instanceof Error && error.message) {
    return error.message
  }

  return 'Something went wrong while contacting the service.'
}

async function requestJson(url, options = {}, session) {
  if (!url.startsWith('/api/')) {
    throw new Error('Invalid request path.')
  }
  const headers = {
    ...(options.headers || {}),
    ...createAuthHeaders(session),
  }

  if (!(options.body instanceof FormData) && options.body !== undefined && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

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
        ? payload?.error?.message ||
          payload?.detail?.error?.message ||
          payload?.detail ||
          'Request failed.'
        : 'Request failed.'

    throw new Error(message)
  }

  return payload
}

function App() {
  const [session, setSession] = useState(getStoredSession())
  const [activeView, setActiveView] = useState('dashboard')
  const [loginForm, setLoginForm] = useState({
    role: 'user',
    token: '',
  })
  const [authError, setAuthError] = useState('')
  const [overview, setOverview] = useState({
    tickets: [],
    reviews: [],
    securityChecks: [],
    workflows: [],
  })
  const [overviewState, setOverviewState] = useState({
    loading: false,
    error: '',
  })

  const [chatInput, setChatInput] = useState('')
  const [chatState, setChatState] = useState({
    loading: false,
    error: '',
    messages: [],
  })

  const [ticketForm, setTicketForm] = useState(defaultTicketForm)
  const [ticketState, setTicketState] = useState({
    loading: false,
    error: '',
    success: '',
  })

  const [reviewForm, setReviewForm] = useState(defaultReviewForm)
  const [reviewState, setReviewState] = useState({
    loading: false,
    error: '',
    success: '',
  })

  const [approvalForm, setApprovalForm] = useState(defaultApprovalForm)
  const [approvalState, setApprovalState] = useState({
    loading: false,
    error: '',
    success: '',
  })

  const roleTabs = useMemo(
    () =>
      session?.role === 'admin'
        ? [
            { id: 'dashboard', label: 'Dashboard' },
            { id: 'chat', label: 'Chat' },
            { id: 'tickets', label: 'Tickets' },
            { id: 'reviews', label: 'Reviews' },
            { id: 'workflow', label: 'Workflow history' },
          ]
        : [
            { id: 'dashboard', label: 'Dashboard' },
            { id: 'chat', label: 'Chat' },
            { id: 'tickets', label: 'Tickets' },
            { id: 'reviews', label: 'Reviews' },
          ],
    [session?.role],
  )

  const dashboardSummary = useMemo(
    () => [
      { label: 'Open tickets', value: safeArray(overview.tickets).length },
      { label: 'Review items', value: safeArray(overview.reviews).length },
      { label: 'Security checks', value: safeArray(overview.securityChecks).length },
      { label: 'Workflow states', value: safeArray(overview.workflows).length },
    ],
    [overview],
  )

  useEffect(() => {
    if (!session) {
      return
    }

    loadOverview()
  }, [session])

  async function loadOverview() {
    if (!session) {
      return
    }

    setOverviewState({ loading: true, error: '' })

    try {
      const ticketPromise = requestJson('/api/tickets', { method: 'GET' }, session)
      const reviewPromise = requestJson('/api/reviews', { method: 'GET' }, session)
      const securityPromise = requestJson('/api/security-checks', { method: 'GET' }, session)
      const workflowPromise =
        session.role === 'admin'
          ? requestJson('/api/workflow-states', { method: 'GET' }, session)
          : Promise.resolve([])

      const [tickets, reviews, securityChecks, workflows] = await Promise.all([
        ticketPromise,
        reviewPromise,
        securityPromise,
        workflowPromise,
      ])

      setOverview({
        tickets: safeArray(tickets),
        reviews: safeArray(reviews),
        securityChecks: safeArray(securityChecks),
        workflows: safeArray(workflows),
      })
      setOverviewState({ loading: false, error: '' })
    } catch (error) {
      setOverviewState({
        loading: false,
        error: extractErrorMessage(error),
      })
    }
  }

  async function submitChat(rawMessage) {
    const message = rawMessage.trim()
    if (!message || message.length < 3) {
      setChatState((prev) => ({
        ...prev,
        loading: false,
        error: 'Please enter at least 3 characters before sending a message.',
      }))
      return
    }

    setChatState((prev) => ({ ...prev, loading: true, error: '' }))

    try {
      const data = await requestJson(
        '/api/chat',
        {
          method: 'POST',
          body: JSON.stringify({ message }),
        },
        session,
      )

      setChatState((prev) => ({
        loading: false,
        error: '',
        messages: [{ input: message, reply: data }, ...(prev.messages || [])],
      }))
      setChatInput('')
    } catch (error) {
      setChatState((prev) => ({
        ...prev,
        loading: false,
        error: extractErrorMessage(error),
      }))
    }
  }

  async function submitTicket(event) {
    event.preventDefault()

    const summary = ticketForm.summary.trim()
    const requester = ticketForm.requester.trim()

    if (!summary || !requester) {
      setTicketState({
        loading: false,
        error: 'Summary and requester are required before submitting the ticket.',
        success: '',
      })
      return
    }

    setTicketState({ loading: true, error: '', success: '' })

    try {
      const payload = await requestJson(
        '/api/tickets',
        {
          method: 'POST',
          body: JSON.stringify({
            summary,
            category: ticketForm.category,
            priority: ticketForm.priority,
            requester,
            assignee: ticketForm.assignee.trim(),
          }),
        },
        session,
      )

      setOverview((previous) => ({
        ...previous,
        tickets: [payload, ...safeArray(previous.tickets)],
      }))
      setTicketForm(defaultTicketForm)
      setTicketState({
        loading: false,
        error: '',
        success: 'Ticket created successfully. The support team has the latest details.',
      })
    } catch (error) {
      setTicketState({
        loading: false,
        error: extractErrorMessage(error),
        success: '',
      })
    }
  }

  async function submitReview(event) {
    event.preventDefault()

    const title = reviewForm.title.trim()
    const reviewer = reviewForm.reviewer.trim()
    const content = reviewForm.content.trim()

    if (!title || !reviewer || !content) {
      setReviewState({
        loading: false,
        error: 'Title, reviewer, and content are required before saving the review.',
        success: '',
      })
      return
    }

    setReviewState({ loading: true, error: '', success: '' })

    try {
      const payload = await requestJson(
        '/api/reviews',
        {
          method: 'POST',
          body: JSON.stringify({
            title,
            reviewer,
            status: reviewForm.status,
            content,
          }),
        },
        session,
      )

      setOverview((previous) => ({
        ...previous,
        reviews: [payload, ...safeArray(previous.reviews)],
      }))
      setReviewForm(defaultReviewForm)
      setReviewState({
        loading: false,
        error: '',
        success: 'Review saved and ready for approval workflow.',
      })
    } catch (error) {
      setReviewState({
        loading: false,
        error: extractErrorMessage(error),
        success: '',
      })
    }
  }

  async function submitApproval(event) {
    event.preventDefault()

    const title = approvalForm.title.trim()
    const reviewer = approvalForm.reviewer.trim()
    const comments = approvalForm.comments.trim()

    if (!title || !reviewer || !comments) {
      setApprovalState({
        loading: false,
        error: 'Approval title, reviewer, and comments are required.',
        success: '',
      })
      return
    }

    setApprovalState({ loading: true, error: '', success: '' })

    try {
      const payload = await requestJson(
        '/api/reviews',
        {
          method: 'POST',
          body: JSON.stringify({
            title,
            reviewer,
            status: approvalForm.decision,
            content: comments,
          }),
        },
        session,
      )

      setOverview((previous) => ({
        ...previous,
        reviews: [payload, ...safeArray(previous.reviews)],
      }))
      setApprovalForm(defaultApprovalForm)
      setApprovalState({
        loading: false,
        error: '',
        success: `Approval ${approvalForm.decision} recorded successfully.`,
      })
    } catch (error) {
      setApprovalState({
        loading: false,
        error: extractErrorMessage(error),
        success: '',
      })
    }
  }

  function handleLogin(event) {
    event.preventDefault()

    const token = loginForm.token.trim()
    if (!token) {
      setAuthError('Enter a valid session token to continue.')
      return
    }

    const nextSession = {
      token,
      role: loginForm.role,
      username: `${loginForm.role}-user`,
    }

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
    const normalized = String(value || 'pending').toLowerCase()
    const tone =
      normalized.includes('approved') || normalized.includes('ok') || normalized.includes('success')
        ? 'success'
        : normalized.includes('rejected') || normalized.includes('error') || normalized.includes('fail')
          ? 'danger'
          : 'neutral'

    return <span className={`status-badge ${tone}`}>{value || 'pending'}</span>
  }

  const renderEmptyState = (label) => (
    <div className="empty-state">No {label} found yet.</div>
  )

  return (
    <div className="app-shell">
      {!session ? (
        <div className="login-shell">
          <div className="login-card">
            <div className="brand-block">
              <div className="brand-icon">AI</div>
              <div>
                <p className="eyebrow">Enterprise</p>
                <h1>Agent Console</h1>
              </div>
            </div>

            <div className="login-copy">
              <h2>Secure workspace access</h2>
              <p>Use your role to access the enterprise workflow console for chat, operations, reviews, and approvals.</p>
            </div>

            <form className="login-form" onSubmit={handleLogin}>
              <label>
                Role
                <select
                  value={loginForm.role}
                  onChange={(event) => setLoginForm((current) => ({ ...current, role: event.target.value }))}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </label>

              <label>
                Session token
                <input
                  type="text"
                  value={loginForm.token}
                  onChange={(event) => setLoginForm((current) => ({ ...current, token: event.target.value }))}
                  placeholder="user-demo-token"
                />
              </label>

              {authError ? <div className="alert error">{authError}</div> : null}

              <button type="submit" className="primary-button full-width">
                Continue to workspace
              </button>
            </form>

            <div className="demo-hint">
              Demo tokens: <strong>user-demo-token</strong> or <strong>admin-demo-token</strong>
            </div>
          </div>
        </div>
      ) : (
        <>
          <aside className="sidebar">
            <div className="brand-block">
              <div className="brand-icon">AI</div>
              <div>
                <p className="eyebrow">Enterprise</p>
                <h1>Agent Console</h1>
              </div>
            </div>

            <div className="sidebar-card">
              <p className="section-title">Workspace</p>
              <div className="user-pill">
                <span className="dot" />
                <div>
                  <strong>{session.username}</strong>
                  <small>{session.role}</small>
                </div>
              </div>
            </div>

            <nav className="nav-stack" aria-label="Main navigation">
              {roleTabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  className={`nav-button ${activeView === tab.id ? 'active' : ''}`}
                  onClick={() => setActiveView(tab.id)}
                >
                  {tab.label}
                </button>
              ))}
            </nav>

            <button type="button" className="primary-button ghost" onClick={handleLogout}>
              Sign out
            </button>
          </aside>

          <main className="workspace-panel">
            <header className="topbar">
              <div>
                <p className="eyebrow muted">Live workspace</p>
                <h2>{session.role === 'admin' ? 'Operations command center' : 'Employee workspace'}</h2>
              </div>
              <span className="status-pill">System online</span>
            </header>

            {activeView === 'dashboard' ? (
              <section className="panel-stack">
                <div className="metric-grid">
                  {dashboardSummary.map((stat) => (
                    <div key={stat.label} className="metric-card">
                      <span>{stat.label}</span>
                      <strong>{stat.value}</strong>
                    </div>
                  ))}
                </div>

                {overviewState.loading ? (
                  <div className="loading-card">Loading workspace data…</div>
                ) : overviewState.error ? (
                  <div className="alert error">
                    {overviewState.error}
                    <button type="button" className="inline-button" onClick={loadOverview}>
                      Retry
                    </button>
                  </div>
                ) : null}

                <div className="content-grid">
                  <div className="card-panel">
                    <div className="card-header">
                      <h3>Open tickets</h3>
                    </div>
                    {safeArray(overview.tickets).length ? (
                      <ul className="list-stack">
                        {overview.tickets.slice(0, 5).map((ticket) => (
                          <li key={ticket.ticket_id || ticket.id} className="list-item">
                            <div>
                              <strong>{ticket.summary || 'Untitled ticket'}</strong>
                              <small>{ticket.category || 'general'} • {ticket.requester || 'unknown requester'}</small>
                            </div>
                            {renderStatusBadge(ticket.status || 'open')}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      renderEmptyState('tickets')
                    )}
                  </div>

                  <div className="card-panel">
                    <div className="card-header">
                      <h3>Review queue</h3>
                    </div>
                    {safeArray(overview.reviews).length ? (
                      <ul className="list-stack">
                        {overview.reviews.slice(0, 5).map((review) => (
                          <li key={review.review_id || review.id} className="list-item">
                            <div>
                              <strong>{review.title || review.summary || 'Review item'}</strong>
                              <small>{review.reviewer || 'reviewer'} • {review.status || 'pending'}</small>
                            </div>
                            {renderStatusBadge(review.status || 'pending')}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      renderEmptyState('reviews')
                    )}
                  </div>
                </div>

                <div className="card-panel">
                  <div className="card-header">
                    <h3>Workflow status history</h3>
                  </div>
                  {safeArray(overview.workflows).length ? (
                    <ul className="timeline-list">
                      {overview.workflows.slice(0, 6).map((workflow) => (
                        <li key={workflow.workflow_id || workflow.id} className="timeline-item">
                          <div>
                            <strong>{workflow.route || workflow.type || 'workflow'}</strong>
                            <small>{workflow.workflow_id || workflow.id || 'workflow'}</small>
                          </div>
                          <div className="timeline-meta">
                            {renderStatusBadge(workflow.status || 'in_review')}
                            {Array.isArray(workflow.execution_history) && workflow.execution_history.length ? (
                              <span>{workflow.execution_history.length} steps</span>
                            ) : null}
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    renderEmptyState('workflow history')
                  )}
                </div>
              </section>
            ) : null}

            {activeView === 'chat' ? (
              <section className="panel-stack">
                <div className="card-panel">
                  <div className="card-header">
                    <h3>Assistant</h3>
                  </div>
                  <div className="quick-prompts">
                    {quickPrompts.map((prompt) => (
                      <button key={prompt} type="button" className="chip" onClick={() => setChatInput(prompt)}>
                        {prompt}
                      </button>
                    ))}
                  </div>

                  <form
                    className="form-stack"
                    onSubmit={(event) => {
                      event.preventDefault()
                      submitChat(chatInput)
                    }}
                  >
                    <label>
                      Message
                      <textarea
                        rows="5"
                        value={chatInput}
                        onChange={(event) => setChatInput(event.target.value)}
                        placeholder="Describe the task or question to route to the right enterprise agent..."
                      />
                    </label>

                    {chatState.error ? <div className="alert error">{chatState.error}</div> : null}

                    <div className="form-actions">
                      <button type="submit" className="primary-button" disabled={chatState.loading}>
                        {chatState.loading ? 'Routing request...' : 'Send to agent'}
                      </button>
                    </div>
                  </form>
                </div>

                <div className="card-panel">
                  <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3>Conversation</h3>
                    {chatState.messages?.length > 0 && (
                      <button type="button" className="inline-button" style={{ fontSize: '0.8rem', opacity: 0.6 }}
                        onClick={() => setChatState((prev) => ({ ...prev, messages: [] }))}>
                        Clear
                      </button>
                    )}
                  </div>
                  {chatState.loading && (
                    <div className="loading-card">Running enterprise workflow…</div>
                  )}
                  {(chatState.messages?.length ?? 0) === 0 && !chatState.loading ? (
                    <div className="empty-state">No messages yet. Ask a question to get started.</div>
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
                            <AgentResponse reply={msg.reply} />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </section>
            ) : null}

            {activeView === 'tickets' ? (
              <section className="panel-stack">
                <div className="card-panel">
                  <div className="card-header">
                    <h3>Create support ticket</h3>
                  </div>
                  <form className="form-stack" onSubmit={submitTicket}>
                    <label>
                      Summary
                      <input
                        type="text"
                        value={ticketForm.summary}
                        onChange={(event) => setTicketForm((current) => ({ ...current, summary: event.target.value }))}
                        placeholder="Password reset for employee ID 123"
                      />
                    </label>

                    <div className="two-column-grid">
                      <label>
                        Category
                        <select
                          value={ticketForm.category}
                          onChange={(event) => setTicketForm((current) => ({ ...current, category: event.target.value }))}
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
                          onChange={(event) => setTicketForm((current) => ({ ...current, priority: event.target.value }))}
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
                          onChange={(event) => setTicketForm((current) => ({ ...current, requester: event.target.value }))}
                          placeholder="jane.doe@company.com"
                        />
                      </label>

                      <label>
                        Assignee
                        <input
                          type="text"
                          value={ticketForm.assignee}
                          onChange={(event) => setTicketForm((current) => ({ ...current, assignee: event.target.value }))}
                          placeholder="Ops team"
                        />
                      </label>
                    </div>

                    {ticketState.error ? <div className="alert error">{ticketState.error}</div> : null}
                    {ticketState.success ? <div className="alert success">{ticketState.success}</div> : null}

                    <div className="form-actions">
                      <button type="submit" className="primary-button" disabled={ticketState.loading}>
                        {ticketState.loading ? 'Submitting ticket...' : 'Create ticket'}
                      </button>
                    </div>
                  </form>
                </div>

                <div className="card-panel">
                  <div className="card-header">
                    <h3>Recent tickets</h3>
                  </div>
                  {safeArray(overview.tickets).length ? (
                    <ul className="list-stack">
                      {overview.tickets.slice(0, 6).map((ticket) => (
                        <li key={ticket.ticket_id || ticket.id} className="list-item large-gap">
                          <div>
                            <strong>{ticket.summary || 'Untitled'}</strong>
                            <small>{ticket.requester || 'Requester missing'} • {ticket.category || 'general'}</small>
                          </div>
                          {renderStatusBadge(ticket.status || 'open')}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    renderEmptyState('tickets')
                  )}
                </div>
              </section>
            ) : null}

            {activeView === 'reviews' ? (
              <section className="panel-stack">
                <div className="card-panel">
                  <div className="card-header">
                    <h3>Save review</h3>
                  </div>
                  <form className="form-stack" onSubmit={submitReview}>
                    <label>
                      Review title
                      <input
                        type="text"
                        value={reviewForm.title}
                        onChange={(event) => setReviewForm((current) => ({ ...current, title: event.target.value }))}
                        placeholder="Employee performance review"
                      />
                    </label>

                    <div className="two-column-grid">
                      <label>
                        Reviewer
                        <input
                          type="text"
                          value={reviewForm.reviewer}
                          onChange={(event) => setReviewForm((current) => ({ ...current, reviewer: event.target.value }))}
                          placeholder="HR manager"
                        />
                      </label>

                      <label>
                        Status
                        <select
                          value={reviewForm.status}
                          onChange={(event) => setReviewForm((current) => ({ ...current, status: event.target.value }))}
                        >
                          <option value="pending">Pending</option>
                          <option value="in_review">In review</option>
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
                        onChange={(event) => setReviewForm((current) => ({ ...current, content: event.target.value }))}
                        placeholder="Provide objective notes, risks, and final recommendations."
                      />
                    </label>

                    {reviewState.error ? <div className="alert error">{reviewState.error}</div> : null}
                    {reviewState.success ? <div className="alert success">{reviewState.success}</div> : null}

                    <div className="form-actions">
                      <button type="submit" className="primary-button" disabled={reviewState.loading}>
                        {reviewState.loading ? 'Saving review...' : 'Save review'}
                      </button>
                    </div>
                  </form>
                </div>

                <div className="card-panel">
                  <div className="card-header">
                    <h3>Approval decision</h3>
                  </div>
                  <form className="form-stack" onSubmit={submitApproval}>
                    <label>
                      Decision title
                      <input
                        type="text"
                        value={approvalForm.title}
                        onChange={(event) => setApprovalForm((current) => ({ ...current, title: event.target.value }))}
                        placeholder="Approval for salary adjustment"
                      />
                    </label>

                    <div className="two-column-grid">
                      <label>
                        Reviewer
                        <input
                          type="text"
                          value={approvalForm.reviewer}
                          onChange={(event) => setApprovalForm((current) => ({ ...current, reviewer: event.target.value }))}
                          placeholder="Operations lead"
                        />
                      </label>

                      <label>
                        Decision
                        <select
                          value={approvalForm.decision}
                          onChange={(event) => setApprovalForm((current) => ({ ...current, decision: event.target.value }))}
                        >
                          <option value="approved">Approve</option>
                          <option value="rejected">Reject</option>
                          <option value="escalated">Escalate</option>
                        </select>
                      </label>
                    </div>

                    <label>
                      Comments
                      <textarea
                        rows="4"
                        value={approvalForm.comments}
                        onChange={(event) => setApprovalForm((current) => ({ ...current, comments: event.target.value }))}
                        placeholder="List the rationale, risk level, and any required follow-up."
                      />
                    </label>

                    {approvalState.error ? <div className="alert error">{approvalState.error}</div> : null}
                    {approvalState.success ? <div className="alert success">{approvalState.success}</div> : null}

                    <div className="form-actions">
                      <button type="submit" className="primary-button" disabled={approvalState.loading}>
                        {approvalState.loading ? 'Recording approval...' : 'Submit decision'}
                      </button>
                    </div>
                  </form>
                </div>
              </section>
            ) : null}

            {session.role === 'admin' && activeView === 'workflow' ? (
              <section className="panel-stack">
                <div className="card-panel">
                  <div className="card-header">
                    <h3>Workflow execution history</h3>
                  </div>
                  {safeArray(overview.workflows).length ? (
                    <ul className="timeline-list">
                      {overview.workflows.map((workflow) => (
                        <li key={workflow.workflow_id || workflow.id} className="timeline-item detail">
                          <div>
                            <strong>{workflow.route || workflow.type || 'agent route'}</strong>
                            <small>{workflow.workflow_id || workflow.id || ''}</small>
                          </div>
                          <div className="workflow-detail">
                            <span>{workflow.status || 'in_review'}</span>
                            {workflow.execution_history ? (
                              <pre>{formatPayload(workflow.execution_history)}</pre>
                            ) : null}
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    renderEmptyState('workflow history')
                  )}
                </div>
              </section>
            ) : null}
          </main>
        </>
      )}
    </div>
  )
}

export default App
