from typing import TypedDict


class AgentState(TypedDict, total=False):
    user_input: str
    route: str
    response: dict
    score: float
    approved: bool
    iteration: int
    workflow_id: str
    status: str
    execution_history: list[dict]
    last_error: str | None
    cancelled: bool
    replay_of: str | None