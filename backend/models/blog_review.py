from typing import List, Optional
from pydantic import BaseModel


class BlogReview(BaseModel):
    score: int
    approved: bool
    issues: List[str] = []
    recommendations: List[str] = []
    message: Optional[str] = None
    blog_content: Optional[str] = None
    status: Optional[str] = "in review"
    risk_level: Optional[str] = "medium"
    requires_human_review: bool = False
    fallback: bool = False
    quality_criteria: Optional[dict] = None
    iteration: Optional[int] = 0

    model_config = {"extra": "ignore"}
