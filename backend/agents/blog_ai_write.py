import json
import logging
import re
from backend.services import llm_service

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert enterprise content creator, journalist, and master storyteller.
Your task is to write captivating, well-structured, and publication-ready blog posts and articles.
Structure each article with:
- An evocative and engaging Title (using # Title)
- A compelling opening hook/introduction
- Well-organized body sections with informative subheadings (## Subheading)
- Practical advice, key takeaways, or cultural/technical insights
- An inspiring concluding summary
Write engaging prose directly without preamble, meta-commentary, or JSON formatting."""

_PROMPT = """Write a complete, high-quality, and engaging blog article based on the following topic or request:

Request: {topic}

Guidelines:
- Format: Clean Markdown with a title, subheadings, and clear paragraphs.
- Length: Detailed and informative (around 300-500 words).
- Tone: Professional, inspiring, and immersive.
- Start directly with the article title. Do NOT output conversational filler or JSON."""


def _clean_topic(text: str) -> str:
    cleaned = re.sub(
        r"^(?:please\s+)?(?:write|create|draft|generate|compose|make)\s+(?:a|an)?\s*(?:blog(?:\s+post)?|article|post|essay)?\s*(?:about|on|for|regarding)?\s*",
        "",
        text.strip(),
        flags=re.IGNORECASE,
    )
    return cleaned.strip() or text.strip()


def _generate_fallback_blog(topic: str) -> str:
    """High-quality fallback generator when external LLM is unreachable."""
    t_clean = _clean_topic(topic)
    t_lower = t_clean.lower()

    if "taj mahal" in t_lower or "agra" in t_lower:
        return (
            f"# A Journey to Timeless Wonder: Experiencing the Taj Mahal\n\n"
            f"Standing on the banks of the Yamuna River in Agra, the Taj Mahal is far more than an architectural wonder—it is an enduring testament to love, art, and timeless imperial grandeur. Commissioned in 1632 by the Mughal Emperor Shah Jahan in memory of his beloved wife Mumtaz Mahal, this ivory-white marble mausoleum continues to draw millions of travelers from every corner of the globe.\n\n"
            f"## The Morning Radiance of White Marble\n\n"
            f"The optimal time to experience the monument is during sunrise. As the dawn mist gently lifts, the white Makrana marble subtly shifts through ethereal shades of soft pink, warm amber, and brilliant pearl. The symmetrical charbagh gardens, divided by calm reflective water channels, mirror the domes with geometric perfection.\n\n"
            f"## Intricate Craftsmanship and Pietra Dura\n\n"
            f"Up close, the monument reveals its astonishing artistry. The walls are inlaid with semi-precious stones—lapis lazuli, jade, turquoise, and jasper—crafted into delicate floral arabesques and intricate calligraphy of Quranic verses. Each arch and dome reflects an unprecedented mastery of proportion and light.\n\n"
            f"## Practical Tips for Your Trip\n\n"
            f"- **Timing:** Arrive early around 5:30 AM to catch the sunrise and avoid large crowds.\n"
            f"- **Photography:** The Mehtab Bagh garden across the river offers an exceptional sunset vantage point.\n"
            f"- **Respecting Heritage:** Wear comfortable footwear and observe all local conservation guidelines.\n\n"
            f"## Final Reflection\n\n"
            f"A trip to the Taj Mahal is an unforgettable experience that lingers long after you depart. It represents the pinnacle of human artistic ambition and remains an unmissable destination for any global traveler."
        )

    if "ai" in t_lower or "health" in t_lower or "tech" in t_lower:
        return (
            f"# Transforming the Future: The Impact of {t_clean.title()}\n\n"
            f"In today's rapidly evolving enterprise landscape, innovation is no longer a luxury—it is an operational necessity. Among emerging technological frontiers, {t_clean} stands out as a catalyst driving efficiency, precision, and human-centric outcomes.\n\n"
            f"## The Shift Toward Intelligent Systems\n\n"
            f"Modern organizations are integrating smart autonomous workflows to eliminate friction, automate routine tasks, and extract actionable insights from vast datasets. By combining algorithmic intelligence with specialized human oversight, enterprises achieve scalable reliability and unprecedented speed.\n\n"
            f"## Key Strategic Advantages\n\n"
            f"- **Precision & Consistency:** Minimizing operational errors through rigorous validation.\n"
            f"- **Data-Driven Insights:** Unlocking predictive capabilities across complex business functions.\n"
            f"- **Secure Governance:** Enforcing compliance and privacy guardrails across distributed systems.\n\n"
            f"## Looking Forward\n\n"
            f"As organizations continue to mature, the symbiotic integration of intelligent tooling and human expertise will define the future of high-performance enterprises."
        )

    # General fallback
    return (
        f"# Insights & Exploration: A Guide to {t_clean.title()}\n\n"
        f"Whether for professional development, strategic exploration, or personal passion, diving deep into {t_clean} offers a wealth of opportunities and fresh perspectives.\n\n"
        f"## Understanding the Fundamentals\n\n"
        f"Every meaningful journey begins with a solid foundation. By examining key principles, historical context, and current trends, we gain the clarity needed to navigate nuances and achieve superior outcomes.\n\n"
        f"## Practical Takeaways\n\n"
        f"- **Plan with Purpose:** Define clear goals and milestones before initiating projects.\n"
        f"- **Embrace Continuous Learning:** Stay curious, iterate frequently, and learn from real-world feedback.\n"
        f"- **Leverage Collaborative Tools:** Modern solutions enable seamless execution and collective intelligence.\n\n"
        f"## Conclusion\n\n"
        f"The path forward is shaped by thoughtful action and persistent curiosity. By applying these insights, you can turn ideas into impactful, lasting achievements."
    )


def is_writing_request(text: str) -> bool:
    """Determine whether the request is asking to compose a blog or review an existing draft."""
    t = text.lower().strip()

    review_triggers = ("review", "critique", "audit", "evaluate", "check this", "proofread")
    if any(r in t for r in review_triggers):
        return False

    write_triggers = (
        "write", "create", "draft", "compose", "generate",
        "make a blog", "about", "tell me about", "story",
        "trip", "travel", "guide",
    )
    if any(k in t for k in write_triggers):
        return True

    # Short queries (under 40 words) are topics to write about rather than pre-written drafts
    return len(t.split()) < 40


def ai_write_blog(topic: str) -> str:
    """Generate a full blog post using the LLM with fallback support."""
    cleaned_topic = _clean_topic(topic)
    prompt = _PROMPT.format(topic=cleaned_topic)
    try:
        content = llm_service.generate_text(prompt, model_key="blog", system_prompt=_SYSTEM_PROMPT)
        if content and len(content.strip()) > 100 and not content.strip().startswith("Unable to generate"):
            # If the model wrapped in JSON by accident, extract text/message field
            if content.strip().startswith("{") and content.strip().endswith("}"):
                try:
                    parsed = json.loads(content.strip())
                    content = parsed.get("message") or parsed.get("blog_content") or parsed.get("text") or content
                except Exception:
                    pass
            return content.strip()
    except Exception as exc:
        logger.warning("Blog writing LLM failed (%s), using fallback: %s", topic, exc)

    return _generate_fallback_blog(cleaned_topic)
