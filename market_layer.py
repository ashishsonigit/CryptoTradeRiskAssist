# ================= market_layer.py =================
from dataclasses import dataclass


@dataclass
class MarketConfig:
    w_price: float = 0.30
    w_macro: float = 0.30
    w_flow: float = 0.25
    w_sentiment: float = 0.15


def compute_market_layer(snapshot: dict, cfg: MarketConfig):
    """
    Computes the 4‑pillar Market Layer:
    - Price Structure & Volatility
    - Macro & Cross‑Asset
    - Positioning & Flow
    - Sentiment & Narrative
    """

    # -----------------------------
    # PRICE STRUCTURE & VOLATILITY
    # -----------------------------
    price_score = (
        snapshot.get("regime_ema_slope_score", 50) * 0.40 +
        snapshot.get("regime_compression_score", 50) * 0.30 +
        snapshot.get("btc_structure_hh_hl", True) * 30 +
        snapshot.get("btc_atr_current", 1) / max(snapshot.get("btc_atr_30d", 1), 1) * 10
    )

    # -----------------------------
    # MACRO & CROSS‑ASSET
    # -----------------------------
    macro_score = (
        (snapshot.get("us10y_avg_5d", 4) - snapshot.get("us10y_current", 4)) * 10 +
        (0 - abs(snapshot.get("cpi_z_surprise", 0))) * 10 +
        snapshot.get("equities_score", 50) * 0.50 +
        snapshot.get("dxy_score", 50) * 0.50
    )

    # Normalize
    macro_score = max(0, min(100, macro_score))

    # -----------------------------
    # POSITIONING & FLOW
    # -----------------------------
    flow_score = (
        (0 - snapshot.get("funding_z", 0)) * 10 +
        (0 - snapshot.get("oi_z", 0)) * 10 +
        snapshot.get("etf_flow", 0) * 5 +
        snapshot.get("stable_30d_change_pct", 0) * 2
    )

    flow_score = max(0, min(100, flow_score))

    # -----------------------------
    # SENTIMENT & NARRATIVE
    # -----------------------------
    sentiment_score = (
        snapshot.get("fear_greed", 50) * 0.60 +
        snapshot.get("headline_sentiment", 0) * 20 +
        snapshot.get("equities_score", 50) * 0.20
    )

    sentiment_score = max(0, min(100, sentiment_score))

    # -----------------------------
    # FINAL MARKET SCORE
    # -----------------------------
    M_score = (
        price_score * cfg.w_price +
        macro_score * cfg.w_macro +
        flow_score * cfg.w_flow +
        sentiment_score * cfg.w_sentiment
    )

    return {
        "price_score": price_score,
        "macro_score": macro_score,
        "flow_score": flow_score,
        "sentiment_score": sentiment_score,
        "M_score": M_score,
        "market_risk_mode": (
            "Strong Risk‑On" if M_score >= 80 else
            "Constructive" if M_score >= 60 else
            "Neutral" if M_score >= 40 else
            "Risk‑Off"
        ),
    }
