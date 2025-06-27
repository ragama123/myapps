import streamlit as st
from intraday_stock_call import main as intraday_stock_call
from intraday_stock_summary import main as intraday_stock_summary
from swing_trade_screener import main as swing_trade_screener
from Stock_delivery_analysis import main as Stock_delivery_analysis

st.set_page_config(
    page_title="Stock Screener - Home 📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

#from data_query_engine import main as data_query_engine

# Custom CSS for a better-looking UI
st.markdown(
    """
    <style>
    .sidebar .sidebar-content {
        background: linear-gradient(to bottom, #5b86e5, #36d1dc);
        color: white;
    }
    .css-1aumxhk {
        background-color: #ffffff;
        border-radius: 10px;
        box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
        padding: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Your logo file path
#logo_path = 'C:/Users/sinmanis/OneDrive - HP Inc/Python/Streamlit/HP Analysis/logo.png'

def welcome_screen():
    st.title("Welcome to the Stock Screener Models App")
    # Display your logo
    #st.image(logo_path, width=200)
    st.write("This app is your all-in-one command center for real-time trading insights and swing trade analysis. It combines intelligent technical indicators, price trends, and volume dynamics to help you make smarter trading decisions—whether you're trading intraday or planning for the next breakout move.")

# 🔧 Page Configuration


def main():
    # Sidebar navigation
    st.sidebar.title("Stock Screener Models")
    app_selection = st.sidebar.radio(" ", ["Intraday Stock calls", "Intraday Stocks Summary", "Swing Trade Screener (Daily Refresh)","Stock Delivery Analysis (Daily Refresh)"])

    if app_selection == "Intraday Stock calls":
        intraday_stock_call()
    elif app_selection == "Intraday Stocks Summary":
        intraday_stock_summary()
    elif app_selection == "Swing Trade Screener (Daily Refresh)":
        swing_trade_screener()
    elif app_selection == "Stock Delivery Analysis (Daily Refresh)":
        Stock_delivery_analysis()
    
if __name__ == "__main__":
    main()
