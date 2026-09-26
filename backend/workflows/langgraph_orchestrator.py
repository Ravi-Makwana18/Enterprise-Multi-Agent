import uuid
from datetime import datetime, timezone
from typing import Literal

from langgraph.graph import END, StateGraph

from backend.agents.salary_agent import calculate_employee_salary
from backend.agents.security_agent import run_security_check
from backend.agents.support_agent import create_support_ticket
from backend.models.state import AgentState
from backend.workflows.blog_workflow import blog_graph

ROUTE_TO_NODE = {
    "BLOG": "blog_agent",
    "SALARY": "salary_agent",
    "SECURITY": "security_agent",
    "SUPPORT": "support_agent",
}


def normalize_route(route: str | None) -> str:
    if route is None:
        return "SUPPORT"
    candidate = str(route).strip().upper()
    return candidate if candidate in ROUTE_TO_NODE else "SUPPORT"


def normalize_state(state: AgentState) -> AgentState:
    normalized = dict(state)
    normalized["user_input"] = str(normalized.get("user_input", "")).strip()
    normalized["route"] = normalize_route(normalized.get("route"))
    normalized["response"] = normalized.get("response") if isinstance(normalized.get("response"), dict) else {"status": "pending"}
    normalized["score"] = float(normalized.get("score", 0))
    normalized["approved"] = bool(normalized.get("approved", False))
    normalized["iteration"] = int(normalized.get("iteration", 0))
    normalized["workflow_id"] = normalized.get("workflow_id") or f"wf-{uuid.uuid4().hex[:8]}"
    normalized["status"] = normalized.get("status") or "submitted"
    normalized["execution_history"] = normalized.get("execution_history") or []
    normalized["last_error"] = normalized.get("last_error")
    normalized["cancelled"] = bool(normalized.get("cancelled", False))
    normalized["replay_of"] = normalized.get("replay_of")
    return normalized


def record_observation(state: AgentState, event: str, **details) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "details": details,
    }
    state["execution_history"] = state.get("execution_history", []) + [entry]


def build_standard_response(state: AgentState, status: str, payload: dict | None = None, error: str | None = None) -> dict:
    response = payload.copy() if isinstance(payload, dict) else {}
    if error:
        response["error"] = error
    response.setdefault("status", status)
    response.setdefault("route", normalize_route(state.get("route")))
    response.setdefault("workflow_id", state.get("workflow_id"))
    return response


def _llm_classify_intent(user_input: str) -> str:
    """Use LLM reasoning to classify user intent when keywords are ambiguous."""
    try:
        from backend.services import llm_service
        prompt = (
            "Classify the enterprise user request into exactly ONE category: 'BLOG', 'SALARY', 'SECURITY', or 'SUPPORT'.\n"
            "- BLOG: requests to write, review, critique, or polish blog posts or articles\n"
            "- SALARY: questions about payroll, compensation, pay calculation, tax deduction, or bonuses\n"
            "- SECURITY: personnel security clearance, ID checks, background verification, compliance audits\n"
            "- SUPPORT: IT help, service desk, access issues, system bugs, software help, or general issues\n\n"
            f"User request: \"{user_input[:500]}\"\n\n"
            "Return ONLY JSON: {\"route\": \"BLOG\" | \"SALARY\" | \"SECURITY\" | \"SUPPORT\"}"
        )
        res = llm_service.generate(prompt, model_key="router")
        route_cand = str(res.get("route", "")).upper()
        if route_cand in ROUTE_TO_NODE:
            return route_cand
    except Exception:
        pass
    return "SUPPORT"


def classify_request(state: AgentState):
    normalized = normalize_state(state)
    text = normalized["user_input"].lower()

    # 1. Deterministic fast heuristic
    if any(w in text for w in ("blog", "article", "draft", "write", "rewrite", "essay")):
        route = "BLOG"
    elif any(w in text for w in ("salary", "pay", "payroll", "compensation", "wage", "hra", "bonus")):
        route = "SALARY"
    elif any(w in text for w in ("security", "compliance", "police verification", "aadhaar", "clearance", "audit")):
        route = "SECURITY"
    elif any(w in text for w in ("ticket", "incident", "outage", "broken", "issue", "bug", "support", "help", "login")):
        route = "SUPPORT"
    else:
        # 2. LLM intent classification for complex or subtle queries
        route = _llm_classify_intent(text)

    normalized["route"] = route
    normalized["status"] = "routed"
    normalized["response"] = build_standard_response(normalized, "routed", {"message": f"Request routed to {route} agent"})
    record_observation(normalized, "classified", route=route)
    return normalized


def blog_agent(state: AgentState):
    normalized = normalize_state(state)
    try:
        result = blog_graph.invoke(
            {
                "user_input": normalized["user_input"],
                "route": normalized["route"],
                "response": {},
                "score": 0,
                "approved": False,
                "iteration": 0,
            }
        )
        normalized["response"] = build_standard_response(normalized, "completed", result.get("response", result))
        normalized["score"] = float(result.get("score", normalized.get("score", 0)))
        normalized["approved"] = bool(result.get("approved", False))
        normalized["status"] = "completed"
        record_observation(normalized, "blog_agent_completed")
        return normalized
    except Exception as exc:
        normalized["status"] = "failed"
        normalized["last_error"] = str(exc)
        normalized["response"] = build_standard_response(normalized, "failed", {"message": "Blog workflow failed"}, str(exc))
        record_observation(normalized, "blog_agent_failed", error=str(exc))
        return normalized


