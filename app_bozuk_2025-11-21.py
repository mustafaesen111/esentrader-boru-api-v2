from datetime import datetime

from flask import Flask, jsonify, request, render_template

from api.ibkr_adapter import ibkr
from admin_mode import get_ib_target, set_admin_mode


app = Flask(__name__)


@app.route("/api/health", methods=["GET"])
def health() -> "flask.Response":
    """
    Basit sağlık kontrolü.
    systemd ve dış dünya için 'API ayakta mı?' sorusuna cevap verir.
    """
    return jsonify(
        {
            "service": "esentrader-boru-api",
            "status": "ok",
        }
    )


@app.route("/api/status", methods=["GET"])
def status() -> "flask.Response":
    """
    Boru API'nin genel durum özeti.
    İleride buraya Binance, web, copy-engine vs. de eklenebilir.
    Admin API mode bilgisi de eklendi.

    NOT: IBKR tarafı çökerse bile API dönsün diye try/except ile korunuyor.
    """
    # IBKR tarafı hata verirse bile API çökmesin:
    try:
        ib_status = ibkr.get_status()
    except Exception as e:
        ib_status = {
            "connected": False,
            "error": str(e),
        }

    ib_target = get_ib_target()

    return jsonify(
        {
            "service": "esentrader-boru-api",
            "time_utc": datetime.utcnow().isoformat() + "Z",
            "admin_mode": ib_target["mode"],
            "ib_target": {
                "host": ib_target["host"],
                "port": ib_target["port"],
                "label": ib_target["label"],
            },
            "ibkr": ib_status,
        }
    )


@app.route("/api/ibkr/status", methods=["GET"])
def ibkr_status() -> "flask.Response":
    """
    Sadece IBKR boru durumunu döner.
    Şu an için 7497/4001 portu açık mı / kapalı mı onu kontrol ediyor.

    NOT: Burada da try/except var; IBKR düşse bile JSON döner.
    """
    try:
        status = ibkr.get_status()
        return jsonify(status)
    except Exception as e:
        return jsonify(
            {
                "connected": False,
                "error": str(e),
            }
        )


# -------------------------------
# ADMIN API MODE ENDPOINT'LERİ
# -------------------------------

@app.route("/api/admin/mode", methods=["GET"])
def api_get_mode() -> "flask.Response":
    """
    Geçerli ADMIN_API_MODE + IB hedef bilgisi
    """
    target = get_ib_target()
    return jsonify(target)


@app.route("/api/admin/mode", methods=["POST"])
def api_set_mode_endpoint() -> "flask.Response":
    """
    Mode değiştir: body: {"mode": "LOCAL"} veya {"mode": "VPS"}

    Basit kullanım:
      curl -X POST http://IP:5055/api/admin/mode \
        -H "Content-Type: application/json" \
        -d '{"mode":"LOCAL"}'
    """
    data = request.get_json(silent=True) or {}
    mode = str(data.get("mode", "")).upper()

    if mode not in ("LOCAL", "VPS"):
        return jsonify({"ok": False, "error": "mode must be LOCAL or VPS"}), 400

    set_admin_mode(mode)
    target = get_ib_target()
    return jsonify({"ok": True, **target})


# -------------------------------
# ADMIN PANEL SAYFASI
# -------------------------------

@app.route("/admin")
def admin_page():
    """
    Basit web arayüzü: admin mode (LOCAL/VPS) toggle.
    """
    return render_template("admin.html")


if __name__ == "__main__":
    # systemd zaten bu dosyayı python ile çalıştırıyor.
    # Lokal testte de aynı dosyayı kullanabilirsin.
    app.run(host="0.0.0.0", port=5055)
