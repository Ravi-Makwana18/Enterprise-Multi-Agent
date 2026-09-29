from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, desc, select

from backend.core.exceptions import AppError
from backend.db.database import SessionLocal
from backend.db.models import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


def get_or_create_session(
    session_id: str | None,
    employee_id: str | None,
    username: str | None,
    user_role: str = "user",
    initial_message: str | None = None,
) -> tuple[ChatSession, bool]:
    """Retrieve an existing chat session or create a new one bound to the employee."""
    db = SessionLocal()
    try:
        session = None
        if session_id:
            session = db.execute(
                select(ChatSession).where(ChatSession.session_id == session_id)
            ).scalar_one_or_none()

            if session:
                # Security boundary: ensure standard employee cannot access another employee's session
                if user_role != "admin" and session.employee_id and employee_id:
                    if session.employee_id.upper() != employee_id.upper():
                        raise AppError(
                            "Unauthorized access to another employee's chat session.",
                            status_code=403,
                            code="forbidden_chat_session",
                        )
                return session, False

        # Create new session bound to this employee / user
        prefix = employee_id.lower().replace("-", "_") if employee_id else "adm"
        new_session_id = f"cs_{prefix}_{uuid.uuid4().hex[:12]}"
        
        title = "New Chat"
        if initial_message:
            trimmed = initial_message.strip()
            title = trimmed[:35] + ("…" if len(trimmed) > 35 else "")

        new_session = ChatSession(
            session_id=new_session_id,
            employee_id=employee_id,
            username=username,
            user_role=user_role,
            title=title,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return new_session, True
    finally:
        db.close()


def record_chat_interaction(
    session_id: str | None,
    employee_id: str | None,
    username: str | None,
    user_role: str,
    user_message: str,
    agent_response: dict[str, Any],
    route: str = "SUPPORT",
    score: float | None = None,
    approved: bool | None = None,
) -> str:
    """Persist both the user prompt and the agent response into the database."""
    session, _ = get_or_create_session(
        session_id=session_id,
        employee_id=employee_id,
        username=username,
        user_role=user_role,
        initial_message=user_message,
    )

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        
        # 1. Record User Message
        user_msg = ChatMessage(
            session_id=session.session_id,
            sender="user",
            content=user_message,
            created_at=now,
        )
        db.add(user_msg)

        # 2. Record Agent Message
        summary = (
            agent_response.get("message")
            or agent_response.get("blog_content")
            or agent_response.get("revised_content")
            or agent_response.get("summary")
            or "Agent response generated"
        )
        raw_json = json.dumps(agent_response)

        agent_msg = ChatMessage(
            session_id=session.session_id,
            sender="agent",
            content=str(summary),
            route=route,
            raw_response=raw_json,
            score=score,
            approved=approved,
            created_at=now,
        )
        db.add(agent_msg)

        # Update session timestamp
        db_sess = db.execute(
            select(ChatSession).where(ChatSession.session_id == session.session_id)
        ).scalar_one_or_none()
        if db_sess:
            db_sess.updated_at = now
            if db_sess.title == "New Chat" and user_message:
                trimmed = user_message.strip()
                db_sess.title = trimmed[:35] + ("…" if len(trimmed) > 35 else "")

        db.commit()
        return session.session_id
    finally:
        db.close()


def list_chat_sessions(employee_id: str | None, user_role: str) -> list[dict[str, Any]]:
    """List chat sessions belonging to the authenticated employee or all if admin."""
    db = SessionLocal()
    try:
        query = select(ChatSession).order_by(desc(ChatSession.updated_at))
        if user_role != "admin":
            if employee_id:
                query = query.where(ChatSession.employee_id == employee_id)
            else:
                return []

        rows = db.execute(query).scalars().all()
        return [
            {
                "id": r.session_id,
                "session_id": r.session_id,
                "title": r.title,
                "employee_id": r.employee_id,
                "username": r.username,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ]
    finally:
        db.close()


def get_chat_session_history(session_id: str, employee_id: str | None, user_role: str) -> dict[str, Any]:
    """Retrieve full conversation messages for a session formatted for the UI."""
    db = SessionLocal()
    try:
        session = db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        ).scalar_one_or_none()

        if not session:
            raise AppError(f"Chat session '{session_id}' was not found.", status_code=404, code="session_not_found")

        # Authorization check
        if user_role != "admin" and session.employee_id and employee_id:
            if session.employee_id.upper() != employee_id.upper():
                raise AppError(
                    "Unauthorized: You cannot access chat history belonging to another employee.",
                    status_code=403,
                    code="forbidden_chat_session",
                )

        raw_messages = db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        ).scalars().all()

        # Group sequential user & agent messages into turns:
        # format: [{ "input": "user text", "reply": { "route": "...", "score": 90, "approved": True, "response": {...} } }]
        formatted_turns: list[dict[str, Any]] = []
        pending_user: str | None = None

        for msg in raw_messages:
            if msg.sender == "user":
                if pending_user is not None:
                    # Previous user message without agent reply
                    formatted_turns.append({"input": pending_user, "reply": {"response": {"message": ""}}})
                pending_user = msg.content
            elif msg.sender == "agent":
                parsed_resp: dict[str, Any] = {}
                if msg.raw_response:
                    try:
                        parsed_resp = json.loads(msg.raw_response)
                    except Exception:
                        parsed_resp = {"message": msg.content}
                else:
                    parsed_resp = {"message": msg.content}

                user_text = pending_user or ""
                pending_user = None

                formatted_turns.append({
                    "input": user_text,
                    "reply": {
                        "route": msg.route or "SUPPORT",
                        "response": parsed_resp,
                        "score": msg.score,
                        "approved": msg.approved,
                    }
                })

        if pending_user is not None:
            formatted_turns.append({"input": pending_user, "reply": {"response": {"message": ""}}})

        # Most recent first for the UI's messages list
        formatted_turns.reverse()

        return {
            "id": session.session_id,
            "session_id": session.session_id,
            "title": session.title,
            "employee_id": session.employee_id,
            "username": session.username,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "messages": formatted_turns,
        }
    finally:
        db.close()


def delete_chat_session(session_id: str, employee_id: str | None, user_role: str) -> bool:
    """Delete a chat session and all its messages."""
    db = SessionLocal()
    try:
        session = db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        ).scalar_one_or_none()

        if not session:
            return False

        if user_role != "admin" and session.employee_id and employee_id:
            if session.employee_id.upper() != employee_id.upper():
                raise AppError(
                    "Unauthorized to delete this chat session.",
                    status_code=403,
                    code="forbidden_chat_session",
                )

        db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
        db.execute(delete(ChatSession).where(ChatSession.session_id == session_id))
        db.commit()
        return True
    finally:
        db.close()
