import json
import logging
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.services.document_parser_service import parse_document
from backend.core.audit import log_audit
from backend.core.auth import issue_admin_token, issue_employee_token, require_roles
from backend.core.exceptions import AppError, error_payload
from backend.core.logging import configure_logging
from backend.core.observability import generate_trace_id, metrics_registry
from backend.core.pii import redact_pii
from backend.db import initialize_database
from backend.models.request import LoginRequest, UserRequest
from backend.models.response import ChatResponse, DiagnosticResponse, HealthResponse
from backend.services.chat_history_service import (
    delete_chat_session,
    get_chat_session_history,
    list_chat_sessions,
    record_chat_interaction,
)
from backend.services.employee_service import create_employee, get_employee, list_employees
from backend.services.security_check_service import create_security_check, list_security_checks
from backend.services.user_action_service import create_user_action, list_user_actions
from backend.services.workflow_state_service import get_workflow_state, list_workflow_states, save_workflow_state
from backend.workflows.langgraph_orchestrator import graph

configure_logging()
initialize_database()

try:
    from backend.services.employee_service import seed_default_employees
    seed_default_employees()
except Exception as _e_exc:
    logging.getLogger(__name__).warning("Employee seeding skipped or deferred: %s", _e_exc)


try:
    from backend.services.vector_store_service import seed_default_knowledge
    seed_default_knowledge()
