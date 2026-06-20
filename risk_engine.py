# ================= risk_engine.py =================
from typing import List, Dict
import pandas as pd

from performance_layer import compute_performance_layer
from market_layer import MarketConfig, compute_market_layer


def build_market_config_from_state(state) -> MarketConfig:
    w_price = float(state.get("m_w_price", 0.30))
    w_macro = float(state.get("m_w_macro", 0.30))
    w_flow = float(state.get("m_w_flow", 0.25))
    w_sentiment = float(state.get("m_w_sentiment", 0.15))

    total = w_price + w_macro + w_flow + w_sentiment
    if total <= 0:
        return MarketConfig()

    return MarketConfig(
        w_price=w_price / total,
        w_macro=w_macro / total,
        w_flow=w_flow / total,
        w_sentiment=w_sentiment / total,
    )


def apply_risk_engine_multiplier(P, M, base_risk_pct, engine_type):
    engine_mult = 1.25 if engine_type == "Aggressive" else 1.0 if engine_type == "Moderate" else 0.75
    combined_signal = 0.60 * float(P) + 0.40 * float(M)
    normalized_signal = combined_signal / 100.0

    market_gate = 0.80 if float(M) < 40 else 1.00
    upside_boost = 1.10 if float(P) > 70 and float(M) > 60 else 1.00

    # Base risk is scaled from roughly 0.5x to 1.5x, then gated by market quality.
    risk = float(base_risk_pct) * (0.50 + normalized_signal) * market_gate * upside_boost * engine_mult
    return max(0.10, min(5.00, risk))


def compute_risk_and_perf(trades: List[Dict], state) -> Dict:
    df = pd.DataFrame(trades)
    perf = compute_performance_layer(df)
    P = perf["P_score"]

    market_snapshot = state.get("market_snapshot", {})
    market_cfg = build_market_config_from_state(state)
    market = compute_market_layer(market_snapshot, market_cfg)
    M = market["M_score"]

    base_risk_pct = float(state.get("base_risk_pct", 1.0))
    engine_type = state.get("risk_engine_type", "Moderate")

    acceptable_risk_pct = apply_risk_engine_multiplier(P, M, base_risk_pct, engine_type)

    combined_signal = 0.60 * float(P) + 0.40 * float(M)
    market_gate = 0.80 if float(M) < 40 else 1.00
    upside_boost = 1.10 if float(P) > 70 and float(M) > 60 else 1.00
    engine_mult = 1.25 if engine_type == "Aggressive" else 1.0 if engine_type == "Moderate" else 0.75

    return {
        "perf": perf,
        "market": market,
        "acceptable_risk_pct": acceptable_risk_pct,
        "P_score": P,
        "M_score": M,
        "risk_breakdown": {
            "base_risk_pct": base_risk_pct,
            "performance_strength": P,
            "market_conditions": M,
            "combined_signal": combined_signal,
            "market_gate": market_gate,
            "performance_boost": upside_boost,
            "engine_multiplier": engine_mult,
            "formula": "risk = base_risk_pct * (0.50 + (0.60*P + 0.40*M)/100) * market_gate * performance_boost * engine_multiplier",
        },
    }
