from flask import Flask, render_template
import requests

API_BASE = "http://5.161.110.7:5055"

app = Flask(__name__)


def get_api_health():
    try:
        r = requests.get(f"{API_BASE}/api/health", timeout=2)
        r.raise_for_status()
        data = r.json()
        return data.get("status", "unknown"), data
    except Exception as e:
        return "error", {"error": str(e)}


def get_ibkr_status():
    try:
        r = requests.get(f"{API_BASE}/api/ibkr/status", timeout=2)
        r.raise_for_status()
        data = r.json()
        return bool(data.get("ibkr_connected", False)), data
    except Exception as e:
        return False, {"error": str(e)}


@app.route("/")
def home():
    api_status, api_raw = get_api_health()
    ibkr_connected, ibkr_raw = get_ibkr_status()

    return render_template(
        "home.html",
        api_status=api_status,
        api_raw=api_raw,
        ibkr_connected=ibkr_connected,
        ibkr_raw=ibkr_raw,
    )


if __name__ == "__main__":
    # Şimdilik debug açık, port 8000’de çalışsın
    app.run(host="0.0.0.0", port=8000, debug=True)
