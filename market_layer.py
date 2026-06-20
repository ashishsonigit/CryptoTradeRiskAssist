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
    - Price Structure & Volatility  (includes Regime sub-score)
    - Macro & Cross‑Asset
    - Positioning & Flow
    - Sentiment & Narrative
    """

    # -----------------------------
    # MARKET REGIME SUB-SCORE
    # Combines EMA slope, ADX strength, and HH/HL structure quality.
    # Trending (>70) / Ranging (40-70) / Choppy (<40)
    # -----------------------------
    ema_slope  = float(snapshot.get("regime_ema_slope_score", 50))
    adx_score  = float(snapshot.get("regime_adx_score", 50))
    structure  = float(snapshot.get("regime_structure_score", 50))   # 80 if HH/HL intact, else 40
    compression = float(snapshot.get("regime_compression_score", 50))

    regime_score = (
        ema_slope   * 0.35 +
        adx_score   * 0.30 +
        structure   * 0.20 +
        compression * 0.15
    )
    regime_score = max(0.0, min(100.0, regime_score))

    if regime_score >= 68:
        regime_label = "Trending — Strategy fit high"
    elif regime_score >= 42:
        regime_label = "Ranging — Suitable for mean reversion"
    else:
        regime_label = "Choppy — Avoid aggressive entries"

    # -----------------------------
    # PRICE STRUCTURE & VOLATILITY
    # Price Trend Score  = EMA slope (0-100)
    # Volatility Score   = blend of ATR ratio and Bollinger compression (0-100)
    # Regime Score       = already computed above (0-100)
    # -----------------------------
    atr_ratio      = float(snapshot.get("btc_atr_current", 1)) / max(float(snapshot.get("btc_atr_30d", 1)), 1)
    atr_normalized = max(0.0, min(100.0, atr_ratio * 50.0))   # 1.0 ratio → 50, 2.0 → 100, 0.5 → 25
    volatility_score = max(0.0, min(100.0, atr_normalized * 0.50 + compression * 0.50))

    price_score = (
        ema_slope        * 0.40 +
        volatility_score * 0.30 +
        regime_score     * 0.30
    )
    price_score = max(0.0, min(100.0, price_score))

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
        "volatility_score": volatility_score,
        "macro_score": macro_score,
        "flow_score": flow_score,
        "sentiment_score": sentiment_score,
        "regime_score": regime_score,
        "regime_label": regime_label,
        "M_score": M_score,
        "market_risk_mode": (
            "Strong Risk‑On" if M_score >= 80 else
            "Constructive" if M_score >= 60 else
            "Neutral" if M_score >= 40 else
            "Risk‑Off"
        ),
    }
