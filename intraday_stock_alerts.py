import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 🔧 Page Configuration
st.set_page_config(
    page_title="Intraday & Swing Screener 📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


#st.set_page_config(layout="wide")
st.markdown("<h3 style='font-size:35px; color:#333;'>📈 Intraday Trading Buy/Sell Signal</h3>", unsafe_allow_html=True)

# --- Sidebar Inputs ---
st.sidebar.markdown("## Select or Enter a Stock")

# --- Stock Label to Actual Mapping
stock_display_to_actual = {
    "^NSEI": "^NSEI",
    "ADANIENT": "ADANIENT.NS", 
    "ADANIPORTS": "ADANIPORTS.NS", "APOLLOHOSP": "APOLLOHOSP.NS", 
    "ASIANPAINT": "ASIANPAINT.NS", "AXISBANK": "AXISBANK.NS", 
    "BAJAJ-AUTO": "BAJAJ-AUTO.NS", "BAJFINANCE": "BAJFINANCE.NS", 
    "BAJAJFINSV": "BAJAJFINSV.NS", "BEL": "BEL.NS", "BHARTIARTL": "BHARTIARTL.NS", 
    "CIPLA": "CIPLA.NS", "COALINDIA": "COALINDIA.NS", "DRREDDY": "DRREDDY.NS", "EICHERMOT": "EICHERMOT.NS", 
    "ETERNAL": "ETERNAL.NS", "GRASIM": "GRASIM.NS", "HCLTECH": "HCLTECH.NS", "HDFCBANK": "HDFCBANK.NS", 
    "HDFCLIFE": "HDFCLIFE.NS", "HEROMOTOCO": "HEROMOTOCO.NS", "HINDALCO": "HINDALCO.NS", "HINDUNILVR": "HINDUNILVR.NS", 
    "ICICIBANK": "ICICIBANK.NS", "ITC": "ITC.NS", "INDUSINDBK": "INDUSINDBK.NS", "INFY": "INFY.NS", 
    "JSWSTEEL": "JSWSTEEL.NS", "JIOFIN": "JIOFIN.NS", "KOTAKBANK": "KOTAKBANK.NS", "LT": "LT.NS", 
    "M&M": "M&M.NS", "MARUTI": "MARUTI.NS", "NTPC": "NTPC.NS", "NESTLEIND": "NESTLEIND.NS", 
    "ONGC": "ONGC.NS", "POWERGRID": "POWERGRID.NS", "RELIANCE": "RELIANCE.NS", "SBILIFE": "SBILIFE.NS", 
    "SHRIRAMFIN": "SHRIRAMFIN.NS", "SBIN": "SBIN.NS", "SUNPHARMA": "SUNPHARMA.NS", "TCS": "TCS.NS", 
    "TATACONSUM": "TATACONSUM.NS", "TATAMOTORS": "TATAMOTORS.NS", "TATASTEEL": "TATASTEEL.NS", "TECHM": "TECHM.NS", 
    "TITAN": "TITAN.NS", "TRENT": "TRENT.NS", "ULTRACEMCO": "ULTRACEMCO.NS", "WIPRO": "WIPRO.NS", "VEDL": "VEDL.NS", 
    "LIC": "LICI.NS", "MCX": "MCX.NS", "ADANIGREEN": "ADANIGREEN.NS", "ADANIPOWER": "ADANIPOWER.NS",
    "ADANIENSOL": "ADANIENSOL.NS", "VBL": "VBL.NS"
}
stock_options = list(stock_display_to_actual.keys())  # UI labels without .NS

# --- Initialize session state (with label keys, not actual tickers)
if "selected_stocks" not in st.session_state:
    st.session_state.selected_stocks = ["^NSEI"]  # ✅ must match `stock_options`
if "custom_stock_input" not in st.session_state:
    st.session_state.custom_stock_input = ""


# --- Callbacks to clear
def clear_selected():
    st.session_state.selected_stocks = []
def clear_custom():
    st.session_state.custom_stock_input = ""

# --- UI: Stock Selection (clean display)
selected_labels = st.sidebar.multiselect(
    "Select Stocks",
    stock_options,
    default=st.session_state.selected_stocks,
    key="selected_stocks",
    on_change=clear_custom  # ← this triggers when user selects stock
)

# --- UI: Custom Stock Entry
# --- Custom Input ---
custom_input = st.sidebar.text_input(
    "Or type a custom Stock Code (e.g. INFY, TCS, LTIM)",
    value=st.session_state.custom_stock_input,
    key="custom_stock_input",
    on_change=clear_selected
)


# --- Final Yahoo Finance Ticker Symbols
tickers = []

if custom_input.strip():
    symbol = custom_input.strip().upper()
    if not symbol.endswith(".NS") and symbol != "^NSEI":
        symbol += ".NS"
    tickers = [symbol]
else:
    tickers = [stock_display_to_actual[label] for label in selected_labels if label in stock_display_to_actual]



# --- Final Tickers Logic ---
if custom_input.strip():
    custom_symbol = custom_input.strip().upper()
    if not custom_symbol.endswith(".NS"):
        custom_symbol += ".NS"
    tickers = [custom_symbol]  # overrides multiselect

# --- Interval and Candle Limit ---
st.sidebar.markdown("## Chart Settings")

interval = st.sidebar.selectbox(
    "Select Interval", 
    ['1m', '5m', '15m'], 
    index=1
)

limit = st.sidebar.slider(
    "Number of recent candles", 
    50, 500, 150
)


# --- Display calculated time span ---
interval_minutes = {"1m": 1, "5m": 5, "15m": 15}
total_minutes = interval_minutes[interval] * limit
hours = total_minutes // 60
minutes = total_minutes % 60

st.sidebar.caption(f"🕒 Showing approx: **{hours}h {minutes}m** of data for `{interval}` interval")


# --- Data Fetch ---
def fetch_data(ticker, interval, limit):
    df = yf.download(ticker, period="1d", interval=interval)
    df.dropna(inplace=True)
    return df.tail(limit)


# --- Add Indicators ---
def add_indicators(df):
    df = df.copy().reset_index(drop=True)
    close_series = pd.Series(df['Close'].values.ravel(), index=df.index).astype(float)

    df['RSI'] = ta.momentum.RSIIndicator(close=close_series, window=14).rsi()
    macd_calc = ta.trend.MACD(close_series)
    df['MACD'] = macd_calc.macd()
    df['MACD_Signal'] = macd_calc.macd_signal()

    high = pd.Series(df['High'].values.ravel(), index=df.index).astype(float)
    low = pd.Series(df['Low'].values.ravel(), index=df.index).astype(float)
    close = pd.Series(df['Close'].values.ravel(), index=df.index).astype(float)
    volume = pd.Series(df['Volume'].values.ravel(), index=df.index).astype(float)

    tp = (high + low + close) / 3
    vwap = (tp * volume).cumsum() / volume.cumsum()
    df['VWAP'] = vwap

    return df

# --- Candlestick Pattern Detection ---
def detect_candlestick_pattern(df):
    pattern = []

    for i in range(len(df)):
        row = df.iloc[i]
        o = float(row['Open'])
        h = float(row['High'])
        l = float(row['Low'])
        c = float(row['Close'])

        body = abs(c - o)
        range_ = h - l

        if abs(range_) < 1e-6:
            pattern.append("")
            continue

        # Doji
        if body < 0.1 * range_:
            pattern.append("Doji")
        # Hammer
        elif (c > o) and ((o - l) > 2 * body) and ((h - c) < body):
            pattern.append("Hammer")
        # Bullish/Bearish Engulfing
        elif i > 0:
            prev = df.iloc[i - 1]
            p_o, p_c = float(prev['Open']), float(prev['Close'])

            if (p_c < p_o) and (c > o) and (c > p_o) and (o < p_c):
                pattern.append("Bullish Engulfing")
            elif (p_c > p_o) and (c < o) and (c < p_o) and (o > p_c):
                pattern.append("Bearish Engulfing")
            else:
                pattern.append("")
        else:
            pattern.append("")

    df['Candle_Pattern'] = pattern
    return df


# --- Signal Engine ---
def generate_signals(df):
    latest = df.tail(1).squeeze()

    signals = []
    score = 0

    try:
        rsi = float(latest['RSI'])
        close = float(latest['Close'])
        vwap = float(latest['VWAP'])
        macd = float(latest['MACD'])
        macd_signal = float(latest['MACD_Signal'])
        pattern = str(latest['Candle_Pattern']).strip()  # ← get pattern safely
    except:
        return ["❌ Could not generate signals (NaN or series issue)"], "⚠️ FINAL ACTION: HOLD (Insufficient Data)"

    # --- RSI ---
    if rsi < 30:
        signals.append("🟢 RSI < 30 (Buy)")
        score += 1
    elif rsi > 70:
        signals.append("🔴 RSI > 70 (Sell)")
        score -= 1
    else:
        signals.append("🟡 RSI Neutral")

    # --- VWAP ---
    if close > vwap:
        signals.append("🟢 Price above VWAP")
        score += 1
    else:
        signals.append("🔴 Price below VWAP")
        score -= 1

    # --- MACD ---
    if macd > macd_signal:
        signals.append("🟢 MACD Bullish")
        score += 1
    else:
        signals.append("🔴 MACD Bearish")
        score -= 1

    # --- Pattern (NEW scoring) ---
    if pattern == "Hammer":
        signals.append("🟢 Hammer Pattern Detected")
        score += 1
    elif pattern == "Bullish Engulfing":
        signals.append("🟢 Bullish Engulfing Detected")
        score += 1
    elif pattern == "Bearish Engulfing":
        signals.append("🔴 Bearish Engulfing Detected")
        score -= 1
    elif pattern == "Doji":
        signals.append("🟡 Doji (Neutral Signal)")

    # --- Final Decision ---
    if score >= 2:
        final = "🟢 FINAL ACTION: BUY"
    elif score <= -2:
        final = "🔴 FINAL ACTION: SELL"
    else:
        final = "🟡 FINAL ACTION: HOLD"

    return signals, final


# --- Candlestick Plot ---
def plot_candlestick(df, ticker):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name="Price",
        increasing=dict(line=dict(color="green")),
        decreasing=dict(line=dict(color="red")),
        showlegend=True
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['VWAP'],
        line=dict(color='orange', width=1),
        name="VWAP"
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['MACD'],
        name="MACD",
        line=dict(color='blue', width=1),
        yaxis="y2"
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['MACD_Signal'],
        name="MACD Signal",
        line=dict(color='red', width=1),
        yaxis="y2"
    ))

    fig.update_layout(
        title=f"{ticker} Intraday Candlestick",
        xaxis_rangeslider_visible=False,
        height=400,
        yaxis=dict(title='Price'),
        yaxis2=dict(title='MACD', overlaying='y', side='right', showgrid=False)
    )

    return fig
