from flask import Flask, jsonify, send_from_directory, request
import os, sys

sys.path.insert(0, os.path.dirname(__file__))

app = Flask(__name__, static_folder="static")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/pairs")
def api_pairs():
    from config import TRADING_PAIRS
    return jsonify(TRADING_PAIRS)


@app.route("/api/signal")
def api_signal():
    raw = request.args.get("pair", "BTC/USDT")
    pair = raw.replace("-", "/").upper()

    try:
        from main import analyze_pair
        from data.fetcher import MarketDataFetcher
        from data.sentiment import fetch_fear_greed

        fetcher = MarketDataFetcher()
        fg = fetch_fear_greed()
        result = analyze_pair(pair, fetcher, fg)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"pair": pair, "signal": "HOLD", "error": str(exc)}), 200


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
