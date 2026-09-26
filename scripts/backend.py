import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "asthma-app"

venv_python = APP_DIR / ".venv" / "Scripts" / "python.exe"

env = os.environ.copy()
env["PYTHONPATH"] = str(APP_DIR)

subprocess.run(
    [
        str(venv_python),
        "-m",
        "uvicorn",
        "api.main:app",
        "--reload",
        "--app-dir",
        ".",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ],
    cwd=APP_DIR,
    env=env,
)