def compute_weighted_score(interval_signals):
    weight_map = {"1m": 0.5, "5m": 1.0, "15m": 1.5}
    score = 0

    for interval, action in interval_signals.items():
        w = weight_map.get(interval, 1)
        if "BUY" in action:
            score += w
        elif "SELL" in action:
            score -= w

    if score >= 2:
        return "🟢 OVERALL: STRONG BUY"
    elif score <= -2:
        return "🔴 OVERALL: STRONG SELL"
    else:
        return "🟡 OVERALL: HOLD / WAIT"


# --- Show warning if no stock is selected or typed ---
if not tickers:
    st.warning("👈 Please select a stock from the dropdown or type one manually to begin.")
    #st.stop()  # prevents rest of the app from running without a stock

# --- Output ---
final_action_summary = None
if tickers:

    for ticker in tickers:
        st.subheader(f"📌 {ticker}")

        # --- Part 1: Chart & Metrics for selected interval ---
        st.markdown(f"<h4 style='font-size:18px; margin-bottom:10px;'>📈 {interval} View with Indicators</h4>", unsafe_allow_html=True
)


        try:
            df = fetch_data(ticker, interval, limit)
            df = add_indicators(df)
            df = detect_candlestick_pattern(df)
            signals, final_action = generate_signals(df)

            col1, col2 = st.columns([2, 1])
            with col1:
                st.plotly_chart(plot_candlestick(df, ticker), use_container_width=True)

              # --- Three Column Layout
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("#### 💰 Price & Momentum")
                st.metric("Last Price", f"₹{float(df['Close'].iloc[-1]):,.2f}")
                st.metric("RSI", round(df['RSI'].iloc[-1], 2))
                st.metric("VWAP", round(df['VWAP'].iloc[-1], 2))

            with col2:
                st.markdown("#### 📉 MACD Indicators")
                st.metric("MACD", round(df['MACD'].iloc[-1], 3))
                st.metric("Signal Line", round(df['MACD_Signal'].iloc[-1], 3))

            with col3:
                st.markdown("#### 🕯️ Candlestick Pattern")
                pattern = df['Candle_Pattern'].iloc[-1] or "None"
                st.metric("Candle Pattern", pattern)

                st.markdown("### 🔔 Trade Signals")
                for sig in signals:
                    st.write(sig)


                st.markdown(f"### 📌 Final Signal for {interval} Chart Interval")

                if "BUY" in final_action:
                    st.success(final_action)
                elif "SELL" in final_action:
                    st.error(final_action)
                else:
                    st.warning(final_action)

        except Exception as e:
            st.error(f"Error loading chart for {ticker}: {e}")

        # --- Part 2: Multi-Interval Signal Summary ---
