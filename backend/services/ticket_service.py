import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from backend.db.database import SessionLocal
from backend.db.models import Ticket

VALID_TICKET_STATUSES = {"submitted", "in review", "approved", "rejected", "escalated"}
ALLOWED_TICKET_TRANSITIONS = {
    "submitted": {"in review", "approved", "rejected", "escalated"},
    "in review": {"approved", "rejected", "escalated"},
    "approved": {"submitted", "in review", "escalated"},
    "rejected": {"submitted", "in review", "escalated"},
    "escalated": {"in review", "approved", "rejected"},
}


def _normalize_status(status: str | None) -> str:
    candidate = (status or "submitted").strip().lower()
    if candidate not in VALID_TICKET_STATUSES:
        raise ValueError(f"Unsupported ticket status: {status}")
    return candidate


def create_ticket(
    summary: str,
    *,
    category: str = "general",
    priority: str = "normal",
    requester: str | None = None,
    assignee: str | None = None,
    status: str = "submitted",
) -> dict:
    if not summary or not str(summary).strip():
        raise ValueError("Ticket summary is required")

    normalized_status = _normalize_status(status)
    ticket_id = f"TKT-{str(uuid.uuid4())[:8]}"
    session = SessionLocal()
    try:
        ticket = Ticket(
            ticket_id=ticket_id,
            summary=str(summary).strip(),
            status=normalized_status,
            category=category,
            priority=priority,
            requester=requester,
            assignee=assignee,
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        return {
            "ticket_id": ticket.ticket_id,
            "summary": ticket.summary,
            "status": ticket.status,
            "category": ticket.category,
            "priority": ticket.priority,
            "requester": ticket.requester,
            "assignee": ticket.assignee,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        }
    finally:
        session.close()


def get_ticket(ticket_id: str):
    session = SessionLocal()
    try:
        ticket = session.execute(select(Ticket).where(Ticket.ticket_id == ticket_id)).scalar_one_or_none()
        if ticket is None:
            return None
        return {
            "ticket_id": ticket.ticket_id,
            "summary": ticket.summary,
            "status": ticket.status,
            "category": getattr(ticket, "category", "general"),
            "priority": getattr(ticket, "priority", "normal"),
            "requester": getattr(ticket, "requester", None),
            "assignee": getattr(ticket, "assignee", None),
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        }
    finally:
        session.close()


def list_tickets():
    session = SessionLocal()
    try:
        rows = session.execute(select(Ticket).order_by(Ticket.created_at.desc())).scalars().all()
        return [
            {
                "ticket_id": row.ticket_id,
                "summary": row.summary,
                "status": row.status,
                "category": getattr(row, "category", "general"),
                "priority": getattr(row, "priority", "normal"),
                "requester": getattr(row, "requester", None),
                "assignee": getattr(row, "assignee", None),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def update_ticket_status(ticket_id: str, status: str, *, reviewer: str | None = None, reason: str | None = None):
    normalized_status = _normalize_status(status)
    session = SessionLocal()
    try:
        ticket = session.execute(select(Ticket).where(Ticket.ticket_id == ticket_id)).scalar_one_or_none()
        if ticket is None:
            return None

        current_status = ticket.status.lower()
        if current_status in ALLOWED_TICKET_TRANSITIONS and normalized_status not in ALLOWED_TICKET_TRANSITIONS[current_status]:
            raise ValueError(
                f"Ticket status cannot transition from '{current_status}' to '{normalized_status}'"
            )

        if current_status == "submitted" and normalized_status == "approved":
            ticket.status = "approved"
        else:
            ticket.status = normalized_status

        ticket.updated_at = datetime.now(timezone.utc)
        ticket.reviewed_by = reviewer
        ticket.review_notes = reason or ticket.review_notes
        session.commit()
        session.refresh(ticket)
        return get_ticket(ticket_id)
    finally:
        session.close()


def escalate_ticket(ticket_id: str, *, reason: str, assignee: str | None = None):
    ticket = get_ticket(ticket_id)
    if ticket is None:
        return None
    return update_ticket_status(ticket_id, "escalated", reviewer=assignee, reason=reason)