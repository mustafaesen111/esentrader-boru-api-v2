import os
import sys
import json

import requests
from flask import Flask, render_template, jsonify, redirect, url_for, request

# Flask uygulaması
app = Flask(__name__)

# Boru API'nin temel adresi
BORU_API_BASE = "http://127.0.0.1:5055"

# Mod dosyası (LOCAL / VPS toggle)
MODE_FILE = "/opt/esentrader-boru-api/admin_mode.json"


# ================================================================
# MOD OKUMA / YAZMA
# ================================================================
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


# SAĞLIK TESTİ
# ================================================================
@app.route("/admin/ping")
def admin_ping():
    return "ADMIN OK", 200


# ================================================================
# ROOT YÖNLENDİRME
# ================================================================
@app.route("/admin")
def admin_index():
    return redirect(url_for("admin_home"))


# ================================================================
# ANA SAYFA
# ================================================================
@app.route("/admin/home")
def admin_home():
    mode = load_mode()

    api_ok = False
    api_status = {"ok": False}

    try:
        # Boru API status endpoint
        r = requests.get(f"{BORU_API_BASE}/api/status", timeout=1)
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


# ================================================================
# MODE DEĞİŞTİR
# ================================================================
@app.route("/admin/mode/<string:new_mode>")
def admin_change_mode(new_mode: str):
    """LOCAL / VPS toggle."""
    if new_mode not in ("LOCAL", "VPS"):
        new_mode = "LOCAL"
    save_mode(new_mode)
    return redirect(url_for("admin_home"))


# ================================================================
# BORU API – STATUS PROXY
# (Dashboard'taki 'API Durumunu Yenile' butonu için)
# ================================================================
@app.route("/admin/api/status")
def admin_api_status():
    try:
        resp = requests.get(f"{BORU_API_BASE}/api/status", timeout=3)
        data = resp.json()
        return jsonify(data), resp.status_code
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ================================================================
# ================================================================
# YARDIMCI: BORU API'YE GÜVENLİ JSON PROXY
# ================================================================
def _proxy_json(path: str, method: str = "GET", payload: dict | None = None, timeout: int = 5):
    """Tek bir path'e istek at, JSON parse edemezsek raw text döndür."""
    try:
        url = f"{BORU_API_BASE}{path}"
        if method.upper() == "GET":
            resp = requests.get(url, timeout=timeout)
        else:
            resp = requests.post(url, json=payload or {}, timeout=timeout)

        try:
            data = resp.json()
        except Exception:
            # JSON değilse, en azından raw text'i gösterelim
            data = {
                "ok": False,
                "status_code": resp.status_code,
                "raw": resp.text[:1000],
                "error": "JSON parse edilemedi",
                "path": path,
            }
        return jsonify(data), resp.status_code
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "path": path}), 500


# ================================================================
# YARDIMCI: BİRDEN FAZLA PATH DENE
# ================================================================
def _proxy_json_multi(paths: list[str], method: str = "GET", payload: dict | None = None, timeout: int = 5):
    """
    Sırayla birden fazla endpoint dener.
    İlk düzgün JSON dönen veya 404 dışındaki cevabı döner.
    Hiçbiri çalışmazsa debug bilgisi ile hata döndürür.
    """
    last_info = {}
    for path in paths:
        try:
            url = f"{BORU_API_BASE}{path}"
            if method.upper() == "GET":
                resp = requests.get(url, timeout=timeout)
            else:
                resp = requests.post(url, json=payload or {}, timeout=timeout)

            # 404 ise sonraki path'i dene
            if resp.status_code == 404:
                last_info = {
                    "status_code": 404,
                    "path": path,
                    "raw": resp.text[:400],
                }
                continue

            try:
                data = resp.json()
                # Başarılı JSON → direkt bunu döndür
                return jsonify(data), resp.status_code
            except Exception:
                # JSON parse olmazsa sonraki path'e geç
                last_info = {
                    "status_code": resp.status_code,
                    "path": path,
                    "raw": resp.text[:400],
                    "error": "JSON parse edilemedi",
                }
                continue

        except Exception as e:
            last_info = {"error": str(e), "path": path}
            continue

    # Hiçbir path düzgün çalışmadı
    return jsonify({
        "ok": False,
        "error": "Uygun endpoint bulunamadı",
        "tried_paths": paths,
        "last_info": last_info,
    }), 502


# ================================================================
# BORU API – HESAP (ACCOUNT) PROXY
# ================================================================
@app.route("/admin/api/account")
def admin_api_account():
    # Sırayla bu path'leri dener:
    # 1) /api/account
    # 2) /api/ibkr/account
    # 3) /api/ibkr/account_summary
    return _proxy_json_multi(
        ["/api/account", "/api/ibkr/account", "/api/ibkr/account_summary"],
        method="GET",
        timeout=8,
    )


# ================================================================
# BORU API – POZİSYONLAR PROXY
# ================================================================
@app.route("/admin/api/positions")
def admin_api_positions():
    # Sırayla bu path'leri dener:
    # 1) /api/positions
    # 2) /api/ibkr/positions
    # 3) /api/ibkr/open_positions
    return _proxy_json_multi(
        ["/api/positions", "/api/ibkr/positions", "/api/ibkr/open_positions"],
        method="GET",
        timeout=8,
    )


# ================================================================
# BORU API – MANUEL EMİR PROXY
# ================================================================
@app.route("/admin/api/order", methods=["POST"])
def admin_api_order():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        payload.setdefault("source", "admin_trade_panel")
    except Exception:
        payload = {"source": "admin_trade_panel"}

    # Sırayla bu path'leri dener:
    # 1) /api/order
    # 2) /api/ibkr/order
    # 3) /api/ibkr/place_order
    return _proxy_json_multi(
        ["/api/order", "/api/ibkr/order", "/api/ibkr/place_order"],
        method="POST",
        payload=payload,
        timeout=10,
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
# YENİ ADMIN SAYFALARI – sade placeholder ekranlar
# ----------------------------------------------------------------------

@app.route("/admin/binance")
def admin_binance():
    return render_template("admin_binance.html")

@app.route("/admin/copytrade")
def admin_copytrade():
    return render_template("admin_copytrade.html")

@app.route("/admin/tradepanel")
def admin_tradepanel():
    return render_template("admin_tradepanel.html")

@app.route("/admin/tradehistory")
def admin_tradehistory():
    return render_template("admin_tradehistory.html")

@app.route("/admin/ranks")
def admin_ranks():
    return render_template("admin_ranks.html")

@app.route("/admin/signals")
def admin_signals():
    return render_template("admin_signals.html")

@app.route("/admin/risk")
def admin_risk():
    return render_template("admin_risk.html")

@app.route("/admin/subscribers")
def admin_subscribers():
    return render_template("admin_subscribers.html")

@app.route("/admin/settings")
def admin_settings():
    return render_template("admin_settings.html")

# ----------------------------------------------------------------------
# ÇALIŞTIR
# ----------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5056)
