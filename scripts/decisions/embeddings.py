import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env.local")

VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
VOYAGE_MODEL = "voyage-3"


def embed(text: str, input_type: str = "document") -> list[float]:
    """Embed a single text via Voyage AI. Returns 1024-dim vector."""
    resp = requests.post(
        "https://api.voyageai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {VOYAGE_API_KEY}", "Content-Type": "application/json"},
        json={"model": VOYAGE_MODEL, "input": [text], "input_type": input_type},
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def prepare_decision_text(question: str, chosen: str = "", rationale: str = "") -> str:
    parts = [f"Decision: {question}"]
    if chosen:
        parts.append(f"Choice: {chosen}")
    if rationale:
        parts.append(f"Rationale: {rationale}")
    return " | ".join(parts)
