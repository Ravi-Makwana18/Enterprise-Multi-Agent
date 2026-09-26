import requests, os
from dotenv import load_dotenv
load_dotenv('.env', override=True)
token = os.getenv('HUGGINGFACE_API_TOKEN','')
print("Token:", token[:12], flush=True)

models = [
    'HuggingFaceH4/zephyr-7b-beta',
    'mistralai/Mistral-7B-Instruct-v0.1',
    'microsoft/Phi-3-mini-4k-instruct',
    'Qwen/Qwen2.5-7B-Instruct',
    'google/gemma-2-2b-it',
    'meta-llama/Llama-3.2-1B-Instruct',
]
for m in models:
    try:
        r = requests.post(
            f'https://api-inference.huggingface.co/models/{m}/v1/chat/completions',
            headers={'Authorization': 'Bearer '+token},
            json={'model': m, 'messages':[{'role':'user','content':'Say hi'}], 'max_tokens':10},
            timeout=20
        )
        print(m, '->', r.status_code, r.text[:100], flush=True)
    except Exception as e:
        print(m, '-> ERROR:', e, flush=True)
