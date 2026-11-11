"""Valida telas públicas e a prancha visual, sem alterar dados ou executar ações."""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import manage

ROOT = manage.BASE_DIR
PORT = int(os.getenv("VISUAL_PORT", "51234"))
BASE = os.getenv("VISUAL_BASE", f"http://127.0.0.1:{PORT}")
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
SCREENSHOTS = ROOT / ".runtime" / "screenshots"
SCREENSHOTS.mkdir(parents=True, exist_ok=True)
LOG_PATH = ROOT / ".runtime" / "visual-server.log"


def capture_page(browser, name, url, width, height, mobile=False, storage_state=None):
    context = browser.new_context(
        viewport={"width": width, "height": height},
        device_scale_factor=1,
        is_mobile=mobile,
        storage_state=storage_state,
    )
    page = context.new_page()
    try:
        response = page.goto(url, wait_until="networkidle", timeout=30000)
        if response and response.status >= 400:
            raise RuntimeError(f"HTTP {response.status} em {name}")
        overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
        if overflow:
            raise RuntimeError(f"Overflow horizontal em {name}")
        if name == "guia-visual-desktop":
            expected_colors = {
                ".plan-card-featured": "rgb(220, 235, 221)",
                ".event-included": "rgb(215, 235, 156)",
                ".status-last-seats": "rgb(244, 237, 218)",
                ".status-declined": "rgb(245, 228, 223)",
                ".status-sold-out": "rgb(238, 240, 234)",
            }
            for selector, expected in expected_colors.items():
                actual = page.locator(selector).first.evaluate("element => getComputedStyle(element).backgroundColor")
                if actual != expected:
                    raise RuntimeError(f"Cor inesperada em {selector}: {actual}; esperado {expected}")
        if name == "eventos-desktop" and page.locator(".event-card").count() != 5:
            raise RuntimeError("O catálogo autenticado não apresentou os cinco eventos fictícios.")
        destination = SCREENSHOTS / f"{name}.png"
        page.screenshot(path=str(destination), full_page=True)
        print(f"CAPTURA: {destination}")
    finally:
        context.close()


TEMP_PASSWORD = "TudunVisual-2026!"
TEMP_TOTP_HEX = "0123456789abcdef0123456789abcdef01234567"
ACCOUNT_SETUP = """
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from communities.models import Community, Membership
from identity.models import IdentityProfile
User = get_user_model()
with transaction.atomic():
    if User.objects.filter(username__in=['moderador_visual_temp', 'super_visual_temp']).exists():
        raise RuntimeError('Contas temporárias de validação visual já existem; não serão sobrescritas.')
    moderator = User.objects.create_user('moderador_visual_temp', 'moderador.visual.temp@example.invalid', 'TudunVisual-2026!')
    administrator = User.objects.create_superuser('super_visual_temp', 'super.visual.temp@example.invalid', 'TudunVisual-2026!')
    IdentityProfile.objects.create(user=moderator, email_verified_at=timezone.now())
    IdentityProfile.objects.create(user=administrator, email_verified_at=timezone.now())
    Membership.objects.create(
        community=Community.objects.get(slug='comunidade-ficticia'),
        user=moderator,
        role=Membership.Role.MODERATOR,
        status=Membership.Status.ACTIVE,
        joined_at=timezone.now(),
    )
    TOTPDevice.objects.create(user=administrator, name='Validação visual', key='0123456789abcdef0123456789abcdef01234567', confirmed=True)
"""
ACCOUNT_CLEANUP = """
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.filter(username='moderador_visual_temp', email='moderador.visual.temp@example.invalid').delete()
User.objects.filter(username='super_visual_temp', email='super.visual.temp@example.invalid').delete()
"""


