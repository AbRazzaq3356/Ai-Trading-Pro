import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import date, timedelta

st.set_page_config(page_title="AI Trading Pro", page_icon="📈", layout="wide")

st.markdown("""
<style>
.main {background-color:#0b1220}
[data-testid="stMetric"] {background:#111c2e;padding:14px;border-radius:12px}
.stTabs [data-baseweb="tab"] {font-size:15px}
</style>
""", unsafe_allow_html=True)

st.title("📈 AI Trading Pro")
st.caption("Independent market analysis • Backtesting • Virtual paper trading")
st.warning("Educational simulator only. Not connected to Quotex or any broker. Signals are not financial advice; no accuracy or profit is guaranteed.")

def indicators(df):
    d = df.copy()
    close = d["Close"]
    d["EMA9"] = close.ewm(span=9, adjust=False).mean()
    d["EMA21"] = close.ewm(span=21, adjust=False).mean()
    d["EMA50"] = close.ewm(span=50, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    d["RSI"] = 100 - (100 / (1 + rs))
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    d["MACD"] = ema12 - ema26
    d["MACD_Signal"] = d["MACD"].ewm(span=9, adjust=False).mean()
    return d

def add_signals(d):
    x = d.copy()
    x["Signal"] = "NO TRADE"
    call = (x["EMA9"] > x["EMA21"]) & (x["EMA21"] > x["EMA50"]) & (x["RSI"].between(50, 68)) & (x["MACD"] > x["MACD_Signal"])
    put = (x["EMA9"] < x["EMA21"]) & (x["EMA21"] < x["EMA50"]) & (x["RSI"].between(32, 50)) & (x["MACD"] < x["MACD_Signal"])
    x.loc[call, "Signal"] = "CALL"
    x.loc[put, "Signal"] = "PUT"
    return x

def backtest(d, initial_balance, risk_pct, payout, fee_pct):
    # Signal is generated using the completed candle; outcome uses the next candle.
    x = d.copy().dropna().reset_index()
    balance = float(initial_balance)
    peak = balance
    max_dd = 0.0
    rows = []
    for i in range(len(x)-1):
        sig = x.loc[i, "Signal"]
        if sig not in ("CALL", "PUT"):
            continue
        stake = balance * risk_pct / 100
        entry = float(x.loc[i, "Close"])
        exit_price = float(x.loc[i+1, "Close"])
        won = (exit_price > entry) if sig == "CALL" else (exit_price < entry)
        # Payout is net profit percentage on a winning stake; losing stake is lost.
        pnl = stake * payout / 100 if won else -stake
        pnl -= stake * fee_pct / 100
        balance += pnl
        peak = max(peak, balance)
        max_dd = max(max_dd, (peak-balance)/peak*100 if peak else 0)
        rows.append({"Time": x.loc[i, "Date"], "Signal": sig, "Entry": entry,
                     "Next close": exit_price, "Stake": stake, "P/L": pnl,
                     "Result": "WIN" if won else "LOSS", "Balance": balance})
        if balance <= 0:
            break
    trades = pd.DataFrame(rows)
    wins = int((trades["Result"] == "WIN").sum()) if not trades.empty else 0
    count = len(trades)
    gross_profit = trades.loc[trades["P/L"] > 0, "P/L"].sum() if count else 0
    gross_loss = abs(trades.loc[trades["P/L"] < 0, "P/L"].sum()) if count else 0
    stats = {
        "Final balance": balance,
        "Trades": count,
        "Win rate": (wins/count*100) if count else 0,
        "Net P/L": balance-initial_balance,
        "Max drawdown": max_dd,
        "Profit factor": (gross_profit/gross_loss) if gross_loss else (float("inf") if gross_profit else 0)
    }
    return trades, stats

@st.cache_data(ttl=300)
def load_yahoo(ticker, period, interval):
    raw = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
    if raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = raw.rename_axis("Date").reset_index()
    required = ["Open","High","Low","Close"]
    if not all(c in raw.columns for c in required):
        return pd.DataFrame()
    return raw

with st.sidebar:
    st.header("⚙️ Settings")
    source = st.radio("Market data source", ["Yahoo Finance", "Upload CSV"])
    if source == "Yahoo Finance":
        ticker = st.text_input("Symbol", "EURUSD=X", help="Examples: EURUSD=X, GBPUSD=X, BTC-USD, AAPL")
        period = st.selectbox("History", ["1mo","3mo","6mo","1y","2y"], index=2)
        interval = st.selectbox("Candle interval", ["1d","1h","30m","15m","5m"], index=0)
    else:
        uploaded = st.file_uploader("Upload OHLC CSV", type=["csv"])
    st.divider()
    initial_balance = st.number_input("Virtual starting balance", min_value=100.0, value=10000.0, step=500.0)
    risk_pct = st.slider("Stake per trade (% of balance)", 0.5, 5.0, 1.0, 0.5)
    payout = st.slider("Winning payout (%)", 10, 100, 80, 5)
    fee_pct = st.number_input("Fee per trade (% of stake)", min_value=0.0, max_value=10.0, value=0.0, step=0.1)

if source == "Yahoo Finance":
    with st.spinner("Loading market data..."):
        data = load_yahoo(ticker.strip(), period, interval)
else:
    if uploaded is not None:
        data = pd.read_csv(uploaded)
        data.columns = [str(c).strip().title() for c in data.columns]
        if "Date" not in data.columns:
            st.error("CSV must include a Date column.")
            data = pd.DataFrame()
        else:
            data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    else:
        data = pd.DataFrame()

if data.empty:
    st.info("Load market data from Yahoo Finance or upload a CSV with Date, Open, High, Low, Close columns.")
    st.markdown("**CSV example**")
    st.code("Date,Open,High,Low,Close,Volume\\n2026-01-01,1.10,1.12,1.09,1.11,1000")
    st.stop()

data.columns = [str(c).title() for c in data.columns]
data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
for c in ["Open","High","Low","Close"]:
    data[c] = pd.to_numeric(data[c], errors="coerce")
data = data.dropna(subset=["Date","Open","High","Low","Close"]).sort_values("Date")
if len(data) < 60:
    st.error("Please provide at least 60 candles for indicator calculations.")
    st.stop()

analysis = add_signals(indicators(data))
latest = analysis.iloc[-1]
signal = latest["Signal"]

c1,c2,c3,c4 = st.columns(4)
c1.metric("Latest close", f"{latest['Close']:.5f}")
c2.metric("Current signal", signal)
c3.metric("RSI (14)", f"{latest['RSI']:.1f}")
c4.metric("Candles loaded", f"{len(analysis):,}")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🧪 Backtesting", "💵 Paper Trading", "📚 Strategy & Help"])

with tab1:
    st.subheader("Price chart and indicators")
    chart = analysis.set_index("Date")[["Close","EMA9","EMA21","EMA50"]]
    st.line_chart(chart)
    left,right = st.columns(2)
    with left:
        st.subheader("Indicator snapshot")
        st.dataframe(analysis[["Date","Close","RSI","MACD","MACD_Signal","Signal"]].tail(12), use_container_width=True, hide_index=True)
    with right:
        st.subheader("Signal interpretation")
        if signal == "CALL":
            st.success("Trend filters currently align upward. Treat this as a research signal, not a trade instruction.")
        elif signal == "PUT":
            st.error("Trend filters currently align downward. Treat this as a research signal, not a trade instruction.")
        else:
            st.info("No trade: current conditions do not meet all strategy filters.")

with tab2:
    st.subheader("Historical backtest")
    st.caption("This simple baseline evaluates the next candle's close direction after a completed-candle signal. Results are historical simulations and may not represent executable binary-option prices.")
    trades, stats = backtest(analysis, initial_balance, risk_pct, payout, fee_pct)
    a,b,c,d,e = st.columns(5)
    a.metric("Final virtual balance", f"{stats['Final balance']:,.2f}")
    b.metric("Trades", stats["Trades"])
    c.metric("Win rate", f"{stats['Win rate']:.1f}%")
    d.metric("Net P/L", f"{stats['Net P/L']:+,.2f}")
    e.metric("Max drawdown", f"{stats['Max drawdown']:.1f}%")
    st.metric("Profit factor", "∞" if np.isinf(stats["Profit factor"]) else f"{stats['Profit factor']:.2f}")
    if trades.empty:
        st.info("No qualifying trades in this dataset. Try a longer history or another symbol.")
    else:
        st.line_chart(trades.set_index("Time")["Balance"])
        st.dataframe(trades.sort_values("Time", ascending=False), use_container_width=True, hide_index=True)
        st.download_button("Download backtest CSV", trades.to_csv(index=False), "backtest_trades.csv", "text/csv")

with tab3:
    st.subheader("Paper trading — virtual only")
    st.write(f"Starting virtual balance: **{initial_balance:,.2f}**")
    st.write(f"Configured stake: **{risk_pct:.1f}%** of current virtual balance")
    st.write("This first version provides a paper-trading preview and does not persist trades between app sessions.")
    if signal in ("CALL","PUT"):
        st.success(f"Latest strategy signal: {signal}")
    else:
        st.info("Latest strategy signal: NO TRADE")
    st.metric("Illustrative next-trade stake", f"{initial_balance*risk_pct/100:,.2f}")
    st.caption("No real money is used. A live, candle-by-candle paper ledger and persistent storage are planned for the next development stage.")

with tab4:
    st.subheader("How the baseline strategy works")
    st.markdown("""
    - **CALL filter:** EMA 9 > EMA 21 > EMA 50, RSI between 50 and 68, and MACD above its signal line.
    - **PUT filter:** EMA 9 < EMA 21 < EMA 50, RSI between 32 and 50, and MACD below its signal line.
    - Otherwise the strategy returns **NO TRADE**.
    - Signals use completed candle values. Backtesting applies the signal to the following candle to reduce look-ahead bias.
    """)
    st.warning("Limitations: Yahoo Finance data availability varies by symbol and interval; some FX/OTC or broker-specific Quotex prices may not be available. This is a starter research tool, not a validated AI model. Add out-of-sample testing, realistic execution assumptions, and independent data verification before relying on results.")
    st.markdown("**Required CSV columns:** Date, Open, High, Low, Close. Volume is optional.")

st.divider()
st.caption("AI Trading Pro • Version 0.1 • Educational research software")
