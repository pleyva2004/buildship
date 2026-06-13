"""Central config for /agent. Loads .env, exposes settings + backend flag.

VISTA_BACKEND=mock|live selects the backend for ALL clients (per-client override
via e.g. NEBIUS_BACKEND). Mock is the default — the demo must run with zero keys.
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets"
SPECS_DIR = REPO_ROOT / "specs"
MOCKS_DIR = Path(__file__).resolve().parent / "mocks"


def _load_dotenv() -> None:
    """Tiny .env loader — no dependency, never overrides real env vars."""
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def backend(client: str = "") -> str:
    """Backend for a client: per-client override, else global, else mock."""
    if client:
        per_client = os.environ.get(f"{client.upper()}_BACKEND")
        if per_client:
            return per_client.lower()
    return os.environ.get("VISTA_BACKEND", "mock").lower()


# Nebius Token Factory (OpenAI-compatible)
NEBIUS_API_KEY = os.environ.get("NEBIUS_API_KEY", "")
NEBIUS_BASE_URL = os.environ.get("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1/")
NEBIUS_MODEL = os.environ.get("NEBIUS_MODEL", "Qwen/Qwen3.5-397B-A17B-fast")

# Filled in as the layers land (designs 01, 03):
MEM0_API_KEY = os.environ.get("MEM0_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY", "")
