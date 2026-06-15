# ================= risk_engine.py =================
from typing import List, Dict
import pandas as pd

from performance_layer import compute_performance_layer
from market_layer import MarketConfig, compute_market_layer


def build_market_config_from_state(state) -> MarketConfig:
    return MarketConfig(
        w_price=float(state.get("m_w_price", 0.30)),
        w_macro=float(state.get("m_w_macro", 0.30)),
        w_flow=float(state.get("m_w_flow", 0.25)),
        w_sentiment=float(state.get("m_w_sentiment", 0.15)),
    )


def apply_risk_engine_multiplier(P, M, base_risk_pct, engine_type):
    mult = 1.25 if engine_type == "Aggressive" else 1.0 if engine_type == "Moderate" else 0.75
    B = 50
    return base_risk_pct * (P / 50) * (M / 50) * (B / 50) * mult


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

    return {
        "perf": perf,
        "market": market,
        "acceptable_risk_pct": acceptable_risk_pct,
        "P_score": P,
        "M_score": M,
    }
