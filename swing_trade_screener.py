import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go
from datetime import datetime, timedelta

def main():

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
                        "HINDPETRO.NS", "ACC.NS", "AMBUJACEM.NS", "DLF.NS"]

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

        
    show_daily_stock_summary()

    if __name__ == "__main__":
        main()