def manage_visual_accounts(cleanup=False):
    subprocess.run(
        [str(ROOT / ".venv" / "Scripts" / "python.exe"), "manage.py", "shell", "-c", ACCOUNT_CLEANUP if cleanup else ACCOUNT_SETUP],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def authenticated_state(browser, username, password, mfa_hex=None):
    from django_otp.oath import totp

    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    try:
        page.goto(BASE + "/identidade/entrar/", wait_until="networkidle", timeout=30000)
        page.locator('input[name="username"]').fill(username)
        page.locator('input[name="password"]').fill(password)
        with page.expect_navigation(wait_until="networkidle", timeout=30000):
            page.locator('button[type="submit"]').click()
        if mfa_hex:
            if "/identidade/mfa/" not in page.url:
                raise RuntimeError("O acesso administrativo temporário não exigiu MFA.")
            page.locator('input[name="token"]').fill(f"{totp(bytes.fromhex(mfa_hex)):06d}")
            with page.expect_navigation(wait_until="networkidle", timeout=30000):
                page.locator('form button.button[type="submit"]').click()
        if "/identidade/entrar/" in page.url or "/identidade/mfa/" in page.url:
            raise RuntimeError(f"Não foi possível entrar com a conta fictícia {username}.")
        print(f"JORNADA AUTENTICADA: login de {username} concluído.")
        return context.storage_state()
    finally:
        context.close()


accounts_created = False
try:
    manage_visual_accounts()
    accounts_created = True
    with LOG_PATH.open("w") as log:
        server = subprocess.Popen(
            ["npm.cmd", "run", "dev", "--", "--port", str(PORT)],
            cwd=ROOT,
            stdout=log,
            stderr=log,
        )
        browser = None
        try:
            for _ in range(80):
                if server.poll() is not None:
                    raise RuntimeError(f"Servidor encerrou antes da validação; consulte {LOG_PATH}")
                try:
                    with urllib.request.urlopen(BASE, timeout=1) as response:
                        if response.status == 200:
                            break
                except Exception:
                    time.sleep(0.25)
            else:
                raise RuntimeError("Servidor não ficou disponível.")

            for route in ("/", "/identidade/entrar/", "/identidade/criar-conta/", "/static/tudun.css"):
                with urllib.request.urlopen(BASE + route, timeout=5) as response:
                    if response.status != 200:
                        raise RuntimeError(f"Rota {route}: HTTP {response.status}")
                    print(f"HTTP 200: {route}")

            playwright = sync_playwright().start()
            try:
                browser = playwright.chromium.launch(executable_path=str(CHROME), headless=True)
                guide_url = (ROOT / "visual" / "guia-visual.html").as_uri()
                capture_page(browser, "home-desktop", BASE + "/", 1440, 1000)
                capture_page(browser, "home-mobile", BASE + "/", 390, 844, mobile=True)
                capture_page(browser, "login-desktop", BASE + "/identidade/entrar/", 1440, 1000)
                capture_page(browser, "guia-visual-desktop", guide_url, 1440, 1000)
                capture_page(browser, "guia-visual-mobile", guide_url, 390, 844, mobile=True)
                member_state = authenticated_state(browser, "membro_teste", "TudunTeste-2026!")
                moderator_state = authenticated_state(browser, "moderador_visual_temp", TEMP_PASSWORD)
                administrator_state = authenticated_state(browser, "super_visual_temp", TEMP_PASSWORD, TEMP_TOTP_HEX)
                community_url = BASE + "/comunidades/comunidade-ficticia/"
                events_url = community_url + "eventos/"
                event_url = events_url + "encontro-da-comunidade/"
                capture_page(browser, "comunidade-desktop", community_url, 1440, 1000, storage_state=member_state)
                capture_page(browser, "comunidade-mobile", community_url, 390, 844, mobile=True, storage_state=member_state)
                capture_page(browser, "eventos-desktop", events_url, 1440, 1000, storage_state=member_state)
                capture_page(browser, "eventos-mobile", events_url, 390, 844, mobile=True, storage_state=member_state)
                capture_page(browser, "evento-detalhe-desktop", event_url, 1440, 1000, storage_state=member_state)
                capture_page(browser, "evento-detalhe-mobile", event_url, 390, 844, mobile=True, storage_state=member_state)
                capture_page(browser, "evento-novo-desktop", events_url + "novo/", 1440, 1000, storage_state=moderator_state)
                capture_page(browser, "evento-novo-mobile", events_url + "novo/", 390, 844, mobile=True, storage_state=moderator_state)
                capture_page(browser, "evento-editar-desktop", event_url + "editar/", 1440, 1000, storage_state=moderator_state)
                capture_page(browser, "evento-editar-mobile", event_url + "editar/", 390, 844, mobile=True, storage_state=moderator_state)
                capture_page(browser, "evento-cancelar-desktop", event_url + "cancelar/", 1440, 1000, storage_state=moderator_state)
                capture_page(browser, "evento-cancelar-mobile", event_url + "cancelar/", 390, 844, mobile=True, storage_state=moderator_state)
                capture_page(browser, "comunidade-nova-desktop", BASE + "/comunidades/nova/", 1440, 1000, storage_state=administrator_state)
                capture_page(browser, "comunidade-nova-mobile", BASE + "/comunidades/nova/", 390, 844, mobile=True, storage_state=administrator_state)
            finally:
                if browser:
                    browser.close()
                playwright.stop()
            print("VALIDAÇÃO VISUAL CONCLUÍDA: membro e gestão, cores oficiais e ausência de overflow horizontal.")
        finally:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(server.pid)], capture_output=True)
            print("Servidor temporário encerrado.")
finally:
    if accounts_created:
        manage_visual_accounts(cleanup=True)
        print("Contas temporárias de validação visual removidas.")
