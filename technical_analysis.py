import gzip
import io
import json
from dataclasses import dataclass
from typing import List, Tuple, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots


# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Technical Analysis App - Live API",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Technical Analysis App - Live API")
st.caption("Support/Resistance zones + trendlines + market structure + volume analysis + buy/sell confirmation")

INDIA_TZ = "Asia/Kolkata"
INDIAN_DATE_FMT = "%d-%m-%Y"
INDIAN_DATETIME_FMT = "%d-%m-%Y %H:%M:%S"
INTRADAY_INTERVALS = {"1h", "30m", "15m", "5m"}
EMPTY_PIVOT_COLUMNS = ["Date", "Price", "Type"]

UPSTOX_BASE_URL = "https://api.upstox.com"
UPSTOX_HIST_V3 = f"{UPSTOX_BASE_URL}/v3/historical-candle"
UPSTOX_INTRADAY_V3 = f"{UPSTOX_BASE_URL}/v3/historical-candle/intraday"
UPSTOX_OHLC_V3 = f"{UPSTOX_BASE_URL}/v3/market-quote/ohlc"

# Option APIs
UPSTOX_OPTION_CONTRACTS_V2 = f"{UPSTOX_BASE_URL}/v2/option/contract"
UPSTOX_OPTION_CHAIN_V2 = f"{UPSTOX_BASE_URL}/v2/option/chain"

# Instruments lookup files
UPSTOX_INSTRUMENTS_NSE_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
UPSTOX_INSTRUMENTS_BSE_URL = "https://assets.upstox.com/market-quote/instruments/exchange/BSE.json.gz"


# ============================================================
# DATA CLASSES
# ============================================================
@dataclass
class Zone:
    zone_type: str
    center: float
    lower: float
    upper: float
    touches: int
    last_touch: pd.Timestamp


@dataclass
class Trendline:
    line_type: str
    x0: pd.Timestamp
    y0: float
    x1: pd.Timestamp
    y1: float
    slope_per_bar: float
    touches: int
    status: str


@dataclass
class MarketStructure:
    structure: str
    trend_bias: str
    latest_swing_high: float | None
    previous_swing_high: float | None
    latest_swing_low: float | None
    previous_swing_low: float | None
    summary: str


@dataclass
class TradeConfirmation:
    signal: str
    confidence: int
    buy_score: int
    sell_score: int
    quality: str
    reasons: List[str]
    breakout_confirmed: bool
    breakdown_confirmed: bool
    retest_buy_ready: bool
    retest_sell_ready: bool


# ============================================================
# TIME / DISPLAY HELPERS
# ============================================================
def to_india_time(ts):
    if pd.isna(ts):
        return pd.NaT

    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        return ts.tz_localize(INDIA_TZ)
    return ts.tz_convert(INDIA_TZ)


def format_indian_date(ts) -> str:
    ts = to_india_time(ts)
    if pd.isna(ts):
        return ""
    return ts.strftime(INDIAN_DATE_FMT)


def format_indian_datetime(ts) -> str:
    ts = to_india_time(ts)
    if pd.isna(ts):
        return ""
    return ts.strftime(INDIAN_DATETIME_FMT)


def format_display_timestamp(ts, interval: str) -> str:
    return format_indian_datetime(ts) if interval in INTRADAY_INTERVALS else format_indian_date(ts)


def now_ist() -> pd.Timestamp:
    return pd.Timestamp.now(tz=INDIA_TZ)


def is_market_hours_india() -> bool:
    current = now_ist()
    if current.weekday() >= 5:
        return False

    market_open = current.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = current.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= current <= market_close


# ============================================================
# UPSTOX AUTH / API HELPERS
# ============================================================
def get_auth_headers(access_token: str) -> dict:
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }


def interval_to_upstox(interval: str) -> tuple[str, str]:
    mapping = {
        "5m": ("minutes", "5"),
        "15m": ("minutes", "15"),
        "30m": ("minutes", "30"),
        "1h": ("hours", "1"),
        "1d": ("days", "1"),
    }
    if interval not in mapping:
        raise ValueError(f"Unsupported interval: {interval}")
    return mapping[interval]


def ohlc_quote_interval(interval: str) -> Optional[str]:
    mapping = {
        "1d": "1d",
        "30m": "I30",
    }
    return mapping.get(interval)


def period_to_from_date(period: str, to_date: pd.Timestamp) -> pd.Timestamp:
    if period == "5d":
        return to_date - pd.Timedelta(days=7)
    if period == "1mo":
        return to_date - pd.DateOffset(months=1)
    if period == "3mo":
        return to_date - pd.DateOffset(months=3)
    if period == "6mo":
        return to_date - pd.DateOffset(months=6)
    if period == "1y":
        return to_date - pd.DateOffset(years=1)
    if period == "2y":
        return to_date - pd.DateOffset(years=2)
    if period == "5y":
        return to_date - pd.DateOffset(years=5)
    raise ValueError(f"Unsupported period: {period}")


def validate_period_interval(period: str, interval: str) -> Optional[str]:
    if interval in {"5m", "15m"} and period not in {"5d", "1mo"}:
        return "For 5m and 15m, keep lookback to 5d or 1mo."
    if interval in {"30m", "1h"} and period not in {"5d", "1mo", "3mo"}:
        return "For 30m and 1h, keep lookback to 5d, 1mo, or 3mo."
    return None


# ============================================================
# UPSTOX INSTRUMENT LOOKUP
# ============================================================
@st.cache_data(show_spinner=False, ttl=60 * 60 * 6)
def load_upstox_instruments(exchange: str = "NSE") -> pd.DataFrame:
    exchange = exchange.upper().strip()
    if exchange == "NSE":
        url = UPSTOX_INSTRUMENTS_NSE_URL
    elif exchange == "BSE":
        url = UPSTOX_INSTRUMENTS_BSE_URL
    else:
        raise ValueError("Only NSE and BSE are supported in this lookup.")

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as gz:
        payload = json.loads(gz.read().decode("utf-8"))

    df = pd.DataFrame(payload)

    useful_cols = [
        "segment",
        "name",
        "exchange",
        "instrument_type",
        "instrument_key",
        "trading_symbol",
        "short_name",
        "isin",
        "underlying_symbol",
        "strike_price",
        "expiry",
    ]
    keep_cols = [c for c in useful_cols if c in df.columns]
    df = df[keep_cols].copy()

    for col in [
        "segment",
        "exchange",
        "instrument_type",
        "instrument_key",
        "trading_symbol",
        "short_name",
        "name",
        "underlying_symbol",
    ]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    if "expiry" in df.columns:
        df["expiry_dt"] = pd.to_datetime(df["expiry"], unit="ms", errors="coerce")
    else:
        df["expiry_dt"] = pd.NaT

    return df


def filter_instruments(
    instruments_df: pd.DataFrame,
    query: str,
    mode: str = "Equity",
    exchange: str = "NSE",
) -> pd.DataFrame:
    df = instruments_df.copy()
    exchange = exchange.upper().strip()

    if exchange == "NSE":
        if mode == "Equity":
            df = df[(df["segment"] == "NSE_EQ") & (df["instrument_type"] == "EQ")]
        elif mode == "Index":
            df = df[df["segment"] == "NSE_INDEX"]
        elif mode == "Futures":
            df = df[(df["segment"] == "NSE_FO") & (df["instrument_type"] == "FUT")]
        elif mode == "Call Option":
            df = df[(df["segment"] == "NSE_FO") & (df["instrument_type"] == "CE")]
        elif mode == "Put Option":
            df = df[(df["segment"] == "NSE_FO") & (df["instrument_type"] == "PE")]
    elif exchange == "BSE":
        if mode == "Equity":
            df = df[(df["segment"] == "BSE_EQ") & (df["instrument_type"] == "EQ")]
        elif mode == "Index":
            df = df[df["segment"] == "BSE_INDEX"]
        else:
            df = df[df["exchange"] == "BSE"]

    query = str(query).strip().upper()
    if not query:
        return df.head(100)

    mask = pd.Series(False, index=df.index)

    for col in ["trading_symbol", "short_name", "name", "underlying_symbol"]:
        if col in df.columns:
            mask = mask | df[col].astype(str).str.upper().str.contains(query, na=False)

    df = df[mask].copy()

    if "trading_symbol" in df.columns:
        df["exact_match"] = (df["trading_symbol"].str.upper() == query).astype(int)
    else:
        df["exact_match"] = 0

    sort_cols = ["exact_match"]
    ascending = [False]

    if "trading_symbol" in df.columns:
        sort_cols.append("trading_symbol")
        ascending.append(True)

    df = df.sort_values(sort_cols, ascending=ascending).reset_index(drop=True)
    return df.head(200)


