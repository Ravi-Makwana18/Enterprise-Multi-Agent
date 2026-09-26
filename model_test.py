from backend.models.response import ChatResponse
try:
    r = ChatResponse(route='BLOG', response={}, score=92.0, approved=True, iteration=0)
    print('score type:', type(r.score), 'value:', r.score)
except Exception as e:
    print('ERROR:', e)
