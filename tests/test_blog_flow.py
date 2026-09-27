from backend.agents.blog_review import review_blog
from backend.agents.blog_ai_write import is_writing_request


def test_is_writing_request():
    assert is_writing_request("write a blog about trip of taj mahal") is True
    assert is_writing_request("draft an article on AI in healthcare") is True
    assert is_writing_request("Review this draft: Long article text...") is False


def test_blog_review_with_write_request():
    state = {
        "user_input": "write a blog about trip of taj mahal",
        "route": "BLOG",
        "response": {},
        "score": 0,
        "approved": False,
        "iteration": 0,
    }
    result = review_blog(state)
    assert result["approved"] is True
    assert result["score"] >= 80
    resp = result["response"]
    assert "Taj Mahal" in resp.get("message", "") or "taj mahal" in resp.get("message", "").lower()
    assert bool(resp.get("blog_content")) is True