def salary_agent(state):
    normalized = normalize_state(state)
    try:
        result = calculate_employee_salary(normalized)
        normalized["response"] = build_standard_response(normalized, "completed", result.get("response", result))
        normalized["score"] = float(result.get("score", normalized.get("score", 0)))
        normalized["approved"] = bool(result.get("approved", False))
        normalized["status"] = "completed"
        record_observation(normalized, "salary_agent_completed")
        return normalized
    except Exception as exc:
        normalized["status"] = "failed"
        normalized["last_error"] = str(exc)
        normalized["response"] = build_standard_response(normalized, "failed", {"message": "Salary workflow failed"}, str(exc))
        record_observation(normalized, "salary_agent_failed", error=str(exc))
        return normalized


def security_agent(state):
    normalized = normalize_state(state)
    try:
        result = run_security_check(normalized)
        normalized["response"] = build_standard_response(normalized, "completed", result.get("response", result))
        normalized["score"] = float(result.get("score", normalized.get("score", 0)))
        normalized["approved"] = bool(result.get("approved", False))
        normalized["status"] = "completed"
        record_observation(normalized, "security_agent_completed")
        return normalized
    except Exception as exc:
        normalized["status"] = "failed"
        normalized["last_error"] = str(exc)
        normalized["response"] = build_standard_response(normalized, "failed", {"message": "Security workflow failed"}, str(exc))
        record_observation(normalized, "security_agent_failed", error=str(exc))
        return normalized


def support_agent(state: AgentState):
    normalized = normalize_state(state)
    try:
        result = create_support_ticket(normalized)
        normalized["response"] = build_standard_response(normalized, "completed", result.get("response", result))
        normalized["score"] = float(result.get("score", normalized.get("score", 0)))
        normalized["approved"] = bool(result.get("approved", False))
        normalized["status"] = "completed"
        record_observation(normalized, "support_agent_completed")
        return normalized
    except Exception as exc:
        normalized["status"] = "failed"
        normalized["last_error"] = str(exc)
        normalized["response"] = build_standard_response(normalized, "failed", {"message": "Support workflow failed"}, str(exc))
        record_observation(normalized, "support_agent_failed", error=str(exc))
        return normalized


def route_error_handler(state: AgentState, error: Exception) -> str:
    normalized = normalize_state(state)
    normalized["status"] = "failed"
    normalized["last_error"] = str(error)
    normalized["response"] = build_standard_response(normalized, "failed", {"message": "Route decision failed"}, str(error))
    record_observation(normalized, "route_error", error=str(error))
    return "support_agent"


def execute_with_retry(node_name: str, state: AgentState, func, max_retries: int = 2):
    current = normalize_state(state)
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            record_observation(current, "agent_attempt", node=node_name, attempt=attempt + 1)
            result = func(current)
            current.update(normalize_state(result))
            current["status"] = current.get("status", "completed")
            return current
        except Exception as exc:
            last_error = str(exc)
            current["status"] = "retrying"
            current["last_error"] = last_error
            record_observation(current, "retry", node=node_name, attempt=attempt + 1, error=last_error)
            if attempt >= max_retries:
                current["status"] = "failed"
                current["response"] = build_standard_response(current, "failed", {"message": f"{node_name} failed after {max_retries + 1} attempts"}, last_error)
                record_observation(current, "agent_failed", node=node_name, attempts=attempt + 1, error=last_error)
                return current
    return current


def cancel_workflow(state: AgentState):
    normalized = normalize_state(state)
    normalized["cancelled"] = True
    normalized["status"] = "cancelled"
    normalized["response"] = build_standard_response(normalized, "cancelled", {"message": "Workflow cancelled"})
    record_observation(normalized, "cancelled")
    return normalized


def replay_workflow(state: AgentState, snapshot: dict):
    normalized = normalize_state(state)
    normalized.update(normalize_state(snapshot))
    normalized["status"] = "replayed"
    normalized["replay_of"] = snapshot.get("workflow_id") or normalized.get("workflow_id")
    normalized["response"] = build_standard_response(normalized, "replayed", {"message": "Workflow replayed"})
    record_observation(normalized, "replayed", replay_of=normalized["replay_of"])
    return normalized


def route_decision(state: AgentState) -> Literal["blog_agent", "salary_agent", "security_agent", "support_agent"]:
    normalized = normalize_state(state)
    route = normalize_route(normalized.get("route"))
    if route not in ROUTE_TO_NODE:
        normalized["status"] = "failed"
        normalized["last_error"] = f"Unknown route: {normalized.get('route')}"
        normalized["response"] = build_standard_response(normalized, "failed", {"message": "Route decision failed"}, normalized["last_error"])
        record_observation(normalized, "unsupported_route", route=normalized.get("route"))
        return "support_agent"
    return ROUTE_TO_NODE[route]


builder = StateGraph(AgentState)

builder.add_node("classifier", classify_request)
builder.add_node("blog_agent", lambda state: execute_with_retry("blog_agent", state, blog_agent))
builder.add_node("salary_agent", lambda state: execute_with_retry("salary_agent", state, salary_agent))
builder.add_node("security_agent", lambda state: execute_with_retry("security_agent", state, security_agent))
builder.add_node("support_agent", lambda state: execute_with_retry("support_agent", state, support_agent))

builder.set_entry_point("classifier")

builder.add_conditional_edges(
    "classifier",
    route_decision,
    {
        "blog_agent": "blog_agent",
        "salary_agent": "salary_agent",
        "security_agent": "security_agent",
        "support_agent": "support_agent",
    }
)

builder.add_edge("blog_agent", END)
builder.add_edge("salary_agent", END)
builder.add_edge("security_agent", END)
builder.add_edge("support_agent", END)

graph = builder.compile()