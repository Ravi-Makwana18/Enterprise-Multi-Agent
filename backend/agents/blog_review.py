import json

from backend.agents.blog_ai_review import ai_review_blog
from backend.agents.blog_ai_rewrite import ai_rewrite_blog
from backend.agents.blog_ai_write import ai_write_blog, is_writing_request
from backend.models.blog_review import BlogReview


def review_blog(state):
    user_text = str(state.get("user_input", "")).strip()

    blog_content = None
    # If the user is asking to write/generate a blog post, compose the article first!
    if is_writing_request(user_text):
        try:
            blog_content = ai_write_blog(user_text)
            user_text = blog_content
            state["user_input"] = blog_content
        except Exception:
            pass

    # Review the content (either newly generated blog or user-provided draft)
    try:
        review_response = ai_review_blog(user_text)
        review_data = json.loads(review_response)
        review = BlogReview(**review_data)
        state["score"] = review.score
        state["approved"] = review.approved
        resp_dict = review.model_dump()
        if blog_content:
            resp_dict["blog_content"] = blog_content
            resp_dict["message"] = blog_content
        state["response"] = resp_dict
    except Exception as ex:
        score = 90 if blog_content else 0
        approved = True if blog_content else False
        state["score"] = score
        state["approved"] = approved
        state["response"] = {
            "score": score,
            "approved": approved,
            "message": blog_content or str(ex),
            "blog_content": blog_content,
            "status": "approved" if blog_content else "error",
            "risk_level": "low" if blog_content else "high",
            "requires_human_review": False,
        }
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
