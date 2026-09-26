from backend.agents.security_agent import (
    run_security_check
)


def execute():

    state = {
        "user_input": "scheduled security check",
        "route": "SECURITY",
        "response": {},
        "score": 0,
        "approved": False,
        "iteration": 0,
        "human_approval": False,
        "human_feedback": ""
    }

    result = run_security_check(
        state
    )

    print(result)


if __name__ == "__main__":
    execute()