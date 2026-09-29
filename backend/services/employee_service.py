import csv
import os
import uuid

from sqlalchemy import select, func, or_

from backend.db.database import SessionLocal
from backend.db.models import Employee, SecurityCheck


def _format_employee_dict(row: Employee) -> dict:
    return {
        "employee_id": row.employee_id,
        "employee_name": row.employee_name,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "email": row.email,
        "phone": row.phone,
        "department": row.department,
        "designation": row.designation,
        "manager_name": row.manager_name,
        "location": row.location,
        "date_of_joining": row.date_of_joining,
        "employment_type": row.employment_type,
        "basic_salary": row.basic_salary,
        "hra": row.hra,
        "bonus": row.bonus,
        "annual_ctc": row.annual_ctc,
        "performance_rating": row.performance_rating,
        "gender": row.gender,
        "age": row.age,
        "pan": row.pan,
        "account_number": row.account_number,
    }


def create_employee(payload: dict) -> dict:
    session = SessionLocal()
    try:
        employee_id = payload.get("employee_id") or f"EMP-{str(uuid.uuid4())[:8]}"
        basic = float(payload.get("basic_salary", 50000.0))
        hra = float(payload.get("hra", round(basic * 0.25, 2)))
        bonus = float(payload.get("bonus", 10000.0))
        employee = Employee(
            employee_id=employee_id,
            employee_name=payload.get("employee_name") or payload.get("full_name") or "Employee",
            first_name=payload.get("first_name"),
            last_name=payload.get("last_name"),
            email=payload.get("email"),
            phone=payload.get("phone"),
            department=payload.get("department"),
            designation=payload.get("designation"),
            manager_name=payload.get("manager_name"),
            location=payload.get("location"),
            date_of_joining=payload.get("date_of_joining"),
            employment_type=payload.get("employment_type", "Full-Time"),
            basic_salary=basic,
            hra=hra,
            bonus=bonus,
            annual_ctc=float(payload.get("annual_ctc", (basic + hra + bonus) * 12)),
            performance_rating=float(payload.get("performance_rating", 3.5)),
            gender=payload.get("gender"),
            age=int(payload.get("age", 30)) if payload.get("age") else None,
            pan=payload.get("pan") or (f"ABCDE{employee_id[-4:]}F" if len(employee_id) >= 4 else "ABCDE1234F"),
            account_number=payload.get("account_number") or f"100200{employee_id[-4:].zfill(6)}",
        )
        session.add(employee)
        session.commit()
        session.refresh(employee)
        return _format_employee_dict(employee)
    finally:
        session.close()


