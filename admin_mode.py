import json
import os

MODE_FILE = os.path.join(os.path.dirname(__file__), "admin_mode.json")
DEFAULT_MODE = "LOCAL"  # LOCAL veya VPS

def get_admin_mode() -> str:
    """
    Admin panelindeki toggle butonunun seçtiği modu döndürür.
    Dosya yoksa veya bozuksa DEFAULT_MODE döner.
    """
    try:
        if not os.path.exists(MODE_FILE):
            return DEFAULT_MODE

        with open(MODE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            mode = data.get("mode", DEFAULT_MODE)
            if mode not in ("LOCAL", "VPS"):
                return DEFAULT_MODE
            return mode
    except Exception:
        return DEFAULT_MODE


def set_admin_mode(mode: str) -> None:
    """
    Admin’den gelen yeni modu json dosyasına yazar.
    """
    if mode not in ("LOCAL", "VPS"):
        mode = DEFAULT_MODE

    data = {"mode": mode}
    with open(MODE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


if __name__ == "__main__":
    # Test için: python admin_mode.py
    print(get_admin_mode())

