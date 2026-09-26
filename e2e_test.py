import sys, os
sys.path.insert(0, '.')
os.environ.setdefault('PYTHONPATH', '.')

from backend.services.huggingface_service import generate

print("=== Testing blog generate ===", flush=True)
result = generate(
    'Review this blog: "AI is transforming healthcare by enabling faster diagnosis." Return JSON with score, approved, message, issues, recommendations, status, risk_level, requires_human_review.',
    model_key='blog'
)
print("Result keys:", list(result.keys()), flush=True)
print("Score:", result.get('score'), flush=True)
print("Approved:", result.get('approved'), flush=True)
print("Message:", str(result.get('message', ''))[:100], flush=True)
print("Fallback:", result.get('fallback'), flush=True)