def migrate_csv_to_sqlite(csv_path: str | None = None) -> dict:
    """Migrate all employee records from CSV file into the SQLite database."""
    if csv_path is None:
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "enterprise_employees.csv"
        )

    if not os.path.exists(csv_path):
        return {"status": "skipped", "message": f"CSV not found at {csv_path}", "count": 0}

    session = SessionLocal()
    migrated_count = 0
    updated_count = 0

    try:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                eid = (r.get("employee_id") or "").strip().upper()
                if not eid:
                    continue

                full_name = r.get("full_name") or f"{r.get('first_name', '')} {r.get('last_name', '')}".strip() or "Employee"
                salary = float(r.get("salary") or 50000.0)
                bonus = float(r.get("bonus") or 10000.0)
                hra = round(salary * 0.25, 2)
                ctc = float(r.get("annual_ctc") or (salary + hra + bonus) * 12)
                perf = float(r.get("performance_rating") or 3.5)
                age = int(r.get("age")) if r.get("age") and str(r.get("age")).isdigit() else None
                pan = f"ABCDE{eid[-4:]}F" if len(eid) >= 4 else "ABCDE1234F"
                acc = f"100200{eid[-4:].zfill(6)}"

                existing = session.execute(select(Employee).where(Employee.employee_id == eid)).scalar_one_or_none()
                if existing:
                    existing.department = r.get("department") or existing.department
                    existing.designation = r.get("designation") or existing.designation
                    existing.manager_name = r.get("manager_name") or existing.manager_name
                    existing.location = r.get("location") or existing.location
                    existing.first_name = r.get("first_name") or existing.first_name
                    existing.last_name = r.get("last_name") or existing.last_name
                    existing.email = r.get("email") or existing.email
                    existing.phone = r.get("phone") or existing.phone
                    existing.date_of_joining = r.get("date_of_joining") or existing.date_of_joining
                    existing.employment_type = r.get("employment_type") or existing.employment_type
                    existing.annual_ctc = ctc
                    existing.performance_rating = perf
                    existing.gender = r.get("gender") or existing.gender
                    existing.age = age
                    updated_count += 1
                else:
                    emp = Employee(
                        employee_id=eid,
                        employee_name=full_name,
                        first_name=r.get("first_name"),
                        last_name=r.get("last_name"),
                        email=r.get("email"),
                        phone=r.get("phone"),
                        department=r.get("department"),
                        designation=r.get("designation"),
                        manager_name=r.get("manager_name"),
                        location=r.get("location"),
                        date_of_joining=r.get("date_of_joining"),
                        employment_type=r.get("employment_type", "Full-Time"),
                        basic_salary=salary,
                        hra=hra,
                        bonus=bonus,
                        annual_ctc=ctc,
                        performance_rating=perf,
                        gender=r.get("gender"),
                        age=age,
                        pan=pan,
                        account_number=acc,
                    )
                    session.add(emp)
                    migrated_count += 1

                sec_id = f"SEC-{eid}"
                sec_exist = session.execute(select(SecurityCheck).where(SecurityCheck.security_id == sec_id)).scalar_one_or_none()
                if not sec_exist:
                    sec = SecurityCheck(
                        security_id=sec_id,
                        employee_id=eid,
                        employee_name=full_name,
                        passport=f"P{eid[-6:].zfill(7)}" if len(eid) >= 4 else "P1000001",
                        aadhaar=f"998877{eid[-4:].zfill(6)}",
                        address=f"Enterprise Campus, {r.get('location', 'Bangalore')}",
                        police_verification="cleared" if perf >= 3.0 else "pending",
                    )
                    session.add(sec)

            session.commit()
            return {
                "status": "success",
                "migrated": migrated_count,
                "updated": updated_count,
                "total_processed": migrated_count + updated_count,
            }
    except Exception as exc:
        session.rollback()
        return {"status": "error", "error": str(exc)}
    finally:
        session.close()


_CSV_EMPLOYEES_CACHE: dict[str, dict] | None = None


