import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from datetime import datetime, timedelta

# Predefined list of stock codes with company names
stock_list = {
    "^NSEI": "NIFTY 50",
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
    "Or type a custom Stock Code (e.g. INFY.NS, LICI.NS, CDSL.NS, LTIM.NS...etc)",
    value=st.session_state.custom_stock,
    key="custom_stock",
    on_change=clear_selected_stock
)

# Logic to update stock code based on user interaction
if custom_stock:
    stock_code = custom_stock
else:
    stock_code = selected_stock if selected_stock != "Choose from here" else None

# Display the selected or custom stock code
if stock_code and stock_code != "Choose from here":
    company_name = stock_list.get(stock_code, "")
    st.write(f"Selected Stock Code: {stock_code} {f'({company_name})' if company_name else ''}")

# Input widgets for date range
start_date = st.date_input("Start Date:", start_date_default)
end_date = st.date_input("End Date:", end_date_default)

# Fetch data if stock_code is available
if stock_code:
    data = yf.download(stock_code, start=start_date, end=end_date)

    # Check if data is available
    if not data.empty:
        # Get current stock price
        ticker = yf.Ticker(stock_code)
        current_price = ticker.history(period="1d")["Close"]
        if not current_price.empty:
            current_price = current_price.iloc[-1]
            current_price_str = f"{current_price:.2f}"
        else:
            current_price_str = "No data available"
        
        # Display current stock price above the chart
        st.subheader(f"Current Stock Price {f'({stock_code})' if stock_code else ''}: {current_price_str}")
    else:
        st.error("No data available for the provided stock code and date range. Please check the inputs and try again.")
        st.stop()
else:
    st.info("Please select or enter a stock code.")
    st.stop()

# Calculate RSI
def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=window, min_periods=1).mean()
    avg_loss = loss.rolling(window=window, min_periods=1).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

data["RSI"] = calculate_rsi(data)

