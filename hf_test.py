import requests, os, sys
from dotenv import load_dotenv
load_dotenv('.env', override=True)
token = os.getenv('HUGGINGFACE_API_TOKEN', '')
print('Token prefix:', token[:12], flush=True)
try:
    resp = requests.post(
        'https://router.huggingface.co/v1/chat/completions',
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
        json={
            'model': 'meta-llama/Llama-3.1-8B-Instruct',
            'messages': [{'role': 'user', 'content': 'Say hi'}],
            'max_tokens': 10
        },
        timeout=30
    )
    print('Status:', resp.status_code, flush=True)
    print('Body:', resp.text[:400], flush=True)
except Exception as e:
    print('Error:', type(e).__name__, str(e), flush=True)
