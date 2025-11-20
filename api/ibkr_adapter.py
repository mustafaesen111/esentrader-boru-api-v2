"""
IBKR boru adaptörü (iskelet sürüm)

Şu an sadece 7497 portu açık mı kontrol ediyor.
IB Gateway + IBC tam oturduğunda, buraya ib_insync tabanlı
gerçek hesap / pozisyon fonksiyonlarını ekleyeceğiz.

Ama app.py ve web tarafı bundan etkilenmeyecek;
sadece bu dosyanın içi genişleyecek.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Dict


@dataclass
class IbkrConfig:
    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 1
    timeout: float = 1.0  # saniye


class IbkrAdapter:
    def __init__(self, cfg: IbkrConfig | None = None) -> None:
        self.cfg = cfg or IbkrConfig()

    # ---------- İç yardımcılar ----------

    def _check_port_open(self) -> bool:
        """
        Sadece TCP seviyesinde 7497 portu açık mı diye bakar.
        IB Gateway gerçekten login olduysa bu port dinlemededir.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.cfg.timeout)
        try:
            sock.connect((self.cfg.host, self.cfg.port))
            sock.close()
            return True
        except OSError:
            return False

    # ---------- Dış API ----------

    def get_status(self) -> Dict:
        """
        API'nin dünyaya döndüğü tek IBKR status fonksiyonu.
        Şu an sadece port durumuna göre 'connected' alanını dolduruyor.
        İleride buraya gerçek IBKR API bağlantı kontrolü,
        account id, son ping zamanı vs. ekleyebiliriz.
        """
        port_open = self._check_port_open()

        if port_open:
            note = (
                "IB Gateway 7497 portu açık görünüyor. "
                "2FA temizlenip IBC otomatik login oturduktan sonra "
                "hesap/pozisyon fonksiyonları aktifleştirilebilir."
            )
        else:
            note = (
                "IB Gateway henüz bağlanmadı veya 7497 portu kapalı. "
                "Google Authenticator kaldırılıp IBC login tamamlanınca "
                "buradaki 'connected' alanı true olacak."
            )

        return {
            "service": "ibkr",
            "host": self.cfg.host,
            "port": self.cfg.port,
            "client_id": self.cfg.client_id,
            "connected": port_open,
            "note": note,
        }

    # Buraya ileride:
    # - get_account()
    # - get_positions()
    # - place_order()
    # gibi fonksiyonlar eklenecek. app.py ve web bunlardan bağımsız kalacak.


# Uygulama genelinde kullanılacak tek instance
ibkr = IbkrAdapter()
