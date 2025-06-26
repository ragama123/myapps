import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import requests
from io import StringIO

# ✅ Set page config FIRST
st.set_page_config(page_title="5-Day Stock Delivery Analysis", layout="wide")

# ✅ Rest of your script starts here...
st.title("📊 Last 5 Trading Days Stock Delivery & Trend Analysis")

# === CONFIG ===
GITHUB_BASE = "https://raw.githubusercontent.com/ragama123/stock-daily-data/main"
DAYS_TO_FETCH = 5  # Number of recent days to pull

# === Generate URLs for Last N Days ===
def build_github_urls(base_url, days=5):
    urls = []
    today = datetime.today()
    for i in range(days + 7):  # buffer for weekends/holidays
        date = today - timedelta(days=i)
        formatted = date.strftime("%d%m%Y")
        filename = f"sec_bhavdata_full_{formatted}.csv"
        url = f"{base_url}/{filename}"
        urls.append(url)
        if len(urls) >= days:
            break
    return urls

# === Load from GitHub ===
def load_recent_csvs(urls, limit=5):
    data = []
    count = 0
    for url in urls:
        try:
            r = requests.get(url)
            r.raise_for_status()
            df = pd.read_csv(StringIO(r.text))
            df["SOURCE_FILE"] = url.split("/")[-1]
            data.append(df)
            count += 1
            if count >= limit:
                break
        except Exception as e:
            continue  # skip missing files
    return pd.concat(data, ignore_index=True) if data else pd.DataFrame()

# === Example Usage in Streamlit App ===
with st.spinner("Loading last 5 available trading days..."):
    urls = build_github_urls(GITHUB_BASE, days=DAYS_TO_FETCH * 2)
    df = load_recent_csvs(urls, limit=DAYS_TO_FETCH)

if df.empty:
    st.error("❌ No data files could be loaded from GitHub.")
else:
    st.success(f"✅ Loaded {DAYS_TO_FETCH} recent data files from GitHub.")
    #st.dataframe(df.head())

WATCHLIST = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO",
    "BAJFINANCE", "BAJAJFINSV", "BEL", "BHARTIARTL", "CIPLA", "COALINDIA", "DRREDDY",
    "EICHERMOT", "ETERNAL", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO",
    "HINDALCO", "HINDUNILVR", "ICICIBANK", "ITC", "INDUSINDBK", "INFY", "JSWSTEEL",
    "JIOFIN", "KOTAKBANK", "LT", "M&M", "MARUTI", "NTPC", "NESTLEIND", "ONGC",
    "POWERGRID", "RELIANCE", "SBILIFE", "SHRIRAMFIN", "SBIN", "SUNPHARMA", "TCS",
    "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TECHM", "TITAN", "TRENT", "ULTRACEMCO",
    "WIPRO", "VEDL", "LICI", "NMDC", "CDSL", "BSE", "CANBK", "RVNL", "MCX", "ADANIGREEN",
    "ADANIPOWER", "ADANIENSOL", "VBL", "GMDCLTD", "INDIGO", "IRCTC", "MAZDOCK",
    "COCHINSHIP", "GESHIP", "GRSE", "YESBANK", "POLYCAB", "LTIM", "IOC", "BPCL",
    "HINDPETRO", "ACC", "AMBUJACEM"
]


if st.button("🔍 Analyze Last 5 Days"):
    st.session_state.analyzed = True

if "analyzed" not in st.session_state:
    st.session_state.analyzed = False

