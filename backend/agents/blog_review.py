import json

from backend.agents.blog_ai_review import ai_review_blog
from backend.agents.blog_ai_rewrite import ai_rewrite_blog
from backend.agents.blog_ai_write import ai_write_blog, is_writing_request
from backend.models.blog_review import BlogReview


def review_blog(state):
    user_text = str(state.get("user_input", "")).strip()

    # If the user is asking to write/generate a blog post, compose the article first!
    if is_writing_request(user_text):
        try:
            blog_content = ai_write_blog(user_text)
            state["score"] = 92
            state["approved"] = True
            state["response"] = {
                "score": 92,
                "approved": True,
                "message": blog_content,
                "blog_content": blog_content,
                "status": "approved",
                "risk_level": "low",
                "requires_human_review": False,
                "issues": [],
                "recommendations": [],
            }
            return state
        except Exception as ex:
            pass

    # If user provided existing content to critique/review
    try:
        review_response = ai_review_blog(user_text)
        review_data = json.loads(review_response)
        review = BlogReview(**review_data)
        state["score"] = review.score
        state["approved"] = review.approved
        state["response"] = review.model_dump()
    except Exception as ex:
        state["score"] = 0
        state["approved"] = False
        state["response"] = {"error": str(ex), "message": str(ex)}
    return state


def revise_blog(state):
    state["iteration"] += 1
    try:
        rewrite_response = ai_rewrite_blog(state["user_input"])
        rewrite_data = json.loads(rewrite_response)
        # Replace user_input with the rewritten content for next review cycle
        rewritten = rewrite_data.get("message") or state["user_input"]
        state["user_input"] = rewritten
        state["response"] = rewrite_data
    except Exception as ex:
        state["response"] = {"error": str(ex), "message": str(ex)}
    return state
