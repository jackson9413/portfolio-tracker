"""
Portfolio Tracker - A full-stack web app for tracking stock/crypto investments.

Features:
- Add/remove holdings (ticker, shares, cost basis)
- Live-ish price updates (with caching)
- Portfolio analytics: total value, P/L, allocation by sector
- Transaction history
- Dividend tracking
- Export to CSV

Stack: Python/Flask + SQLite + vanilla HTML/JS frontend
"""
import os
import json
import sqlite3
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, send_file
from io import StringIO
import csv

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "portfolio.db")


# ---------- Database ----------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                asset_type TEXT NOT NULL DEFAULT 'stock',  -- stock | crypto | etf
                shares REAL NOT NULL,
                cost_basis REAL NOT NULL,                   -- avg cost per share (USD)
                sector TEXT,
                purchase_date TEXT,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                holding_id INTEGER,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,        -- buy | sell | dividend
                shares REAL NOT NULL,
                price REAL NOT NULL,
                date TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY (holding_id) REFERENCES holdings(id)
            );

            CREATE TABLE IF NOT EXISTS price_cache (
                ticker TEXT PRIMARY KEY,
                price REAL NOT NULL,
                change_pct REAL NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
    print("[init_db] database ready")


# ---------- "Live" prices ----------
# In a real app this would hit Yahoo Finance / Alpha Vantage / CoinGecko.
# For the demo we generate a deterministic-ish price walk so the dashboard
# always has something interesting to show, and we simulate a real network call.
PRICE_BASE = {
    "AAPL": 195.40, "MSFT": 420.10, "NVDA": 138.55, "TSLA": 245.30,
    "GOOGL": 175.20, "AMZN": 188.40, "META": 530.10, "V": 285.60,
    "BTC": 71200.0, "ETH": 3850.0, "SOL": 168.40, "DOGE": 0.158,
    "SPY": 580.20, "QQQ": 510.40, "VOO": 525.10, "VTI": 290.50,
    "SCHD": 82.10, "JEPI": 56.40,
}


def get_price(ticker):
    """Return (price, change_pct) for a ticker, with light randomization."""
    ticker = ticker.upper()
    base = PRICE_BASE.get(ticker, 50.0 + random.random() * 200)
    # Simulate ~+/- 2% daily move
    noise = (random.random() - 0.5) * 0.04
    price = round(base * (1 + noise), 2)
    change_pct = round(noise * 100, 2)
    return price, change_pct


def get_cached_price(ticker):
    """Cache prices for 60s to avoid hammering the (simulated) upstream."""
    now = datetime.utcnow()
    with get_db() as conn:
        row = conn.execute(
            "SELECT price, change_pct, updated_at FROM price_cache WHERE ticker=?",
            (ticker.upper(),)
        ).fetchone()
        if row:
            updated = datetime.fromisoformat(row["updated_at"])
            if now - updated < timedelta(seconds=60):
                return row["price"], row["change_pct"]
        price, change_pct = get_price(ticker)
        conn.execute(
            "INSERT OR REPLACE INTO price_cache (ticker, price, change_pct, updated_at) VALUES (?,?,?,?)",
            (ticker.upper(), price, change_pct, now.isoformat())
        )
        return price, change_pct


# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/holdings", methods=["GET"])
def list_holdings():
    with get_db() as conn:
        holdings = conn.execute("SELECT * FROM holdings ORDER BY created_at DESC").fetchall()
        out = []
        total_value = 0.0
        total_cost = 0.0
        for h in holdings:
            price, change_pct = get_cached_price(h["ticker"])
            value = price * h["shares"]
            cost = h["cost_basis"] * h["shares"]
            pl = value - cost
            pl_pct = (pl / cost * 100) if cost else 0
            total_value += value
            total_cost += cost
            out.append({
                "id": h["id"],
                "ticker": h["ticker"],
                "asset_type": h["asset_type"],
                "shares": h["shares"],
                "cost_basis": h["cost_basis"],
                "sector": h["sector"] or "—",
                "purchase_date": h["purchase_date"],
                "notes": h["notes"],
                "price": price,
                "change_pct": change_pct,
                "value": round(value, 2),
                "cost": round(cost, 2),
                "pl": round(pl, 2),
                "pl_pct": round(pl_pct, 2),
            })
        total_pl = total_value - total_cost
        total_pl_pct = (total_pl / total_cost * 100) if total_cost else 0
        return jsonify({
            "holdings": out,
            "summary": {
                "total_value": round(total_value, 2),
                "total_cost": round(total_cost, 2),
                "total_pl": round(total_pl, 2),
                "total_pl_pct": round(total_pl_pct, 2),
                "position_count": len(out),
            }
        })


@app.route("/api/holdings", methods=["POST"])
def add_holding():
    data = request.get_json() or {}
    ticker = (data.get("ticker") or "").upper().strip()
    shares = float(data.get("shares") or 0)
    cost_basis = float(data.get("cost_basis") or 0)
    if not ticker or shares <= 0 or cost_basis <= 0:
        return jsonify({"error": "ticker, shares (>0), cost_basis (>0) required"}), 400
    asset_type = (data.get("asset_type") or "stock").lower()
    sector = data.get("sector") or None
    purchase_date = data.get("purchase_date") or datetime.today().date().isoformat()
    notes = data.get("notes") or None
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO holdings (ticker, asset_type, shares, cost_basis, sector, purchase_date, notes)
               VALUES (?,?,?,?,?,?,?)""",
            (ticker, asset_type, shares, cost_basis, sector, purchase_date, notes)
        )
        holding_id = cur.lastrowid
        conn.execute(
            """INSERT INTO transactions (holding_id, ticker, action, shares, price, date, notes)
               VALUES (?,?,?,?,?,?,?)""",
            (holding_id, ticker, "buy", shares, cost_basis, purchase_date, notes)
        )
    return jsonify({"ok": True, "id": holding_id}), 201


@app.route("/api/holdings/<int:holding_id>", methods=["DELETE"])
def delete_holding(holding_id):
    with get_db() as conn:
        conn.execute("DELETE FROM transactions WHERE holding_id=?", (holding_id,))
        conn.execute("DELETE FROM holdings WHERE id=?", (holding_id,))
    return jsonify({"ok": True})


@app.route("/api/transactions", methods=["GET"])
def list_transactions():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions ORDER BY date DESC, id DESC LIMIT 100"
        ).fetchall()
        return jsonify({"transactions": [dict(r) for r in rows]})


@app.route("/api/transactions", methods=["POST"])
def add_transaction():
    """Record a dividend or additional buy/sell."""
    data = request.get_json() or {}
    ticker = (data.get("ticker") or "").upper().strip()
    action = (data.get("action") or "buy").lower()
    shares = float(data.get("shares") or 0)
    price = float(data.get("price") or 0)
    date = data.get("date") or datetime.today().date().isoformat()
    notes = data.get("notes")
    if not ticker or shares <= 0 or price <= 0:
        return jsonify({"error": "ticker, shares, price required"}), 400
    with get_db() as conn:
        holding = conn.execute(
            "SELECT id FROM holdings WHERE ticker=? ORDER BY id DESC LIMIT 1", (ticker,)
        ).fetchone()
        holding_id = holding["id"] if holding else None
        conn.execute(
            """INSERT INTO transactions (holding_id, ticker, action, shares, price, date, notes)
               VALUES (?,?,?,?,?,?,?)""",
            (holding_id, ticker, action, shares, price, date, notes)
        )
    return jsonify({"ok": True}), 201


@app.route("/api/allocation", methods=["GET"])
def allocation():
    """Return allocation by sector and by asset_type for pie charts."""
    with get_db() as conn:
        holdings = conn.execute("SELECT * FROM holdings").fetchall()
    by_sector = {}
    by_type = {}
    for h in holdings:
        price, _ = get_cached_price(h["ticker"])
        value = price * h["shares"]
        sec = h["sector"] or "Uncategorized"
        by_sector[sec] = by_sector.get(sec, 0) + value
        by_type[h["asset_type"]] = by_type.get(h["asset_type"], 0) + value
    return jsonify({
        "by_sector": [{"label": k, "value": round(v, 2)} for k, v in sorted(by_sector.items(), key=lambda x: -x[1])],
        "by_type": [{"label": k, "value": round(v, 2)} for k, v in sorted(by_type.items(), key=lambda x: -x[1])],
    })


@app.route("/api/export", methods=["GET"])
def export_csv():
    """Export holdings to CSV."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM holdings").fetchall()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["id", "ticker", "asset_type", "shares", "cost_basis", "sector", "purchase_date", "notes", "created_at"])
    for r in rows:
        writer.writerow([r["id"], r["ticker"], r["asset_type"], r["shares"], r["cost_basis"],
                         r["sector"], r["purchase_date"], r["notes"], r["created_at"]])
    output = si.getvalue()
    return app.response_class(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=holdings.csv"}
    )


