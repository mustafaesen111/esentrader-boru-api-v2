from flask import Flask, request, jsonify

from ibkr_adapter import IBKRBroker
from binance_adapter import BinanceBroker
from copy_engine import CopyEngine

app = Flask(__name__)

# ------- Broker & CopyEngine Tek Boru Nesneleri -------

# IBKR: Şimdilik sadece iskelet, ileride ib_insync ile dolduracağız
ibkr_broker = IBKRBroker(host="127.0.0.1", port=7497, client_id=1)
ibkr_broker.connect()  # iskelette sadece connected=True yapıyor

# Binance: Şimdilik API key boş, ileride gerçek key ile dolduracağız
binance_broker = BinanceBroker(api_key="", api_secret="")

# Copy Engine: ileride follower listesi eklenecek
copy_engine = CopyEngine()


# ------- Healthcheck -------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "esentrader-boru-api"})


# ------- Manual Test Endpoint -------
@app.route("/api/test", methods=["POST"])
def test_order():
    data = request.json
    return jsonify({"received": data})


# ------- TradingView Signal Processor -------
def process_tradingview_signal(payload: dict) -> dict:
    """
    TradingView'den gelen webhook datasını normalize eder.
    symbol / side / mode / qty / usd / note alanlarını çıkarır.
    """

    symbol = (
        payload.get("symbol")
        or payload.get("ticker")
        or payload.get("SYMBOL")
    )
    side = (
        payload.get("side")
        or payload.get("action")
        or payload.get("SIDE")
        or payload.get("direction")
    )
    note = payload.get("note") or payload.get("comment") or payload.get("NOTE")
    mode = payload.get("mode") or payload.get("MODE") or "usd"

    qty = payload.get("qty") or payload.get("quantity")
    usd = payload.get("usd") or payload.get("amount_usd") or payload.get("AMOUNT_USD")

    print("[TV SIGNAL RAW]   ", payload, flush=True)
    print("[TV SIGNAL PARSED]", "symbol=", symbol, "side=", side, "mode=", mode,
          "qty=", qty, "usd=", usd, "note=", note, flush=True)

    return {
        "symbol": symbol,
        "side": side,
        "mode": mode,
        "qty": qty,
        "usd": usd,
        "note": note,
    }


# ------- Router: Tek Boru ile Broker'lara Emir Dağıtımı -------
def route_order_to_brokers(order: dict) -> dict:
    """
    Tek boru router:
    - IBKR'ye emir yollar
    - Binance'e emir yollar
    - CopyEngine ile follower hesaplara dağıtım yapar (iskelet)
    """

    symbol = order.get("symbol")
    side = order.get("side")
    qty = order.get("qty")
    usd = order.get("usd")
    note = order.get("note")
    mode = order.get("mode")

    print("[ROUTER] Gelen emir:", order, flush=True)

    # Şimdilik çok basit: qty varsa qty ile, yoksa None ile geçiyoruz.
    # İleride: mode == 'usd' ise fiyat çekip usd → adet dönüşümü yapılacak.
    ibkr_result = ibkr_broker.place_order(symbol=symbol, qty=qty, side=side)
    binance_result = binance_broker.place_order(symbol=symbol, qty=qty, side=side)

    copy_payload = {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "usd": usd,
        "note": note,
        "mode": mode,
    }
    copy_result = copy_engine.distribute(copy_payload)

    print("[ROUTER] IBKR result:    ", ibkr_result, flush=True)
    print("[ROUTER] Binance result: ", binance_result, flush=True)
    print("[ROUTER] CopyEngine:     ", copy_result, flush=True)

    return {
        "ibkr": ibkr_result,
        "binance": binance_result,
        "copy_engine": copy_result,
    }


# ------- /alert (ana TradingView webhook endpoint'i) -------
@app.route("/alert", methods=["POST"])
def alert():
    payload = request.get_json(force=True, silent=True) or {}

    parsed = process_tradingview_signal(payload)
    routed = route_order_to_brokers(parsed)

    return jsonify({
        "status": "ok",
        "source": "tradingview",
        "received": payload,
        "parsed": parsed,
        "routed": routed,
    })


# ------- /signal (TradingView'deki eski URL için alias) -------
@app.route("/signal", methods=["POST"])
def signal_alias():
    """
    TradingView tarafında webhook URL'in /signal ise,
    burası /alert ile aynı işlevi görür.
    """
    return alert()


if __name__ == "__main__":
    # Port: 5055
    # Dışarıdan: http://5.161.110.7:5055/alert veya /signal
    app.run(host="0.0.0.0", port=5055, debug=True)