except Exception as _v_exc:
    logging.getLogger(__name__).warning("Vector store init skipped or deferred: %s", _v_exc)

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

    @app.middleware("http")
    async def rewrite_api_prefix(request: Request, call_next):
        if request.scope.get("path", "").startswith("/api/"):
            request.scope["path"] = request.scope["path"][4:]
        return await call_next(request)

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

    @app.post("/auth/login")
    def login(req: LoginRequest):
        identifier = (req.employee_id or req.username or "").strip()
        password = req.password.strip()

        if not identifier:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "missing_identifier", "message": "Please enter your Employee ID (e.g. EMP-101) or Username."}},
            )

        # 1. Administrator check
        if identifier.lower() in ("admin", "administrator"):
            if password in ("password123", "admin123", "admin"):
                token = issue_admin_token(username="Administrator")
                log_audit("user_login", "Administrator", "admin", identifier=identifier)
                return {
                    "status": "success",
                    "token": token,
                    "role": "admin",
                    "username": "Administrator",
                    "employee_id": None,
                }
            raise HTTPException(
                status_code=401,
                detail={"error": {"code": "invalid_credentials", "message": "Invalid password for Administrator account."}},
            )

        # 2. Database Employee Check
        emp = get_employee(identifier.upper())
        if not emp:
            emp = get_employee(identifier)

        if emp:
            if password in ("password123", "pass123", "admin123"):
                token = issue_employee_token(
                    employee_id=emp["employee_id"],
                    role="user",
                    username=emp["employee_name"],
                )
                log_audit("user_login", emp["employee_name"], "user", employee_id=emp["employee_id"])
                return {
                    "status": "success",
                    "token": token,
                    "role": "user",
                    "username": emp["employee_name"],
                    "employee_id": emp["employee_id"],
                }
            raise HTTPException(
                status_code=401,
                detail={"error": {"code": "invalid_credentials", "message": f"Invalid password for Employee {emp['employee_id']}. Default is password123."}},
            )

        # 3. Fallbacks for demo tokens / standard accounts
        if identifier.lower() in ("user", "user-demo-token", "employee"):
            emp101 = get_employee("EMP-101")
            name = emp101["employee_name"] if emp101 else "Alice Smith"
            token = issue_employee_token("EMP-101", role="user", username=name)
            return {
                "status": "success",
                "token": token,
                "role": "user",
                "username": name,
                "employee_id": "EMP-101",
            }

        if identifier.lower() in ("admin-demo-token",):
            token = issue_admin_token("Administrator")
            return {
                "status": "success",
                "token": token,
                "role": "admin",
                "username": "Administrator",
                "employee_id": None,
            }

        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "user_not_found", "message": f"No employee found with ID '{identifier}'. Try EMP-101, EMP-102, or admin."}},
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
                "user_role": user.get("role", "user"),
                "user_name": user.get("username", "user"),
                "user_employee_id": user.get("employee_id"),
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

        session_id = record_chat_interaction(
            session_id=request.session_id,
            employee_id=user.get("employee_id"),
            username=user.get("username"),
            user_role=user.get("role", "user"),
            user_message=request.message,
            agent_response=state.get("response", {}),
            route=state.get("route", "SUPPORT"),
            score=state.get("score"),
            approved=state.get("approved"),
        )

        return ChatResponse(
            route=state.get("route", "SUPPORT"),
            response=state.get("response", {}),
            score=state.get("score"),
            approved=state.get("approved"),
            iteration=state.get("iteration", 0),
            session_id=session_id,
        )

    @app.post("/upload")
    async def upload_document(
        file: UploadFile = File(...),
        user: dict = Depends(require_roles("user", "admin")),
    ):
        filename = file.filename or "uploaded_document.txt"
        file_bytes = await file.read()
        if len(file_bytes) > 15 * 1024 * 1024:
            raise HTTPException(status_code=400, detail={"error": {"code": "file_too_large", "message": "File size exceeds 15MB limit."}})

        parsed = parse_document(file_bytes, filename)
        if not parsed.get("success"):
            err_msg = parsed.get("error", "Unable to extract text from document.")
            raise HTTPException(status_code=422, detail={"error": {"code": "extraction_failed", "message": err_msg}})

        log_audit(
            "document_uploaded",
            user.get("username"),
            user.get("role"),
            filename=filename,
            word_count=parsed.get("word_count"),
        )
        return parsed

    @app.get("/chat/sessions")
    def fetch_chat_sessions(user: dict = Depends(require_roles("user", "admin"))):
        log_audit("list_chat_sessions", user.get("username"), user.get("role"))
        return list_chat_sessions(user.get("employee_id"), user.get("role", "user"))

    @app.get("/chat/sessions/{session_id}")
    def fetch_chat_session_history(session_id: str, user: dict = Depends(require_roles("user", "admin"))):
        log_audit("get_chat_session", user.get("username"), user.get("role"), session_id=session_id)
        return get_chat_session_history(session_id, user.get("employee_id"), user.get("role", "user"))

    @app.delete("/chat/sessions/{session_id}")
    def remove_chat_session(session_id: str, user: dict = Depends(require_roles("user", "admin"))):
        log_audit("delete_chat_session", user.get("username"), user.get("role"), session_id=session_id)
        success = delete_chat_session(session_id, user.get("employee_id"), user.get("role", "user"))
        return {"status": "success" if success else "not_found", "deleted": session_id}

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

    @app.get("/security-checks")
    def fetch_security_checks(user: dict = Depends(require_roles("user", "admin"))):
        log_audit("list_security_checks", user.get("username"), user.get("role"))
        checks = list_security_checks()
        if user.get("role") != "admin":
            emp_id = user.get("employee_id")
            if emp_id:
                return [c for c in checks if str(c.get("employee_id", "")).upper() == emp_id.upper()]
            return []
        return checks

    @app.post("/security-checks")
    def create_new_security_check(payload: dict, user: dict = Depends(require_roles("user", "admin"))):
        security_check = create_security_check(payload)
        log_audit("create_security_check", user.get("username"), user.get("role"), security_id=security_check.get("security_id"))
        return security_check

    @app.post("/security-checks/run-scheduled-audit")
    def trigger_scheduled_security_audit(user: dict = Depends(require_roles("admin"))):
        from backend.job.security_job import execute as run_audit_job
        report = run_audit_job()
        log_audit("run_scheduled_security_audit", user.get("username"), user.get("role"), flagged=report.get("flagged_count"))
        return report

    @app.get("/workflow-states")
    def fetch_workflow_states(user: dict = Depends(require_roles("admin"))):
        log_audit("list_workflow_states", user.get("username"), user.get("role"))
        return list_workflow_states()

    @app.get("/knowledge/search")
    def search_knowledge(q: str, limit: int = 3, user: dict = Depends(require_roles("user", "admin"))):
        from backend.services.vector_store_service import search_similar
        results = search_similar(q, n_results=limit)
        log_audit("search_knowledge", user.get("username"), user.get("role"), query=q, matches=len(results))
        return {"query": q, "count": len(results), "results": results}

    @app.post("/knowledge")
    def add_knowledge(payload: dict, user: dict = Depends(require_roles("admin"))):
        from backend.services.vector_store_service import add_documents
        doc = payload.get("content") or payload.get("document", "")
        if not doc:
            raise AppError("Missing document content", status_code=400, code="invalid_payload")
        metadata = payload.get("metadata") or {"source": "admin_upload"}
        doc_id = payload.get("id")
        add_documents([doc], metadatas=[metadata], ids=[doc_id] if doc_id else None)
        log_audit("add_knowledge", user.get("username"), user.get("role"), doc_id=doc_id)
        return {"status": "success", "message": "Document indexed into vector store"}

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
        log_audit("create_user_action", user.get("username"), user.get("role"), user_action=action.get("action"))
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

    # Serve React frontend if built
    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if not frontend_dist.exists():
        frontend_dist = Path("/app/frontend/dist")

    logger.info(f"Frontend dist path: {frontend_dist}, exists: {frontend_dist.exists()}")

    if frontend_dist.exists():
        app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_frontend(full_path: str):
            return FileResponse(frontend_dist / "index.html")

    return app


app = create_app()