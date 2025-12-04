"""
app.py
EsenTrader Boru API (VPS tarafı)
- /          : basit info sayfası
- /api/health
- /api/ibkr/status
- /api/ibkr/positions

IBKR ile direkt bağlantı KURMAZ.
admin_mode + ibkr_client kullanarak uygun backend'e HTTP proxy yapar.
"""
from flask import Flask, render_template, jsonify, request

from admin_mode import get_admin_mode
from ibkr_client import IBKRClient

from datetime import datetime
import os, json

# ----------------------------------------
# Portfolio → IBKR Hesap mapping
# ----------------------------------------
portfolio_to_account = {
    "gold": "U14813758",      # Gold portföy hesabı
    "growth": "U7960949",     # Growth portföy hesabı
    "power_etf": "U23330667"  # Power ETF portföy hesabı
}

# ----------------------------------------
# LIVE / DEMO modu
#  False  -> Sadece log + admin panel (şu an güvenli)
#  True   -> IBKR'a gerçek emir yollar
# ----------------------------------------
LIVE_MODE = False


def send_order_to_ibkr(symbol, side, qty, usd_amount,
                       portfolio, account_id, tp, sl, note, source):
    """
    IBKR tarafına gerçek emir gönderen yardımcı fonksiyon.
    ibkr_client.place_order(order_payload) çağrısını yapar.
    """
    order_payload = {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "usd_amount": usd_amount,
        "portfolio": portfolio,
        "account_id": account_id,
        "tp_percent": tp,
        "sl_percent": sl,
        "note": note,
        "source": source,
    }
    try:
        result = ibkr_client.place_order(order_payload)
    except Exception as e:
        print("send_order_to_ibkr error:", e)
        return {"ok": False, "error": str(e), "url": None, "mode": "error"}

    return result



app = Flask(__name__)
ibkr_client = IBKRClient()

# --- Sağlık kontrolü endpoint'i ---
@app.route("/api/status")
def api_status():
    return jsonify({
        "ok": True,
        "service": "esentrader-boru-api",
        "version": "v1",
        "message": "boru API ayakta"
    })


@app.route("/")
def index():
    """
    Basit web sayfası: API'nin çalıştığını ve admin panel linkini gösterir.
    """
    mode = get_admin_mode()
    return f"""
    <html>
      <head>
        <title>EsenTrader Boru API</title>
      </head>
      <body style="font-family: Arial; background-color: #111; color: #eee;">
        <h1>EsenTrader Boru API (VPS)</h1>
        <p>Servis çalışıyor. Geçerli IBKR modu: <b>{mode}</b></p>
        <ul>
          <li><a href="/api/health" style="color:#0f0;">/api/health</a></li>
          <li><a href="/api/ibkr/status" style="color:#0f0;">/api/ibkr/status</a></li>
          <li><a href="/api/ibkr/positions" style="color:#0f0;">/api/ibkr/positions</a></li>
        </ul>
        <p>
          Admin Panel:
          <a href="http://5.78.152.122:5056/admin" style="color:#0af;">
            http://5.78.152.122:5056/admin
          </a>
        </p>
      </body>
    </html>
    """


@app.route("/api/health", methods=["GET"])
def health():
    """Temel sağlık kontrolü."""
    return jsonify({
        "service": "esentrader-boru-api",
        "mode": get_admin_mode(),
        "status": "ok",
    })


@app.route("/api/ibkr/status", methods=["GET"])
def api_ibkr_status():
    """
    IBKR durumu:
    - LOCAL: PC'deki boru-api-local → (VPS'ten 6001 ile)
    - VPS:   İleride VPS IBKR servisi
    """
    result = ibkr_client.get_status()

    if result["ok"]:
        return jsonify({
            "mode": result["mode"],
            "ok": True,
            "url": result["url"],
            "remote": result["data"],   # PC'den gelen ham JSON
        })
    else:
        return jsonify({
            "mode": result["mode"],
            "ok": False,
            "url": result["url"],
            "error": result["error"],
        }), 502

# ============================================================
# IBKR ACCOUNT — Trade Panel için basit endpointler
# ============================================================

@app.route("/api/ibkr/account", methods=["GET"])
def api_ibkr_account():
    """
    IBKR ana hesap özeti.
    Şimdilik dummy; ileride gerçek IBKR client ile dolduracağız.
    """
    data = {
        "ok": True,
        "account": {
            "account": "DEMO",
            "cash": 0.0,
            "equity": 0.0,
            "currency": "USD",
            "buying_power": 0.0,
        },
    }
    return jsonify(data)


@app.route("/api/ibkr/account_summary", methods=["GET"])
def api_ibkr_account_summary():
    """
    Trade panel fallback olarak bunu da deniyor.
    Şimdilik aynı veriyi döndürüyoruz.
    """
    return api_ibkr_account()


@app.route("/api/ibkr/positions", methods=["GET"])
def api_ibkr_positions():
    """
    IBKR pozisyonları proxy:
    Uzak servisten gelen JSON'u 'remote' alanında döner.
    """
    result = ibkr_client.get_positions()

    if result["ok"]:
        return jsonify({
            "mode": result["mode"],
            "ok": True,
            "url": result["url"],
            "remote": result["data"],
        })
    else:
        return jsonify({
            "mode": result["mode"],
            "ok": False,
            "url": result["url"],
            "error": result["error"],
        }), 502
# ============================================================

# ------------------------------------------------------
# GENEL ORDER ENDPOINT'i  (TradingView + ileride web)
# ------------------------------------------------------

