import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env.local")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def rest(method: str, path: str, **kwargs) -> requests.Response:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    resp = requests.request(method, url, headers=_HEADERS, **kwargs)
    resp.raise_for_status()
    return resp


def rpc(fn: str, params: dict) -> list:
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/rpc/{fn}",
        headers=_HEADERS,
        json=params,
    )
    resp.raise_for_status()
    return resp.json()
