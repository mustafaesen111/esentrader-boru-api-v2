from __future__ import annotations

from typing import Any, Dict, List

import asyncio
from ib_insync import IB

from admin_mode import get_ib_target, get_admin_mode


def ensure_event_loop() -> None:
    """
    Flask her request'i ayrı thread'de çalıştırdığı için,
    o thread'de bir asyncio event loop yoksa ib_insync hata veriyor:

        "There is no current event loop in thread 'Thread-1 (...)'"

    Bu fonksiyon, içinde çağrıldığı thread'e bir event loop atıyor.
    """
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)


class IBKRBroker:
    def __init__(self) -> None:
        # IB nesnesini ana thread'de oluşturuyoruz
        ensure_event_loop()
        self.ib = IB()
        self.host: str = "127.0.0.1"
        self.port: int = 7496
        self.client_id: int = 1

    # ---------------- Helpers ----------------

    def _refresh_target(self) -> None:
        target = get_ib_target()
        self.host = target.get("host", "127.0.0.1")
        self.port = int(target.get("port", 7496))

    def _base_status(self) -> Dict[str, Any]:
        return {
            "service": "ibkr",
            "host": self.host,
            "port": self.port,
            "client_id": self.client_id,
            "connected": self.ib.isConnected(),
        }

    # ---------------- Public Methods ----------------

    def connect(self) -> Dict[str, Any]:
        """
        IBKR'a bağlanmayı dener. Hata olursa error alanına yazar.
        Bu metod her çağrıldığında içinde bulunduğu thread'e
        event loop atıyoruz.
        """
        ensure_event_loop()
        self._refresh_target()
        status = self._base_status()

        if self.ib.isConnected():
            return status

        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            status["connected"] = self.ib.isConnected()
        except Exception as e:
            status["connected"] = False
            status["error"] = str(e)

        return status

    def get_status(self) -> Dict[str, Any]:
        """
        Hesap özetini döner.
        """
        ensure_event_loop()
        self._refresh_target()
        status = self._base_status()
        status["mode"] = get_admin_mode()

        if not self.ib.isConnected():
            status = self.connect()
            if not status.get("connected"):
                status.setdefault(
                    "note",
                    "Bağlantı sağlanamadı. IBKR TWS/Gateway açık mı?",
                )
                return status

        try:
            values = self.ib.accountValues()
            data: Dict[str, str] = {}
            for v in values:
                data[v.tag] = v.value

            def _to_float(val: str | None) -> float:
                try:
                    return float(val) if val else 0.0
                except ValueError:
                    return 0.0

            status.update(
                {
                    "account_id": data.get("Account", "N/A"),
                    "equity": _to_float(data.get("NetLiquidation")),
                    "cash": _to_float(data.get("AvailableFunds")),
                    "buying_power": _to_float(data.get("BuyingPower")),
                    "currency": data.get("Currency", "USD"),
                }
            )
        except Exception as e:
            status["error"] = str(e)

        return status

    def positions(self) -> List[Dict[str, Any]]:
        """
        Açık pozisyonları döner.
        """
        ensure_event_loop()
        self._refresh_target()

        if not self.ib.isConnected():
            s = self.connect()
            if not s.get("connected"):
                return []

        try:
            raw_positions = self.ib.positions()
        except Exception:
            return []

        result: List[Dict[str, Any]] = []
        for p in raw_positions:
            result.append(
                {
                    "symbol": p.contract.symbol,
                    "secType": p.contract.secType,
                    "position": float(p.position),
                    "avg_cost": float(p.avgCost),
                }
            )
        return result


# Global tek instance
ibkr = IBKRBroker()
