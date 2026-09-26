import sys, traceback
sys.path.insert(0, '.')
results = []

def test(name, fn):
    try:
        fn()
        results.append(f"OK  {name}")
    except Exception as e:
        results.append(f"ERR {name}: {e}")
        traceback.print_exc()

# 1. Config
def t1():
    from backend.config import settings
    assert settings.llm_provider == "huggingface"
    assert settings.allow_demo_auth == True
test("config", t1)

# 2. Auth
def t2():
    from backend.core.auth import get_known_tokens
    tokens = get_known_tokens()
    assert "user-demo-token" in tokens
    assert "admin-demo-token" in tokens
test("auth tokens", t2)

# 3. DB
def t3():
    from backend.db import initialize_database
    initialize_database()
test("database init", t3)

# 4. HF service
def t4():
    from backend.services.huggingface_service import generate
    r = generate('Return JSON: {"score":80,"approved":true,"message":"ok","issues":[],"recommendations":[],"status":"approved","risk_level":"low","requires_human_review":false}', model_key="blog")
    assert not r.get("fallback"), f"fallback=True, issues={r.get('issues')}"
test("huggingface generate", t4)

# 5. LLM service routing
def t5():
    from backend.services import llm_service
    assert llm_service._get_provider() == "huggingface"
test("llm_service provider", t5)

# 6. Blog agent
def t6():
    from backend.agents.blog_ai_review import ai_review_blog
    import json
    r = json.loads(ai_review_blog("AI is changing healthcare."))
    assert "score" in r
test("blog_ai_review", t6)

# 7. Blog workflow
def t7():
    from backend.workflows.blog_workflow import blog_graph
    r = blog_graph.invoke({"user_input":"AI blog","route":"BLOG","response":{},"score":0,"approved":False,"iteration":0})
    assert r.get("route") == "BLOG"
test("blog_workflow", t7)

# 8. Salary agent
def t8():
    from backend.agents.salary_agent import calculate_employee_salary
    r = calculate_employee_salary({"user_input":"salary for basic 50000"})
    assert r["response"].get("net_salary") is not None
test("salary_agent", t8)

# 9. Security agent
def t9():
    from backend.agents.security_agent import run_security_check
    r = run_security_check({"user_input":"security check for EMP001"})
    assert "score" in r["response"]
test("security_agent", t9)

# 10. Support agent
def t10():
    from backend.agents.support_agent import create_support_ticket
    r = create_support_ticket({"user_input":"I cannot login"})
    assert r["response"].get("ticket_id")
test("support_agent", t10)

# 11. Full orchestrator
def t11():
    from backend.workflows.langgraph_orchestrator import graph
    r = graph.invoke({"user_input":"Write a blog about cloud","route":"","response":{},"score":0,"approved":False,"iteration":0})
    assert r.get("route") == "BLOG"
    assert r.get("status") == "completed"
test("orchestrator BLOG", t11)

def t12():
    from backend.workflows.langgraph_orchestrator import graph
    r = graph.invoke({"user_input":"I need help with login issue","route":"","response":{},"score":0,"approved":False,"iteration":0})
    assert r.get("route") == "SUPPORT"
test("orchestrator SUPPORT", t12)

# 12. FastAPI app import
def t13():
    from backend.main import app
    assert app is not None
test("fastapi app import", t13)

print("\n=== RESULTS ===")
for r in results:
    print(r)
