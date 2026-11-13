import base64
import io
import json
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs

from django.core.mail import EmailMessage
from django.test import SimpleTestCase

from identity.gmail_backend import GmailAPIBackend


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return io.BytesIO(json.dumps(self.payload).encode("utf-8"))

    def __exit__(self, *args):
        return False


class GmailAPIBackendTests(SimpleTestCase):
    credentials = {
        "GMAIL_CLIENT_ID": "cliente-teste",
        "GMAIL_CLIENT_SECRET": "segredo-teste",
        "GMAIL_REFRESH_TOKEN": "renovacao-teste",
    }

    def message(self):
        return EmailMessage("Assunto", "Corpo", "remetente@gmail.com", ["destino@example.invalid"])

    @patch.dict("os.environ", credentials, clear=False)
    @patch("identity.gmail_backend.urlopen")
    def test_sends_rfc2822_message_over_https(self, urlopen):
        urlopen.side_effect = [FakeResponse({"access_token": "acesso-temporario"}), FakeResponse({"id": "enviado"})]

        self.assertEqual(GmailAPIBackend().send_messages([self.message()]), 1)

        token_request = urlopen.call_args_list[0].args[0]
        self.assertEqual(token_request.full_url, "https://oauth2.googleapis.com/token")
        self.assertEqual(parse_qs(token_request.data.decode())["grant_type"], ["refresh_token"])
        send_request = urlopen.call_args_list[1].args[0]
        self.assertEqual(send_request.get_header("Authorization"), "Bearer acesso-temporario")
        raw = json.loads(send_request.data)["raw"]
        mime = base64.urlsafe_b64decode(raw).decode("utf-8")
        self.assertIn("Subject: Assunto", mime)
        self.assertIn("To: destino@example.invalid", mime)
        self.assertIn("Corpo", mime)

    @patch.dict("os.environ", credentials, clear=False)
    @patch("identity.gmail_backend.urlopen")
    def test_ignores_messages_without_recipients(self, urlopen):
        message = self.message()
        message.to = []
        self.assertEqual(GmailAPIBackend().send_messages([message]), 0)
        urlopen.assert_not_called()

    @patch.dict("os.environ", credentials, clear=False)
    @patch("identity.gmail_backend.urlopen")
    def test_http_error_does_not_expose_credentials(self, urlopen):
        urlopen.side_effect = HTTPError("https://oauth2.googleapis.com/token", 401, "Unauthorized", {}, io.BytesIO())
        with self.assertRaises(RuntimeError) as raised:
            GmailAPIBackend().send_messages([self.message()])
        self.assertEqual(str(raised.exception), "Falha na API do Gmail (HTTP 401).")
        for secret in self.credentials.values():
            self.assertNotIn(secret, str(raised.exception))

    @patch.dict("os.environ", {"GMAIL_CLIENT_ID": "", "GMAIL_CLIENT_SECRET": "", "GMAIL_REFRESH_TOKEN": ""})
    def test_fail_silently_with_missing_credentials(self):
        self.assertEqual(GmailAPIBackend(fail_silently=True).send_messages([self.message()]), 0)
