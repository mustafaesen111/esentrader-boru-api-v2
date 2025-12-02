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
# IBKR ORDER - Trade Panel için DEMO endpoint
# ============================================================

@app.route("/api/ibkr/place_order", methods=["POST"])
@app.route("/api/ibkr/order", methods=["POST"])
def api_ibkr_place_order():
    """
    Trade Panel'den gelen manuel emirler için DEMO endpoint.
    Şimdilik gerçek IBKR'a gitmiyor, sadece payload'ı geri döndürüyor.
    """
    payload = request.get_json() or {}

    # Basit validasyon
    symbol = payload.get("symbol")
    side = payload.get("side")
    qty = payload.get("qty")
    usd_amount = payload.get("usd_amount")
    order_type = payload.get("order_type", "MKT")

    if not symbol or not side:
        return jsonify({
            "ok": False,
            "error": "symbol ve side zorunlu alanlardır.",
        }), 400

    return jsonify({
        "ok": True,
        "demo": True,
        "message": "DEMO: Emir kaydedildi (IBKR'a gönderilmedi).",
        "order": {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "usd_amount": usd_amount,
            "order_type": order_type,
            "note": payload.get("note"),
        },
    }), 200


if __name__ == "__main__":
    # VPS ana API portu
    app.run(host="0.0.0.0", port=5055, debug=True)
