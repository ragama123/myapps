import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go
from datetime import datetime, timedelta

def main():

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


    def show_intraday_stock_summary():
        #st.markdown("---")
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
                            "ONGC.NS", "HINDPETRO.NS", "ACC.NS", "AMBUJACEM.NS", "DLF.NS"]

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
                        "30m Signal": multi_signals.get("30m", "N/A"),
                        "1h Signal": multi_signals.get("1h", "N/A"),
                        "4h Signal": multi_signals.get("4h", "N/A"),
                        "1d Signal": multi_signals.get("1d", "N/A"),
                        "1w Signal": multi_signals.get("1w", "N/A"),
                        "1mo Signal": multi_signals.get("1mo", "N/A"),
                        "3mo Signal": multi_signals.get("3mo", "N/A"),
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


    show_intraday_stock_summary()

if __name__ == "__main__":
     main()
