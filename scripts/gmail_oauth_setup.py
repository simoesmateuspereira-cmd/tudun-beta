"""Autoriza o Gmail por loopback e guarda o refresh token fora do Git."""
import json
import os
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
CLIENT_ID = os.getenv("GMAIL_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "").strip()
if not CLIENT_ID or not CLIENT_SECRET:
    raise SystemExit("Preencha GMAIL_CLIENT_ID e GMAIL_CLIENT_SECRET no arquivo .env local.")

state = secrets.token_urlsafe(32)
result = {}
server = HTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
redirect_uri = f"http://127.0.0.1:{server.server_port}/oauth/callback"


class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        result.update({key: values[0] for key, values in query.items()})
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<h1>Autorização concluída</h1><p>Volte ao terminal.</p>".encode("utf-8"))
        threading.Thread(target=server.shutdown, daemon=True).start()

    def log_message(self, *args):
        pass


server.RequestHandlerClass = OAuthHandler
authorization_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
    {
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/gmail.send",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
)
print("Abra esta URL no navegador se ela não abrir automaticamente:\n" + authorization_url)
webbrowser.open(authorization_url)
server.timeout = 300
server.serve_forever(poll_interval=0.5)
server.server_close()
if result.get("state") != state or not result.get("code"):
    raise SystemExit("Autorização não concluída ou estado OAuth inválido. Nenhuma credencial foi gravada.")

token_request = Request(
    "https://oauth2.googleapis.com/token",
    data=urlencode(
        {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": result["code"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
    ).encode("ascii"),
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    method="POST",
)
with urlopen(token_request, timeout=30) as response:
    token = json.load(response)
if not token.get("refresh_token"):
    raise SystemExit("O Google não retornou refresh token. Revogue o acesso anterior e tente novamente.")

output = ROOT / ".runtime" / "gmail-oauth-credentials.json"
output.parent.mkdir(exist_ok=True)
output.write_text(
    json.dumps(
        {
            "GMAIL_CLIENT_ID": CLIENT_ID,
            "GMAIL_CLIENT_SECRET": CLIENT_SECRET,
            "GMAIL_REFRESH_TOKEN": token["refresh_token"],
        },
        indent=2,
    ),
    encoding="utf-8",
)
try:
    output.chmod(0o600)
except OSError:
    pass
print(f"Credenciais salvas somente em: {output}")
print("Nenhum segredo foi exibido. Copie os valores diretamente para os campos secretos do Render.")
