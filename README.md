# AI Trading Pro — Starter v0.1

Independent market-analysis, backtesting and virtual paper-trading dashboard.
It does not connect to Quotex or any broker and cannot place real trades.

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Create and activate a virtual environment (recommended).
4. Install dependencies:

   `pip install -r requirements.txt`

5. Start the dashboard:

   `streamlit run app.py`

6. Open the local URL shown by Streamlit.

## Data

- Yahoo Finance mode supports symbols such as `EURUSD=X`, `GBPUSD=X`, `BTC-USD`, and `AAPL`, subject to Yahoo's data availability.
- CSV mode requires `Date, Open, High, Low, Close`. `Volume` is optional.
- This is not Quotex OTC data. Do not assume prices match a broker feed.

## Strategy baseline

CALL: EMA9 > EMA21 > EMA50, RSI 50–68, MACD > MACD signal.
PUT: EMA9 < EMA21 < EMA50, RSI 32–50, MACD < MACD signal.
Otherwise: NO TRADE.

The backtest generates signals on a completed candle and evaluates the following candle's close direction. Payout, stake sizing and fees are simplified assumptions. This is not a complete binary-options execution simulator.

## Next development stages

1. Validate data quality and add an independent data source.
2. Add out-of-sample / walk-forward testing and parameter controls.
3. Add persistent paper-trading ledger and configurable virtual execution rules.
4. Add trade journal, equity curve, drawdown and risk limits.
5. Only consider model-based scoring after enough clean, labeled historical data exists.

## Risk notice

Educational software only. No profit or accuracy is guaranteed. Historical performance does not predict future results. Do not use this app as a substitute for financial, legal, or regulatory advice.
