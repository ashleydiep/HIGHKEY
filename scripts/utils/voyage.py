import os
import time
import requests
from typing import List

VOYAGE_API_KEY = os.environ.get('VOYAGE_API_KEY')

def embed_batch(texts: List[str], retries: int = 8) -> List[List[float]]:
    if not texts:
        return []
    if not VOYAGE_API_KEY:
        raise EnvironmentError('Missing VOYAGE_API_KEY')

    delay = 15.0
    for attempt in range(retries):
        res = requests.post(
            'https://api.voyageai.com/v1/embeddings',
            headers={'Authorization': f'Bearer {VOYAGE_API_KEY}', 'Content-Type': 'application/json'},
            json={'model': 'voyage-3-large', 'input': texts},
            timeout=60,
        )
        if res.status_code == 429:
            wait = min(delay * (2 ** attempt), 120)
            print(f'  [voyage] rate limited, waiting {wait:.0f}s...')
            time.sleep(wait)
            continue
        res.raise_for_status()
        return [d['embedding'] for d in res.json()['data']]

    raise RuntimeError(f'Voyage rate limit not resolved after {retries} retries')

def chunk_list(lst: list, size: int) -> list:
    return [lst[i:i + size] for i in range(0, len(lst), size)]
