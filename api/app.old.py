from flask import Flask, jsonify, request
from adapters.ibkr_adapter import IBKRBroker
from core.master_trade import place_master_trade


app = Flask(__name__)


# -------------------------
#  MASTER BROKER (IBKR)
# -------------------------
# Tek boru: Şimdilik IBKR adapter bağlanıyor.
# İstersen buraya BinanceBroker da eklenebilir.
ibkr = IBKRBroker(
    host="127.0.0.1",
    port=7497,
    client_id=1
)
app.config["MASTER_BROKER"] = ibkr



# -------------------------
#  HEALTHCHECK
# -------------------------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "esentrader-boru-api"
    })



# -------------------------
#  IBKR STATUS (DEMO)
# -------------------------
@app.route("/api/ibkr/status", methods=["GET"])
def ibkr_status():
    status = app.config["MASTER_BROKER"].get_status()
    return jsonify(status)



# -------------------------
#  IBKR ACCOUNT (DEMO)
# -------------------------
@app.route("/api/ibkr/account", methods=["GET"])
def ibkr_account():
    b = app.config["MASTER_BROKER"]
    info = b.account_summary()
    return jsonify(info)



# -------------------------
#  IBKR POSITIONS (DEMO)
# -------------------------
@app.route("/api/ibkr/positions", methods=["GET"])
def ibkr_positions():
    b = app.config["MASTER_BROKER"]
    positions = b.positions()
    return jsonify({"positions": positions})



# -------------------------
#  TEST ENDPOINT
# -------------------------
@app.route("/api/test", methods=["POST"])
def api_test():
    payload = request.get_json(force=True, silent=True) or {}
    return jsonify({
        "status": "ok",
        "echo": payload,
    })



# ============================================================
#  🔥 ANA BORU: TradingView → /api/signal  (BOT + COPY-TRADE)
# ============================================================
@app.route("/api/signal", methods=["POST"])
def api_signal():
    try:
        payload = request.get_json(force=True) or {}

        symbol = payload.get("symbol")
        side_raw = (payload.get("side") or "").lower()
        mode = (payload.get("mode") or "LIVE").upper()
        risk_type = (payload.get("risk_type") or "USD").upper()
        usd_amount = payload.get("usd_amount")

        # ----------------------------
        #  VALIDASYON
        # ----------------------------
        if not symbol or side_raw not in ("buy", "sell"):
            return jsonify({"ok": False, "error": "invalid symbol or side"}), 400

        if risk_type != "USD":
            return jsonify({"ok": False, "error": "only USD supported"}), 400

        usd_amount = float(usd_amount)
        if usd_amount <= 0:
            return jsonify({"ok": False, "error": "usd_amount must be > 0"}), 400


        # ----------------------------
        #  PAPER MODE
        # ----------------------------
        if mode == "PAPER":
            print(f"[PAPER] {symbol} {side_raw} {usd_amount}")
            return jsonify({"ok": True, "mode": "PAPER"})


        # ----------------------------
        #  REAL TRADE (MASTER)
        # ----------------------------
        broker = app.config["MASTER_BROKER"]

        side = "BUY" if side_raw == "buy" else "SELL"

        meta = {
            "source": payload.get("source"),
            "strategy": payload.get("strategy"),
            "signal_id": payload.get("signal_id")
        }

        master_event = place_master_trade(
            broker=broker,
            symbol=symbol,
            side=side,
            usd_amount=usd_amount,
            meta=meta
        )

        return jsonify({"ok": True, "event": master_event})


    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500




# -------------------------
#  RUN SERVER
# -------------------------
if __name__ == "__main__":
    # Debug kapalı: stabil çalışsın
    app.run(host="0.0.0.0", port=5055, debug=False)