if st.session_state.analyzed:
    # your code here

    # ✅ Use the df already loaded from GitHub earlier
    if df.empty:
        st.error("🚫 No CSV files found from GitHub.")
    else:
        # Proceed with processing `df`
        # 👉 You can start from: df.columns = df.columns.str.strip().str.upper()

        #df = pd.concat(all_data, ignore_index=True)
        df.columns = df.columns.str.strip().str.upper()
        df = df.rename(columns={"PREV_C": "PREV_CLOSE", "CLOSE_": "CLOSE_PRICE", "DELIV_%": "DELIV_PER"})
        df["SYMBOL"] = df["SYMBOL"].astype(str).str.strip().str.upper()
        df["SERIES"] = df["SERIES"].astype(str).str.strip().str.upper()
        df["DATE1"] = pd.to_datetime(df["DATE1"], errors="coerce")

        df = df[(df["SERIES"] == "EQ") & (df["SYMBOL"].isin(WATCHLIST))]
        df["% CHANGE"] = ((df["CLOSE_PRICE"] - df["PREV_CLOSE"]) / df["PREV_CLOSE"]) * 100
        df["DELIV_PER"] = pd.to_numeric(df["DELIV_PER"], errors="coerce")
        df["% CHANGE"] = pd.to_numeric(df["% CHANGE"], errors="coerce")

        # Get last 5 available days for each stock
        df = df.sort_values(["SYMBOL", "DATE1"])
        df = df.groupby("SYMBOL", group_keys=False).tail(5)

        if df.empty:
            st.warning("⚠️ No data available for last 5 trading days.")
        else:
            latest = df.sort_values("DATE1").groupby("SYMBOL").tail(1)[["SYMBOL", "% CHANGE", "DELIV_PER"]]
            latest = latest.rename(columns={"% CHANGE": "LATEST % CHANGE", "DELIV_PER": "LATEST DELIVERY %"})

            summary = df.groupby("SYMBOL").agg({
                "% CHANGE": "mean",
                "DELIV_PER": "mean",
                "DATE1": "count"
            }).reset_index().rename(columns={"DATE1": "OBS_DAYS"})

            summary["SIGNAL"] = summary.apply(
                lambda row: "📈 Bullish" if row["DELIV_PER"] > 60 and row["% CHANGE"] > 1
                else "😐 Neutral" if row["DELIV_PER"] >= 50 else "⚠️ Caution", axis=1
            )
            summary = pd.merge(summary, latest, on="SYMBOL", how="left")
            summary[["CLOSE_PRICE", "% CHANGE", "DELIV_PER", "LATEST % CHANGE", "LATEST DELIVERY %"]] = summary[
                ["CLOSE_PRICE", "% CHANGE", "DELIV_PER", "LATEST % CHANGE", "LATEST DELIVERY %"]
            ].round(2)

            # Display Summary
            st.subheader("📌 Signal Summary (Top by Avg % Change)")
            st.dataframe(summary.sort_values(by="% CHANGE", ascending=False), use_container_width=True)

            # Chart Section
            st.subheader("📈 Stock Trend View")
            selected = st.selectbox("Pick a stock", sorted(df["SYMBOL"].unique()))
            stock_df = df[df["SYMBOL"] == selected].sort_values("DATE1")

            fig, ax1 = plt.subplots(figsize=(6, 3.5))
            ax1.plot(stock_df["DATE1"], stock_df["% CHANGE"], marker='o', color='tab:blue', label="% Change", linewidth=2)
            ax1.set_ylabel("% Change", color='tab:blue')
            ax1.tick_params(axis='y', labelcolor='tab:blue')
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
            ax1.set_xticks(stock_df["DATE1"])
            plt.setp(ax1.get_xticklabels(), rotation=45, ha="right")

            ax2 = ax1.twinx()
            ax2.fill_between(stock_df["DATE1"], stock_df["DELIV_PER"], color='tab:orange', alpha=0.2)
            ax2.plot(stock_df["DATE1"], stock_df["DELIV_PER"], marker='s', color='tab:orange', label="Delivery %", linewidth=2)
            ax2.set_ylabel("Delivery %", color='tab:orange')
            ax2.tick_params(axis='y', labelcolor='tab:orange')

            fig.suptitle(f"{selected} – % Change vs Delivery % (Last 5 Trading Days)", fontsize=11, weight='bold')

            # Recommended for compact layout:
            fig.legend(loc="lower center", bbox_to_anchor=(0.5, -0.07), ncol=2, fontsize=8)

            fig.tight_layout(pad=1)
            st.pyplot(fig)

    # At the end of your existing Streamlit app, add this section:

            st.subheader(f"📉 Price Action & Volume Analysis – {selected}")
            #selected_pa_stock = st.selectbox("🔎 Select Stock for Price Action Insight", sorted(df["SYMBOL"].unique()), key="pa")
            pa_df = df[df["SYMBOL"] == selected].sort_values("DATE1")
            pa_df["DATE1"] = pa_df["DATE1"].dt.strftime("%d-%B-%Y (%A)")
            
            if not pa_df.empty:
                pa_df["VOLATILITY"] = pa_df["HIGH_PRICE"] - pa_df["LOW_PRICE"]
                avg_volatility = pa_df["VOLATILITY"].mean()
                avg_volume = pa_df["TTL_TRD_QNTY"].mean() 

                pa_df["CANDLE"] = pa_df.apply(
                    lambda x: "Bullish" if x["CLOSE_PRICE"] > x["OPEN_PRICE"]
                    else "Bearish" if x["CLOSE_PRICE"] < x["OPEN_PRICE"]
                    else "Doji",
                    axis=1
                )

                pa_df["VOLUME_SPIKE"] = pa_df["TTL_TRD_QNTY"] > 1.2 * avg_volume

                def interpret(row):
                    if row["CANDLE"] == "Bullish" and row["DELIV_PER"] > 50:
                        return "Strong Bullish"
                    elif row["CANDLE"] == "Bullish" and row["DELIV_PER"] < 30:
                        return "Speculative Rally"
                    elif row["CANDLE"] == "Bearish" and row["DELIV_PER"] > 50:
                        return "Possible Distribution"
                    elif row["DELIV_PER"] > 60 and row["VOLUME_SPIKE"]:
                        return "Institutional Activity"
                    else:
                        return "Neutral"

                pa_df["INTERPRETATION"] = pa_df.apply(interpret, axis=1)

                display_cols = ["DATE1", "CANDLE", "VOLATILITY", "VOLUME_SPIKE", "DELIV_PER", "INTERPRETATION"]
                st.dataframe(pa_df[display_cols].sort_values("DATE1"), use_container_width=True)
            else:
                st.warning("No data available for this stock.")

            # === Final Signal based on 5-day behavior ===
            bullish_days = sum(pa_df["CANDLE"] == "Bullish")
            bearish_days = sum(pa_df["CANDLE"] == "Bearish")
            avg_change = pa_df["% CHANGE"].mean()
            avg_delivery = pa_df["DELIV_PER"].mean()

            if bullish_days >= 3 and avg_change > 1 and avg_delivery > 50:
                final_call = "📈 Bullish"
                reason = f"{bullish_days}/5 Bullish candles, Avg % Change = {avg_change:.2f}%, Avg Delivery = {avg_delivery:.2f}%"
            elif bearish_days >= 3 and avg_change < -1 and avg_delivery < 40:
                final_call = "📉 Bearish"
                reason = f"{bearish_days}/5 Bearish candles, Avg % Change = {avg_change:.2f}%, Avg Delivery = {avg_delivery:.2f}%"
            else:
                final_call = "😐 Neutral"
                reason = f"Mixed signals – Avg % Change = {avg_change:.2f}%, Avg Delivery = {avg_delivery:.2f}%"

            st.markdown("---")
            st.markdown(f"### 🧾 Final 5-Day Call for **{selected}**: {final_call}")
            st.caption(f"📌 {reason}")

        

