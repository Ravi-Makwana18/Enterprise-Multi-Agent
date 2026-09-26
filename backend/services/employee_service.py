import uuid

from sqlalchemy import select

from backend.db.database import SessionLocal
from backend.db.models import Employee


def create_employee(payload: dict) -> dict:
    session = SessionLocal()
    try:
        employee_id = payload.get("employee_id") or f"EMP-{str(uuid.uuid4())[:8]}"
        employee = Employee(
            employee_id=employee_id,
            employee_name=payload["employee_name"],
            basic_salary=float(payload["basic_salary"]),
            hra=float(payload["hra"]),
            bonus=float(payload["bonus"]),
            pan=payload["pan"],
            account_number=payload["account_number"],
        )
        session.add(employee)
        session.commit()
        session.refresh(employee)
        return {
            "employee_id": employee.employee_id,
            "employee_name": employee.employee_name,
            "basic_salary": employee.basic_salary,
            "hra": employee.hra,
            "bonus": employee.bonus,
            "pan": employee.pan,
            "account_number": employee.account_number,
        }
    finally:
        session.close()


def get_employee(employee_id: str):
    session = SessionLocal()
    try:
        row = session.execute(select(Employee).where(Employee.employee_id == employee_id)).scalar_one_or_none()
        if row is None:
            return None
        return {
            "employee_id": row.employee_id,
            "employee_name": row.employee_name,
            "basic_salary": row.basic_salary,
            "hra": row.hra,
            "bonus": row.bonus,
            "pan": row.pan,
            "account_number": row.account_number,
        }
    finally:
        session.close()


def list_employees():
    session = SessionLocal()
    try:
        rows = session.execute(select(Employee).order_by(Employee.employee_name.asc())).scalars().all()
        return [
            {
                "employee_id": row.employee_id,
                "employee_name": row.employee_name,
                "basic_salary": row.basic_salary,
                "hra": row.hra,
                "bonus": row.bonus,
                "pan": row.pan,
                "account_number": row.account_number,
            }
            for row in rows
        ]
    finally:
        session.close()
