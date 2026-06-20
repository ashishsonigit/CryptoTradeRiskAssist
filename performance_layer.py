# ================= performance_layer.py =================
import pandas as pd
import numpy as np


# ---------------------------------------------------------
# UTILITY
# ---------------------------------------------------------
def _clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))


def _coalesce_float(value, fallback):
    try:
        if pd.isna(value):
            return float(fallback)
        return float(value)
    except Exception:
        return float(fallback)


# ---------------------------------------------------------
# MAIN PERFORMANCE LAYER
# ---------------------------------------------------------
def compute_performance_layer(df, initial_balance=10000.0):
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
            "initial_balance": float(initial_balance),
            "current_balance": float(initial_balance),
            "peak_balance": float(initial_balance),
            "equity_return_pct": 0,
            "recent_return_pct": 0,
            "max_drawdown_pct": 0,
            "current_drawdown_pct": 0,
            "growth_score": 50,
            "drawdown_score": 50,
            "balance_efficiency_score": 50,
            "P_score": 50,
        }

    work = df.copy()

    if "pnl" in work:
        work["pnl"] = pd.to_numeric(work["pnl"], errors="coerce")

    if "initial_balance" in work:
        first_initial = pd.to_numeric(work["initial_balance"], errors="coerce").dropna()
        if not first_initial.empty:
            initial_balance = float(first_initial.iloc[0])

    if "balance_before" in work:
        work["balance_before"] = pd.to_numeric(work["balance_before"], errors="coerce")
    if "balance_after" in work:
        work["balance_after"] = pd.to_numeric(work["balance_after"], errors="coerce")

    if "balance_before" not in work or work["balance_before"].isna().all():
        work["balance_before"] = float(initial_balance) + work["pnl"].fillna(0).cumsum().shift(fill_value=0)

    if "balance_after" not in work or work["balance_after"].isna().all():
        work["balance_after"] = work["balance_before"] + work["pnl"].fillna(0)

    work["cumulative_pnl"] = work["balance_after"] - float(initial_balance)
    work["peak_balance"] = work["balance_after"].cummax().clip(lower=float(initial_balance))
    work["drawdown_pct"] = np.where(
        work["peak_balance"] > 0,
        ((work["peak_balance"] - work["balance_after"]) / work["peak_balance"]) * 100.0,
        0.0,
    )
    work["return_pct"] = np.where(
        work["balance_before"] > 0,
        (work["pnl"].fillna(0) / work["balance_before"]) * 100.0,
        0.0,
    )

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
    # BALANCE / EQUITY CURVE
    # ---------------------------------------------------------
    current_balance = _coalesce_float(work["balance_after"].iloc[-1], initial_balance)
    peak_balance = _coalesce_float(work["peak_balance"].max(), initial_balance)
    equity_return_pct = ((current_balance - float(initial_balance)) / float(initial_balance) * 100.0) if float(initial_balance) > 0 else 0.0
    recent_return_pct = _coalesce_float(work["return_pct"].tail(10).mean(), 0.0)
    max_drawdown_pct = _coalesce_float(work["drawdown_pct"].max(), 0.0)
    current_drawdown_pct = _coalesce_float(work["drawdown_pct"].iloc[-1], 0.0)

    growth_score = _clamp(50 + (equity_return_pct * 2.5) + (recent_return_pct * 1.5))
    drawdown_score = _clamp(100 - (max_drawdown_pct * 4.0) - (current_drawdown_pct * 2.0))
    balance_efficiency_score = _clamp(0.60 * growth_score + 0.40 * drawdown_score)

    # ---------------------------------------------------------
    # FINAL P-SCORE
    # ---------------------------------------------------------
    P = (
        0.20 * winrate_score +
        0.15 * loss_streak_score +
        0.15 * drift_score +
        0.15 * trade_quality_score +
        0.15 * expectancy_score +
        0.10 * growth_score +
        0.10 * drawdown_score
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
        "initial_balance": float(initial_balance),
        "current_balance": current_balance,
        "peak_balance": peak_balance,
        "equity_return_pct": equity_return_pct,
        "recent_return_pct": recent_return_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "current_drawdown_pct": current_drawdown_pct,
        "growth_score": growth_score,
        "drawdown_score": drawdown_score,
        "balance_efficiency_score": balance_efficiency_score,
        "P_score": P,
    }
