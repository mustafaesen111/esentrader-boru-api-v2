# api/ibkr_adapter.py

from ib_insync import IB, Stock

class IBKRBroker:
    def __init__(self, host="127.0.0.1", port=7497, client_id=1):
        """
        IBKR bağlantı ayarları:
        - host : TWS / IB Gateway çalışan makine
        - port : Paper TWS = 7497, Real TWS = 7496 (Gateway'de farklı olabilir)
        """
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()

    def connect(self) -> bool:
        """
        Bağlı değilse IBKR'a bağlanır, True/False döner.
        """
        if not self.ib.isConnected():
            try:
                self.ib.connect(self.host, self.port, clientId=self.client_id)
                print(f"[IBKR] Bağlandı: {self.host}:{self.port} clientId={self.client_id}")
            except Exception as e:
                print("[IBKR] Bağlanamadı:", e)
        return self.ib.isConnected()

    def account_info(self):
        """
        Hesap özetini (equity, cash vs.) döndürür.
        """
        if not self.connect():
            return {"error": "IBKR bağlantısı yok"}

        summary = self.ib.accountSummary()
        data = {}
        for item in summary:
            # Örnek: NetLiquidation_USD: 5380.00
            key = f"{item.tag}_{item.currency}" if item.currency else item.tag
            data[key] = item.value
        return data

    def positions(self):
        """
        Açık pozisyonları döndürür.
        """
        if not self.connect():
            return {"error": "IBKR bağlantısı yok"}

        positions = self.ib.positions()
        out = []
        for p in positions:
            c = p.contract
            out.append({
                "account": p.account,
                "symbol": c.symbol,
                "secType": c.secType,
                "currency": c.currency,
                "exchange": getattr(c, "exchange", ""),
                "position": float(p.position),
                "avgCost": float(p.avgCost),
            })
        return out
