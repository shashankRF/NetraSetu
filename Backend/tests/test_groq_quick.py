from __future__ import annotations

import os
import time

import pytest
from dotenv import load_dotenv

load_dotenv('.env')

# This is an opt-in live-provider smoke check. Ordinary CI/local test runs stay
# offline and deterministic; the app's retrieval pipeline does not require Groq.
pytestmark = pytest.mark.skipif(
    os.getenv('NETRASETU_RUN_LIVE_API_TESTS') != '1' or not os.getenv('GROQ_API_KEY'),
    reason='Set NETRASETU_RUN_LIVE_API_TESTS=1 and GROQ_API_KEY to run the live Groq check.',
)


def test_groq_live_smoke():
    from groq import Groq

    client = Groq(api_key=os.getenv('GROQ_API_KEY'))
    started = time.perf_counter()
    response = client.chat.completions.create(
        model='openai/gpt-oss-120b',
        messages=[{'role': 'user', 'content': 'Say "test" only.'}],
        max_tokens=10,
        timeout=15.0,
    )
    elapsed = time.perf_counter() - started
    assert response.choices[0].message.content
    print(f'Groq smoke test succeeded in {elapsed:.2f}s.')
