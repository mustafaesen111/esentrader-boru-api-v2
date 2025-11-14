from ib_insync import IB, Stock


class IBKRBroker:
    def __init__(self, host="127.0.0.1", port=7496, client_id=1):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = None
        self.connected = False
        self.last_error = None

    def connect(self):
        """
        IB Gateway yoksa veya port kapalıysa burada takılmasın diye
        kısa timeout ile deniyoruz ve hata mesajını saklıyoruz.
        """
        try:
            if self.ib is None:
                self.ib = IB()
            if not self.ib.isConnected():
                self.ib.connect(self.host, self.port, clientId=self.client_id, timeout=2.0)
            self.connected = True
            self.last_error = None
        except Exception as e:
            self.connected = False
            self.last_error = str(e)
        return self.status()

    def status(self):
        """
        /api/ibkr/status burayı kullanacak.
        """
        if not self.connected:
            self.connect()
        return {
            "connected": self.connected,
            "last_error": self.last_error,
            "host": self.host,
            "port": self.port,
            "client_id": self.client_id,
        }

    def get_account_summary(self):
        if not self.connected:
            self.connect()
        if not self.connected:
            return {"connected": False, "error": self.last_error}
        try:
            vals = self.ib.accountSummary()
            out = {}
            for v in vals:
                key = f"{v.tag}::{v.currency}"
                out[key] = v.value
            return {"connected": True, "summary": out}
        except Exception as e:
            self.last_error = str(e)
            return {"connected": False, "error": self.last_error}

    def get_positions(self):
        if not self.connected:
            self.connect()
        if not self.connected:
            return {"connected": False, "positions": [], "error": self.last_error}
        try:
            positions = self.ib.positions()
            result = []
            for acc, contract, position, avgCost in positions:
                result.append({
                    "account": acc,
                    "symbol": contract.symbol,
                    "position": float(position),
                    "avg_cost": float(avgCost),
                })
            return {"connected": True, "positions": result}
        except Exception as e:
            self.last_error = str(e)
            return {"connected": False, "positions": [], "error": self.last_error}

    def place_order(self, symbol, qty, side):
        if not self.connected:
            self.connect()
        if not self.connected:
            return {
                "ok": False,
                "error": self.last_error or "IB Gateway not connected",
                "symbol": symbol,
                "qty": qty,
                "side": side,
            }
        side_up = side.upper()
        if side_up not in ("BUY", "SELL"):
            return {"ok": False, "error": f"invalid side: {side}"}
        try:
            contract = Stock(symbol, "SMART", "USD")
            order = self.ib.marketOrder(side_up, qty)
            trade = self.ib.placeOrder(contract, order)
            self.ib.sleep(1.0)
            return {
                "ok": True,
                "symbol": symbol,
                "qty": qty,
                "side": side_up,
                "status": trade.orderStatus.status,
            }
        except Exception as e:
            self.last_error = str(e)
            return {
                "ok": False,
                "error": self.last_error,
                "symbol": symbol,
                "qty": qty,
                "side": side,
            }
