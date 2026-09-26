import json
import uuid

from sqlalchemy import select

from backend.db.database import SessionLocal
from backend.db.models import UserAction


def create_user_action(payload: dict) -> dict:
    session = SessionLocal()
    try:
        action_id = payload.get("action_id") or f"ACT-{str(uuid.uuid4())[:8]}"
        row = UserAction(
            action=payload["action"],
            username=payload.get("username"),
            role=payload.get("role"),
            details=json.dumps(payload.get("details", {})),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            "id": row.id,
            "action": row.action,
            "username": row.username,
            "role": row.role,
            "details": json.loads(row.details) if row.details else {},
        }
    finally:
        session.close()


def list_user_actions():
    session = SessionLocal()
    try:
        rows = session.execute(select(UserAction).order_by(UserAction.created_at.desc())).scalars().all()
        return [
            {
                "id": row.id,
                "action": row.action,
                "username": row.username,
                "role": row.role,
                "details": json.loads(row.details) if row.details else {},
            }
            for row in rows
        ]
    finally:
        session.close()
