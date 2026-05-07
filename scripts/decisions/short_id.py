import random
import string
from .db import rest

_CHARS = string.ascii_letters + string.digits  # base62


def generate_unique_short_id() -> str:
    """Generate rec_XXXXXX — unique against decisions.short_id."""
    for _ in range(8):
        candidate = "rec_" + "".join(random.choices(_CHARS, k=6))
        rows = rest("GET", f"decisions?short_id=eq.{candidate}&select=short_id").json()
        if not rows:
            return candidate
    raise RuntimeError("Could not generate unique short_id after 8 attempts")
