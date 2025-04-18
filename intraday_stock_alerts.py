import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.markdown("<h3 style='font-size:35px; color:#333;'>📈 Intraday Trading Buy/Sell Signal</h3>", unsafe_allow_html=True)

# --- Sidebar Inputs ---
st.sidebar.markdown("## Select or Enter a Stock")

# --- Stock Label to Actual Mapping
stock_display_to_actual = {
    "^NSEI": "^NSEI",
    "BSE": "BSE.NS",
    "KAYNES": "KAYNES.NS",
    "INFY": "INFY.NS",
    "CANBK": "CANBK.NS",
    "LICI": "LICI.NS",
    "MAZDOCK": "MAZDOCK.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "VEDL": "VEDL.NS"
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

        for interval in ['1m', '5m', '15m']:
            try:
                df = yf.download(ticker, period="1d", interval=interval)
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

                interval_signals[interval] = final_action

                table_data.append({
                    "Interval": interval,
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


# --- Part 4: Multi-Stock Consolidated Recommendation Table ---
# --- Final Summary Table for Predefined Stocks (Always Shown) ---
st.markdown("---")
st.markdown("<h3 style='font-size:30px; color:#333;'>📊 Stock Wise Summary</h3>", unsafe_allow_html=True)

predefined_stocks = ['^NSEI', 'BSE.NS', 'KAYNES.NS', 'INFY.NS', 'CANBK.NS', 'LICI.NS','ICICIBANK.NS','NMDC.NS','GMDCLTD.NS',
                     'RVNL.NS','INDUSINDBK.NS','MAZDOCK.NS', 'HDFCBANK.NS', 'VEDL.NS','HINDZINC.NS']
summary_rows = []

for ticker in predefined_stocks:
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

        summary_rows.append({
            "Stock": ticker,
            "1m Signal": multi_signals.get("1m", "N/A"),
            "5m Signal": multi_signals.get("5m", "N/A"),
            "15m Signal": multi_signals.get("15m", "N/A"),
            "Pattern": last_pattern,
            "Verdict": final_verdict
        })

    except Exception as e:
        summary_rows.append({
            "Stock": ticker,
            "1m Signal": "❌ Error",
            "5m Signal": "❌ Error",
            "15m Signal": "❌ Error",
            "Pattern": "Error",
            "Verdict": str(e)
        })

# ✅ Render the table — always visible
if summary_rows:
    summary_df = pd.DataFrame(summary_rows)
    st.dataframe(summary_df, use_container_width=True)
