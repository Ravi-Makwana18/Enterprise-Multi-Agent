import json
import uuid

from sqlalchemy import select

from backend.db.database import SessionLocal
from backend.db.models import WorkflowState


def save_workflow_state(workflow_id: str | None, payload: dict) -> dict:
    session = SessionLocal()
    try:
        workflow_key = workflow_id or f"WF-{str(uuid.uuid4())[:8]}"
        row = session.execute(select(WorkflowState).where(WorkflowState.workflow_id == workflow_key)).scalar_one_or_none()
        if row is None:
            row = WorkflowState(workflow_id=workflow_key)
            session.add(row)

        row.user_input = payload.get("user_input", row.user_input or "")
        row.route = payload.get("route", row.route or "SUPPORT")
        row.response = json.dumps(payload.get("response", {})) if isinstance(payload.get("response", {}), (dict, list)) else payload.get("response")
        row.score = payload.get("score", row.score or 0)
        row.approved = bool(payload.get("approved", row.approved or False))
        row.iteration = payload.get("iteration", row.iteration or 0)

        session.commit()
        session.refresh(row)
        return {
            "workflow_id": row.workflow_id,
            "user_input": row.user_input,
            "route": row.route,
            "response": json.loads(row.response) if row.response else {},
            "score": row.score,
            "approved": row.approved,
            "iteration": row.iteration,
        }
    finally:
        session.close()


def get_workflow_state(workflow_id: str):
    session = SessionLocal()
    try:
        row = session.execute(select(WorkflowState).where(WorkflowState.workflow_id == workflow_id)).scalar_one_or_none()
        if row is None:
            return None
        return {
            "workflow_id": row.workflow_id,
            "user_input": row.user_input,
            "route": row.route,
            "response": json.loads(row.response) if row.response else {},
            "score": row.score,
            "approved": row.approved,
            "iteration": row.iteration,
        }
    finally:
        session.close()


def list_workflow_states():
    session = SessionLocal()
    try:
        rows = session.execute(select(WorkflowState).order_by(WorkflowState.updated_at.desc())).scalars().all()
        return [
            {
                "workflow_id": row.workflow_id,
                "user_input": row.user_input,
                "route": row.route,
                "response": json.loads(row.response) if row.response else {},
                "score": row.score,
                "approved": row.approved,
                "iteration": row.iteration,
            }
            for row in rows
        ]
    finally:
        session.close()
