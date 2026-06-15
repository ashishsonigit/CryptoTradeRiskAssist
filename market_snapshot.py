# ================= market_snapshot.py =================
import time
import math
import requests
import datetime as dt
import streamlit as st


BINANCE_BASE = "https://api.binance.com"
FRED_BASE = "https://api.stlouisfed.org/fred"
ALPHAVANTAGE_BASE = "https://www.alphavantage.co/query"
DEFILLAMA_BASE = "https://stablecoins.llama.fi"
FEAR_GREED_URL = "https://api.alternative.me/fng/"


# ======================================================
#  UTILITY FUNCTIONS
# ======================================================

def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


# ---------------- EMA (SMA-initialized) ----------------
def ema(values, period):
    if len(values) < period:
        return None
    sma = sum(values[:period]) / period
    alpha = 2 / (period + 1)
    ema_val = sma
    for v in values[period:]:
        ema_val = alpha * v + (1 - alpha) * ema_val
    return ema_val


# ---------------- ATR (Wilder smoothing) ----------------
def atr(candles, period=14):
    if len(candles) < period + 1:
        return None

    trs = []
    for i in range(1, len(candles)):
        _, high, low, close, _ = candles[i]
        _, _, _, prev_close, _ = candles[i - 1]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)

    if len(trs) < period:
        return None

    atr_prev = sum(trs[:period]) / period

    for tr_val in trs[period:]:
        atr_prev = (atr_prev * (period - 1) + tr_val) / period

    return atr_prev


# ---------------- ADX (full DI+, DI–, DX) ----------------
def adx(candles, period=14):
    if len(candles) < period + 2:
        return None

    highs = [c[1] for c in candles]
    lows = [c[2] for c in candles]
    closes = [c[3] for c in candles]

    trs, plus_dm, minus_dm = [], [], []

    for i in range(1, len(candles)):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]

        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)

        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)

    if len(trs) < period:
        return None

    tr14 = sum(trs[:period])
    plus14 = sum(plus_dm[:period])
    minus14 = sum(minus_dm[:period])

    for i in range(period, len(trs)):
        tr14 = tr14 - (tr14 / period) + trs[i]
        plus14 = plus14 - (plus14 / period) + plus_dm[i]
        minus14 = minus14 - (minus14 / period) + minus_dm[i]

    if tr14 == 0:
        return None

    plus_di = 100.0 * (plus14 / tr14)
    minus_di = 100.0 * (minus14 / tr14)

    dx = 100.0 * abs(plus_di - minus_di) / max(plus_di + minus_di, 1e-9)
    return dx


# ---------------- Bollinger Band Width ----------------
def bollinger_bandwidth(closes, period=20, mult=2):
    if len(closes) < period:
        return None
    window = closes[-period:]
    mean = sum(window) / period
    var = sum((c - mean) ** 2 for c in window) / period
    std = math.sqrt(var)
    upper = mean + mult * std
    lower = mean - mult * std
    if mean == 0:
        return None
    return (upper - lower) / mean * 100.0


# ---------------- Structure (HH/HL) ----------------
def detect_structure(candles, swings=3):
    if len(candles) < swings + 1:
        return True
    highs = [c[1] for c in candles]
    lows = [c[2] for c in candles]

    last_highs = highs[-swings:]
    last_lows = lows[-swings:]

    hh = all(last_highs[i] > last_highs[i - 1] for i in range(1, swings))
    hl = all(last_lows[i] > last_lows[i - 1] for i in range(1, swings))

    return hh and hl


# ---------------- EMA Slope Score ----------------
def ema_slope_score(ema20, ema50):
    if ema20 is None or ema50 is None or ema50 == 0:
        return 50.0
    slope = (ema20 - ema50) / ema50
    return _clamp(50.0 + slope * 200.0, 0.0, 100.0)


# ---------------- Z-score ----------------
def _zscore(vals):
    if not vals:
        return 0.0
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    std = math.sqrt(var)
    if std == 0:
        return 0.0
    return (vals[-1] - mean) / std


