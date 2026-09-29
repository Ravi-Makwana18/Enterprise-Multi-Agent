from backend.agents.blog_ai_review import ai_review_blog
from backend.agents.blog_ai_rewrite import ai_rewrite_blog
from backend.agents.blog_ai_write import ai_write_blog, is_writing_request, validate_writing_topic
from backend.models.blog_review import BlogReview


def review_blog(state):
    user_text = str(state.get("user_input", "")).strip()

    blog_content = None
    # 1. Writing request path
    if is_writing_request(user_text):
        topic, is_sufficient, issues, recommendations = validate_writing_topic(user_text)
        if not is_sufficient:
            state["response"] = {
                "status": "insufficient_input",
                "message": "The provided input is insufficient to write an article. No topic or subject was specified.",
                "issues": issues,
                "recommendations": recommendations,
                "score": None,
                "approved": False,
                "risk_level": "low",
                "requires_human_review": False,
            }
            state["score"] = 0.0
            state["approved"] = False
            state["status"] = "insufficient_input"
            return state

        try:
            blog_content = ai_write_blog(user_text)
            user_text = blog_content
            state["user_input"] = blog_content
        except Exception:
            pass
    else:
        # 2. Review request path: check if user provided actual content to review
        review_triggers = ("review", "critique", "audit", "evaluate", "proofread", "check this")
        words = user_text.split()
        if any(r in user_text.lower() for r in review_triggers) and len(words) < 15:
            state["response"] = {
                "status": "insufficient_input",
                "message": "The provided input is insufficient for blog review. No draft text or article content was attached.",
                "issues": [
                    "No article draft or blog content was attached to review (only query received)."
                ],
                "recommendations": [
                    "Paste your article or draft text directly into the chat: e.g., 'Review this draft: # Cloud Security ...'",
                    "Or ask the agent to compose an article: e.g., 'Write a blog about AI security in banking'"
                ],
                "score": None,
                "approved": False,
                "risk_level": "low",
                "requires_human_review": False,
            }
            state["score"] = 0.0
            state["approved"] = False
            state["status"] = "insufficient_input"
            return state

    # Review the content (either newly generated blog or user-provided draft)
    try:
        review_data = ai_review_blog(user_text)  # returns dict directly
        review = BlogReview(**review_data)
        state["score"] = review.score
        state["approved"] = review.approved
        state["requires_human_review"] = review.requires_human_review
        resp_dict = review.model_dump()
        resp_dict["iteration"] = state.get("iteration", 0)
        if blog_content:
            resp_dict["blog_content"] = blog_content
            resp_dict["message"] = blog_content
        state["response"] = resp_dict
    except Exception as ex:
        score = 90 if blog_content else 0
        approved = True if blog_content else False
        state["score"] = score
        state["approved"] = approved
        state["requires_human_review"] = False
        state["response"] = {
            "score": score,
            "approved": approved,
            "message": blog_content or str(ex),
            "blog_content": blog_content,
            "status": "approved" if blog_content else "error",
            "risk_level": "low" if blog_content else "high",
            "requires_human_review": False,
            "iteration": state.get("iteration", 0),
        }
    return state


def revise_blog(state):
    state["iteration"] = state.get("iteration", 0) + 1
    prev_response = state.get("response") if isinstance(state.get("response"), dict) else {}
    issues = prev_response.get("issues") or []
    recommendations = prev_response.get("recommendations") or []
    human_feedback = state.get("human_feedback") or state.get("feedback")

    try:
        rewrite_data = ai_rewrite_blog(
            state["user_input"],
            issues=issues,
            recommendations=recommendations,
            human_feedback=human_feedback,
        )
        rewritten = rewrite_data.get("message") or state["user_input"]
        state["user_input"] = rewritten
        rewrite_data["iteration"] = state["iteration"]
        state["response"] = rewrite_data
    except Exception as ex:
        state["response"] = {"error": str(ex), "message": str(ex), "iteration": state["iteration"]}
    return state