# ------------------------------------------------------
# GENEL ORDER ENDPOINT'i  (TradingView + ileride web)
# ------------------------------------------------------
@app.route("/api/order", methods=["POST"])
def api_order():
    """
    Tek boru emir endpoint'i.
    TradingView webhook'ları ve ileride web panel buraya POST edecek.
    Şimdilik:
      - HER ZAMAN manual_orders.log'a yazar
      - Eğer LIVE_MODE=True ise IBKR'a gerçek emir yollar.
    """
    try:
        payload = request.get_json(force=True, silent=True) or {}
    except Exception as e:
        print("api_order JSON error:", e)
        return jsonify({"ok": False, "error": "INVALID_JSON"}), 400

    # Basit validasyon
    symbol = payload.get("symbol")
    side = payload.get("side")
    qty = payload.get("qty")
    usd_amount = payload.get("usd_amount")

    if not symbol or not side:
        return jsonify({
            "ok": False,
            "demo": True,
            "error": "symbol ve side zorunlu alanlardır.",
        }), 400

    # Portföy ve IBKR hesap ID'si
    portfolio = payload.get("portfolio") or "growth"
    account_id = portfolio_to_account.get(portfolio)

    tp = payload.get("tp_percent")
    sl = payload.get("sl_percent")
    note = payload.get("note")
    source = payload.get("source") or "tv_bot"

    # --- LOG: manual_orders.log ---
    try:
        log_path = os.path.join(os.path.dirname(__file__), "manual_orders.log")

        log_entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "symbol": symbol,
            "side": (side or "").upper(),
            "qty": qty,
            "usd_amount": usd_amount,
            "tp_percent": tp,
            "sl_percent": sl,
            "note": note,
            "source": source,
            "portfolio": portfolio,
            "account_id": account_id,
        }

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    except Exception as e:
        print("api_order log error:", e)

    # --- LIVE: IBKR'a emir gönder (opsiyonel) ---
    ibkr_result = None
    if LIVE_MODE and account_id:
        ibkr_result = send_order_to_ibkr(
            symbol=symbol,
            side=(side or "").upper(),
            qty=qty,
            usd_amount=usd_amount,
            portfolio=portfolio,
            account_id=account_id,
            tp=tp,
            sl=sl,
            note=note,
            source=source,
        )

    return jsonify({
        "ok": True,
        "demo": not LIVE_MODE,
        "live": LIVE_MODE,
        "message": "Emir kaydedildi. IBKR'a gönderme durumu: LIVE_MODE=%s" % LIVE_MODE,
        "order": {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "usd_amount": usd_amount,
            "portfolio": portfolio,
            "account_id": account_id,
        },
        "ibkr_result": ibkr_result,
    }), 200



# ============================================================
#  IBKR ORDER - Trade Panel için DEMO endpoint
# ============================================================

# ============================================================
#  IBKR ORDER - Trade Panel için endpoint
# ============================================================
@app.route("/api/ibkr/place_order", methods=["POST"])
@app.route("/api/ibkr/order", methods=["POST"])
def api_ibkr_place_order():
    """
    Trade Panel'den gelen manuel emirler için endpoint.
    - HER ZAMAN manual_orders.log'a yazar
    - Eğer LIVE_MODE=True ise IBKR'a gerçek emir yollar.
    """
    payload = request.get_json() or {}

    symbol = payload.get("symbol")
    side = payload.get("side")
    qty = payload.get("qty")
    usd_amount = payload.get("usd_amount")
    order_type = payload.get("order_type", "MKT")

    if not symbol or not side:
        return jsonify({
            "ok": False,
            "demo": True,
            "error": "symbol ve side zorunlu alanlardır.",
        }), 400

    portfolio = payload.get("portfolio") or "growth"
    account_id = portfolio_to_account.get(portfolio)
    tp = payload.get("tp_percent")
    sl = payload.get("sl_percent")
    note = payload.get("note")
    source = payload.get("source") or "manual_panel"

    # --- LOG ---
    try:
        log_path = os.path.join(os.path.dirname(__file__), "manual_orders.log")

        log_entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "symbol": symbol,
            "side": (side or "").upper(),
            "qty": qty,
            "usd_amount": usd_amount,
            "tp_percent": tp,
            "sl_percent": sl,
            "note": note,
            "source": source,
            "portfolio": portfolio,
            "account_id": account_id,
        }

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    except Exception as e:
        print("api_ibkr_place_order log error:", e)

    # --- LIVE: IBKR'a emir gönder (opsiyonel) ---
    ibkr_result = None
    if LIVE_MODE and account_id:
        ibkr_result = send_order_to_ibkr(
            symbol=symbol,
            side=(side or "").upper(),
            qty=qty,
            usd_amount=usd_amount,
            portfolio=portfolio,
            account_id=account_id,
            tp=tp,
            sl=sl,
            note=note,
            source=source,
        )

    return jsonify({
        "ok": True,
        "demo": not LIVE_MODE,
        "live": LIVE_MODE,
        "message": "Emir kaydedildi. IBKR'a gönderme durumu: LIVE_MODE=%s" % LIVE_MODE,
        "order": {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "usd_amount": usd_amount,
            "order_type": order_type,
            "portfolio": portfolio,
            "account_id": account_id,
        },
        "ibkr_result": ibkr_result,
    }), 200



# ===================buraya kadar =========================================

if __name__ == "__main__":
    # VPS ana API portu
    app.run(host="0.0.0.0", port=5055, debug=True)
