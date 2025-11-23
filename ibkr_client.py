"""
ibkr_client.py
IBKRClient:
- LOCAL modda: PC üzerindeki boru-api-local servisine gider (SSH reverse tünel ile 6001).
- VPS modda : İleride VPS üzerindeki IBKR servisine gidecek (şimdilik placeholder).
Bu sınıf IBKR verisini HTTP üzerinden çeker, IBKR'a direkt bağlanmaz.
"""

import requests
from admin_mode import get_admin_mode


class IBKRClient:
    def __init__(self):
        pass

    def get_base_url(self) -> str:
        """
        LOCAL:
            VPS → ssh reverse ile PC'ye gider:
            ssh -R 6001:127.0.0.1:5055 root@5.78.152.122

            Sonra VPS'ten 127.0.0.1:6001 → PC'deki boru-api-local:5055

        VPS:
            İleride VPS IBKR servisini buraya bağlayacağız (ör: 6002).
        """
        mode = get_admin_mode()
        if mode == "LOCAL":
            return "http://127.0.0.1:6001"
        elif mode == "VPS":
            # Şimdilik placeholder, ileride gerçek VPS IBKR servisine gidecek
            return "http://127.0.0.1:6002"
        else:
            return "http://127.0.0.1:6001"

    def _request_json(self, path: str, timeout: float = 5.0):
        """Verilen path için JSON isteği yapar ve sonuç + meta döner."""
        base = self.get_base_url()
        url = base + path
        mode = get_admin_mode()
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return {
                "ok": True,
                "mode": mode,
                "url": url,
                "data": resp.json(),
                "error": None,
            }
        except Exception as e:
            return {
                "ok": False,
                "mode": mode,
                "url": url,
                "data": None,
                "error": str(e),
            }

    def get_status(self):
        """Uzak /api/ibkr/status endpoint'ini çağırır."""
        return self._request_json("/api/ibkr/status")

    def get_positions(self):
        """Uzak /api/ibkr/positions endpoint'ini çağırır."""
        return self._request_json("/api/ibkr/positions")
