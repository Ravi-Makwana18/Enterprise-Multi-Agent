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


def list_reviews():
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
