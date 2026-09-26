import sys
sys.path.insert(0, '.')

print("Testing orchestrator...", flush=True)
from backend.workflows.langgraph_orchestrator import graph

# Test 1: Blog
print("\n--- BLOG ---", flush=True)
try:
    result = graph.invoke({
        "user_input": "Write a blog about AI in healthcare",
        "route": "", "response": {}, "score": 0, "approved": False, "iteration": 0
    })
    print("Route:", result.get("route"), flush=True)
    print("Status:", result.get("status"), flush=True)
    resp = result.get("response", {})
    print("Response keys:", list(resp.keys()) if isinstance(resp, dict) else type(resp), flush=True)
    print("Score:", result.get("score"), flush=True)
    print("Message:", str(resp.get("message", ""))[:120], flush=True)
except Exception as e:
    print("BLOG ERROR:", e, flush=True)
    import traceback; traceback.print_exc()

# Test 2: Support
print("\n--- SUPPORT ---", flush=True)
try:
    result = graph.invoke({
        "user_input": "I can't login to my account",
        "route": "", "response": {}, "score": 0, "approved": False, "iteration": 0
    })
    print("Route:", result.get("route"), flush=True)
    resp = result.get("response", {})
    print("Ticket ID:", resp.get("ticket_id"), flush=True)
    print("Message:", str(resp.get("message", ""))[:120], flush=True)
except Exception as e:
    print("SUPPORT ERROR:", e, flush=True)
    import traceback; traceback.print_exc()

# Test 3: Salary
print("\n--- SALARY ---", flush=True)
try:
    result = graph.invoke({
        "user_input": "What is my salary breakdown for basic 50000?",
        "route": "", "response": {}, "score": 0, "approved": False, "iteration": 0
    })
    print("Route:", result.get("route"), flush=True)
    resp = result.get("response", {})
    print("Net salary:", resp.get("net_salary"), flush=True)
    print("Message:", str(resp.get("message", ""))[:120], flush=True)
except Exception as e:
    print("SALARY ERROR:", e, flush=True)
    import traceback; traceback.print_exc()
