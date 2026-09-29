import uuid

from sqlalchemy import select

from backend.db.database import SessionLocal
from backend.db.models import SecurityCheck


def create_security_check(payload: dict) -> dict:
    session = SessionLocal()
    try:
        security_id = payload.get("security_id") or f"SEC-{str(uuid.uuid4())[:8]}"
        record = SecurityCheck(
            security_id=security_id,
            employee_id=payload.get("employee_id"),
            employee_name=payload.get("employee_name", ""),
            passport=payload.get("passport"),
            aadhaar=payload.get("aadhaar"),
            address=payload.get("address"),
            police_verification=payload.get("police_verification"),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return {
            "security_id": record.security_id,
            "employee_id": record.employee_id,
            "employee_name": record.employee_name,
            "passport": record.passport,
            "aadhaar": record.aadhaar,
            "address": record.address,
            "police_verification": record.police_verification,
        }
    finally:
        session.close()


def list_security_checks():
    session = SessionLocal()
    try:
        rows = session.execute(select(SecurityCheck).order_by(SecurityCheck.created_at.desc())).scalars().all()
        return [
            {
                "security_id": row.security_id,
                "employee_id": row.employee_id,
                "employee_name": row.employee_name,
                "passport": row.passport,
                "aadhaar": row.aadhaar,
                "address": row.address,
                "police_verification": row.police_verification,
            }
            for row in rows
        ]
    finally:
        session.close()


def get_security_check_by_employee_id(employee_id: str):
    session = SessionLocal()
    try:
        row = session.execute(
            select(SecurityCheck).where(SecurityCheck.employee_id == employee_id).order_by(SecurityCheck.created_at.desc())
        ).scalars().first()
        if row is None:
            return None
        return {
            "security_id": row.security_id,
            "employee_id": row.employee_id,
            "employee_name": row.employee_name,
            "passport": row.passport,
            "aadhaar": row.aadhaar,
            "address": row.address,
            "police_verification": row.police_verification,
        }
    finally:
        session.close()

