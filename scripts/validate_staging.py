"""Sobe homologação local temporária, valida respostas e encerra tudo."""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
PORT = int(os.getenv("STAGING_TEST_PORT", "51235"))
BASE = f"http://127.0.0.1:{PORT}"
LOG = ROOT / ".runtime" / "staging-validation.log"
LOG.parent.mkdir(parents=True, exist_ok=True)

with LOG.open("w", encoding="utf-8") as log:
    server = subprocess.Popen(
        [str(PYTHON), "scripts/staging.py", "--port", str(PORT)],
        cwd=ROOT,
        stdout=log,
        stderr=log,
    )
    try:
        for _ in range(80):
            if server.poll() is not None:
                raise RuntimeError(f"Homologação encerrou antes do teste; consulte {LOG}")
            try:
                with urllib.request.urlopen(BASE + "/saude/", timeout=1) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(0.25)
        else:
            raise RuntimeError("Homologação não ficou disponível.")

        for route in ("/", "/identidade/entrar/", "/identidade/privacidade/", "/saude/", "/static/tudun.css"):
            with urllib.request.urlopen(BASE + route, timeout=5) as response:
                if response.status != 200:
                    raise RuntimeError(f"Rota {route}: HTTP {response.status}")
                if response.headers.get("X-Content-Type-Options") != "nosniff":
                    raise RuntimeError(f"Cabeçalho nosniff ausente em {route}")
                print(f"HTTP {response.status}: {route}")
        print("HOMOLOGAÇÃO LOCAL VALIDADA: DEBUG=False, PostgreSQL, Waitress e WhiteNoise.")
    finally:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(server.pid)], capture_output=True)
        print("Servidor temporário de homologação encerrado.")
