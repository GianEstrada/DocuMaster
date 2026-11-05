import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SESSION_TTL_SECONDS = 60 * 60 * 12


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}.")
    return value
