"""Shared config loader for all agent attraction scripts."""
import json
from pathlib import Path


def load_config(config_path: str = None) -> dict:
    """Load agent config.json. Looks in the same directory as the script by default."""
    if config_path:
        path = Path(config_path)
    else:
        path = Path(__file__).parent / 'config.json'

    if not path.exists():
        raise FileNotFoundError(
            f'config.json not found at {path}.\n'
            'Run: python3 setup.py  to create it.'
        )
    return json.loads(path.read_text())
