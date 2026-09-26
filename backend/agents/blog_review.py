import json

from backend.agents.blog_ai_review import ai_review_blog
from backend.agents.blog_ai_rewrite import ai_rewrite_blog
from backend.models.blog_review import BlogReview


def review_blog(state):
    try:
        review_response = ai_review_blog(state["user_input"])
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
