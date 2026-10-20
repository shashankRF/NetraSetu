import os, time
from groq import Groq
from dotenv import load_dotenv

load_dotenv('.env')
key = os.getenv('GROQ_API_KEY')
print('API key present:', bool(key))

client = Groq(api_key=key)
print('Testing Groq openai/gpt-oss-120b with timeout=15.0...')
t0 = time.perf_counter()
try:
    resp = client.chat.completions.create(
        model='openai/gpt-oss-120b',
        messages=[{'role': 'user', 'content': 'Say "test" only.'}],
        max_tokens=10,
        timeout=15.0,
    )
    t1 = time.perf_counter()
    print(f'Success in {t1-t0:.2f}s: {resp.choices[0].message.content}')
except Exception as e:
    t1 = time.perf_counter()
    print(f'Failed in {t1-t0:.2f}s: {type(e).__name__}: {e}')