st.markdown("---")
st.markdown("### 📊 All-Interval Signal Summary")

interval_signals = {}
table_data = []

# Map interval to appropriate period
interval_period_map = {
    '1m': '1d',
    '5m': '1d',
    '15m': '1d',
    '1d': '3mo',        # Daily interval for past 3 months
    '1wk': '6mo',       # Weekly for past 6 months
    'Month': '1y'         # Monthly for past 1 year
}

for interval, period in interval_period_map.items():
    try:
        df = yf.download(ticker, period=period, interval=interval)
        df = df.tail(150)
        df.dropna(inplace=True)

        df = add_indicators(df)
        df = detect_candlestick_pattern(df)
        signals, final_action = generate_signals(df)

        last_price = f"₹{float(df['Close'].iloc[-1]):,.2f}"
        rsi = round(df['RSI'].iloc[-1], 2)
        vwap = round(df['VWAP'].iloc[-1], 2)
        macd = round(df['MACD'].iloc[-1], 3)
        signal_line = round(df['MACD_Signal'].iloc[-1], 3)
        pattern = df['Candle_Pattern'].iloc[-1] or "None"

        interval_label = interval.replace("1m", "1-Min").replace("5m", "5-Min").replace("15m", "15-Min").replace("1d", "Daily").replace("1wk", "Weekly").replace("Month", "Monthly")

        interval_signals[interval_label] = final_action

        table_data.append({
            "Interval": interval_label,
            "Last Price": last_price,
            "RSI": rsi,
            "VWAP": vwap,
            "MACD": macd,
            "Signal Line": signal_line,
            "Pattern": pattern,
            "Final Action": final_action
        })

    except Exception as e:
        table_data.append({
            "Interval": interval,
            "Last Price": "Error",
            "RSI": "-",
            "VWAP": "-",
            "MACD": "-",
            "Signal Line": "-",
            "Pattern": "Error",
            "Final Action": str(e)
        })

