"""
admin_mode.py
Admin panelden seçilen IBKR modu (LOCAL / VPS) için yardımcı fonksiyonlar.
Seçim admin_mode.json dosyasına yazılır.
"""

from pathlib import Path
import json

MODE_FILE = Path(__file__).with_name("admin_mode.json")
DEFAULT_MODE = "LOCAL"  # Başlangıç modu


def get_admin_mode() -> str:
    """Geçerli modu oku (LOCAL veya VPS). Dosya yoksa LOCAL döner."""
    try:
        if MODE_FILE.exists():
            data = json.loads(MODE_FILE.read_text(encoding="utf-8"))
            mode = data.get("mode", DEFAULT_MODE)
            if mode in ("LOCAL", "VPS"):
                return mode
    except Exception:
        pass
    return DEFAULT_MODE


def set_admin_mode(mode: str) -> str:
    """Modu ayarla ve dosyaya yaz. Sadece LOCAL veya VPS kabul edilir."""
    mode = (mode or "").upper()
    if mode not in ("LOCAL", "VPS"):
        raise ValueError("mode must be 'LOCAL' or 'VPS'")
    data = {"mode": mode}
    MODE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return mode
def get_ibkr_mode():
    """Eski isimle uyumluluk için (geri dönük)."""
    return get_admin_mode()


def set_ibkr_mode(mode: str):
    """Eski isimle uyumluluk için (geri dönük)."""
    set_admin_mode(mode)
