from backend.models.state import AgentState


def classify_request(state: AgentState):
    text = state["user_input"].lower()

    if "blog" in text:
        route = "BLOG"

    elif "salary" in text:
        route = "SALARY"

    elif "security" in text:
        route = "SECURITY"

    else:
        route = "SUPPORT"

    state["route"] = route
    state["response"] = f"Request routed to {route} agent"

    return state