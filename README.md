# Portfolio Tracker

A simple but full-featured portfolio tracking web app for stocks, ETFs, and crypto. Built as a daily full-stack exercise.

## What it does

- Track holdings across **stocks, ETFs, and crypto** in one place
- See **live P/L, day-change %, and total portfolio value** at a glance
- **Allocation breakdown** by sector and by asset type (donut charts)
- **Transaction history** with buy / sell / dividend logging
- **One-click CSV export** for tax prep or spreadsheet analysis
- **Demo data seeder** — populate the portfolio with sample holdings in one click
- Auto-refreshes prices every 60 seconds

## Why it matters

Most portfolio trackers are either heavyweight SaaS subscriptions (with locked data) or
Excel spreadsheets. This is the middle ground: a self-hosted, dependency-light app
that gives you real-time-ish P/L visibility with full ownership of your data (SQLite file
on your machine). The transaction log makes it useful for tax time, and the allocation
charts show whether you're accidentally 80% tech.

## Tech stack

- **Backend:** Python 3 / Flask / SQLite
- **Frontend:** Vanilla HTML + CSS + JavaScript (no build step)
- **Charts:** Chart.js (CDN)
- **Storage:** SQLite (file-based, zero config)

## Project structure

```
portfolio-tracker/
├── app.py                  # Flask backend + REST API
├── templates/index.html    # Single-page UI
├── static/
│   ├── style.css           # Dark theme styling
│   └── app.js              # Frontend logic
├── requirements.txt
└── README.md
```

## REST API

| Method | Endpoint                  | Purpose                       |
|--------|---------------------------|-------------------------------|
| GET    | `/api/holdings`           | List holdings + summary       |
| POST   | `/api/holdings`           | Add a new holding             |
| DELETE | `/api/holdings/<id>`      | Remove a holding              |
| GET    | `/api/transactions`       | List recent transactions      |
| POST   | `/api/transactions`       | Record buy/sell/dividend      |
| GET    | `/api/allocation`         | Sector + type breakdown       |
| GET    | `/api/export`             | Download CSV of holdings      |
| POST   | `/api/seed`               | Seed demo portfolio           |

## How to run

```bash
cd portfolio-tracker
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open <http://127.0.0.1:5001> in your browser.

Click **Load Demo Data** to populate the portfolio with sample holdings, or
add your own positions with the form.

## Future ideas

- Real price API integration (Alpha Vantage, Finnhub, CoinGecko)
- Historical price charts per holding
- Multi-portfolio support
- Authentication + cloud sync
- Dividend yield / forward income calculations
- Tax lot tracking (FIFO/LIFO/Spec ID)

## License

MIT
