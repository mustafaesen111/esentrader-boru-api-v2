import os
import json
import requests
from flask import Flask, render_template, jsonify

# Flask uygulaması
app = Flask(__name__)

# Mod dosyası (LOCAL / VPS toggle)
MODE_FILE = "/opt/esentrader-boru-api/admin_mode.json"


# ----------------------------------------------------------------------
# MOD OKUMA / YAZMA
# ----------------------------------------------------------------------

def load_mode() -> str:
    """LOCAL / VPS mod bilgisini oku."""
    if os.path.exists(MODE_FILE):
        try:
            with open(MODE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("mode", "LOCAL")
        except Exception:
            return "LOCAL"
    return "LOCAL"


def save_mode(mode: str) -> None:
    """LOCAL / VPS mod bilgisini kaydet."""
    try:
        with open(MODE_FILE, "w", encoding="utf-8") as f:
            json.dump({"mode": mode}, f)
    except Exception:
        pass


# ----------------------------------------------------------------------
# SAĞLIK TESTİ
# ----------------------------------------------------------------------

@app.route("/admin/ping")
def admin_ping():
    return "ADMIN OK", 200


# ----------------------------------------------------------------------
# ANA SAYFA
# ----------------------------------------------------------------------

@app.route("/admin/home")
def admin_home():
    mode = load_mode()

    api_ok = False
    api_status = {"ok": False}

    try:
        r = requests.get("http://127.0.0.1:5055/api/status", timeout=1)
        api_status = r.json()
        api_ok = True
    except Exception as e:
        api_status = {"ok": False, "error": str(e)}

    return render_template(
        "admin_home.html",
        mode=mode,
        api_ok=api_ok,
        api_status=api_status,
    )


# ----------------------------------------------------------------------
# MODE DEĞİŞTİR
# ----------------------------------------------------------------------

@app.route("/admin/set-mode/<mode>", methods=["POST"])
def set_mode(mode):
    m = mode.upper()
    if m not in ("LOCAL", "VPS"):
        return jsonify({"status": "error", "error": "invalid mode"}), 400

    save_mode(m)
    return jsonify({"status": "ok", "mode": m})


# ----------------------------------------------------------------------
# DİĞER SAYFALAR
# ----------------------------------------------------------------------

@app.route("/admin/analytics")
def admin_analytics():
    return render_template("admin_analytics.html")


@app.route("/admin/ibkr")
def admin_ibkr():
    return render_template("admin_ibkr.html")


# ----------------------------------------------------------------------
# ÇALIŞTIR
# ----------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5056)
