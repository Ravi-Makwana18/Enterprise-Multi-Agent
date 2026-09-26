from pydantic import BaseModel


class SecurityRecord(BaseModel):
    employee_id: str
    employee_name: str
    passport: str | None = None
    aadhaar: str | None = None
    address: str | None = None
    police_verification: str | None = None