import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from datetime import datetime, timedelta


# Google Analytics Tracking Code
st.markdown(
    """
   <!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-R6T7WXG8D8"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-R6T7WXG8D8');
</script>
    """, unsafe_allow_html=True
)

# Predefined list of stock codes with company names
stock_list = {
    "^NSEI": "NIFTY 50",
    "^NSEBANK": "^NIFTY BANK",
    "INFY.NS": "INFY",
    "LICI.NS": "LIC",
    "CDSL.NS": "CDSL",
    "LTIM.NS": "LTIM",
    "IRFC.NS": "IRFC",
    "BSE.NS": "BSE Ltd.",
    "RELIANCE.NS": "Reliance Industries Ltd.",
    "TCS.NS": "Tata Consultancy Services Ltd.",
    "RVNL.NS": "RVNL",
    "WIPRO.NS": "WIPRO",
    "HDFCBANK.NS": "HDFCBANK",
    "YESBANK.NS": "YESBANK",
    "ICICIBANK.NS": "ICICIBANK",
    "MAZDOCK.NS": "MAZDOCK"
}

# Title
st.title("Technical Analysis Tool")

# Calculate default start and end dates
end_date_default = datetime.today() + timedelta(days=1)
start_date_default = end_date_default - timedelta(days=91)

# Initialize session state variables
if "custom_stock" not in st.session_state:
    st.session_state.custom_stock = ""
if "selected_stock" not in st.session_state:
    st.session_state.selected_stock = "Choose from here"

# Callback to clear custom stock when dropdown is used
def clear_custom_stock():
    st.session_state.custom_stock = ""

# Callback to clear selected stock when custom stock is typed
def clear_selected_stock():
    st.session_state.selected_stock = "Choose from here"

# Combine selectbox and text input for stock code selection
selected_stock = st.selectbox(
    "Select Stock Code (or type a custom code below):",
    ["Choose from here"] + list(stock_list.keys()),
    index=0,
    key="selected_stock",
    on_change=clear_custom_stock
)

