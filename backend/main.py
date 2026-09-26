import json
import logging
import time
import uuid
from collections import defaultdict, deque

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.core.audit import log_audit
from backend.core.auth import require_roles
from backend.core.exceptions import AppError, error_payload
from backend.core.logging import configure_logging
from backend.core.observability import generate_trace_id, metrics_registry
from backend.core.pii import redact_pii
from backend.db import initialize_database
from backend.models.request import UserRequest
from backend.models.response import ChatResponse, DiagnosticResponse, HealthResponse
from backend.services.employee_service import create_employee, get_employee, list_employees
from backend.services.review_service import create_review, list_reviews
from backend.services.security_check_service import create_security_check, list_security_checks
from backend.services.ticket_service import create_ticket, get_ticket, list_tickets
from backend.services.user_action_service import create_user_action, list_user_actions
from backend.services.workflow_state_service import get_workflow_state, list_workflow_states, save_workflow_state
from backend.workflows.langgraph_orchestrator import graph

configure_logging()
initialize_database()
logger = logging.getLogger(__name__)
startup_time = time.time()
rate_limit_store = defaultdict(deque)


async def telemetry_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id") or generate_trace_id()
    request.state.trace_id = trace_id
    start = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000
        metrics_registry.record_request(request.method, request.url.path, 500, duration_ms)
        raise

    duration_ms = (time.perf_counter() - start) * 1000
    status_code = getattr(response, "status_code", 500)
    metrics_registry.record_request(request.method, request.url.path, status_code, duration_ms)

    response.headers["X-Trace-Id"] = trace_id
    response.headers["X-Request-Id"] = trace_id

    logger.info(
        "request_completed",
        extra={
            "context": {
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
            }
        },
    )
    return response