st.dataframe(pd.DataFrame(table_data).set_index("Interval"))

# --- Part 3: Weighted Recommendation ---
st.markdown("### 🎯 Overall Recommendation")
overall = compute_weighted_score(interval_signals)

if "BUY" in overall:
    st.success(overall)
elif "SELL" in overall:
    st.error(overall)
else:
    st.warning(overall)


def show_intraday_stock_summary():
    st.markdown("---")
    st.markdown("<h3 style='font-size:30px; color:#333;'>📊 Stock Wise Summary (Intra Day Signals)</h3>", unsafe_allow_html=True)

    predefined_stocks = ['^NSEI', 'ADANIENT.NS', 'ADANIPORTS.NS', 'APOLLOHOSP.NS', 'ASIANPAINT.NS', 'AXISBANK.NS',
                         'BAJAJ-AUTO.NS', 'BAJFINANCE.NS', 'BAJAJFINSV.NS', 'BEL.NS', 'BHARTIARTL.NS', 'CIPLA.NS',
                         'COALINDIA.NS', 'DRREDDY.NS', 'EICHERMOT.NS', 'ETERNAL.NS', 'GRASIM.NS', 'HCLTECH.NS', 'HDFCBANK.NS',
                         'HDFCLIFE.NS', 'HEROMOTOCO.NS', 'HINDALCO.NS', 'HINDUNILVR.NS', 'ICICIBANK.NS', 'ITC.NS',
                         'INDUSINDBK.NS', 'INFY.NS', 'JSWSTEEL.NS', 'JIOFIN.NS', 'KOTAKBANK.NS', 'LT.NS', 'M&M.NS', 'MARUTI.NS',
                         'NTPC.NS', 'NESTLEIND.NS', 'ONGC.NS', 'POWERGRID.NS', 'RELIANCE.NS', 'SBILIFE.NS', 'SHRIRAMFIN.NS',
                         'SBIN.NS', 'SUNPHARMA.NS', 'TCS.NS', 'TATACONSUM.NS', 'TATAMOTORS.NS', 'TATASTEEL.NS', 'TECHM.NS',
                         'TITAN.NS', 'TRENT.NS', 'ULTRACEMCO.NS', 'WIPRO.NS', 'VEDL.NS', 'LICI.NS', 'NMDC.NS', 'CDSL.NS', 'BSE.NS',
                         'CANBK.NS', 'RVNL.NS', 'MCX.NS', "ADANIGREEN.NS", "ADANIPOWER.NS", "ADANIENSOL.NS", "VBL.NS", "GMDCLTD.NS", "INDIGO.NS", 
                         "IRCTC.NS", "MAZDOCK.NS", "COCHINSHIP.NS", "GESHIP.NS", "GRSE.NS", "YESBANK.NS", "POLYCAB.NS", "LTIM.NS", "IOC.NS", "BPCL.NS", 
                         "ONGC.NS", "HINDPETRO.NS", "ACC.NS", "AMBUJACEM.BO"]

    summary_rows = []

    with st.spinner("⏳ Fetching intraday signals..."):
        progress_bar = st.progress(0)
        for i, ticker in enumerate(predefined_stocks):
            try:
                multi_signals = {}
                last_pattern = "None"

                for intv in ['1m', '5m', '15m']:
                    df = fetch_data(ticker, intv, 150)
                    df = add_indicators(df)
                    df = detect_candlestick_pattern(df)
                    _, action = generate_signals(df)
                    multi_signals[intv] = action
                    last_pattern = df['Candle_Pattern'].iloc[-1] if 'Candle_Pattern' in df.columns else "None"

                final_verdict = compute_weighted_score(multi_signals)

                df_latest = yf.download(ticker, period="1d", interval="1m")
                if not df_latest.empty:
                    last_price = float(df_latest['Close'].iloc[-1])
                    open_price = float(df_latest['Open'].iloc[0])
                    pct_change = ((last_price - open_price) / open_price) * 100
                    formatted_change = f"{pct_change:+.2f}%"
                    formatted_price = f"₹{last_price:,.2f}"
                else:
                    formatted_change = "N/A"
                    formatted_price = "N/A"

                if pct_change > 0:
                    formatted_change = f"🟢 +{pct_change:.2f}%"
                elif pct_change < 0:
                    formatted_change = f"🔻 {pct_change:.2f}%"
                else:
                    formatted_change = f"➖ **0.00%**"

                summary_rows.append({
                    "Stock": ticker,
                    "Last Price": formatted_price,
                    "Change %": formatted_change,
                    "1m Signal": multi_signals.get("1m", "N/A"),
                    "5m Signal": multi_signals.get("5m", "N/A"),
                    "15m Signal": multi_signals.get("15m", "N/A"),
                    "Pattern": last_pattern,
                    "Verdict": final_verdict
                })

            except Exception as e:
                summary_rows.append({
                    "Stock": ticker,
                    "Last Price": "Error",
                    "Change %": "-",
                    "1m Signal": "❌ Error",
                    "5m Signal": "❌ Error",
                    "15m Signal": "❌ Error",
                    "Pattern": "Error",
                    "Verdict": str(e)
                })

            progress_bar.progress((i + 1) / len(predefined_stocks))

    if summary_rows:
        summary_df = pd.DataFrame(summary_rows)
        st.dataframe(summary_df, use_container_width=True)