# Calculate MACD
def calculate_macd(data, slow=26, fast=12, signal=9):
    exp1 = data['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = data['Close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    macd_hist = macd - signal_line
    return macd, signal_line, macd_hist

data["MACD"], data["MACD_Signal"], data["MACD_Hist"] = calculate_macd(data)

# Calculate Bollinger Bands
def calculate_bollinger_bands(data, window=20):
    sma = data['Close'].rolling(window=window).mean()
    std = data['Close'].rolling(window=window).std()
    upper_band = sma + (std * 2)
    lower_band = sma - (std * 2)
    return sma, upper_band, lower_band

data['SMA'], data['Upper_Band'], data['Lower_Band'] = calculate_bollinger_bands(data)

# Calculate Stochastic Oscillator
def calculate_stochastic(data, window=14, smooth_window=3):
    lowest_low = data['Low'].rolling(window=window).min()
    highest_high = data['High'].rolling(window=window).max()
    stoch_k = 100 * ((data['Close'] - lowest_low) / (highest_high - lowest_low))
    stoch_d = stoch_k.rolling(window=smooth_window).mean()
    return stoch_k, stoch_d

data['Stoch_K'], data['Stoch_D'] = calculate_stochastic(data)

# Calculate Simple Moving Average (SMA)
def calculate_sma(data, window=50):
    return data['Close'].rolling(window=window).mean()

data['SMA_50'] = calculate_sma(data, 50)
data['SMA_200'] = calculate_sma(data, 200)

# Calculate Exponential Moving Average (EMA)
def calculate_ema(data, window=50):
    return data['Close'].ewm(span=window, adjust=False).mean()

data['EMA_50'] = calculate_ema(data, 50)
data['EMA_200'] = calculate_ema(data, 200)

# CSS for styling
st.markdown("""
    <style>
    .chart-container {
        border: 1px solid #ccc;
        padding: 10px;
        margin: 10px;
        border-radius: 5px;
    }
    .chart-title {
        text-align: center;
        font-size: 20px;
        margin-bottom: 10px;
        background-color: #f0f0f0;  /* Light grey background */
        padding: 10px;
        border-radius: 5px;
    }
    .chart-plot {
        height: 400px;
    }
    .analysis-table {
        width: 100%;
        border-collapse: collapse;
    }
    .analysis-table th, .analysis-table td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: center;
    }
    .analysis-table th {
        background-color: #f2f2f2;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# Plot charts side by side
st.subheader("Charts")

# Use columns to display charts side by side
col1, col2 = st.columns(2)

with col1:
    st.markdown("<div class='chart-container'><div class='chart-title'>Candlestick Chart</div>", unsafe_allow_html=True)
    fig1 = go.Figure(data=[go.Candlestick(x=data.index, open=data["Open"], high=data["High"], low=data["Low"], close=data["Close"])])
    fig1.update_layout(height=400)
    st.plotly_chart(fig1)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='chart-container'><div class='chart-title'>RSI Chart</div>", unsafe_allow_html=True)
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=data.index, y=data["RSI"], name="RSI"))
    fig2.add_trace(go.Scatter(x=data.index, y=[30]*len(data), name="RSI Buy Signal", line=dict(dash='dash')))
    fig2.add_trace(go.Scatter(x=data.index, y=[70]*len(data), name="RSI Sell Signal", line=dict(dash='dash')))
    fig2.update_layout(height=400)
    st.plotly_chart(fig2)
    st.markdown("</div>", unsafe_allow_html=True)

col3, col4 = st.columns(2)

with col3:
    st.markdown("<div class='chart-container'><div class='chart-title'>MACD Chart</div>", unsafe_allow_html=True)
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=data.index, y=data["MACD"], name="MACD"))
    fig3.add_trace(go.Scatter(x=data.index, y=data["MACD_Signal"], name="MACD Signal"))
    fig3.add_trace(go.Bar(x=data.index, y=data["MACD_Hist"], name="MACD Hist"))
    fig3.update_layout(height=400)
    st.plotly_chart(fig3)
    st.markdown("</div>", unsafe_allow_html=True)

with col4:
    st.markdown("<div class='chart-container'><div class='chart-title'>Bollinger Bands Chart</div>", unsafe_allow_html=True)
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(x=data.index, y=data["Close"], name="Close"))
    fig4.add_trace(go.Scatter(x=data.index, y=data["SMA"], name="SMA"))
    fig4.add_trace(go.Scatter(x=data.index, y=data["Upper_Band"], name="Upper Band"))
    fig4.add_trace(go.Scatter(x=data.index, y=data["Lower_Band"], name="Lower Band"))
    fig4.update_layout(height=400)
    st.plotly_chart(fig4)
    st.markdown("</div>", unsafe_allow_html=True)

col5, col6 = st.columns(2)

with col5:
    st.markdown("<div class='chart-container'><div class='chart-title'>Stochastic Oscillator Chart</div>", unsafe_allow_html=True)
    fig5 = go.Figure()
    fig5.add_trace(go.Scatter(x=data.index, y=data["Stoch_K"], name="Stochastic %K"))
    fig5.add_trace(go.Scatter(x=data.index, y=data["Stoch_D"], name="Stochastic %D"))
    fig5.add_trace(go.Scatter(x=data.index, y=[20]*len(data), name="Stochastic Buy Signal", line=dict(dash='dash')))
    fig5.add_trace(go.Scatter(x=data.index, y=[80]*len(data), name="Stochastic Sell Signal", line=dict(dash='dash')))
    fig5.update_layout(height=400)
    st.plotly_chart(fig5)
    st.markdown("</div>", unsafe_allow_html=True)

with col6:
    st.markdown("<div class='chart-container'><div class='chart-title'>SMA and EMA Chart</div>", unsafe_allow_html=True)
    fig6 = go.Figure()
    fig6.add_trace(go.Scatter(x=data.index, y=data["Close"], name="Close"))
    fig6.add_trace(go.Scatter(x=data.index, y=data["SMA_50"], name="SMA 50"))
    fig6.add_trace(go.Scatter(x=data.index, y=data["SMA_200"], name="SMA 200"))
    fig6.add_trace(go.Scatter(x=data.index, y=data["EMA_50"], name="EMA 50"))
    fig6.add_trace(go.Scatter(x=data.index, y=data["EMA_200"], name="EMA 200"))
    fig6.update_layout(height=400)
    st.plotly_chart(fig6)
    st.markdown("</div>", unsafe_allow_html=True)

# Display analysis
st.subheader("Analysis")
st.write(f"Selected Stock Code: {stock_code} {f'({company_name})' if company_name else ''}")

# RSI and MACD signals
rsi_signal = "No Signal"
macd_signal = "No Signal"
bollinger_signal = "No Signal"
stochastic_signal = "No Signal"
ema_signal = "No Signal"

if data["RSI"].iloc[-1] < 30 and data["MACD"].iloc[-1] > data["MACD_Signal"].iloc[-1]:
    rsi_signal = "Buy Signal"
    macd_signal = "Buy Signal"
elif data["RSI"].iloc[-1] > 70 and data["MACD"].iloc[-1] < data["MACD_Signal"].iloc[-1]:
    rsi_signal = "Sell Signal"
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
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>RSI and MACD</td>
            <td style='color:{};'>{}</td>
        </tr>
        <tr>
            <td>Bollinger Bands</td>
            <td style='color:{};'>{}</td>
        </tr>
        <tr>
            <td>Stochastic Oscillator</td>
            <td style='color:{};'>{}</td>
        </tr>
        <tr>
            <td>SMA</td>
            <td style='color:{};'>{}</td>
        </tr>
        <tr>
            <td>EMA</td>
            <td style='color:{};'>{}</td>
        </tr>
    </tbody>
</table>
""".format(
    get_signal_color(rsi_signal + " and " + macd_signal), rsi_signal + " and " + macd_signal,
    get_signal_color(bollinger_signal), bollinger_signal,
    get_signal_color(stochastic_signal), stochastic_signal,
    get_signal_color(sma_signal), sma_signal,
    get_signal_color(ema_signal), ema_signal
), unsafe_allow_html=True)

# Summary of signals
st.subheader("Summary")
buy_signals = [rsi_signal, macd_signal, bollinger_signal, stochastic_signal, ema_signal].count("Buy Signal")
sell_signals = [rsi_signal, macd_signal, bollinger_signal, stochastic_signal, ema_signal].count("Sell Signal")

if buy_signals > sell_signals:
    st.markdown("<h2 style='color:green'>Overall Signal: Buy</h2>", unsafe_allow_html=True)
elif sell_signals > buy_signals:
    st.markdown("<h2 style='color:red'>Overall Signal: Sell</h2>", unsafe_allow_html=True)
else:
    st.markdown("<h2 style='color:grey'>Overall Signal: No clear direction</h2>", unsafe_allow_html=True)