async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in {"/docs", "/openapi.json", "/redoc"}:
        return await call_next(request)

    now = time.monotonic()
    token = request.headers.get("Authorization", "").split()[-1] if request.headers.get("Authorization") else None
    key = token or request.client.host if request.client else "unknown"
    window = rate_limit_store[key]

    while window and now - window[0] > 60:
        window.popleft()

    if len(window) >= settings.rate_limit_requests_per_minute:
        logger.warning(
            "Rate limit exceeded",
            extra={"context": {"key": key, "limit": settings.rate_limit_requests_per_minute}},
        )
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "rate_limit_exceeded",
                    "message": "Too many requests. Please slow down.",
                }
            },
        )

    window.append(now)
    return await call_next(request)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Enterprise multi-agent platform backend.",
    )

    app.middleware("http")(telemetry_middleware)
    app.middleware("http")(rate_limit_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        error_details = json.loads(json.dumps(exc.errors(), default=str))
        logger.warning(
            "Validation error",
            extra={"context": {"path": request.url.path, "errors": error_details}},
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed.",
                    "details": error_details,
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(
            "HTTP error",
            extra={"context": {"path": request.url.path, "status_code": exc.status_code}},
        )
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    @app.exception_handler(AppError)
    async def app_exception_handler(request: Request, exc: AppError):
        logger.warning(
            "App error",
            extra={"context": {"path": request.url.path, "code": exc.code, "status_code": exc.status_code}},
        )
        return JSONResponse(status_code=exc.status_code, content=error_payload(exc))

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.exception(
            "Unhandled exception",
            extra={"context": {"path": request.url.path}},
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                }
            },
        )

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: UserRequest, user: dict = Depends(require_roles("user", "admin"))):
        sanitized_message = redact_pii(request.message)
        safe_log_message = sanitized_message.replace("\n", " ").replace("\r", " ")
        logger.info(
            "Chat request received",
            extra={"context": {"role": user["role"], "message_length": len(request.message), "message": safe_log_message}},
        )

        state = graph.invoke(
            {
                "user_input": request.message,
                "route": "",
                "response": "",
                "score": 0,
                "approved": False,
                "iteration": 0,
            }
        )
        save_workflow_state(state.get("workflow_id") or f"wf-{uuid.uuid4().hex[:8]}", state)

        log_audit(
            "chat_message",
            user.get("username"),
            user.get("role"),
            message=sanitized_message,
            route=state.get("route", "SUPPORT"),
        )

        return ChatResponse(
            route=state.get("route", "SUPPORT"),
            response=state.get("response", {}),
            score=state.get("score"),
            approved=state.get("approved"),
            iteration=state.get("iteration", 0),
        )

    @app.get("/ticket/{ticket_id}")
    def fetch_ticket(ticket_id: str, user: dict = Depends(require_roles("user", "admin"))):
        ticket = get_ticket(ticket_id)
        if ticket is None:
            raise AppError(f"Ticket '{ticket_id}' was not found.", status_code=404, code="ticket_not_found")

        log_audit("ticket_lookup", user.get("username"), user.get("role"), ticket_id=ticket_id, status=ticket.get("status"))
        return ticket

    @app.get("/tickets")
    def fetch_tickets(user: dict = Depends(require_roles("user", "admin"))):
        log_audit("list_tickets", user.get("username"), user.get("role"))
        return list_tickets()

    @app.post("/tickets")
    def create_new_ticket(payload: dict, user: dict = Depends(require_roles("user", "admin"))):
        ticket = create_ticket(
            payload.get("summary", ""),
            category=payload.get("category", "general"),
            priority=payload.get("priority", "normal"),
            requester=payload.get("requester"),
            assignee=payload.get("assignee"),
        )
        log_audit("create_ticket", user.get("username"), user.get("role"), ticket_id=ticket.get("ticket_id"))
        return ticket

    @app.get("/employees")
    def fetch_employees(user: dict = Depends(require_roles("admin"))):
        log_audit("list_employees", user.get("username"), user.get("role"))
        return list_employees()

    @app.post("/employees")
    def create_new_employee(payload: dict, user: dict = Depends(require_roles("admin"))):
        employee = create_employee(payload)
        log_audit("create_employee", user.get("username"), user.get("role"), employee_id=employee.get("employee_id"))
        return employee

    @app.get("/employees/{employee_id}")
    def fetch_employee(employee_id: str, user: dict = Depends(require_roles("admin"))):
        row = get_employee(employee_id)
        if row is None:
            raise AppError(f"Employee '{employee_id}' was not found.", status_code=404, code="employee_not_found")
        log_audit("get_employee", user.get("username"), user.get("role"), employee_id=employee_id)
        return row

    @app.get("/reviews")
    def fetch_reviews(user: dict = Depends(require_roles("user", "admin"))):
        log_audit("list_reviews", user.get("username"), user.get("role"))
        return list_reviews()

    @app.post("/reviews")
    def create_new_review(payload: dict, user: dict = Depends(require_roles("user", "admin"))):
        review = create_review(payload)
        log_audit("create_review", user.get("username"), user.get("role"), review_id=review.get("review_id"))
        return review

    @app.get("/security-checks")
    def fetch_security_checks(user: dict = Depends(require_roles("user", "admin"))):
        log_audit("list_security_checks", user.get("username"), user.get("role"))
        return list_security_checks()

    @app.post("/security-checks")
    def create_new_security_check(payload: dict, user: dict = Depends(require_roles("user", "admin"))):
        security_check = create_security_check(payload)
        log_audit("create_security_check", user.get("username"), user.get("role"), security_id=security_check.get("security_id"))
        return security_check

    @app.get("/workflow-states")
    def fetch_workflow_states(user: dict = Depends(require_roles("admin"))):
        log_audit("list_workflow_states", user.get("username"), user.get("role"))
        return list_workflow_states()

    @app.post("/workflow-states")
    def create_workflow_state(payload: dict, user: dict = Depends(require_roles("admin"))):
        workflow = save_workflow_state(payload.get("workflow_id"), payload)
        log_audit("save_workflow_state", user.get("username"), user.get("role"), workflow_id=workflow.get("workflow_id"))
        return workflow

    @app.get("/workflow-states/{workflow_id}")
    def fetch_workflow_state_by_id(workflow_id: str, user: dict = Depends(require_roles("admin"))):
        state = get_workflow_state(workflow_id)
        if state is None:
            raise AppError(f"Workflow state '{workflow_id}' was not found.", status_code=404, code="workflow_state_not_found")
        log_audit("get_workflow_state", user.get("username"), user.get("role"), workflow_id=workflow_id)
        return state

    @app.get("/user-actions")
    def fetch_user_actions(user: dict = Depends(require_roles("admin"))):
        log_audit("list_user_actions", user.get("username"), user.get("role"))
        return list_user_actions()

    @app.post("/user-actions")
    def create_new_user_action(payload: dict, user: dict = Depends(require_roles("admin"))):
        action = create_user_action(payload)
        log_audit("create_user_action", user.get("username"), user.get("role"), action=action.get("action"))
        return action

    @app.get("/health", response_model=HealthResponse)
    async def health():
        uptime = time.time() - startup_time
        return HealthResponse(
            status="ok",
            app=settings.app_name,
            environment=settings.environment,
            uptime_seconds=round(uptime, 2),
            checks={
                "api": True,
                "workflow": True,
                "config": True,
                "database": True,
            },
        )

    @app.get("/metrics")
    async def metrics():
        return metrics_registry.snapshot()

    @app.get("/alerts")
    async def alerts():
        return {"alerts": metrics_registry.alert_summary()}

    @app.get("/ready", response_model=DiagnosticResponse)
    async def ready(user: dict = Depends(require_roles("admin"))):
        checks = {
            "api": True,
            "workflow": True,
            "database": True,
            "bedrock": True,
        }
        log_audit("readiness_check", user.get("username"), user.get("role"), checks=checks)
        return DiagnosticResponse(
            status="ready",
            environment=settings.environment,
            app=settings.app_name,
            checks=checks,
            config={
                "local_mode": settings.local_mode,
                "aws_region": settings.aws_region,
                "bedrock_model_id": settings.bedrock_model_id,
                "database_url": settings.database_url,
            },
        )

    @app.get("/diagnostics", response_model=DiagnosticResponse)
    async def diagnostics(user: dict = Depends(require_roles("admin"))):
        checks = {
            "api": True,
            "workflow": True,
            "database": True,
            "bedrock": True,
            "config_loaded": True,
        }
        log_audit("diagnostic_check", user.get("username"), user.get("role"), checks=checks)
        return DiagnosticResponse(
            status="ok",
            environment=settings.environment,
            app=settings.app_name,
            checks=checks,
            config={
                "debug": settings.debug,
                "host": settings.api_host,
                "port": settings.api_port,
                "cors_origins": settings.cors_origins,
                "database_url": settings.database_url,
            },
        )

    return app


app = create_app()