# ======================================================
#  PRICE PIPELINE (BINANCE)
# ======================================================

def fetch_binance_ohlcv(symbol="BTCUSDT", interval="1h", limit=300):
    url = f"{BINANCE_BASE}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    candles = []
    for k in data:
        open_time = k[0]
        high = float(k[2])
        low = float(k[3])
        close = float(k[4])
        volume = float(k[5])
        candles.append((open_time, high, low, close, volume))
    return candles


def build_price_features():
    try:
        candles = fetch_binance_ohlcv()
    except Exception:
        return {}

    closes = [c[3] for c in candles]
    price = closes[-1]

    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)

    atr_current = atr(candles, 14)
    atr_30d = atr_current or 1.0

    adx_val = adx(candles, 14)
    bbw = bollinger_bandwidth(closes, 20, 2)
    structure_ok = detect_structure(candles, 3)

    ema_slope_sc = ema_slope_score(ema20, ema50)
    adx_score = _clamp((adx_val or 20.0) * 3.0, 0.0, 100.0)
    structure_score = 80.0 if structure_ok else 40.0

    if bbw is None:
        compression_score = 50.0
    else:
        if bbw < 2:
            compression_score = 80.0
        elif bbw < 5:
            compression_score = 60.0
        else:
            compression_score = 40.0

    return {
        "btc_price": price,
        "btc_ema20": ema20 or price,
        "btc_ema50": ema50 or price,
        "btc_structure_hh_hl": structure_ok,
        "btc_atr_current": atr_current or 0.0,
        "btc_atr_30d": atr_30d,
        "regime_ema_slope_score": ema_slope_sc,
        "regime_adx_score": adx_score,
        "regime_structure_score": structure_score,
        "regime_compression_score": compression_score,
    }


# ======================================================
#  MACRO PIPELINE (FRED + ALPHAVANTAGE)
# ======================================================

