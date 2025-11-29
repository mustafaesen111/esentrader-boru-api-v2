from __future__ import annotations

from typing import Any, Dict, List

from ib_insync import IB


class IBKRBroker:
    """
    VPS üzerindeki boru API, SSH tüneli üzerinden
    senin PC'deki TWS/IB Gateway'e bağlanır.

    - TWS IB API portu: 7497
    - SSH tüneli: 5.78.152.122:7497 -> PC:7497
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
    ) -> None:
        self.host = host
        self.port = port
        self.client_id = client_id

        self.ib = IB()

    # ----------------- İç yardımcılar -----------------

    def _base_status(self) -> Dict[str, Any]:
        return {
            "service": "ibkr",
            "host": self.host,
            "port": self.port,
            "client_id": self.client_id,
            "connected": self.ib.isConnected(),
        }

    # ----------------- Dışa açık metodlar -----------------

    def connect(self) -> Dict[str, Any]:
        """
        IBKR TWS'e bağlanmayı dener.
        Hata olursa status["error"] içine yazar.
        """
        status = self._base_status()

        if self.ib.isConnected():
            return status

        try:
            # ÖNEMLİ: timeout yok, senkron connect
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            status["connected"] = self.ib.isConnected()
        except Exception as e:  # noqa: BLE001
            status["connected"] = False
            status["error"] = str(e)

        return status

    def get_status(self) -> Dict[str, Any]:
        """
        Status isterken otomatik olarak önce connect() dener.
        Bağlantı yoksa -> bağlanmaya çalışır ve sonucu döner.
        """
        # Bağlı değilsek önce bağlanmayı dene
        if not self.ib.isConnected():
            return self.connect()

        status = self._base_status()

        try:
            # Hesap bilgilerini çek (paper/live fark etmez)
            values = self.ib.accountValues()
            data: Dict[str, str] = {}
            for v in values:
                # her tag için son gelen değeri yaz
                data[v.tag] = v.value

            def _to_float(val: str | None) -> float:
                try:
                    return float(val) if val is not None else 0.0
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
        except Exception as e:  # noqa: BLE001
            status["error"] = str(e)

        return status

    def positions(self) -> List[Dict[str, Any]]:
        """
        Açık pozisyonları döner. Bağlantı yoksa önce connect() dener.
        """
        if not self.ib.isConnected():
            s = self.connect()
            if not s.get("connected"):
                return []

        try:
            raw_positions = self.ib.positions()
        except Exception:  # noqa: BLE001
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
