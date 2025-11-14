from flask import Flask, render_template
import requests

app = Flask(__name__)

# Tek Boru API adresi (VPS içinden bakınca localhost)
API_BASE = "http://127.0.0.1:5055"


def get_api_health():
    data = {
        "ok": False,
        "error": None,
    }
    try:
        r = requests.get(f"{API_BASE}/api/health", timeout=2)
        r.raise_for_status()
        j = r.json()
        data["ok"] = j.get("status") == "ok"
    except Exception as e:
        data["error"] = str(e)
    return data


def get_ibkr_status():
    data = {
        "connected": False,
        "error": None,
    }
    try:
        r = requests.get(f"{API_BASE}/api/ibkr/status", timeout=2)
        r.raise_for_status()
        j = r.json()
        # API şu formatta dönüyor: {"ibkr_connected": true/false}
        data["connected"] = bool(j.get("ibkr_connected"))
    except Exception as e:
        data["error"] = str(e)
    return data


@app.route("/")
def home():
    api_health = get_api_health()
    ibkr_status = get_ibkr_status()

    return render_template(
        "home.html",
        api_base=API_BASE,
        api_health=api_health,
        ibkr_status=ibkr_status,
    )


if __name__ == "__main__":
    # Web paneli 8000 portunda çalışıyor
    app.run(host="0.0.0.0", port=8000, debug=True)
