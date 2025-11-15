from ib_insync import IB, Stock, MarketOrder

from typing import Optional, Dict, Any





class IBKRBroker:

    """

    Basit, senkron IBKR adapter'i.

    - IB Gateway / TWS host:port üzerinde çalışıyorsa bağlanır.

    - Bağlantı kurulamazsa connected=False kalır; last_error içine hata yazılır.

    """



    def __init__(self, host: str = "127.0.0.1", port: int = 4001, client_id: int = 1):

        self.host = host

        self.port = port

        self.client_id = client_id

        self.ib: Optional[IB] = None

        self.connected: bool = False

        self.last_error: Optional[str] = None



    # ---- Dahili yardımcı ----

    def _ensure_ib(self) -> IB:

        if self.ib is None:

            self.ib = IB()

        return self.ib



    # ---- Bağlantı ----

    def connect(self) -> Dict[str, Any]:

        """

        Senkron bağlantı. Timeout kısa tutuldu (2 sn).

        Başarısız olursa exception fırlatmaz, sadece last_error'a yazar.

        """

        ib = self._ensure_ib()

        try:

            if not ib.isConnected():

                # Olası yarım bağlantıyı temizle

                ib.disconnect()

                ib.connect(self.host, self.port, clientId=self.client_id, timeout=2)



            self.connected = ib.isConnected()

            self.last_error = None

        except Exception as e:

            self.connected = False

            self.last_error = str(e)

            print(f"[IBKR] Connect error: {e}", flush=True)



        return self.status()



    # ---- Durum ----

    def status(self) -> Dict[str, Any]:

        """

        IBKR bağlantı durumunu döner.

        """

        ib = self._ensure_ib()

        self.connected = ib.isConnected()

        return {

            "ibkr_connected": self.connected,

            "host": self.host,

            "port": self.port,

            "client_id": self.client_id,

            "last_error": self.last_error,

        }



    # ---- Emir gönderme (çok basit iskelet) ----

    def place_order(self, symbol: str, qty: float, side: str) -> Dict[str, Any]:

        """

        Çok basit market order iskeleti.

        - Bağlı değilse hata döner.

        - Canlı sistemde risk/limit kontrolleri ayrıca eklenecek.

        """

        if not self.connected or self.ib is None or not self.ib.isConnected():

            return {

                "ok": False,

                "error": "IBKR not connected",

                "details": self.status(),

            }



        ib = self.ib

        try:

            contract = Stock(symbol, "SMART", "USD")

            ib.qualifyContracts(contract)



            action = side.upper()

            order = MarketOrder(action, qty)



            trade = ib.placeOrder(contract, order)

            return {

                "ok": True,

                "symbol": symbol,

                "side": action,

                "qty": qty,

                "orderId": trade.order.orderId,

            }

        except Exception as e:

            self.last_error = str(e)

            print(f"[IBKR] place_order error: {e}", flush=True)

            return {

                "ok": False,

                "error": str(e),

            }

