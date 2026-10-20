import time
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from Backend.orchestrator import run_pipeline

print('--- Running test query 1 (Cold) ---')
t0 = time.perf_counter()
res = run_pipeline(
    'What are the key 5G network security controls required for telecom service providers in India?',
    jurisdiction='India',
    demo_mode=True,
)
t1 = time.perf_counter()
print(f'Total end-to-end elapsed (Cold): {t1 - t0:.2f} seconds')
for k, v in res.get('performance', {}).items():
    print(f'  {k}: {v} ms')

print('\n--- Running test query 2 (Warm) ---')
t0 = time.perf_counter()
res2 = run_pipeline(
    'What are the key 5G network security controls required for telecom service providers in India?',
    jurisdiction='India',
    demo_mode=True,
)
t1 = time.perf_counter()
print(f'Total end-to-end elapsed (Warm): {t1 - t0:.2f} seconds')
for k, v in res2.get('performance', {}).items():
    print(f'  {k}: {v} ms')
