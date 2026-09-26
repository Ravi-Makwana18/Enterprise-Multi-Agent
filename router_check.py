import requests, os
from dotenv import load_dotenv
load_dotenv('.env', override=True)
token = os.getenv('HUGGINGFACE_API_TOKEN','')

# Models known to be free on HF router
models = [
    'Qwen/Qwen2.5-72B-Instruct',
    'Qwen/Qwen3-235B-A22B',
    'Qwen/Qwen2.5-7B-Instruct',
    'mistralai/Mistral-7B-Instruct-v0.3',
    'mistralai/Mistral-Nemo-Instruct-2407',
    'google/gemma-3-27b-it',
    'deepseek-ai/DeepSeek-R1-Distill-Qwen-32B',
    'nvidia/Llama-3.1-Nemotron-70B-Instruct-HF',
]
for m in models:
    try:
        r = requests.post(
            'https://router.huggingface.co/v1/chat/completions',
            headers={'Authorization': 'Bearer '+token, 'Content-Type':'application/json'},
            json={'model': m, 'messages':[{'role':'user','content':'Say hi in 3 words'}], 'max_tokens':10},
            timeout=20
        )
        print(m, '->', r.status_code, r.text[:120], flush=True)
    except Exception as e:
        print(m, '-> ERROR:', e, flush=True)
