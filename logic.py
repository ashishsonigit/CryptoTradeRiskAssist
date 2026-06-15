# ================= logic.py =================
import requests
from datetime import datetime
from typing import Dict, Any


# ---------------------------------------------------------
# PRICE FETCHING
# ---------------------------------------------------------
def get_price(symbol: str) -> float:
    """
    Fetch current price from Binance.
    Falls back to 0.0 on failure.
    """
    symbol = symbol.upper()

    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        data = requests.get(url, timeout=5).json()
        return float(data["price"])
    except Exception:
        return 0.0


# ---------------------------------------------------------
# TRADE PLANNING + EXECUTION
# ---------------------------------------------------------
def plan_trade(
    symbol: str,
    direction: str,
    entry_price: float,
    stop_price: float,
    target_price: float,
    units: float,
    fee_pct: float,
    rr: float,
    final_risk_pct: float,
) -> Dict[str, Any]:
    """
    Creates a trade dictionary consistent with the UI + history + performance engine.
    Does NOT update balance — UI handles that.
    """

    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M")

    symbol = symbol.upper()

    # Position value
    position_value = units * entry_price

    # Fees (entry + exit)
    fees = position_value * (fee_pct / 100.0) * 2

    # For planning, actual exit = target
    actual_exit = target_price

    # PnL calculation
    if direction == "Long":
        pnl = (actual_exit - entry_price) * units - fees
    else:
        pnl = (entry_price - actual_exit) * units - fees

    # Risk amount in USD
    risk_usd = position_value * (final_risk_pct / 100.0)
    actual_rr = pnl / risk_usd if risk_usd > 0 else 0.0

    # Result label
    result = "Win" if pnl > 0 else "Loss"

    # Breakeven price
    breakeven_price = (
        entry_price + fees / units if direction == "Long"
        else entry_price - fees / units
    )

    # Final trade dictionary (UI + history compatible)
    trade = {
        "date": date,
        "time": time,
        "symbol": symbol,
        "direction": direction,
        "actual_entry": entry_price,
        "exit_price": actual_exit,
        "units": units,
        "pnl": pnl,
        "actual_rr": actual_rr,
        "result": result,
        "balance_after": None,  # UI updates this
        "risk_pct": final_risk_pct,
        "breakeven_price": breakeven_price,
        "total_fee": fees,
        # Metadata for performance engine
        "baseline_risk": 1.0,
        "recommended_risk": final_risk_pct,
        "drawdown_adj": 1.0,
        "market_risk_mode": "Neutral",
        "market_risk_multiplier": 1.0,
    }

    return trade


# ---------------------------------------------------------
# MARKET INTELLIGENCE FETCHERS
# ---------------------------------------------------------
def fetch_fear_greed():
    try:
        data = requests.get("https://api.alternative.me/fng/", timeout=5).json()
        v = data["data"][0]
        return {"value": int(v["value"]), "classification": v["value_classification"]}
    except Exception:
        return {"value": 50, "classification": "Neutral"}


def fetch_lunarcrush_sentiment(symbol):
    # Placeholder — real API requires auth
    return {"market_sentiment": "Neutral", "influencer_sentiment": "Neutral"}


def fetch_farside_etf():
    # Placeholder — real ETF flows API
    return {"net_flow_musd": 0.0}


def fetch_tradingview_indicators(symbol):
    # Placeholder — real TradingView API requires auth
    return {
        "mfi": 50,
        "rsi": 50,
        "ma20_trend": "Flat",
        "ma50_trend": "Flat",
        "ma100_trend": "Flat",
        "ma200_trend": "Flat",
        "volume_trend": "Neutral",
    }


def fetch_whale_alert_activity():
    return {"activity_score": 0.0}


def fetch_coinglass_exchange_flows():
    return {"net_btc": 0.0}


def fetch_news_events():
    return {"event_risk": 0.0, "headline_count": 0}


# ---------------------------------------------------------
# MARKET SIGNAL ENGINE
# ---------------------------------------------------------
def compute_market_signal(fg, lunar, etf, tv, whales, flows, news):
    """
    Computes a simple 0–10 market confidence score.
    """
    score = 5.0

    # Fear & Greed
    if fg["value"] < 30:
        score -= 1
    elif fg["value"] > 70:
        score += 1

    # RSI
    if tv["rsi"] > 70:
        score -= 1
    elif tv["rsi"] < 30:
        score += 1

    # ETF flows
    score += 0.5 if etf["net_flow_musd"] > 0 else -0.5

    # Whale activity
    score += whales["activity_score"] * 0.1

    # News risk
    score -= news["event_risk"] * 0.5

    # Clamp
    score = max(0, min(10, score))

    # Confidence (placeholder)
    confidence = 0.7

    return score, confidence
