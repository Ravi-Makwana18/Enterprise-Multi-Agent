import json
import uuid

from sqlalchemy import select

from backend.db.database import SessionLocal
from backend.db.models import Review


def create_review(payload: dict) -> dict:
    session = SessionLocal()
    try:
        review_id = payload.get("review_id") or f"REV-{str(uuid.uuid4())[:8]}"
        review = Review(
            review_id=review_id,
            title=payload.get("title", ""),
            reviewer=payload.get("reviewer", ""),
            review_type=payload.get("review_type", "general"),
            content=payload.get("content", ""),
            status=payload.get("status", "pending"),
            score=float(payload.get("score", 0.0)),
            approved=bool(payload.get("approved", False)),
            issues=json.dumps(payload.get("issues", [])),
            recommendations=json.dumps(payload.get("recommendations", [])),
        )
        session.add(review)
        session.commit()
        session.refresh(review)
        return {
            "review_id": review.review_id,
            "title": review.title,
            "reviewer": review.reviewer,
            "review_type": review.review_type,
            "content": review.content,
            "status": review.status,
            "score": review.score,
            "approved": review.approved,
            "issues": json.loads(review.issues) if review.issues else [],
            "recommendations": json.loads(review.recommendations) if review.recommendations else [],
        }
    finally:
        session.close()


def list_reviews() -> list[dict]:
    session = SessionLocal()
    try:
        rows = session.execute(select(Review).order_by(Review.created_at.desc())).scalars().all()
        return [
            {
                "review_id": row.review_id,
                "title": row.title,
                "reviewer": row.reviewer,
                "review_type": row.review_type,
                "content": row.content,
                "status": row.status,
                "score": row.score,
                "approved": row.approved,
                "issues": json.loads(row.issues) if row.issues else [],
                "recommendations": json.loads(row.recommendations) if row.recommendations else [],
            }
            for row in rows
        ]
    finally:
        session.close()


def get_review(review_id: str) -> dict | None:
    session = SessionLocal()
    try:
        row = session.execute(select(Review).where(Review.review_id == review_id)).scalar_one_or_none()
        if not row:
            return None
        return {
            "review_id": row.review_id,
            "title": row.title,
            "reviewer": row.reviewer,
            "review_type": row.review_type,
            "content": row.content,
            "status": row.status,
            "score": row.score,
            "approved": row.approved,
            "issues": json.loads(row.issues) if row.issues else [],
            "recommendations": json.loads(row.recommendations) if row.recommendations else [],
        }
    finally:
        session.close()


def update_review_decision(review_id: str, decision: str, reviewer: str, comments: str | None = None) -> dict | None:
    session = SessionLocal()
    try:
        row = session.execute(select(Review).where(Review.review_id == review_id)).scalar_one_or_none()
        if not row:
            return None

        is_approved = str(decision).lower() in ("approved", "approve", "true", "yes")
        row.status = "approved" if is_approved else "rejected"
        row.approved = is_approved
        row.reviewer = reviewer or "Lead Reviewer"
        if comments:
            row.content = f"{row.content or ''}\n\n[Decision Note by {reviewer}]: {comments}".strip()

        from datetime import datetime, timezone
        row.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(row)

        return {
            "review_id": row.review_id,
            "title": row.title,
            "reviewer": row.reviewer,
            "review_type": row.review_type,
            "content": row.content,
            "status": row.status,
            "score": row.score,
            "approved": row.approved,
            "issues": json.loads(row.issues) if row.issues else [],
            "recommendations": json.loads(row.recommendations) if row.recommendations else [],
        }
    finally:
        session.close()


def seed_default_reviews():
    """Seed initial pending reviews flagged by AI workflows if empty."""
    session = SessionLocal()
    try:
        existing = session.execute(select(Review)).first()
        if existing:
            return

        sample_reviews = [
            {
                "review_id": "REV-SEC-103",
                "title": "[SECURITY] Carol Davis (EMP-103) - Background Verification Flag",
                "reviewer": "Security Policy Agent (Pending Review)",
                "review_type": "SECURITY",
                "content": "AI Security Check detected: Police verification is still marked 'pending' and national passport verification was not submitted.",
                "status": "pending",
                "score": 65.0,
                "approved": False,
                "issues": [
                    "Police verification record has not cleared",
                    "Passport identity credentials missing from employee profile"
                ],
                "recommendations": [
                    "Request secondary identity documentation from Carol Davis",
                    "Contact jurisdictional police department for pending clearance verification"
                ],
            },
            {
                "review_id": "REV-SAL-102",
                "title": "[SALARY] Bob Johnson (EMP-102) - Executive Incentive Adjustment",
                "reviewer": "Payroll Compliance Agent (Pending Review)",
                "review_type": "SALARY",
                "content": "Director Bob Johnson compensation review: Incentive proportion is ₹15,000 against ₹1,10,000 basic salary. Requires managerial approval.",
                "status": "pending",
                "score": 78.0,
                "approved": False,
                "issues": [
                    "Executive bonus payout ratio requires departmental head confirmation",
                    "HRA to basic ratio is at 31.8% (requires audit trail)"
                ],
                "recommendations": [
                    "Confirm Q3 enterprise delivery milestones before disbursement",
                    "Log formal finance committee sign-off"
                ],
            },
        ]

        for r_data in sample_reviews:
            r = Review(
                review_id=r_data["review_id"],
                title=r_data["title"],
                reviewer=r_data["reviewer"],
                review_type=r_data["review_type"],
                content=r_data["content"],
                status=r_data["status"],
                score=r_data["score"],
                approved=r_data["approved"],
                issues=json.dumps(r_data["issues"]),
                recommendations=json.dumps(r_data["recommendations"]),
            )
            session.add(r)
        session.commit()
    finally:
        session.close()

