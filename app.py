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

from flask import Flask, jsonify
from admin_mode import get_admin_mode
from ibkr_client import IBKRClient

app = Flask(__name__)
ibkr_client = IBKRClient()


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


if __name__ == "__main__":
    # VPS ana API portu
    app.run(host="0.0.0.0", port=5055, debug=True)
