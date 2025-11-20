from datetime import datetime

from flask import Flask, jsonify

from api.ibkr_adapter import ibkr


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
    """
    ib_status = ibkr.get_status()

    return jsonify(
        {
            "service": "esentrader-boru-api",
            "time_utc": datetime.utcnow().isoformat() + "Z",
            "ibkr": ib_status,
        }
    )


@app.route("/api/ibkr/status", methods=["GET"])
def ibkr_status() -> "flask.Response":
    """
    Sadece IBKR boru durumunu döner.
    Şu an için 7497 portu açık mı / kapalı mı onu kontrol ediyor.
    """
    return jsonify(ibkr.get_status())


if __name__ == "__main__":
    # systemd zaten bu dosyayı python ile çalıştırıyor.
    # Lokal testte de aynı dosyayı kullanabilirsin.
    app.run(host="0.0.0.0", port=5055)
