# ================= performance_layer.py =================
import pandas as pd
import numpy as np


# ---------------------------------------------------------
# UTILITY
# ---------------------------------------------------------
def _clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))


# ---------------------------------------------------------
# MAIN PERFORMANCE LAYER
# ---------------------------------------------------------
def compute_performance_layer(df):
    if df.empty:
        return {
            "winrate": 0,
            "winrate_score": 50,
            "loss_streak": 0,
            "loss_streak_score": 50,
            "drift_score": 50,
            "trade_quality_score": 50,
            "expectancy_r": 0,
            "expectancy_score": 50,
            "P_score": 50,
        }

    # ---------------------------------------------------------
    # WINRATE
    # ---------------------------------------------------------
    wins = df[df["result"] == "Win"]
    winrate = len(wins) / len(df) * 100 if len(df) else 0
    winrate_score = _clamp(winrate)

    # ---------------------------------------------------------
    # LOSS STREAK
    # ---------------------------------------------------------
    streak = 0
    max_streak = 0
    for _, row in df.iterrows():
        if row["result"] == "Loss":
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    loss_streak = max_streak
    loss_streak_score = _clamp(100 - loss_streak * 15)

    # ---------------------------------------------------------
    # PNL DRIFT (recent vs long-term)
    # ---------------------------------------------------------
    recent = df["pnl"].tail(20).mean() if len(df) >= 5 else 0
    long = df["pnl"].tail(100).mean() if len(df) >= 20 else recent

    drift = recent - long
    drift_score = _clamp(50 + (drift / (abs(long) + 1e-9)) * 50)

    # ---------------------------------------------------------
    # TRADE QUALITY SCORE
    # ---------------------------------------------------------
    violations = 0
    if "rr" in df:
        violations += (df["rr"] < 1.0).sum()
    if "risk_pct" in df:
        violations += (df["risk_pct"] > 2.0).sum()

    trade_quality_score = _clamp(100 - violations * 10)

    # ---------------------------------------------------------
    # EXPECTANCY
    # ---------------------------------------------------------
    if "pnl_r" in df:
        expectancy_r = df["pnl_r"].mean()
    else:
        expectancy_r = 0

    expectancy_score = _clamp(50 + expectancy_r * 20)

    # ---------------------------------------------------------
    # FINAL P-SCORE
    # ---------------------------------------------------------
    P = (
        0.25 * winrate_score +
        0.20 * loss_streak_score +
        0.20 * drift_score +
        0.20 * trade_quality_score +
        0.15 * expectancy_score
    )

    return {
        "winrate": winrate,
        "winrate_score": winrate_score,
        "loss_streak": loss_streak,
        "loss_streak_score": loss_streak_score,
        "drift_score": drift_score,
        "trade_quality_score": trade_quality_score,
        "expectancy_r": expectancy_r,
        "expectancy_score": expectancy_score,
        "P_score": P,
    }
