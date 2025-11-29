from flask import Flask, render_template_string, request, redirect, url_for
import json
import os
import requests
from admin_mode import get_ibkr_mode, set_ibkr_mode

app = Flask(__name__)

API_BASE_URL = "http://127.0.0.1:5055"  # VPS içinden boru API

TEMPLATE = """
<!doctype html>
<html lang="tr">
<head>
    <meta charset="utf-8">
    <title>EsenTrader Admin Paneli</title>
    <style>
        body { background:#0b1220; color:#e5e7eb; font-family:system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
        .container { max-width: 960px; margin: 32px auto; padding: 0 16px; }
        .card { background:#020617; border:1px solid #1f2937; border-radius:12px; padding:20px; margin-bottom:24px; }
        h1 { font-size:28px; margin-bottom:16px; }
        h2 { font-size:20px; margin-bottom:12px; }
        .badge { display:inline-block; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:600; }
        .badge-local { background:#22c55e22; color:#4ade80; border:1px solid #22c55e55; }
        .badge-vps { background:#3b82f622; color:#60a5fa; border:1px solid #3b82f655; }
        .badge-error { background:#b91c1c22; color:#fca5a5; border:1px solid #b91c1c55; }
        .btn { display:inline-block; padding:6px 14px; border-radius:999px; border:none; cursor:pointer; font-size:13px; font-weight:600; margin-right:8px; }
        .btn-local { background:#16a34a; color:white; }
        .btn-vps { background:#2563eb; color:white; }
        .btn-ghost { background:transparent; color:#e5e7eb; border:1px solid #4b5563; }
        .btn-small { padding:4px 10px; font-size:12px; }
        pre { background:#020617; border-radius:8px; padding:12px; font-size:12px; overflow:auto; border:1px solid #111827; }
        table { width:100%; border-collapse:collapse; font-size:13px; }
        th, td { padding:6px 8px; border-bottom:1px solid #1f2937; text-align:left; }
        th { color:#9ca3af; font-weight:500; }
        .text-right { text-align:right; }
        .text-muted { color:#6b7280; font-size:12px; }
    </style>
</head>
<body>
<div class="container">
    <h1>EsenTrader Admin Paneli</h1>

    <div class="card">
        <h2>IBKR Bağlantı Modu</h2>
        <p class="text-muted">Şu anki mod:
            {% if current_mode == "LOCAL" %}
                <span class="badge badge-local">LOCAL (PC üzerinden)</span>
            {% else %}
                <span class="badge badge-vps">VPS (sunucu üzerinden)</span>
            {% endif %}
        </p>
        <form method="post" style="margin-top:12px;">
            <button name="mode" value="LOCAL" class="btn btn-local"
                    {% if current_mode == "LOCAL" %}disabled{% endif %}>
                LOCAL (PC)
            </button>
            <button name="mode" value="VPS" class="btn btn-vps"
                    {% if current_mode == "VPS" %}disabled{% endif %}>
                VPS
            </button>
        </form>
        <p class="text-muted" style="margin-top:10px;">
            LOCAL: IBKR yalnızca senin bilgisayarındaki TWS & boru-api-local üzerinden çalışır.<br>
            VPS: İleride sunucudaki IB Gateway'e doğrudan bağlanmak için kullanılacak.
        </p>
    </div>

    <div class="card">
        <h2>IBKR Durumu</h2>
        {% if status_error %}
            <span class="badge badge-error">HATA</span>
        {% elif status_json %}
            <span class="badge badge-local">AKTİF</span>
        {% else %}
            <span class="badge badge-error">BİLİNMİYOR</span>
        {% endif %}

        <p class="text-muted">Kaynak → {{ status_source }}</p>

        <form method="get" style="margin-bottom:10px;">
            <button class="btn btn-ghost btn-small" type="submit">Sayfayı yenile</button>
        </form>

        <h3 style="font-size:14px; margin-bottom:6px;">Ham JSON</h3>
        <pre>{{ status_display }}</pre>
    </div>

    <div class="card">
        <h2>IBKR Pozisyonları (özet)</h2>
        <p class="text-muted">Kaynak → {{ positions_source }}</p>

        {% if positions_error %}
            <span class="badge badge-error">HATA</span>
            <pre style="margin-top:8px;">{{ positions_error }}</pre>
        {% elif positions and positions|length > 0 %}
            <table>
                <thead>
                <tr>
                    <th>Sembol</th>
                    <th class="text-right">Adet</th>
                    <th class="text-right">Ort. Maliyet</th>
                    <th class="text-right">Para Birimi</th>
                    <th>Hesap</th>
                </tr>
                </thead>
                <tbody>
                {% for p in positions %}
                    <tr>
                        <td>{{ p.symbol }}</td>
                        <td class="text-right">{{ "%.2f"|format(p.position) }}</td>
                        <td class="text-right">{{ "%.2f"|format(p.avgCost) }}</td>
                        <td class="text-right">{{ p.currency }}</td>
                        <td>{{ p.account }}</td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
            <p class="text-muted" style="margin-top:6px;">
                Toplam {{ positions|length }} pozisyon listelendi.
            </p>
        {% else %}
            <p class="text-muted">Hiç pozisyon bulunamadı.</p>
        {% endif %}
    </div>

</div>
</body>
</html>
"""

