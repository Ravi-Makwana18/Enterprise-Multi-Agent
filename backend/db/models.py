from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from backend.db.database import Base

_now = lambda: datetime.now(timezone.utc)  # noqa: E731


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
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(64), unique=True, nullable=False, index=True)
    employee_name = Column(String(255), nullable=False)
    basic_salary = Column(Float, nullable=False)
    hra = Column(Float, nullable=False)
    bonus = Column(Float, nullable=False)
    annual_ctc = Column(Float, nullable=True)
    pan = Column(String(32), nullable=False)
    account_number = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    department = Column(String(255), nullable=True)
    designation = Column(String(255), nullable=True)
    manager_name = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    date_of_joining = Column(String(255), nullable=True)
    employment_type = Column(String(64), nullable=True)
    gender = Column(String(32), nullable=True)
    age = Column(Integer, nullable=True)
    performance_rating = Column(Float, nullable=True)


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
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)


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
    created_at = Column(DateTime, default=_now, nullable=False)


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
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)


class UserAction(Base):
    __tablename__ = "user_actions"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(128), nullable=False)
    username = Column(String(128), nullable=True)
    role = Column(String(32), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now, nullable=False)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    employee_id = Column(String(64), nullable=True, index=True)
    username = Column(String(255), nullable=True)
    user_role = Column(String(32), nullable=False, default="user")
    title = Column(String(255), nullable=False, default="New Chat")
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    sender = Column(String(32), nullable=False, default="user")  # 'user' or 'agent'
    content = Column(Text, nullable=False)
    route = Column(String(64), nullable=True)
    raw_response = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now, nullable=False)