def build_instrument_label(row: pd.Series) -> str:
    trading_symbol = row.get("trading_symbol", "")
    name = row.get("name", "")
    segment = row.get("segment", "")
    instrument_type = row.get("instrument_type", "")
    instrument_key = row.get("instrument_key", "")

    expiry_text = ""
    expiry_val = row.get("expiry_dt", pd.NaT)
    if pd.notna(expiry_val):
        expiry_text = f" | Expiry: {pd.Timestamp(expiry_val).strftime('%d-%m-%Y')}"

    strike_text = ""
    strike_val = row.get("strike_price", None)
    if strike_val is not None and str(strike_val).strip() not in {"", "nan", "None"}:
        try:
            strike = float(strike_val)
            if strike > 0:
                strike_text = f" | Strike: {strike}"
        except Exception:
            pass

    return f"{trading_symbol} | {name} | {segment} | {instrument_type}{expiry_text}{strike_text} | {instrument_key}"


# ============================================================
# UPSTOX MARKET DATA FETCH
# ============================================================
def parse_upstox_candles(candles: list) -> pd.DataFrame:
    """
    Expected candle format:
    [timestamp, open, high, low, close, volume, open_interest]
    """
    if not candles:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume", "Open Interest"])

    rows = []
    for c in candles:
        if len(c) < 6:
            continue
        rows.append(
            {
                "Date": pd.to_datetime(c[0]),
                "Open": float(c[1]),
                "High": float(c[2]),
                "Low": float(c[3]),
                "Close": float(c[4]),
                "Volume": float(c[5]) if c[5] is not None else 0.0,
                "Open Interest": float(c[6]) if len(c) > 6 and c[6] is not None else 0.0,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["Date"] = pd.to_datetime(df["Date"])
    df["Date"] = df["Date"].apply(to_india_time)
    df = df.sort_values("Date").drop_duplicates(subset=["Date"], keep="last")
    df = df.set_index("Date")
    return df


def fetch_historical_v3(access_token: str, instrument_key: str, period: str, interval: str) -> pd.DataFrame:
    unit, intv = interval_to_upstox(interval)

    to_date = now_ist().normalize()
    from_date = period_to_from_date(period, to_date)

    url = f"{UPSTOX_HIST_V3}/{instrument_key}/{unit}/{intv}/{to_date.strftime('%Y-%m-%d')}/{from_date.strftime('%Y-%m-%d')}"
    response = requests.get(url, headers=get_auth_headers(access_token), timeout=30)
    response.raise_for_status()

    payload = response.json()
    candles = payload.get("data", {}).get("candles", [])
    return parse_upstox_candles(candles)


def fetch_intraday_v3(access_token: str, instrument_key: str, interval: str) -> pd.DataFrame:
    unit, intv = interval_to_upstox(interval)

    url = f"{UPSTOX_INTRADAY_V3}/{instrument_key}/{unit}/{intv}"
    response = requests.get(url, headers=get_auth_headers(access_token), timeout=30)
    response.raise_for_status()

    payload = response.json()
    candles = payload.get("data", {}).get("candles", [])
    return parse_upstox_candles(candles)


def fetch_live_ohlc_v3(access_token: str, instrument_key: str, interval: str) -> pd.DataFrame:
    quote_int = ohlc_quote_interval(interval)
    if not quote_int:
        return pd.DataFrame()

    params = {
        "instrument_key": instrument_key,
        "interval": quote_int,
    }
    response = requests.get(UPSTOX_OHLC_V3, headers=get_auth_headers(access_token), params=params, timeout=30)
    response.raise_for_status()

    payload = response.json()
    data = payload.get("data", {})
    if not data:
        return pd.DataFrame()

    item = next(iter(data.values()))
    live = item.get("live_ohlc", {})
    if not live or "ts" not in live:
        return pd.DataFrame()

    ts = pd.to_datetime(int(live["ts"]), unit="ms", utc=True).tz_convert(INDIA_TZ)

    df = pd.DataFrame(
        [
            {
                "Date": ts,
                "Open": float(live.get("open", 0)),
                "High": float(live.get("high", 0)),
                "Low": float(live.get("low", 0)),
                "Close": float(live.get("close", 0)),
                "Volume": float(live.get("volume", 0)),
                "Open Interest": 0.0,
            }
        ]
    )
    return df.set_index("Date")


def load_upstox_data(access_token: str, instrument_key: str, period: str, interval: str, include_live: bool = True) -> pd.DataFrame:
    hist = fetch_historical_v3(access_token, instrument_key, period, interval)

    parts = [hist] if not hist.empty else []

    if include_live and is_market_hours_india():
        try:
            if interval in INTRADAY_INTERVALS:
                intraday = fetch_intraday_v3(access_token, instrument_key, interval)
                if not intraday.empty:
                    parts.append(intraday)
            elif interval == "1d":
                live_daily = fetch_live_ohlc_v3(access_token, instrument_key, interval)
                if not live_daily.empty:
                    parts.append(live_daily)
        except Exception:
            pass

    if not parts:
        return pd.DataFrame()

    df = pd.concat(parts)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df


# ============================================================
# OPTION CHAIN / OI / PCR
# ============================================================
def fetch_option_contracts_v2(access_token: str, instrument_key: str, expiry_date: str | None = None) -> pd.DataFrame:
    params = {"instrument_key": instrument_key}
    if expiry_date:
        params["expiry_date"] = expiry_date

    response = requests.get(
        UPSTOX_OPTION_CONTRACTS_V2,
        headers=get_auth_headers(access_token),
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    data = payload.get("data", [])
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    if "expiry" in df.columns:
        df["expiry"] = pd.to_datetime(df["expiry"], errors="coerce").dt.strftime("%Y-%m-%d")
    return df


def get_available_option_expiries(access_token: str, instrument_key: str) -> list[str]:
    df = fetch_option_contracts_v2(access_token, instrument_key)
    if df.empty or "expiry" not in df.columns:
        return []

    expiries = (
        df["expiry"]
        .dropna()
        .astype(str)
        .sort_values()
        .unique()
        .tolist()
    )
    return expiries


def fetch_option_chain_v2(access_token: str, instrument_key: str, expiry_date: str) -> pd.DataFrame:
    params = {
        "instrument_key": instrument_key,
        "expiry_date": expiry_date,
    }

    response = requests.get(
        UPSTOX_OPTION_CHAIN_V2,
        headers=get_auth_headers(access_token),
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    data = payload.get("data", [])
    if not data:
        return pd.DataFrame()

    rows = []
    for item in data:
        call_md = item.get("call_options", {}).get("market_data", {}) or {}
        put_md = item.get("put_options", {}).get("market_data", {}) or {}
        call_greeks = item.get("call_options", {}).get("option_greeks", {}) or {}
        put_greeks = item.get("put_options", {}).get("option_greeks", {}) or {}

        rows.append(
            {
                "Expiry": item.get("expiry"),
                "Strike": item.get("strike_price"),
                "Underlying Spot": item.get("underlying_spot_price"),
                "PCR": item.get("pcr"),

                "Call Instrument Key": item.get("call_options", {}).get("instrument_key"),
                "Call LTP": call_md.get("ltp"),
                "Call Volume": call_md.get("volume"),
                "Call OI": call_md.get("oi"),
                "Call Prev OI": call_md.get("prev_oi"),
                "Call Bid": call_md.get("bid_price"),
                "Call Ask": call_md.get("ask_price"),
                "Call IV": call_greeks.get("iv"),
                "Call Delta": call_greeks.get("delta"),

                "Put Instrument Key": item.get("put_options", {}).get("instrument_key"),
                "Put LTP": put_md.get("ltp"),
                "Put Volume": put_md.get("volume"),
                "Put OI": put_md.get("oi"),
                "Put Prev OI": put_md.get("prev_oi"),
                "Put Bid": put_md.get("bid_price"),
                "Put Ask": put_md.get("ask_price"),
                "Put IV": put_greeks.get("iv"),
                "Put Delta": put_greeks.get("delta"),
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Strike").reset_index(drop=True)
    return df


def compute_option_chain_summary(option_chain_df: pd.DataFrame) -> dict:
    if option_chain_df is None or option_chain_df.empty:
        return {
            "total_call_oi": np.nan,
            "total_put_oi": np.nan,
            "overall_pcr": np.nan,
            "spot_price": np.nan,
        }

    total_call_oi = pd.to_numeric(option_chain_df["Call OI"], errors="coerce").fillna(0).sum()
    total_put_oi = pd.to_numeric(option_chain_df["Put OI"], errors="coerce").fillna(0).sum()

    overall_pcr = np.nan
    if total_call_oi and total_call_oi != 0:
        overall_pcr = total_put_oi / total_call_oi

    spot_price = pd.to_numeric(option_chain_df["Underlying Spot"], errors="coerce").dropna()
    spot_price = spot_price.iloc[0] if not spot_price.empty else np.nan

    return {
        "total_call_oi": total_call_oi,
        "total_put_oi": total_put_oi,
        "overall_pcr": overall_pcr,
        "spot_price": spot_price,
    }


def interpret_pcr(overall_pcr: float) -> str:
    if pd.isna(overall_pcr):
        return "PCR unavailable"
    if overall_pcr > 1.0:
        return "Put-heavy positioning"
    if overall_pcr < 1.0:
        return "Call-heavy positioning"
    return "Balanced positioning"


# ============================================================
# INDICATORS
# ============================================================
def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    macd_hist = macd - macd_signal
    return macd, macd_signal, macd_hist


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift(1)).abs()
    low_close = (df["Low"] - df["Close"].shift(1)).abs()

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return atr


def compute_vwap(df: pd.DataFrame) -> pd.Series:
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3.0
    cum_tpv = (typical_price * df["Volume"]).cumsum()
    cum_vol = df["Volume"].replace(0, np.nan).cumsum()
    vwap = cum_tpv / cum_vol
    return vwap


# ============================================================
# ANALYSIS HELPERS
# ============================================================
@st.cache_data(show_spinner=False)
def compute_volume_metrics(df: pd.DataFrame, volume_ma_window: int) -> pd.DataFrame:
    out = df.copy()
    out["Vol_MA"] = out["Volume"].rolling(volume_ma_window, min_periods=1).mean()
    out["Vol_Ratio"] = np.where(out["Vol_MA"] > 0, out["Volume"] / out["Vol_MA"], np.nan)
    out["Price_Change_%"] = out["Close"].pct_change() * 100
    out["Candle_Range"] = out["High"] - out["Low"]
    out["Body_Size"] = (out["Close"] - out["Open"]).abs()

    out["RSI"] = compute_rsi(out["Close"], 14)
    out["MACD"], out["MACD_Signal"], out["MACD_Hist"] = compute_macd(out["Close"])
    out["ATR"] = compute_atr(out, 14)
    out["VWAP"] = compute_vwap(out)

    return out


def find_pivots(
    df: pd.DataFrame,
    left_bars: int = 3,
    right_bars: int = 3,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    highs = []
    lows = []

    if len(df) < (left_bars + right_bars + 1):
        return (
            pd.DataFrame(columns=EMPTY_PIVOT_COLUMNS),
            pd.DataFrame(columns=EMPTY_PIVOT_COLUMNS),
        )

    for i in range(left_bars, len(df) - right_bars):
        high_slice = df["High"].iloc[i - left_bars: i + right_bars + 1]
        low_slice = df["Low"].iloc[i - left_bars: i + right_bars + 1]
        cur_high = df["High"].iloc[i]
        cur_low = df["Low"].iloc[i]

        if cur_high == high_slice.max():
            highs.append({"Date": df.index[i], "Price": float(cur_high), "Type": "Resistance"})
        if cur_low == low_slice.min():
            lows.append({"Date": df.index[i], "Price": float(cur_low), "Type": "Support"})

    highs_df = pd.DataFrame(highs, columns=EMPTY_PIVOT_COLUMNS)
    lows_df = pd.DataFrame(lows, columns=EMPTY_PIVOT_COLUMNS)
    return highs_df, lows_df


def cluster_levels(
    pivots: pd.DataFrame,
    current_price: float,
    zone_width_pct: float,
    zone_type: str,
    min_touches: int,
) -> List[Zone]:
    if pivots is None or pivots.empty or "Price" not in pivots.columns or "Date" not in pivots.columns:
        return []

    working = pivots.sort_values("Price").reset_index(drop=True).copy()
    zones: List[Zone] = []

    band = current_price * zone_width_pct / 100.0
    if band <= 0:
        return []

    cluster_prices = [float(working.loc[0, "Price"])]
    cluster_dates = [pd.Timestamp(working.loc[0, "Date"])]

    for i in range(1, len(working)):
        price = float(working.loc[i, "Price"])
        date = pd.Timestamp(working.loc[i, "Date"])
        cluster_center = float(np.mean(cluster_prices))

        if abs(price - cluster_center) <= band:
            cluster_prices.append(price)
            cluster_dates.append(date)
        else:
            if len(cluster_prices) >= min_touches:
                center = float(np.mean(cluster_prices))
                zones.append(
                    Zone(
                        zone_type=zone_type,
                        center=center,
                        lower=center - band,
                        upper=center + band,
                        touches=len(cluster_prices),
                        last_touch=max(cluster_dates),
                    )
                )
            cluster_prices = [price]
            cluster_dates = [date]

    if len(cluster_prices) >= min_touches:
        center = float(np.mean(cluster_prices))
        zones.append(
            Zone(
                zone_type=zone_type,
                center=center,
                lower=center - band,
                upper=center + band,
                touches=len(cluster_prices),
                last_touch=max(cluster_dates),
            )
        )

    return zones


def detect_trendlines(
    df: pd.DataFrame,
    pivot_highs: pd.DataFrame,
    pivot_lows: pd.DataFrame,
    tolerance_pct: float = 1.0,
) -> List[Trendline]:
    trendlines: List[Trendline] = []
    index_lookup = {ts: i for i, ts in enumerate(df.index)}

    def _build(points: pd.DataFrame, line_type: str, direction: str):
        if points is None or len(points) < 2 or "Date" not in points.columns or "Price" not in points.columns:
            return None

        pts = points.sort_values("Date").copy()

        for i in range(len(pts) - 1, 0, -1):
            p2 = pts.iloc[i]
            p1 = pts.iloc[i - 1]
            y1, y2 = float(p1["Price"]), float(p2["Price"])

            if direction == "up" and y2 <= y1:
                continue
            if direction == "down" and y2 >= y1:
                continue

            x0 = pd.Timestamp(p1["Date"])
            x_mid = pd.Timestamp(p2["Date"])
            i0 = index_lookup.get(x0)
            i1 = index_lookup.get(x_mid)
            if i0 is None or i1 is None or i1 == i0:
                continue

            slope = (y2 - y1) / (i1 - i0)
            touches = 0

            for _, row in pts.iterrows():
                xi = index_lookup.get(pd.Timestamp(row["Date"]))
                if xi is None:
                    continue
                projected = y1 + slope * (xi - i0)
                diff_pct = abs(float(row["Price"]) - projected) / max(abs(projected), 1e-9) * 100
                if diff_pct <= tolerance_pct:
                    touches += 1

            last_idx = len(df) - 1
            projected_now = y1 + slope * (last_idx - i0)
            last_close = float(df["Close"].iloc[-1])

            if line_type == "Support Trendline":
                status = "Holding" if last_close >= projected_now * (1 - tolerance_pct / 100) else "Broken"
            else:
                status = "Holding" if last_close <= projected_now * (1 + tolerance_pct / 100) else "Broken"

            return Trendline(
                line_type=line_type,
                x0=x0,
                y0=y1,
                x1=df.index[-1],
                y1=float(projected_now),
                slope_per_bar=float(slope),
                touches=int(touches),
                status=status,
            )
        return None

    support_line = _build(pivot_lows, "Support Trendline", "up")
    resistance_line = _build(pivot_highs, "Resistance Trendline", "down")

    if support_line:
        trendlines.append(support_line)
    if resistance_line:
        trendlines.append(resistance_line)

    return trendlines


def detect_market_structure(pivot_highs: pd.DataFrame, pivot_lows: pd.DataFrame) -> MarketStructure:
    highs = pivot_highs.copy() if pivot_highs is not None else pd.DataFrame(columns=EMPTY_PIVOT_COLUMNS)
    lows = pivot_lows.copy() if pivot_lows is not None else pd.DataFrame(columns=EMPTY_PIVOT_COLUMNS)

    if "Date" not in highs.columns:
        highs = pd.DataFrame(columns=EMPTY_PIVOT_COLUMNS)
    if "Date" not in lows.columns:
        lows = pd.DataFrame(columns=EMPTY_PIVOT_COLUMNS)

    highs = highs.sort_values("Date").copy()
    lows = lows.sort_values("Date").copy()

    latest_h = prev_h = latest_l = prev_l = None

    if len(highs) >= 2:
        prev_h = float(highs.iloc[-2]["Price"])
        latest_h = float(highs.iloc[-1]["Price"])
    if len(lows) >= 2:
        prev_l = float(lows.iloc[-2]["Price"])
        latest_l = float(lows.iloc[-1]["Price"])

    if latest_h is not None and prev_h is not None and latest_l is not None and prev_l is not None:
        hh = latest_h > prev_h
        hl = latest_l > prev_l
        lh = latest_h < prev_h
        ll = latest_l < prev_l

        if hh and hl:
            return MarketStructure(
                "Higher Highs / Higher Lows",
                "Bullish",
                latest_h,
                prev_h,
                latest_l,
                prev_l,
                "Price structure remains bullish with both the latest swing high and swing low above the previous ones.",
            )
        if lh and ll:
            return MarketStructure(
                "Lower Highs / Lower Lows",
                "Bearish",
                latest_h,
                prev_h,
                latest_l,
                prev_l,
                "Price structure remains bearish with both the latest swing high and swing low below the previous ones.",
            )
        if hh and ll:
            return MarketStructure(
                "Expansion / Volatile Mixed Structure",
                "Neutral",
                latest_h,
                prev_h,
                latest_l,
                prev_l,
                "The chart is making a higher high but also a lower low, which suggests expansion and unstable structure.",
            )
        if lh and hl:
            return MarketStructure(
                "Compression / Range Structure",
                "Neutral",
                latest_h,
                prev_h,
                latest_l,
                prev_l,
                "The chart is making a lower high and a higher low, which suggests compression or range behaviour.",
            )

    return MarketStructure(
        "Insufficient swing structure",
        "Neutral",
        latest_h,
        prev_h,
        latest_l,
        prev_l,
        "There are not enough clear swing highs and swing lows yet to classify market structure confidently.",
    )


def summarize_volume(df: pd.DataFrame) -> dict:
    latest = df.iloc[-1]
    recent = df.tail(min(10, len(df))).copy()

    vol_ratio = float(latest["Vol_Ratio"]) if pd.notna(latest["Vol_Ratio"]) else np.nan
    price_change = float(latest["Price_Change_%"]) if pd.notna(latest["Price_Change_%"]) else 0.0

    if pd.isna(vol_ratio):
        latest_signal = "Not enough data"
    elif vol_ratio >= 2.0:
        latest_signal = "Very high volume spike"
    elif vol_ratio >= 1.5:
        latest_signal = "High volume"
    elif vol_ratio >= 1.1:
        latest_signal = "Slightly above average volume"
    elif vol_ratio >= 0.8:
        latest_signal = "Normal volume"
    else:
        latest_signal = "Below-average volume"

    avg_recent_vol_ratio = float(recent["Vol_Ratio"].replace([np.inf, -np.inf], np.nan).dropna().mean()) if len(recent) else np.nan
    recent_up_days = recent[recent["Close"] > recent["Open"]]
    recent_down_days = recent[recent["Close"] < recent["Open"]]

    up_vol = float(recent_up_days["Volume"].mean()) if not recent_up_days.empty else np.nan
    down_vol = float(recent_down_days["Volume"].mean()) if not recent_down_days.empty else np.nan

    if not np.isnan(up_vol) and not np.isnan(down_vol):
        if up_vol > down_vol * 1.15:
            pressure = "Buying pressure is stronger than selling pressure"
        elif down_vol > up_vol * 1.15:
            pressure = "Selling pressure is stronger than buying pressure"
        else:
            pressure = "Buying and selling pressure look balanced"
    else:
        pressure = "Not enough directional candles to compare buying vs selling pressure"

    if price_change > 0 and vol_ratio >= 1.2:
        conviction = "Price rose with volume support"
    elif price_change > 0 and vol_ratio < 1.0:
        conviction = "Price rose, but volume confirmation is weak"
    elif price_change < 0 and vol_ratio >= 1.2:
        conviction = "Price fell with strong participation"
    elif price_change < 0 and vol_ratio < 1.0:
        conviction = "Price fell on lighter participation"
    else:
        conviction = "Price and volume are neutral"

    return {
        "latest_signal": latest_signal,
        "pressure": pressure,
        "conviction": conviction,
        "latest_vol_ratio": vol_ratio,
        "avg_recent_vol_ratio": avg_recent_vol_ratio,
    }


def zones_to_dataframe(zones: List[Zone], current_price: float) -> pd.DataFrame:
    if not zones:
        return pd.DataFrame(columns=["Type", "Zone Range", "Center", "Touches", "Distance %", "Last Touch"])

    rows = []
    for z in zones:
        distance_pct = ((z.center - current_price) / current_price) * 100 if current_price else np.nan
        rows.append(
            {
                "Type": z.zone_type,
                "Zone Range": f"{z.lower:,.2f} - {z.upper:,.2f}",
                "Center": round(z.center, 2),
                "Touches": z.touches,
                "Distance %": round(distance_pct, 2),
                "Last Touch": format_indian_date(z.last_touch),
            }
        )

    out = pd.DataFrame(rows)
    return out.sort_values(["Type", "Center"], ascending=[True, True]).reset_index(drop=True)


def nearest_zones(zones: List[Zone], current_price: float) -> Tuple[Zone | None, Zone | None]:
    supports = [z for z in zones if z.zone_type == "Support" and z.center <= current_price]
    resistances = [z for z in zones if z.zone_type == "Resistance" and z.center >= current_price]

    nearest_support = max(supports, key=lambda x: x.center) if supports else None
    nearest_resistance = min(resistances, key=lambda x: x.center) if resistances else None
    return nearest_support, nearest_resistance


def get_volatility_label(price: float, atr: float) -> str:
    if pd.isna(price) or pd.isna(atr):
        return "N/A"

    if price <= 500:
        if atr < 1.5:
            return "Low Volatility"
        elif atr < 3:
            return "Medium Volatility"
        else:
            return "High Volatility"

    elif price <= 1500:
        if atr < 5:
            return "Low Volatility"
        elif atr < 15:
            return "Medium Volatility"
        else:
            return "High Volatility"

    else:
        if atr < 10:
            return "Low Volatility"
        elif atr < 30:
            return "Medium Volatility"
        else:
            return "High Volatility"


# ============================================================
# TRADE CONFIRMATION ENGINE
# ============================================================
def get_trendline_status(trendlines: List[Trendline], line_type: str) -> Optional[str]:
    for tl in trendlines:
        if tl.line_type == line_type:
            return tl.status
    return None


def get_projected_trendline_price(trendlines: List[Trendline], line_type: str) -> Optional[float]:
    for tl in trendlines:
        if tl.line_type == line_type:
            return tl.y1
    return None


def detect_breakout_breakdown(
    df: pd.DataFrame,
    nearest_support: Zone | None,
    nearest_resistance: Zone | None,
    breakout_buffer_pct: float = 0.15,
):
    if len(df) < 2:
        return False, False

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    breakout_confirmed = False
    breakdown_confirmed = False

    if nearest_resistance is not None:
        res_level = nearest_resistance.upper
        breakout_level = res_level * (1 + breakout_buffer_pct / 100)
        breakout_confirmed = (
            float(prev["Close"]) <= breakout_level and
            float(latest["Close"]) > breakout_level and
            float(latest["Close"]) > float(latest["Open"])
        )

    if nearest_support is not None:
        sup_level = nearest_support.lower
        breakdown_level = sup_level * (1 - breakout_buffer_pct / 100)
        breakdown_confirmed = (
            float(prev["Close"]) >= breakdown_level and
            float(latest["Close"]) < breakdown_level and
            float(latest["Close"]) < float(latest["Open"])
        )

    return breakout_confirmed, breakdown_confirmed


def detect_retest_logic(
    df: pd.DataFrame,
    nearest_support: Zone | None,
    nearest_resistance: Zone | None,
    atr_multiplier: float = 0.35,
):
    if len(df) < 3:
        return False, False

    latest = df.iloc[-1]
    latest_close = float(latest["Close"])
    latest_low = float(latest["Low"])
    latest_high = float(latest["High"])
    atr = float(latest["ATR"]) if pd.notna(latest["ATR"]) else np.nan

    retest_buy_ready = False
    retest_sell_ready = False

    if nearest_resistance is not None and pd.notna(atr):
        resistance_test_zone = nearest_resistance.upper
        if latest_close > resistance_test_zone and latest_low <= resistance_test_zone + atr * atr_multiplier:
            retest_buy_ready = True

    if nearest_support is not None and pd.notna(atr):
        support_test_zone = nearest_support.lower
        if latest_close < support_test_zone and latest_high >= support_test_zone - atr * atr_multiplier:
            retest_sell_ready = True

    return retest_buy_ready, retest_sell_ready


def evaluate_trade_confirmation(
    df: pd.DataFrame,
    trendlines: List[Trendline],
    market_structure: MarketStructure,
    nearest_support: Zone | None,
    nearest_resistance: Zone | None,
    require_trendline_confirmation: bool = False,
    use_retest_bonus: bool = True,
    breakout_buffer_pct: float = 0.15,
) -> TradeConfirmation:
    latest = df.iloc[-1]

    close_price = float(latest["Close"])
    open_price = float(latest["Open"])
    high_price = float(latest["High"])
    low_price = float(latest["Low"])
    volume = float(latest["Volume"])
    avg_volume = float(latest["Vol_MA"]) if pd.notna(latest["Vol_MA"]) else np.nan
    vol_ratio = float(latest["Vol_Ratio"]) if pd.notna(latest["Vol_Ratio"]) else np.nan
    rsi = float(latest["RSI"]) if pd.notna(latest["RSI"]) else np.nan
    macd = float(latest["MACD"]) if pd.notna(latest["MACD"]) else np.nan
    macd_signal = float(latest["MACD_Signal"]) if pd.notna(latest["MACD_Signal"]) else np.nan
    atr = float(latest["ATR"]) if pd.notna(latest["ATR"]) else np.nan
    vwap = float(latest["VWAP"]) if pd.notna(latest["VWAP"]) else np.nan

    support_status = get_trendline_status(trendlines, "Support Trendline")
    resistance_status = get_trendline_status(trendlines, "Resistance Trendline")

    breakout_confirmed, breakdown_confirmed = detect_breakout_breakdown(
        df=df,
        nearest_support=nearest_support,
        nearest_resistance=nearest_resistance,
        breakout_buffer_pct=breakout_buffer_pct,
    )

    retest_buy_ready, retest_sell_ready = detect_retest_logic(
        df=df,
        nearest_support=nearest_support,
        nearest_resistance=nearest_resistance,
    )

    buy_score = 0
    sell_score = 0
    buy_reasons = []
    sell_reasons = []

    # VWAP
    if pd.notna(vwap):
        if close_price > vwap:
            buy_score += 2
            buy_reasons.append("Price is above VWAP")
        elif close_price < vwap:
            sell_score += 2
            sell_reasons.append("Price is below VWAP")

    # RSI
    if pd.notna(rsi):
        if 55 <= rsi <= 70:
            buy_score += 1
            buy_reasons.append("RSI is in bullish range")
        elif 30 <= rsi <= 45:
            sell_score += 1
            sell_reasons.append("RSI is in bearish range")
        elif rsi > 75:
            sell_score += 1
            sell_reasons.append("RSI is overbought")
        elif rsi < 25:
            buy_score += 1
            buy_reasons.append("RSI is in oversold bounce zone")

    # MACD
    if pd.notna(macd) and pd.notna(macd_signal):
        if macd > macd_signal:
            buy_score += 2
            buy_reasons.append("MACD is above signal line")
        elif macd < macd_signal:
            sell_score += 2
            sell_reasons.append("MACD is below signal line")

    # Volume
    if pd.notna(vol_ratio):
        if vol_ratio >= 1.2 and close_price > open_price:
            buy_score += 1
            buy_reasons.append("Bullish candle has above-average volume")
        elif vol_ratio >= 1.2 and close_price < open_price:
            sell_score += 1
            sell_reasons.append("Bearish candle has above-average volume")

    # Trendline
    if support_status == "Holding":
        buy_score += 2
        buy_reasons.append("Support trendline is holding")
    elif support_status == "Broken":
        sell_score += 2
        sell_reasons.append("Support trendline is broken")

    if resistance_status == "Broken":
        buy_score += 2
        buy_reasons.append("Resistance trendline is broken")
    elif resistance_status == "Holding":
        sell_score += 2
        sell_reasons.append("Resistance trendline is still holding")

    # Market structure
    if market_structure.trend_bias == "Bullish":
        buy_score += 2
        buy_reasons.append("Market structure is bullish")
    elif market_structure.trend_bias == "Bearish":
        sell_score += 2
        sell_reasons.append("Market structure is bearish")

    # Breakout / breakdown
    if breakout_confirmed:
        buy_score += 2
        buy_reasons.append("Resistance breakout candle is confirmed")

    if breakdown_confirmed:
        sell_score += 2
        sell_reasons.append("Support breakdown candle is confirmed")

    # Retest logic
    if use_retest_bonus and retest_buy_ready:
        buy_score += 1
        buy_reasons.append("Price is retesting breakout zone constructively")

    if use_retest_bonus and retest_sell_ready:
        sell_score += 1
        sell_reasons.append("Price is retesting breakdown zone weakly")

    # Zone distance filter
    if nearest_resistance is not None:
        upside_room_pct = ((nearest_resistance.center - close_price) / close_price) * 100
        if 0 <= upside_room_pct <= 0.4:
            buy_score -= 1
            buy_reasons.append("Upside room is limited due to nearby resistance")

    if nearest_support is not None:
        downside_room_pct = ((close_price - nearest_support.center) / close_price) * 100
        if 0 <= downside_room_pct <= 0.4:
            sell_score -= 1
            sell_reasons.append("Downside room is limited due to nearby support")

    # ATR chop filter
    if pd.notna(atr) and close_price > 0:
        atr_pct = (atr / close_price) * 100
        if atr_pct < 0.35:
            buy_score -= 1
            sell_score -= 1

    if require_trendline_confirmation:
        if support_status is None and resistance_status is None:
            buy_score -= 1
            sell_score -= 1

    # Final signal
    reasons = []
    signal = "Hold / Neutral"
    confidence = 50
    quality = "Low"

    if buy_score >= 10 and buy_score > sell_score:
        signal = "Strong Buy"
        confidence = min(95, 55 + buy_score * 4)
        quality = "High"
        reasons = buy_reasons
    elif buy_score >= 7 and buy_score > sell_score:
        signal = "Buy"
        confidence = min(90, 48 + buy_score * 4)
        quality = "Medium" if buy_score < 9 else "High"
        reasons = buy_reasons
    elif sell_score >= 10 and sell_score > buy_score:
        signal = "Strong Sell"
        confidence = min(95, 55 + sell_score * 4)
        quality = "High"
        reasons = sell_reasons
    elif sell_score >= 7 and sell_score > buy_score:
        signal = "Sell"
        confidence = min(90, 48 + sell_score * 4)
        quality = "Medium" if sell_score < 9 else "High"
        reasons = sell_reasons
    else:
        signal = "Hold / Neutral"
        confidence = 50
        quality = "Low"
        reasons = ["No strong multi-indicator confirmation"]

    return TradeConfirmation(
        signal=signal,
        confidence=int(confidence),
        buy_score=int(buy_score),
        sell_score=int(sell_score),
        quality=quality,
        reasons=reasons,
        breakout_confirmed=breakout_confirmed,
        breakdown_confirmed=breakdown_confirmed,
        retest_buy_ready=retest_buy_ready,
        retest_sell_ready=retest_sell_ready,
    )


def get_trade_levels(trade_confirmation: TradeConfirmation, df: pd.DataFrame):
    latest = df.iloc[-1]

    close_price = float(latest["Close"])
    high_price = float(latest["High"])
    low_price = float(latest["Low"])
    atr = float(latest["ATR"]) if pd.notna(latest["ATR"]) else np.nan

    if pd.isna(atr) or atr <= 0:
        return None

    signal = trade_confirmation.signal

    if signal in ["Buy", "Strong Buy"]:
        entry = close_price
        safe_entry = high_price + (0.2 * atr)
        stop_loss = entry - (1.5 * atr)
        target_1 = entry + (1.5 * atr)
        target_2 = entry + (2.5 * atr)

        return {
            "side": "BUY",
            "entry": round(entry, 2),
            "safe_entry": round(safe_entry, 2),
            "stop_loss": round(stop_loss, 2),
            "target_1": round(target_1, 2),
            "target_2": round(target_2, 2),
        }

    elif signal in ["Sell", "Strong Sell"]:
        entry = close_price
        safe_entry = low_price - (0.2 * atr)
        stop_loss = entry + (1.5 * atr)
        target_1 = entry - (1.5 * atr)
        target_2 = entry - (2.5 * atr)

        return {
            "side": "SELL",
            "entry": round(entry, 2),
            "safe_entry": round(safe_entry, 2),
            "stop_loss": round(stop_loss, 2),
            "target_1": round(target_1, 2),
            "target_2": round(target_2, 2),
        }

    return None


# ============================================================
# CHART
# ============================================================
def build_chart(
    df: pd.DataFrame,
    support_zones: List[Zone],
    resistance_zones: List[Zone],
    pivot_highs: pd.DataFrame,
    pivot_lows: pd.DataFrame,
    trendlines: List[Trendline],
    show_pivots: bool = True,
) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.72, 0.28],
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume"), row=2, col=1)

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Vol_MA"],
            mode="lines",
            name="Volume MA",
            line=dict(width=2),
        ),
        row=2,
        col=1,
    )

    for z in support_zones:
        fig.add_hrect(
            y0=z.lower,
            y1=z.upper,
            line_width=0,
            opacity=0.16,
            row=1,
            col=1,
            annotation_text=f"Support ({z.touches})",
            annotation_position="bottom right",
        )

    for z in resistance_zones:
        fig.add_hrect(
            y0=z.lower,
            y1=z.upper,
            line_width=0,
            opacity=0.16,
            row=1,
            col=1,
            annotation_text=f"Resistance ({z.touches})",
            annotation_position="top right",
        )

    if show_pivots:
        if pivot_highs is not None and not pivot_highs.empty:
            fig.add_trace(
                go.Scatter(
                    x=pivot_highs["Date"],
                    y=pivot_highs["Price"],
                    mode="markers",
                    name="Pivot Highs",
                    marker=dict(size=7, symbol="triangle-up"),
                ),
                row=1,
                col=1,
            )
        if pivot_lows is not None and not pivot_lows.empty:
            fig.add_trace(
                go.Scatter(
                    x=pivot_lows["Date"],
                    y=pivot_lows["Price"],
                    mode="markers",
                    name="Pivot Lows",
                    marker=dict(size=7, symbol="triangle-down"),
                ),
                row=1,
                col=1,
            )

    for tl in trendlines:
        fig.add_trace(
            go.Scatter(
                x=[tl.x0, tl.x1],
                y=[tl.y0, tl.y1],
                mode="lines",
                name=f"{tl.line_type} ({tl.status})",
                line=dict(width=2, dash="dot"),
            ),
            row=1,
            col=1,
        )

    latest_close = float(df["Close"].iloc[-1])
    fig.add_hline(
        y=latest_close,
        row=1,
        col=1,
        line_dash="dash",
        annotation_text=f"Current Price: {latest_close:,.2f}",
        annotation_position="top left",
    )

    if "VWAP" in df.columns and pd.notna(df["VWAP"].iloc[-1]):
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["VWAP"],
                mode="lines",
                name="VWAP",
                line=dict(width=2),
            ),
            row=1,
            col=1,
        )

    fig.update_layout(
        height=800,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    return fig


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.header("Inputs")

access_token_sidebar = st.sidebar.text_input("Upstox Access Token", type="password")

lookup_exchange = st.sidebar.selectbox(
    "Lookup Exchange",
    options=["NSE", "BSE"],
    index=0,
)

lookup_mode = st.sidebar.selectbox(
    "Instrument Type",
    options=["Equity", "Index", "Futures", "Call Option", "Put Option"],
    index=0,
)

instrument_search = st.sidebar.text_input(
    "Search Instrument",
    value="RELIANCE",
    help="Examples: RELIANCE, TCS, INFY, NIFTY, BANKNIFTY",
)

instrument_key = ""
selected_instrument_label = None
selected_row = None
filtered_df = pd.DataFrame()

try:
    instruments_df = load_upstox_instruments(lookup_exchange)
    filtered_df = filter_instruments(
        instruments_df=instruments_df,
        query=instrument_search,
        mode=lookup_mode,
        exchange=lookup_exchange,
    )

    if filtered_df.empty:
        st.sidebar.warning("No matching instruments found.")
    else:
        filtered_df = filtered_df.copy()
        filtered_df["label"] = filtered_df.apply(build_instrument_label, axis=1)

        selected_instrument_label = st.sidebar.selectbox(
            "Select Instrument",
            options=filtered_df["label"].tolist(),
            index=0,
        )

        selected_row = filtered_df[filtered_df["label"] == selected_instrument_label].iloc[0]
        instrument_key = selected_row["instrument_key"]

        st.sidebar.success(f"Instrument Key: {instrument_key}")
        st.sidebar.caption(
            f"Trading Symbol: {selected_row.get('trading_symbol', '')} | "
            f"Segment: {selected_row.get('segment', '')} | "
            f"Type: {selected_row.get('instrument_type', '')}"
        )

except Exception as e:
    st.sidebar.error("Failed to load instrument lookup.")
    st.sidebar.exception(e)

period = st.sidebar.selectbox(
    "Lookback Period",
    options=["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"],
    index=2,
)

interval = st.sidebar.selectbox(
    "Interval",
    options=["1d", "1h", "30m", "15m", "5m"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.subheader("Detection Settings")

left_bars = st.sidebar.slider("Pivot Left Bars", min_value=2, max_value=10, value=3)
right_bars = st.sidebar.slider("Pivot Right Bars", min_value=2, max_value=10, value=3)
zone_width_pct = st.sidebar.slider("Zone Width %", min_value=0.2, max_value=3.0, value=0.8, step=0.1)
min_touches = st.sidebar.slider("Minimum Touches per Zone", min_value=1, max_value=5, value=2)
volume_ma_window = st.sidebar.slider("Volume MA Window", min_value=5, max_value=50, value=20)
show_pivots = st.sidebar.checkbox("Show Pivot Markers", value=True)
trendline_tolerance_pct = st.sidebar.slider("Trendline Tolerance %", min_value=0.3, max_value=3.0, value=1.0, step=0.1)
include_live = st.sidebar.checkbox("Append live/current-session data", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("Trade Confirmation Settings")
require_trendline_confirmation = st.sidebar.checkbox("Require trendline confirmation", value=False)
use_retest_bonus = st.sidebar.checkbox("Use retest bonus", value=True)
breakout_buffer_pct = st.sidebar.slider("Breakout / Breakdown Buffer %", min_value=0.05, max_value=1.00, value=0.15, step=0.05)

st.sidebar.markdown("---")
st.sidebar.subheader("Option Chain / OI")
show_option_chain = st.sidebar.checkbox(
    "Show Option OI + PCR",
    value=True,
    help="Fetch option-chain OI data for the selected underlying if options are available.",
)

run_btn = st.sidebar.button("Run Analysis", type="primary")


# ============================================================
# MAIN APP
# ============================================================
if run_btn:
    try:
        access_token = access_token_sidebar or st.secrets.get("UPSTOX_ACCESS_TOKEN", "")

        if not access_token:
            st.error("Please provide your Upstox access token in the sidebar or set UPSTOX_ACCESS_TOKEN in Streamlit secrets.")
            st.stop()

        if not instrument_key:
            st.error("Please select a valid instrument from the lookup.")
            st.stop()

        validation_error = validate_period_interval(period, interval)
        if validation_error:
            st.error(validation_error)
            st.stop()

        available_expiries = []
        if show_option_chain:
            try:
                available_expiries = get_available_option_expiries(access_token, instrument_key)
            except Exception:
                available_expiries = []

        with st.spinner("Downloading Upstox market data and analyzing chart..."):
            raw = load_upstox_data(
                access_token=access_token,
                instrument_key=instrument_key,
                period=period,
                interval=interval,
                include_live=include_live,
            )

        if raw.empty:
            st.error("No data returned from Upstox for this instrument/period/interval combination.")
            st.stop()

        display_title = selected_row.get("trading_symbol", instrument_search) if selected_row is not None else instrument_search
        st.caption(f"Selected: {display_title} | Instrument Key: {instrument_key} | Interval: {interval} | Period: {period}")

        df = compute_volume_metrics(raw, volume_ma_window)

        pivot_highs, pivot_lows = find_pivots(df, left_bars=left_bars, right_bars=right_bars)

        current_price = float(df["Close"].iloc[-1])

        support_zones = cluster_levels(
            pivots=pivot_lows,
            current_price=current_price,
            zone_width_pct=zone_width_pct,
            zone_type="Support",
            min_touches=min_touches,
        )
        resistance_zones = cluster_levels(
            pivots=pivot_highs,
            current_price=current_price,
            zone_width_pct=zone_width_pct,
            zone_type="Resistance",
            min_touches=min_touches,
        )

        all_zones = support_zones + resistance_zones
        nearest_support, nearest_resistance = nearest_zones(all_zones, current_price)

        trendlines = detect_trendlines(
            df=df,
            pivot_highs=pivot_highs,
            pivot_lows=pivot_lows,
            tolerance_pct=trendline_tolerance_pct,
        )

        market_structure = detect_market_structure(pivot_highs=pivot_highs, pivot_lows=pivot_lows)
        vol_summary = summarize_volume(df)

        trade_confirmation = evaluate_trade_confirmation(
            df=df,
            trendlines=trendlines,
            market_structure=market_structure,
            nearest_support=nearest_support,
            nearest_resistance=nearest_resistance,
            require_trendline_confirmation=require_trendline_confirmation,
            use_retest_bonus=use_retest_bonus,
            breakout_buffer_pct=breakout_buffer_pct,
        )

        trade_levels = get_trade_levels(trade_confirmation, df)

        c1, c2, c3, c4, c5 = st.columns(5)
        last_vol_ratio = vol_summary["latest_vol_ratio"]
        avg_recent_vol_ratio = vol_summary["avg_recent_vol_ratio"]

        c1.metric("Current Price", f"{current_price:,.2f}")
        c2.metric("Nearest Support", f"{nearest_support.center:,.2f}" if nearest_support else "N/A")
        c3.metric("Nearest Resistance", f"{nearest_resistance.center:,.2f}" if nearest_resistance else "N/A")
        c4.metric(
            "Volume vs MA",
            f"{last_vol_ratio:.2f}x" if pd.notna(last_vol_ratio) else "N/A",
            delta=f"10-bar avg {avg_recent_vol_ratio:.2f}x" if pd.notna(avg_recent_vol_ratio) else None,
        )
        c5.metric("Structure", market_structure.trend_bias)

        st.markdown("### Trade Confirmation")
        tc1, tc2, tc3, tc4 = st.columns(4)
        tc1.metric("Signal", trade_confirmation.signal)
        tc2.metric("Confidence", f"{trade_confirmation.confidence}%")
        tc3.metric("Buy Score", trade_confirmation.buy_score)
        tc4.metric("Sell Score", trade_confirmation.sell_score)
        st.caption(
            f"Signal Quality: {trade_confirmation.quality} | "
            f"Breakout Confirmed: {'Yes' if trade_confirmation.breakout_confirmed else 'No'} | "
            f"Breakdown Confirmed: {'Yes' if trade_confirmation.breakdown_confirmed else 'No'} | "
            f"Retest Buy Ready: {'Yes' if trade_confirmation.retest_buy_ready else 'No'} | "
            f"Retest Sell Ready: {'Yes' if trade_confirmation.retest_sell_ready else 'No'}"
        )

        if trade_levels is not None:
            st.markdown("### Recommended Trade Levels")
            t1, t2, t3, t4, t5 = st.columns(5)

            if trade_levels["side"] == "BUY":
                t1.metric("Recommended Action", trade_levels["side"])
                t2.metric("Buy Price", f"{trade_levels['entry']:,.2f}")
                t3.metric("Safe Buy Above", f"{trade_levels['safe_entry']:,.2f}")
                t4.metric("Stop Loss", f"{trade_levels['stop_loss']:,.2f}")
                t5.metric("Target 1", f"{trade_levels['target_1']:,.2f}")
                st.caption(f"Extended Target 2: {trade_levels['target_2']:,.2f}")

            elif trade_levels["side"] == "SELL":
                t1.metric("Recommended Action", trade_levels["side"])
                t2.metric("Sell Price", f"{trade_levels['entry']:,.2f}")
                t3.metric("Safe Sell Below", f"{trade_levels['safe_entry']:,.2f}")
                t4.metric("Stop Loss", f"{trade_levels['stop_loss']:,.2f}")
                t5.metric("Target 1", f"{trade_levels['target_1']:,.2f}")
                st.caption(f"Extended Target 2: {trade_levels['target_2']:,.2f}")



        fig = build_chart(
            df=df,
            support_zones=support_zones,
            resistance_zones=resistance_zones,
            pivot_highs=pivot_highs,
            pivot_lows=pivot_lows,
            trendlines=trendlines,
            show_pivots=show_pivots,
        )
        st.plotly_chart(fig, use_container_width=True)

        left_col, right_col = st.columns([1.1, 0.9])

        with left_col:
            st.subheader("Support / Resistance Summary")
            zone_df = zones_to_dataframe(all_zones, current_price)
            if zone_df.empty:
                st.info("No strong zones detected with the current settings. Try reducing minimum touches or increasing zone width.")
            else:
                st.dataframe(zone_df, use_container_width=True, hide_index=True)

            st.subheader("Detected Pivot Points")
            piv_col1, piv_col2 = st.columns(2)

            with piv_col1:
                st.markdown("**Pivot Highs**")
                if pivot_highs.empty:
                    st.write("No pivot highs found")
                else:
                    temp = pivot_highs.copy()
                    temp["Date"] = temp["Date"].apply(lambda x: format_display_timestamp(x, interval))
                    temp["Price"] = temp["Price"].round(2)
                    st.dataframe(temp, use_container_width=True, hide_index=True)

            with piv_col2:
                st.markdown("**Pivot Lows**")
                if pivot_lows.empty:
                    st.write("No pivot lows found")
                else:
                    temp = pivot_lows.copy()
                    temp["Date"] = temp["Date"].apply(lambda x: format_display_timestamp(x, interval))
                    temp["Price"] = temp["Price"].round(2)
                    st.dataframe(temp, use_container_width=True, hide_index=True)

            st.subheader("Trade Signal Reasons")
            for reason in trade_confirmation.reasons:
                st.write(f"- {reason}")

        with right_col:
            st.subheader("Trading Summary")
            st.markdown(f"**Market Structure:** {market_structure.structure}")
            st.markdown(f"**Trend Bias:** {market_structure.trend_bias}")
            st.markdown(f"**Structure Read:** {market_structure.summary}")

            st.subheader("Trendlines")
            if trendlines:
                tl_rows = []
                for tl in trendlines:
                    tl_rows.append(
                        {
                            "Type": tl.line_type,
                            "Start": format_display_timestamp(tl.x0, interval),
                            "Start Price": round(tl.y0, 2),
                            "Projected Now": round(tl.y1, 2),
                            "Touches": tl.touches,
                            "Status": tl.status,
                            "Slope/Bar": round(tl.slope_per_bar, 4),
                        }
                    )
                st.dataframe(pd.DataFrame(tl_rows), use_container_width=True, hide_index=True)
            else:
                st.info("No valid trendlines detected yet with the current swing settings.")

            st.subheader("Volume Analysis")
            st.markdown(f"**Latest Volume Signal:** {vol_summary['latest_signal']}")
            st.markdown(f"**Participation Read:** {vol_summary['conviction']}")
            st.markdown(f"**Pressure Read:** {vol_summary['pressure']}")

            latest = df.iloc[-1]
            latest_range = float(latest["High"] - latest["Low"])
            latest_body = float(abs(latest["Close"] - latest["Open"]))
            body_to_range = (latest_body / latest_range) if latest_range > 0 else np.nan

            latest_close_snapshot = float(latest["Close"]) if pd.notna(latest["Close"]) else np.nan
            latest_atr_snapshot = float(latest["ATR"]) if pd.notna(latest["ATR"]) else np.nan
            atr_pct_snapshot = (latest_atr_snapshot / latest_close_snapshot) * 100 if pd.notna(latest_atr_snapshot) and pd.notna(latest_close_snapshot) and latest_close_snapshot != 0 else np.nan
            atr_vol_label = get_volatility_label(latest_close_snapshot, latest_atr_snapshot)
            atr_display = (
                f"{latest_atr_snapshot:.2f} ({atr_pct_snapshot:.2f}% / {atr_vol_label})"
                if pd.notna(latest_atr_snapshot) and pd.notna(atr_pct_snapshot)
                else np.nan
            )

            st.subheader("Latest Candle Snapshot")
            candle_stats = pd.DataFrame(
                {
                    "Metric": [
                        "Open",
                        "High",
                        "Low",
                        "Close",
                        "VWAP",
                        "RSI",
                        "MACD",
                        "MACD Signal",
                        "ATR",
                        "Volume",
                        "Volume MA",
                        "Volume Ratio",
                        "Price Change %",
                        "Body / Range",
                    ],
                    "Value": [
                        round(float(latest["Open"]), 2),
                        round(float(latest["High"]), 2),
                        round(float(latest["Low"]), 2),
                        round(float(latest["Close"]), 2),
                        round(float(latest["VWAP"]), 2) if pd.notna(latest["VWAP"]) else np.nan,
                        round(float(latest["RSI"]), 2) if pd.notna(latest["RSI"]) else np.nan,
                        round(float(latest["MACD"]), 4) if pd.notna(latest["MACD"]) else np.nan,
                        round(float(latest["MACD_Signal"]), 4) if pd.notna(latest["MACD_Signal"]) else np.nan,
                        atr_display,
                        f"{int(latest['Volume']):,}",
                        round(float(latest["Vol_MA"]), 2),
                        round(float(latest["Vol_Ratio"]), 2) if pd.notna(latest["Vol_Ratio"]) else np.nan,
                        round(float(latest["Price_Change_%"]), 2) if pd.notna(latest["Price_Change_%"]) else np.nan,
                        round(float(body_to_range), 2) if pd.notna(body_to_range) else np.nan,
                    ],
                }
            )
            st.dataframe(candle_stats, use_container_width=True, hide_index=True)

            st.subheader("Trading Notes")
            notes = [f"Current structure is {market_structure.trend_bias.lower()} with pattern: {market_structure.structure}."]
            if nearest_support:
                notes.append(f"Nearest support zone is {nearest_support.lower:,.2f} to {nearest_support.upper:,.2f}.")
            if nearest_resistance:
                notes.append(f"Nearest resistance zone is {nearest_resistance.lower:,.2f} to {nearest_resistance.upper:,.2f}.")
            if pd.notna(last_vol_ratio):
                if last_vol_ratio >= 1.5:
                    notes.append("Recent activity is backed by stronger-than-normal volume.")
                elif last_vol_ratio < 0.8:
                    notes.append("Recent move is happening on lighter volume, so conviction is weaker.")
            notes.append(f"Final confirmation engine output is: {trade_confirmation.signal} with {trade_confirmation.confidence}% confidence.")

            for note in notes:
                st.write(f"- {note}")

        # ============================================================
        # OPTION CHAIN / OI / PCR
        # ============================================================
        if show_option_chain:
            st.markdown("---")
            st.subheader("Option OI / Put-Call Ratio")

            if not available_expiries:
                st.info(
                    "No option expiries found for the selected underlying. "
                    "This usually means the selected instrument is not F&O enabled or options are not available for it."
                )
            else:
                selected_expiry = st.selectbox(
                    "Select Option Expiry",
                    options=available_expiries,
                    index=0,
                    key="selected_option_expiry",
                )

                try:
                    option_chain_df = fetch_option_chain_v2(
                        access_token=access_token,
                        instrument_key=instrument_key,
                        expiry_date=selected_expiry,
                    )

                    if option_chain_df.empty:
                        st.info("Option chain returned no rows for the selected expiry.")
                    else:
                        option_summary = compute_option_chain_summary(option_chain_df)

                        oc1, oc2, oc3, oc4 = st.columns(4)
                        oc1.metric(
                            "Underlying Spot",
                            f"{option_summary['spot_price']:,.2f}" if pd.notna(option_summary["spot_price"]) else "N/A",
                        )
                        oc2.metric(
                            "Total Call OI",
                            f"{int(option_summary['total_call_oi']):,}" if pd.notna(option_summary["total_call_oi"]) else "N/A",
                        )
                        oc3.metric(
                            "Total Put OI",
                            f"{int(option_summary['total_put_oi']):,}" if pd.notna(option_summary["total_put_oi"]) else "N/A",
                        )
                        oc4.metric(
                            "Overall PCR",
                            f"{option_summary['overall_pcr']:.2f}" if pd.notna(option_summary["overall_pcr"]) else "N/A",
                            delta=interpret_pcr(option_summary["overall_pcr"]),
                        )

                        st.caption(
                            f"Expiry selected: {selected_expiry} | "
                            f"PCR = Total Put OI / Total Call OI"
                        )

                        spot_price = option_summary["spot_price"]
                        display_df = option_chain_df.copy()

                        if pd.notna(spot_price):
                            display_df["Distance From Spot"] = (
                                pd.to_numeric(display_df["Strike"], errors="coerce") - float(spot_price)
                            ).abs()
                            display_df = display_df.sort_values("Distance From Spot").head(21)
                            display_df = display_df.sort_values("Strike").reset_index(drop=True)

                        visible_cols = [
                            "Strike",
                            "PCR",
                            "Call LTP",
                            "Call Volume",
                            "Call OI",
                            "Call Prev OI",
                            "Put LTP",
                            "Put Volume",
                            "Put OI",
                            "Put Prev OI",
                            "Underlying Spot",
                        ]
                        visible_cols = [c for c in visible_cols if c in display_df.columns]

                        for col in visible_cols:
                            if col in display_df.columns:
                                display_df[col] = pd.to_numeric(display_df[col], errors="coerce").round(2)

                        st.dataframe(display_df[visible_cols], use_container_width=True, hide_index=True)

                except requests.HTTPError as e:
                    try:
                        option_api_error = e.response.json()
                    except Exception:
                        option_api_error = e.response.text if e.response is not None else str(e)

                    st.error("Failed to fetch option chain from Upstox.")
                    st.code(str(option_api_error))

        with st.expander("Instrument Lookup Matches"):
            if not filtered_df.empty:
                show_cols = [c for c in ["trading_symbol", "name", "segment", "instrument_type", "instrument_key", "expiry_dt", "strike_price"] if c in filtered_df.columns]
                st.dataframe(filtered_df[show_cols], use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("Raw OHLCV Data")
        raw_display = df.reset_index().copy()
        raw_display = raw_display.rename(columns={raw_display.columns[0]: "Date"})
        raw_display["Date"] = raw_display["Date"].apply(lambda x: format_display_timestamp(x, interval))

        numeric_cols = [
            "Open", "High", "Low", "Close", "Volume", "Vol_MA", "Vol_Ratio", "Price_Change_%",
            "RSI", "MACD", "MACD_Signal", "MACD_Hist", "ATR", "VWAP"
        ]
        for col in numeric_cols:
            if col in raw_display.columns:
                raw_display[col] = pd.to_numeric(raw_display[col], errors="coerce").round(4)

        st.dataframe(raw_display, use_container_width=True, hide_index=True)

    except requests.HTTPError as e:
        try:
            api_error = e.response.json()
        except Exception:
            api_error = e.response.text if e.response is not None else str(e)
        st.error("Upstox API error")
        st.code(str(api_error))
    except Exception as e:
        st.exception(e)

else:
    st.info("Set your Upstox token, search the instrument, select it, and click **Run Analysis**.")
    st.markdown(
        """
### What this version includes
- Upstox instrument lookup inside the app
- Search by symbol / name / underlying
- Auto instrument-key selection
- Upstox Historical Candle Data V3
- Upstox Intraday Candle Data V3
- Optional live/current-session append
- Support/resistance zones
- Trendlines
- Market structure
- RSI
- MACD
- ATR
- VWAP
- Buy/Sell confirmation engine
- Confidence %
- Signal quality
- Option OI + Put-Call Ratio
        """
    )

    st.code("python -m pip install streamlit requests plotly pandas numpy", language="bash")