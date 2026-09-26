from pydantic import BaseModel


class Employee(BaseModel):
    employee_id: str
    employee_name: str
    basic_salary: float
    hra: float
    bonus: float
    pan: str
    account_number: str