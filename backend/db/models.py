from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from backend.db.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(64), unique=True, nullable=False, index=True)
    summary = Column(Text, nullable=False)
    status = Column(String(32), nullable=True, default="submitted")
    category = Column(String(64), nullable=False, default="general")
    priority = Column(String(32), nullable=False, default="normal")
    requester = Column(String(255), nullable=True)
    assignee = Column(String(255), nullable=True)
    reviewed_by = Column(String(255), nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(64), unique=True, nullable=False, index=True)
    employee_name = Column(String(255), nullable=False)
    basic_salary = Column(Float, nullable=False)
    hra = Column(Float, nullable=False)
    bonus = Column(Float, nullable=False)
    pan = Column(String(32), nullable=False)
    account_number = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=True)
    reviewer = Column(String(255), nullable=True)
    review_type = Column(String(64), nullable=False, default="general")
    content = Column(Text)
    status = Column(String(32), nullable=False, default="pending")
    score = Column(Float, default=0.0)
    approved = Column(Boolean, default=False)
    issues = Column(Text)
    recommendations = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SecurityCheck(Base):
    __tablename__ = "security_checks"

    id = Column(Integer, primary_key=True, index=True)
    security_id = Column(String(64), unique=True, nullable=False, index=True)
    employee_id = Column(String(64), nullable=True)
    employee_name = Column(String(255), nullable=False)
    passport = Column(String(64), nullable=True)
    aadhaar = Column(String(64), nullable=True)
    address = Column(Text, nullable=True)
    police_verification = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class WorkflowState(Base):
    __tablename__ = "workflow_states"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String(64), unique=True, nullable=False, index=True)
    user_input = Column(Text, nullable=False)
    route = Column(String(64), nullable=False, default="SUPPORT")
    response = Column(Text, nullable=True)
    score = Column(Float, default=0.0)
    approved = Column(Boolean, default=False)
    iteration = Column(Integer, default=0)
    status = Column(String(32), nullable=True, default="submitted")
    execution_history = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class UserAction(Base):
    __tablename__ = "user_actions"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(128), nullable=False)
    username = Column(String(128), nullable=True)
    role = Column(String(32), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
