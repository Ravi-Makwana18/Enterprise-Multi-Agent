from langgraph.graph import StateGraph, END

from backend.models.state import AgentState
from backend.agents.blog_review import review_blog, revise_blog


builder = StateGraph(AgentState)

builder.add_node("review", review_blog)
builder.add_node("revise", revise_blog)

builder.set_entry_point("review")


def review_decision(state):
    if state.get("status") == "insufficient_input":
        return "approved"

    if state.get("approved"):
        return "approved"

    if state.get("iteration", 0) >= 3:
        return "approved"

    return "revise"


builder.add_conditional_edges(
    "review",
    review_decision,
    {
        "approved": END,
        "revise": "revise",
    }
)

builder.add_edge("revise", "review")

blog_graph = builder.compile()