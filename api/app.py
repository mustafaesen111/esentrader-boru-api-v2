from flask import Flask, request, jsonify

app = Flask(__name__)

# ------- Healthcheck -------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "esentrader-boru-api"})

# ------- Manual Test Endpoint -------
@app.route("/api/test", methods=["POST"])
def test_order():
    data = request.json
    return jsonify({"received": data})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5055, debug=True)
