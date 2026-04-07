#!/usr/bin/env python3
"""
Wrapper: run live GFW health tests (no prompts).

From repo root:

  python3 scripts/gfw_api_probe.py

Loads ../.env if present, sets GFW_API_HEALTH=1, runs pytest -m gfw_health.

Or run pytest directly from backend/ (see backend/tests/test_gfw_api_health.py).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND = REPO_ROOT / "backend"
ENV_PATH = REPO_ROOT / ".env"


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def main() -> int:
    load_dotenv(ENV_PATH)
    if not os.environ.get("GFW_API_TOKEN"):
        print("GFW_API_TOKEN missing: set it or add to .env at repo root.", file=sys.stderr)
        return 1
    env = {**os.environ, "GFW_API_HEALTH": "1"}
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-m",
        "gfw_health",
        "-v",
        str(BACKEND / "tests" / "test_gfw_api_health.py"),
    ]
    print("Running:", " ".join(cmd), "(cwd=backend)")
    r = subprocess.run(cmd, cwd=str(BACKEND), env=env)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