def fetch_fred_series(series_id, api_key, limit=30):
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "limit": limit,
        "sort_order": "desc",
    }
    r = requests.get(f"{FRED_BASE}/series/observations", params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    obs = data.get("observations", [])
    vals = []
    for o in obs:
        try:
            vals.append(float(o["value"]))
        except Exception:
            continue
    return list(reversed(vals))


def build_macro_features():
    fred_key = st.secrets.get("FRED_API_KEY", "")
    alpha_key = st.secrets.get("ALPHAVANTAGE_API_KEY", "")

    us10y_current = 4.0
    us10y_avg_5d = 4.0
    cpi_z = 0.0
    dxy_score = 50.0
    equities_score = 50.0
    events = []

    try:
        if fred_key:
            yields = fetch_fred_series("DGS10", fred_key, limit=10)
            if yields:
                us10y_current = yields[-1]
                us10y_avg_5d = sum(yields[-5:]) / min(5, len(yields))
    except Exception:
        pass

    try:
        if fred_key:
            cpi_z = 0.0
    except Exception:
        pass

    try:
        if alpha_key:
            dxy_score = 50.0
            equities_score = 60.0
    except Exception:
        pass

    return {
        "us10y_current": us10y_current,
        "us10y_avg_5d": us10y_avg_5d,
        "cpi_z_surprise": cpi_z,
        "events": events,
        "dxy_score": dxy_score,
        "equities_score": equities_score,
    }


# ======================================================
#  FLOW PIPELINE (BINANCE + DEFILLAMA)
# ======================================================

def fetch_binance_funding(symbol="BTCUSDT", limit=60):
    url = f"{BINANCE_BASE}/fapi/v1/fundingRate"
    params = {"symbol": symbol, "limit": limit}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    vals = [float(x["fundingRate"]) for x in data]
    return list(reversed(vals))


def fetch_binance_oi(symbol="BTCUSDT", interval="1h", limit=60):
    url = f"{BINANCE_BASE}/futures/data/openInterestHist"
    params = {"symbol": symbol, "period": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    vals = [float(x["sumOpenInterest"]) for x in data]
    return list(reversed(vals))


def fetch_stablecoins_total():
    url = f"{DEFILLAMA_BASE}/stablecoins"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()
    total = data.get("total", {}).get("totalCirculatingUSD", 0.0)
    return float(total)


def build_flow_features():
    funding_z = 0.0
    oi_z = 0.0
    etf_flow = 0.0
    stable_30d_change_pct = 0.0

    try:
        vals = fetch_binance_funding()
        funding_z = _zscore(vals)
    except Exception:
        pass

    try:
        vals = fetch_binance_oi()
        oi_z = _zscore(vals)
    except Exception:
        pass

    try:
        now = dt.datetime.utcnow().timestamp()
        total = fetch_stablecoins_total()
        hist = st.session_state.get("stable_hist", [])
        hist.append((now, total))
        hist = hist[-60:]
        st.session_state["stable_hist"] = hist

        if len(hist) >= 2:
            first_t, first_v = hist[0]
            last_t, last_v = hist[-1]
            days = (last_t - first_t) / 86400
            if days >= 20:
                stable_30d_change_pct = (last_v - first_v) / first_v * 100 if first_v > 0 else 0.0
    except Exception:
        pass

    return {
        "funding_z": funding_z,
        "oi_z": oi_z,
        "etf_flow": etf_flow,
        "stable_30d_change_pct": stable_30d_change_pct,
    }


# ======================================================
#  SENTIMENT PIPELINE (FEAR & GREED)
# ======================================================

def build_sentiment_features():
    fear_greed = 50.0
    headline_sentiment = 0.0

    try:
        r = requests.get(FEAR_GREED_URL, params={"limit": 1, "format": "json"}, timeout=10)
        if r.ok:
            data = r.json()
            v = data.get("data", [{}])[0].get("value", "50")
            fear_greed = float(v)
    except Exception:
        pass

    return {
        "fear_greed": fear_greed,
        "headline_sentiment": headline_sentiment,
    }


# ======================================================
#  DEFAULT SNAPSHOT
# ======================================================

DEFAULT_SNAPSHOT = {
    "btc_price": 60000.0,
    "btc_ema20": 59500.0,
    "btc_ema50": 58000.0,
    "btc_structure_hh_hl": True,
    "btc_atr_current": 1200.0,
    "btc_atr_30d": 1000.0,
    "regime_ema_slope_score": 50.0,
    "regime_adx_score": 50.0,
    "regime_structure_score": 50.0,
    "regime_compression_score": 50.0,
    "us10y_current": 4.2,
    "us10y_avg_5d": 4.0,
    "cpi_z_surprise": 0.0,
    "events": [],
    "dxy_score": 50.0,
    "equities_score": 50.0,
    "funding_z": 0.0,
    "oi_z": 0.0,
    "etf_flow": 0.0,
    "stable_30d_change_pct": 0.0,
    "fear_greed": 50.0,
    "headline_sentiment": 0.0,
}


# ======================================================
#  SNAPSHOT UPDATE (HYBRID, 15 MIN)
# ======================================================

REFRESH_SECONDS = 15 * 60  # 15 minutes


def update_market_snapshot(force: bool = False):
    now = time.time()
    last_ts = st.session_state.get("market_snapshot_ts", 0)

    if not force and (now - last_ts) < REFRESH_SECONDS and "market_snapshot" in st.session_state:
        return

    snapshot = DEFAULT_SNAPSHOT.copy()

    try:
        snapshot.update(build_price_features())
    except Exception:
        pass

    try:
        snapshot.update(build_macro_features())
    except Exception:
        pass

    try:
        snapshot.update(build_flow_features())
    except Exception:
        pass

    try:
        snapshot.update(build_sentiment_features())
    except Exception:
        pass

    st.session_state["market_snapshot"] = snapshot
    st.session_state["market_snapshot_ts"] = now


def schedule_market_updates():
    update_market_snapshot(force=False)
