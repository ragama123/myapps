import streamlit as st
from nsepython import nse_optionchain_scrapper
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

def main():

    st.set_page_config(page_title="📊 Option Chain Heatmap", layout="wide")
    st.title("📈 NSE Option Chain Heatmap & Analysis")

    # Stock selection
    symbol = st.selectbox("Select a stock:", ['NIFTY', 'ADANIENT', 'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK', 
                            'BAJAJ-AUTO', 'BAJFINANCE', 'BAJAJFINSV', 'BEL', 'BHARTIARTL', 'CIPLA', 
                            'COALINDIA', 'DRREDDY', 'EICHERMOT', 'ETERNAL', 'GRASIM', 'HCLTECH', 'HDFCBANK', 
                            'HDFCLIFE', 'HEROMOTOCO', 'HINDALCO', 'HINDUNILVR', 'ICICIBANK', 'ITC', 
                            'INDUSINDBK', 'INFY', 'JSWSTEEL', 'JIOFIN', 'KOTAKBANK', 'LT', 'M&M', 'MARUTI', 
                            'NTPC', 'NESTLEIND', 'ONGC', 'POWERGRID', 'RELIANCE', 'SBILIFE', 'SHRIRAMFIN', 
                            'SBIN', 'SUNPHARMA', 'TCS', 'TATACONSUM', 'TATAMOTORS', 'TATASTEEL', 'TECHM', 
                            'TITAN', 'TRENT', 'ULTRACEMCO', 'WIPRO', 'VEDL', 'LICI', 'NMDC', 'CDSL', 
                            'BSE','CANBK', 'RVNL', 'MCX', "ADANIGREEN", "ADANIPOWER", "ADANIENSOL", "VBL", "GMDCLTD", "INDIGO", 
                            "IRCTC", "MAZDOCK", "COCHINSHIP", "GESHIP", "GRSE", "YESBANK", "POLYCAB", "LTIM", "IOC", "BPCL", 
                            "HINDPETRO", "ACC", "AMBUJACEM", "DLF"])

    # Load option chain data
    try:
        data = nse_optionchain_scrapper(symbol)
        oc_data = pd.DataFrame(data["records"]["data"])
        underlying_value = data["records"]["underlyingValue"]

        # Expand CE and PE separately
        ce_data = pd.json_normalize(oc_data["CE"].dropna())
        pe_data = pd.json_normalize(oc_data["PE"].dropna())

        # Merge on strike price
        merged = pd.merge(ce_data, pe_data, on="strikePrice", suffixes=("_CE", "_PE"))
        merged["Near_Spot"] = abs(merged["strikePrice"] - underlying_value) <= 100

        st.markdown(
        f"📌 Underlying Value (Current Price): <span style='font-size:21px; color:#000;'>₹{underlying_value:.2f}</span>",
        unsafe_allow_html=True)

        st.subheader("📉 Put-Call OI Heatmap (Near Spot)")

        pivot_df = merged.pivot_table(
            index="strikePrice", 
            values=["openInterest_CE", "openInterest_PE"],
            aggfunc="sum"
        ).sort_index()

        # Plot heatmap
        fig, ax = plt.subplots(figsize=(6, 2))
        # Draw heatmap with smaller font
        sns.heatmap(
            pivot_df.T,
            cmap="YlGnBu",
            annot=True,
            fmt=".0f",
            cbar_kws={'label': 'Open Interest'},
            annot_kws={"size": 4},  # annotation font size
            ax=ax
        )

        # Reduce x/y tick label font size
        ax.set_xticklabels(ax.get_xticklabels(), rotation=25, ha='right', fontsize=5)
        ax.set_yticklabels(ax.get_yticklabels(), fontsize=5)

        # Reduce axis label (title) font size
        ax.set_xlabel("Strike Price", fontsize=5)
        ax.set_ylabel("Option Type", fontsize=5)

        # Reduce colorbar label font size
        cbar = ax.collections[0].colorbar
        cbar.ax.tick_params(labelsize=5)
        cbar.set_label("Open Interest", fontsize=5)

        # Reduce main title
        plt.title("Call vs Put OI by Strike", fontsize=5)

        # Render on Streamlit
        st.pyplot(fig)

        st.subheader("📈 Additional Analysis")
        merged["PCR"] = merged["openInterest_PE"] / merged["openInterest_CE"]

        # Identify max OI strikes
        max_ce_strike = merged.loc[merged['openInterest_CE'].idxmax(), 'strikePrice']
        max_pe_strike = merged.loc[merged['openInterest_PE'].idxmax(), 'strikePrice']

        # Mark zones
        def mark_zones(row):
            if row['strikePrice'] == max_ce_strike:
                return "📉 High Call Writing Zone"
            elif row['strikePrice'] == max_pe_strike:
                return "📈 High Put Writing Zone"
            return ""

        merged["Zone_Comment"] = merged.apply(mark_zones, axis=1)

        st.dataframe(merged[[
            "strikePrice", "openInterest_CE", "openInterest_PE", "PCR",
            "impliedVolatility_CE", "impliedVolatility_PE", "Near_Spot", "Zone_Comment"
        ]])

        # Final Call
        pcr_total = merged["openInterest_PE"].sum() / merged["openInterest_CE"].sum()
        if pcr_total > 1.2:
            signal = "🟢 Bullish Bias (High Put Writing)"
        elif pcr_total < 0.8:
            signal = "🔴 Bearish Bias (High Call Writing)"
        else:
            signal = "🟡 Neutral"

        st.markdown(f"### 📢 Final Market Sentiment for {symbol}: {signal} (PCR: {pcr_total:.2f})")

        # Explanation block
        with st.expander("ℹ️ What does this sentiment mean?"):
            st.markdown("""
            - 🟢 **Bullish Bias**: Indicates strong put writing, suggesting traders expect the price to rise or stay stable.  
            > 📈 You might look for buying opportunities or bullish strategies (e.g., Bull Call Spread).
            
            - 🔴 **Bearish Bias**: Indicates strong call writing, suggesting expectation of downward movement.  
            > 📉 Consider selling strategies or protection if you're holding long positions.
            
            - 🟡 **Neutral**: Balanced call and put OI, suggesting no clear directional bias.  
            > 🤝 Ideal for non-directional strategies like Iron Condor or waiting for confirmation.
            """)

    except Exception as e:
        st.error(f"❌ Error fetching data: {e}")

if __name__ == "__main__":
    main()