@app.route("/api/seed", methods=["POST"])
def seed_demo():
    """Seed a demo portfolio for first-time users."""
    demo = [
        ("AAPL", "stock", 25, 165.00, "Technology", "2023-04-12", "Long-term core holding"),
        ("MSFT", "stock", 15, 305.00, "Technology", "2023-06-01", "Cloud + AI play"),
        ("NVDA", "stock", 8, 420.00, "Technology", "2023-09-20", "AI chip leader"),
        ("VOO", "etf", 40, 410.00, "Broad Market", "2023-01-15", "S&P 500 core"),
        ("SCHD", "etf", 50, 72.00, "Dividend", "2023-03-10", "Dividend growth ETF"),
        ("BTC", "crypto", 0.5, 45000.00, "Crypto", "2023-11-05", "Long-term crypto"),
        ("ETH", "crypto", 4.0, 2200.00, "Crypto", "2023-12-15", "Ethereum core"),
    ]
    with get_db() as conn:
        existing = conn.execute("SELECT COUNT(*) as c FROM holdings").fetchone()["c"]
        if existing > 0:
            return jsonify({"ok": False, "msg": "Portfolio already has holdings — seed skipped"}), 200
        for t, at, s, cb, sec, pd, n in demo:
            conn.execute(
                """INSERT INTO holdings (ticker, asset_type, shares, cost_basis, sector, purchase_date, notes)
                   VALUES (?,?,?,?,?,?,?)""",
                (t, at, s, cb, sec, pd, n)
            )
    return jsonify({"ok": True, "msg": "Demo portfolio seeded"}), 201


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5001, debug=True)
