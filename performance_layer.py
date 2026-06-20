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
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0,
            "winrate_score": 50,
            "loss_streak": 0,
            "loss_streak_score": 50,
            "recent_pnl_avg": 0,
            "long_pnl_avg": 0,
            "drift": 0,
            "drift_score": 50,
            "rr_violations": 0,
            "risk_violations": 0,
            "total_violations": 0,
            "violation_rate_pct": 0,
            "tracked_rr_count": 0,
            "tracked_risk_count": 0,
            "trade_quality_score": 50,
            "expectancy_r": 0,
            "expectancy_score": 50,
            "P_score": 50,
        }

    work = df.copy()

    if "pnl" in work:
        work["pnl"] = pd.to_numeric(work["pnl"], errors="coerce")

    if "pnl_r" not in work and {"pnl", "units", "stop_loss_distance"}.issubset(work.columns):
        units = pd.to_numeric(work["units"], errors="coerce")
        stop_dist = pd.to_numeric(work["stop_loss_distance"], errors="coerce")
        risk_notional = units * stop_dist
        work["pnl_r"] = np.where(risk_notional > 0, work["pnl"] / risk_notional, np.nan)

    if "rr" not in work and {"entry", "exit", "stop_loss_distance"}.issubset(work.columns):
        entry = pd.to_numeric(work["entry"], errors="coerce")
        exit_px = pd.to_numeric(work["exit"], errors="coerce")
        stop_dist = pd.to_numeric(work["stop_loss_distance"], errors="coerce")
        move = (exit_px - entry).abs()
        work["rr"] = np.where(stop_dist > 0, move / stop_dist, np.nan)

    total_trades = int(len(work))

    # ---------------------------------------------------------
    # WINRATE
    # ---------------------------------------------------------
    wins = work[work["result"] == "Win"]
    losses = work[work["result"] == "Loss"]
    winrate = len(wins) / total_trades * 100 if total_trades else 0
    winrate_score = _clamp(winrate)

    # ---------------------------------------------------------
    # LOSS STREAK
    # ---------------------------------------------------------
    streak = 0
    max_streak = 0
    for _, row in work.iterrows():
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
    recent = work["pnl"].tail(20).mean() if "pnl" in work and len(work) >= 5 else 0
    long = work["pnl"].tail(100).mean() if "pnl" in work and len(work) >= 20 else recent
    recent = float(0 if pd.isna(recent) else recent)
    long = float(0 if pd.isna(long) else long)

    drift = recent - long
    drift_score = _clamp(50 + (drift / (abs(long) + 1e-9)) * 50)

    # ---------------------------------------------------------
    # TRADE QUALITY SCORE
    # ---------------------------------------------------------
    rr_violations = 0
    tracked_rr_count = 0
    if "rr" in work:
        rr_series = pd.to_numeric(work["rr"], errors="coerce")
        tracked_rr_count = int(rr_series.notna().sum())
        rr_violations = int((rr_series < 1.0).sum())

    risk_violations = 0
    tracked_risk_count = 0
    if "risk_pct" in work:
        risk_series = pd.to_numeric(work["risk_pct"], errors="coerce")
        tracked_risk_count = int(risk_series.notna().sum())
        risk_violations = int((risk_series > 2.0).sum())

    violations = rr_violations + risk_violations
    tracked_quality_count = max(1, tracked_rr_count + tracked_risk_count)
    violation_rate_pct = violations / tracked_quality_count * 100

    trade_quality_score = _clamp(100 - violations * 10)

    # ---------------------------------------------------------
    # EXPECTANCY
    # ---------------------------------------------------------
    if "pnl_r" in work:
        expectancy_r = pd.to_numeric(work["pnl_r"], errors="coerce").mean()
    else:
        expectancy_r = 0
    expectancy_r = float(0 if pd.isna(expectancy_r) else expectancy_r)

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
        "total_trades": total_trades,
        "wins": int(len(wins)),
        "losses": int(len(losses)),
        "winrate": winrate,
        "winrate_score": winrate_score,
        "loss_streak": loss_streak,
        "loss_streak_score": loss_streak_score,
        "recent_pnl_avg": recent,
        "long_pnl_avg": long,
        "drift": drift,
        "drift_score": drift_score,
        "rr_violations": rr_violations,
        "risk_violations": risk_violations,
        "total_violations": violations,
        "violation_rate_pct": violation_rate_pct,
        "tracked_rr_count": tracked_rr_count,
        "tracked_risk_count": tracked_risk_count,
        "trade_quality_score": trade_quality_score,
        "expectancy_r": expectancy_r,
        "expectancy_score": expectancy_score,
        "P_score": P,
    }
