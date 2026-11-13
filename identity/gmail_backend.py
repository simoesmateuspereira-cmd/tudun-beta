"""Backend de e-mail do Django usando a API HTTPS do Gmail e OAuth 2."""
import base64
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.mail.backends.base import BaseEmailBackend


class GmailAPIBackend(BaseEmailBackend):
    token_url = "https://oauth2.googleapis.com/token"
    send_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

    def __init__(self, fail_silently=False, timeout=None, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.client_id = os.getenv("GMAIL_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("GMAIL_CLIENT_SECRET", "").strip()
        self.refresh_token = os.getenv("GMAIL_REFRESH_TOKEN", "").strip()
        self.timeout = timeout or int(os.getenv("EMAIL_TIMEOUT", "10"))

    def _json_request(self, request):
        with urlopen(request, timeout=self.timeout) as response:
            return json.load(response)

    def _access_token(self):
        if not all((self.client_id, self.client_secret, self.refresh_token)):
            raise RuntimeError("Credenciais OAuth do Gmail incompletas.")
        request = Request(
            self.token_url,
            data=urlencode(
                {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                }
            ).encode("ascii"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        response = self._json_request(request)
        token = response.get("access_token", "")
        if not token:
            raise RuntimeError("A API OAuth do Gmail não retornou um token de acesso.")
        return token

    def _send(self, email_message):
        raw = base64.urlsafe_b64encode(email_message.message().as_bytes()).decode("ascii")
        request = Request(
            self.send_url,
            data=json.dumps({"raw": raw}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._access_token()}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        self._json_request(request)

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            if not message.recipients():
                continue
            try:
                self._send(message)
            except (HTTPError, URLError, RuntimeError, ValueError) as error:
                if not self.fail_silently:
                    if isinstance(error, HTTPError):
                        raise RuntimeError(f"Falha na API do Gmail (HTTP {error.code}).") from None
                    if isinstance(error, URLError):
                        raise RuntimeError("Não foi possível conectar à API do Gmail.") from None
                    raise
                break
            sent += 1
        return sent