def _lookup_csv_employee(employee_id: str) -> dict | None:
    """Fallback lookup in CSV if database is not yet populated."""
    global _CSV_EMPLOYEES_CACHE

    if _CSV_EMPLOYEES_CACHE is None:
        _CSV_EMPLOYEES_CACHE = {}
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "enterprise_employees.csv"
        )
        if os.path.exists(csv_path):
            try:
                with open(csv_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        eid = r.get("employee_id", "").strip().upper()
                        if eid:
                            salary = float(r.get("salary", 50000))
                            bonus = float(r.get("bonus", 10000))
                            _CSV_EMPLOYEES_CACHE[eid] = {
                                "employee_id": eid,
                                "employee_name": r.get("full_name", "Employee"),
                                "first_name": r.get("first_name"),
                                "last_name": r.get("last_name"),
                                "email": r.get("email"),
                                "phone": r.get("phone"),
                                "department": r.get("department"),
                                "designation": r.get("designation"),
                                "location": r.get("location"),
                                "manager_name": r.get("manager_name"),
                                "basic_salary": salary,
                                "hra": round(salary * 0.25, 2),
                                "bonus": bonus,
                                "annual_ctc": float(r.get("annual_ctc", (salary * 1.25 + bonus) * 12)),
                                "performance_rating": float(r.get("performance_rating", 3.5)),
                                "gender": r.get("gender"),
                                "age": int(r.get("age", 30)) if r.get("age") else None,
                                "pan": f"ABCDE{eid[-4:]}F" if len(eid) >= 4 else "ABCDE1234F",
                                "account_number": f"100200{eid[-4:].zfill(6)}",
                            }
            except Exception:
                pass
    return _CSV_EMPLOYEES_CACHE.get(employee_id.strip().upper())


def get_employee(employee_id: str) -> dict | None:
    """Fetch employee by ID directly from SQLite with auto-seed and fallback."""
    if not employee_id:
        return None
    normalized_id = employee_id.strip().upper()
    session = SessionLocal()
    try:
        row = session.execute(select(Employee).where(Employee.employee_id == normalized_id)).scalar_one_or_none()
        if row is not None:
            return _format_employee_dict(row)
        
        # Check if table is unseeded
        has_any = session.execute(select(Employee.id)).first()
        if not has_any:
            session.close()
            seed_default_employees()
            session = SessionLocal()
            row = session.execute(select(Employee).where(Employee.employee_id == normalized_id)).scalar_one_or_none()
            if row is not None:
                return _format_employee_dict(row)
    finally:
        session.close()

    # Fallback lookup in CSV
    return _lookup_csv_employee(normalized_id)


def search_employees(query: str, limit: int = 10) -> list[dict]:
    """Search SQLite employees by ID, name, department, or designation."""
    if not query:
        return []
    q_str = f"%{query.strip()}%"
    session = SessionLocal()
    try:
        rows = session.execute(
            select(Employee).where(
                or_(
                    Employee.employee_id.ilike(q_str),
                    Employee.employee_name.ilike(q_str),
                    Employee.department.ilike(q_str),
                    Employee.designation.ilike(q_str),
                    Employee.location.ilike(q_str),
                )
            ).limit(limit)
        ).scalars().all()
        return [_format_employee_dict(r) for r in rows]
    finally:
        session.close()


def query_department_analytics(department: str | None = None) -> list[dict]:
    """Run exact, deterministic SQL aggregations for department salary stats."""
    session = SessionLocal()
    try:
        # Check if table is empty; auto-seed if needed
        has_any = session.execute(select(Employee.id)).first()
        if not has_any:
            session.close()
            seed_default_employees()
            session = SessionLocal()

        query = session.query(
            Employee.department,
            func.count(Employee.id).label("headcount"),
            func.avg(Employee.basic_salary).label("avg_basic"),
            func.min(Employee.basic_salary).label("min_basic"),
            func.max(Employee.basic_salary).label("max_basic"),
            func.avg(Employee.bonus).label("avg_bonus"),
            func.avg(Employee.annual_ctc).label("avg_annual_ctc"),
        )
        if department:
            query = query.filter(Employee.department.ilike(f"%{department.strip()}%"))

        query = query.group_by(Employee.department).order_by(Employee.department.asc())
        results = []
        for r in query.all():
            if not r[0]:
                continue
            results.append({
                "department": r[0],
                "headcount": int(r[1] or 0),
                "avg_basic": round(float(r[2] or 0.0), 2),
                "min_basic": round(float(r[3] or 0.0), 2),
                "max_basic": round(float(r[4] or 0.0), 2),
                "avg_bonus": round(float(r[5] or 0.0), 2),
                "avg_annual_ctc": round(float(r[6] or 0.0), 2),
            })
        return results
    finally:
        session.close()


def list_employees():
    session = SessionLocal()
    try:
        rows = session.execute(select(Employee).order_by(Employee.employee_name.asc())).scalars().all()
        return [_format_employee_dict(row) for row in rows]
    finally:
        session.close()


def seed_default_employees():
    """Populate default enterprise employees and migrate 500-employee CSV roster into SQLite."""
    session = SessionLocal()
    try:
        default_employees = [
            {
                "employee_id": "EMP-101",
                "employee_name": "Alice Smith",
                "department": "Engineering",
                "designation": "Tech Lead",
                "location": "Bangalore",
                "basic_salary": 85000.0,
                "hra": 20000.0,
                "bonus": 10000.0,
                "pan": "ABCDE1234F",
                "account_number": "1234567890123456",
                "passport": "A1234567",
                "aadhaar": "123456789012",
                "address": "124 Innovation Way, Tech Park, Suite 400",
                "police_verification": "cleared",
            },
            {
                "employee_id": "EMP-102",
                "employee_name": "Bob Johnson",
                "department": "Finance",
                "designation": "Financial Analyst",
                "location": "Mumbai",
                "basic_salary": 110000.0,
                "hra": 35000.0,
                "bonus": 15000.0,
                "pan": "BKLPJ8765M",
                "account_number": "9876543210987654",
                "passport": "B9876543",
                "aadhaar": "987654321098",
                "address": "500 Cloud Summit Blvd, Austin, TX",
                "police_verification": "cleared",
            },
            {
                "employee_id": "EMP-103",
                "employee_name": "Carol Davis",
                "department": "Human Resources",
                "designation": "HR Executive",
                "location": "Pune",
                "basic_salary": 45000.0,
                "hra": 18000.0,
                "bonus": 3000.0,
                "pan": "CDMPQ3456K",
                "account_number": "4567890123456789",
                "passport": None,
                "aadhaar": "556677889900",
                "address": "88 Harbor View Lane, Seattle, WA",
                "police_verification": "pending",
            },
            {
                "employee_id": "EMP-104",
                "employee_name": "David Patel",
                "department": "Security",
                "designation": "Security Analyst",
                "location": "Delhi",
                "basic_salary": 72000.0,
                "hra": 15000.0,
                "bonus": 8000.0,
                "pan": "DPZAB5678R",
                "account_number": "3216549870123456",
                "passport": "D4567891",
                "aadhaar": "112233445566",
                "address": "77 Cyber Hub Road, Gurugram, HR",
                "police_verification": "cleared",
            },
            {
                "employee_id": "EMP-105",
                "employee_name": "Elena Rostova",
                "department": "Data Science",
                "designation": "Data Scientist",
                "location": "Hyderabad",
                "basic_salary": 95000.0,
                "hra": 25000.0,
                "bonus": 12000.0,
                "pan": "ERTYU9012N",
                "account_number": "7890123456789012",
                "passport": "E7891234",
                "aadhaar": "334455667788",
                "address": "12 Financial District Center, London",
                "police_verification": "cleared",
            },
        ]

        for item in default_employees:
            existing_emp = session.execute(select(Employee).where(Employee.employee_id == item["employee_id"])).scalar_one_or_none()
            if not existing_emp:
                emp = Employee(
                    employee_id=item["employee_id"],
                    employee_name=item["employee_name"],
                    department=item.get("department"),
                    designation=item.get("designation"),
                    location=item.get("location"),
                    basic_salary=item["basic_salary"],
                    hra=item["hra"],
                    bonus=item["bonus"],
                    annual_ctc=(item["basic_salary"] + item["hra"] + item["bonus"]) * 12,
                    performance_rating=4.0,
                    pan=item["pan"],
                    account_number=item["account_number"],
                )
                session.add(emp)

            sec_id = f"SEC-{item['employee_id']}"
            existing_sec = session.execute(select(SecurityCheck).where(SecurityCheck.security_id == sec_id)).scalar_one_or_none()
            if not existing_sec:
                sec = SecurityCheck(
                    security_id=sec_id,
                    employee_id=item["employee_id"],
                    employee_name=item["employee_name"],
                    passport=item["passport"],
                    aadhaar=item["aadhaar"],
                    address=item["address"],
                    police_verification=item["police_verification"],
                )
                session.add(sec)

        session.commit()
    finally:
        session.close()

    # Migrate the full 500-employee enterprise CSV roster into SQLite
    migrate_csv_to_sqlite()