def safe_get_json(url: str):
    """URL'den JSON çek, hata olursa (data=None, error=...) döndür."""
    try:
        resp = requests.get(url, timeout=4)
        text = resp.text
        resp.raise_for_status()
        try:
            data = resp.json()
        except Exception:
            return None, f"{url} -> JSON parse hatası. Gelen veri: {text[:200]}"
        return data, None
    except Exception as e:
        return None, f"{url} -> {repr(e)}"

def extract_positions(obj):
    """
    JSON içinde 'positions' listesini ne kadar derinde olursa olsun bul.
    Böylece API cevap formatı biraz değişse bile pozisyonları çıkarabiliriz.
    """
    if isinstance(obj, dict):
        if "positions" in obj and isinstance(obj["positions"], list):
            return obj["positions"]
        for v in obj.values():
            res = extract_positions(v)
            if res is not None:
                return res
    elif isinstance(obj, list):
        for item in obj:
            res = extract_positions(item)
            if res is not None:
                return res
    return None

@app.route("/admin", methods=["GET", "POST"])
def admin():
    # 1) Toggle işlemi
    if request.method == "POST":
        mode = request.form.get("mode")
        if mode in ("LOCAL", "VPS"):
            set_ibkr_mode(mode)
        return redirect(url_for("admin"))

    current_mode = get_ibkr_mode()

    # 2) Status & positions URL'leri
    status_url = f"{API_BASE_URL}/api/ibkr/status"
    positions_url = f"{API_BASE_URL}/api/ibkr/positions"

    # 3) Status çek
    status_json, status_error = safe_get_json(status_url)
    if status_json is not None:
        status_display = json.dumps(status_json, indent=2, ensure_ascii=False)
    else:
        status_display = status_error or "Veri yok"

    # 4) Pozisyonları çek
    positions_json, positions_error = safe_get_json(positions_url)
    positions_list = []
    if positions_json is not None:
        raw_positions = extract_positions(positions_json) or []
        # IBKR JSON'unu sadeleştir
        for p in raw_positions:
            try:
                positions_list.append({
                    "symbol": p.get("symbol") or p.get("localSymbol") or "",
                    "position": float(p.get("position", 0)),
                    "avgCost": float(p.get("avgCost", 0)),
                    "currency": p.get("currency", ""),
                    "account": p.get("account", "")
                })
            except Exception:
                continue

    context = {
        "current_mode": current_mode,
        "status_source": status_url,
        "status_json": status_json,
        "status_error": status_error,
        "status_display": status_display,
        "positions_source": positions_url,
        "positions": positions_list,
        "positions_error": positions_error,
    }

    return render_template_string(TEMPLATE, **context)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5056)