custom_stock = st.text_input(
    "Or type a custom Stock Code (e.g. INFY, LICI, CDSL, LTIM...etc)",
    value=st.session_state.custom_stock,
    key="custom_stock",
# Display analysis
st.subheader("Analysis")
st.write(f"Selected Stock Code: {stock_code} {f'({company_name})' if company_name else ''}")

# RSI and MACD signals
rsi_signal = "No Signal"
macd_signal = "No Signal"
bollinger_signal = "No Signal"
stochastic_signal = "No Signal"
ema_signal = "No Signal"
atr_signal = "No Signal"
obv_signal = "No Signal"

# Signal calculations
if data["RSI"].iloc[-1] < 30:
    rsi_signal = "Buy Signal"
elif data["RSI"].iloc[-1] > 70:
    rsi_signal = "Sell Signal"

if data["MACD"].iloc[-1] > data["MACD_Signal"].iloc[-1]:
    macd_signal = "Buy Signal"
elif data["MACD"].iloc[-1] < data["MACD_Signal"].iloc[-1]:
    macd_signal = "Sell Signal"

if data["Close"].iloc[-1] < data["Lower_Band"].iloc[-1]:
    bollinger_signal = "Buy Signal"
elif data["Close"].iloc[-1] > data["Upper_Band"].iloc[-1]:
    bollinger_signal = "Sell Signal"

if data["Stoch_K"].iloc[-1] < 20 and data["Stoch_D"].iloc[-1] < 20:
    stochastic_signal = "Buy Signal"
elif data["Stoch_K"].iloc[-1] > 80 and data["Stoch_D"].iloc[-1] > 80:
    stochastic_signal = "Sell Signal"

if data["SMA_50"].iloc[-1] > data["SMA_200"].iloc[-1]:
    sma_signal = "Golden Cross (Buy Signal)"
elif data["SMA_50"].iloc[-1] < data["SMA_200"].iloc[-1]:
    sma_signal = "Death Cross (Sell Signal)"
else:
    sma_signal = "No Signal"

if data["EMA_50"].iloc[-1] > data["EMA_200"].iloc[-1]:
    ema_signal = "Golden Cross (Buy Signal)"
elif data["EMA_50"].iloc[-1] < data["EMA_200"].iloc[-1]:
    ema_signal = "Death Cross (Sell Signal)"
else:
    ema_signal = "No Signal"

if data['ATR'].iloc[-1] > data['ATR'].mean():
    atr_signal = "High Volatility"
else:
    atr_signal = "Low Volatility"

if data['OBV'].iloc[-1] > data['OBV'].mean():
    obv_signal = "Positive Volume"
else:
    obv_signal = "Negative Volume"

# Function to get the color based on the signal
def get_signal_color(signal):
    if "Buy" in signal:
        return "green"
    elif "Sell" in signal:
        return "red"
    else:
        return "grey"

# Display analysis in a table with colored signals
st.markdown("""
<table class='analysis-table'>
    <thead>
        <tr>
            <th>Indicator</th>
            <th>Signal</th>
            <th>Explanation</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>RSI</td>
            <td style='color:{};'>{}</td>
            <td>RSI below 30 indicates a buy signal as the stock is considered oversold. RSI above 70 indicates a sell signal as the stock is considered overbought.</td>
        </tr>
        <tr>
            <td>MACD</td>
            <td style='color:{};'>{}</td>
            <td>MACD line crossing above the signal line indicates a buy signal. MACD line crossing below the signal line indicates a sell signal.</td>
        </tr>
        <tr>
            <td>Bollinger Bands</td>
            <td style='color:{};'>{}</td>
            <td>Price closing below the lower Bollinger Band indicates a buy signal. Price closing above the upper Bollinger Band indicates a sell signal.</td>
        </tr>
        <tr>
            <td>Stochastic Oscillator</td>
            <td style='color:{};'>{}</td>
            <td>%K line crossing above 20 indicates a buy signal. %K line crossing below 80 indicates a sell signal.</td>
        </tr>
        <tr>
            <td>SMA</td>
            <td style='color:{};'>{}</td>
            <td>Golden Cross (SMA 50 crossing above SMA 200) indicates a buy signal. Death Cross (SMA 50 crossing below SMA 200) indicates a sell signal.</td>
        </tr>
        <tr>
            <td>EMA</td>
            <td style='color:{};'>{}</td>
            <td>Golden Cross (EMA 50 crossing above EMA 200) indicates a buy signal. Death Cross (EMA 50 crossing below EMA 200) indicates a sell signal.</td>
        </tr>
        <tr>
            <td>ATR</td>
            <td style='color:{};'>{}</td>
            <td>High ATR indicates high volatility, suggesting potential large price movements. Low ATR indicates low volatility, suggesting potential smaller price movements.</td>
        </tr>
        <tr>
            <td>OBV</td>
            <td style='color:{};'>{}</td>
            <td>Positive OBV indicates that volume is higher on up-days compared to down-days, suggesting buying pressure. Negative OBV indicates selling pressure.</td>
        </tr>
    </tbody>
</table>
""".format(
    get_signal_color(rsi_signal), rsi_signal,
    get_signal_color(macd_signal), macd_signal,
    get_signal_color(bollinger_signal), bollinger_signal,
    get_signal_color(stochastic_signal), stochastic_signal,
    get_signal_color(sma_signal), sma_signal,
    get_signal_color(ema_signal), ema_signal,
    get_signal_color(atr_signal), atr_signal,
    get_signal_color(obv_signal), obv_signal
), unsafe_allow_html=True)

# Summary of signals
st.subheader("Summary")
buy_signals = [rsi_signal, macd_signal, bollinger_signal, stochastic_signal, sma_signal, ema_signal].count("Buy Signal")
sell_signals = [rsi_signal, macd_signal, bollinger_signal, stochastic_signal, sma_signal, ema_signal].count("Sell Signal")

if buy_signals > sell_signals:
    st.markdown("<h2 style='color:green'>Overall Signal: Buy</h2>", unsafe_allow_html=True)
elif sell_signals > buy_signals:
    st.markdown("<h2 style='color:red'>Overall Signal: Sell</h2>", unsafe_allow_html=True)
else:
    st.markdown("<h2 style='color:grey'>Overall Signal: No clear direction</h2>", unsafe_allow_html=True)