def show_daily_stock_summary():
    st.title("📈 Swing Trade Screener (Daily)")

    nifty_stocks = ['^NSEI', 'ADANIENT.NS', 'ADANIPORTS.NS', 'APOLLOHOSP.NS', 'ASIANPAINT.NS', 'AXISBANK.NS', 
                    'BAJAJ-AUTO.NS', 'BAJFINANCE.NS', 'BAJAJFINSV.NS', 'BEL.NS', 'BHARTIARTL.NS', 'CIPLA.NS', 
                    'COALINDIA.NS', 'DRREDDY.NS', 'EICHERMOT.NS', 'ETERNAL.NS', 'GRASIM.NS', 'HCLTECH.NS', 'HDFCBANK.NS', 
                    'HDFCLIFE.NS', 'HEROMOTOCO.NS', 'HINDALCO.NS', 'HINDUNILVR.NS', 'ICICIBANK.NS', 'ITC.NS', 
                    'INDUSINDBK.NS', 'INFY.NS', 'JSWSTEEL.NS', 'JIOFIN.NS', 'KOTAKBANK.NS', 'LT.NS', 'M&M.NS', 'MARUTI.NS', 
                    'NTPC.NS', 'NESTLEIND.NS', 'ONGC.NS', 'POWERGRID.NS', 'RELIANCE.NS', 'SBILIFE.NS', 'SHRIRAMFIN.NS', 
                    'SBIN.NS', 'SUNPHARMA.NS', 'TCS.NS', 'TATACONSUM.NS', 'TATAMOTORS.NS', 'TATASTEEL.NS', 'TECHM.NS', 
                    'TITAN.NS', 'TRENT.NS', 'ULTRACEMCO.NS', 'WIPRO.NS', 'VEDL.NS', 'LICI.NS', 'NMDC.NS', 'CDSL.NS', 
                    'BSE.NS','CANBK.NS', 'RVNL.NS', 'MCX.NS', "ADANIGREEN.NS", "ADANIPOWER.NS", "ADANIENSOL.NS", "VBL.NS", "GMDCLTD.NS", "INDIGO.NS", 
                    "IRCTC.NS", "MAZDOCK.NS", "COCHINSHIP.NS", "GESHIP.NS", "GRSE.NS", "YESBANK.NS", "POLYCAB.NS", "LTIM.NS", "IOC.NS", "BPCL.NS", 
                    "ONGC.NS", "HINDPETRO.NS", "ACC.NS", "AMBUJACEM.NS"]

    end_date = datetime.today()
    start_date = end_date - timedelta(days=90)

    full_data = []

    with st.spinner("⏳ Scanning stocks..."):
        progress_bar = st.progress(0)
        for i, ticker in enumerate(nifty_stocks):
            try:
                df = yf.download(ticker, start=start_date, end=end_date, interval='1d')
                df.dropna(inplace=True)

                if len(df) < 30:
                    continue

                close_series = pd.Series(df['Close'].values.flatten(), index=df.index)
                volume_series = pd.Series(df['Volume'].values.flatten(), index=df.index)

                df['EMA20'] = ta.trend.EMAIndicator(close=close_series, window=20).ema_indicator()
                df['EMA50'] = ta.trend.EMAIndicator(close=close_series, window=50).ema_indicator()
                df['RSI'] = ta.momentum.RSIIndicator(close=close_series, window=14).rsi()
                df['AvgVolume10'] = volume_series.rolling(10).mean()
                #df.dropna(subset=["EMA20", "EMA50", "RSI", "AvgVolume10"], inplace=True)

                price = float(df['Close'].iloc[-1])
                open_price = float(df['Open'].iloc[-1])
                ema20 = float(df['EMA20'].iloc[-1])
                ema50 = float(df['EMA50'].iloc[-1])
                rsi = float(df['RSI'].iloc[-1])
                vol = float(df['Volume'].iloc[-1])
                avg_vol = float(df['AvgVolume10'].iloc[-1])

                price_change_pct = round((price - open_price) / open_price * 100, 2)

                volume_spike = vol > 1.5 * avg_vol
                uptrend = price > ema20 and price > ema50
                rsi_zone = 45 <= rsi <= 65

                signal = "✅ Swing Setup" if uptrend and volume_spike and rsi_zone else "⏳ Watching"

                df_latest = yf.download(ticker, period="1d", interval="1m")
                last_price = float(df_latest['Close'].iloc[-1]) if not df_latest.empty else None

                price_change_pct = round((price - open_price) / open_price * 100, 2)
                if price_change_pct > 0:
                    formatted_change = f"🟢 +{price_change_pct:.2f}%"
                elif price_change_pct < 0:
                    formatted_change = f"🔻 {price_change_pct:.2f}%"
                else:
                    formatted_change = f"➖ 0.00%"


                # Determine EMA Trend Bias
                if price > ema20 and ema20 > ema50:
                    ema_trend = "🟢 Strong Uptrend"
                elif price < ema20 and ema20 < ema50:
                    ema_trend = "🔻 Strong Downtrend"
                elif price > ema20 and price < ema50:
                    ema_trend = "🟡 Weak Pullback"
                else:
                    ema_trend = "⏸️ Sideways/Unclear"

                full_data.append({
                    "Stock": ticker,
                    "Price": f"₹{last_price:,.2f}" if last_price else "N/A",
                    "% Change": formatted_change,
                    "EMA20": round(ema20, 2),
                    "EMA 50": round(ema50, 2),
                    "RSI": round(rsi, 2),
                    "Volume": f"{int(vol):,}",
                    "10 D Avg Volume": f"{int(avg_vol):,}",
                    "Volume Spike (%)": round((vol / avg_vol - 1) * 100, 1),
                    "EMA Difference": round(ema20 - ema50, 2),
                    "EMA Difference(%)": round(((ema20 - ema50) / price) * 100, 2),
                    "Swing Signal": signal,
                    "EMA Trend": ema_trend  # ✅ New column added here
                })



            except Exception as e:
                full_data.append({
                    "Stock": ticker,
                    "Price": "-",
                    "% Change": "-",
                    "EMA20": "-",
                    "EMA 50": "-",
                    "RSI": "-",
                    "Volume": "-",
                    "10 D Avg Volume": "-",
                    "Volume Spike (%)": "-",
                    "EMA Difference": "-",
                    "EMA Difference(%)": "-",
                    "Swing Signal": f"⚠️ {str(e).split(':')[0]}"
                })

            progress_bar.progress((i + 1) / len(nifty_stocks))

    df_result = pd.DataFrame(full_data)
    st.dataframe(df_result, use_container_width=True)


show_intraday_stock_summary()
show_daily_stock_summary()

