"""Env-file helpers shared by the setup console, the Telegram bot and the CLI.

Kept in their own module so ``aether.cli`` (and the bot) can read/write the
env file without importing the FastAPI app. ``aether.api.routes.setup``
re-exports these names so existing tests and call sites keep working.
"""

import os
from pathlib import Path
from typing import Dict, Optional


def env_file_path() -> Path:
    return Path(os.environ.get("AETHER_ENV_FILE", ".env"))


def load_env(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            data[key.strip()] = value.strip()
    return data


def write_env(updates: Dict[str, str], path: Optional[Path] = None) -> Path:
    """Merge ``updates`` into the env file, preserving unrelated keys."""
    path = path or env_file_path()
    data = load_env(path)
    data.update({k: v for k, v in updates.items() if v is not None})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{k}={v}\n" for k, v in data.items()))
    return path