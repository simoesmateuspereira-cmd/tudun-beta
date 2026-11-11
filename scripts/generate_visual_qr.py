"""Gera apenas o QR fictício usado na prancha visual."""
from pathlib import Path

import qrcode

ROOT = Path(__file__).resolve().parent.parent
image = qrcode.make("TUDUN-VISUAL-FICTICIO-SEM-CHECKIN")
image.save(ROOT / "visual" / "qr-ficticio.png")
