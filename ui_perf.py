import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from storage import load_trades


PERF_CSS = """
<style>
.terminal-wrap { background:#0a0d10; border:1px solid #2d3237; border-radius:0; padding:10px; }
.terminal-head { font-size:11px; color:#8a939f; letter-spacing:0.06em; text-transform:uppercase; margin-bottom:6px; }
.metric-title { font-size:24px; font-weight:700; color:#e8edf2; margin-bottom:2px; }
.metric-score { font-size:40px; font-weight:800; line-height:1.0; color:#f5f7fa; }
.state-pill { display:inline-block; padding:4px 10px; font-size:12px; font-weight:700; border-radius:0; }
.state-good { background:#0f3b22; color:#7fe6aa; border:1px solid #1f5d39; }
.state-neutral { background:#4a3810; color:#ffd27a; border:1px solid #7a5f24; }
.state-poor { background:#4c1f1f; color:#ff9090; border:1px solid #7a3434; }
.action-title { font-size:14px; font-weight:700; margin:2px 0 4px 0; color:#e8edf2; }
.tree-note { font-size:11px; color:#97a4b1; margin-bottom:8px; }
.small-note { font-size:11px; color:#97a4b1; }
.level-pad { margin-left: 10px; }
.dense-rule { border-top:1px solid #2d3237; margin:8px 0 10px 0; }
</style>
"""


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x)))


def _safe_float(x, default=0.0):
    try:
        if pd.isna(x):
            return float(default)
        return float(x)
    except Exception:
        return float(default)


def _state(score):
    if score >= 70:
        return "GOOD", "state-good"
    if score >= 50:
        return "NEUTRAL", "state-neutral"
    return "POOR", "state-poor"


def _score_color(score):
    if score >= 70:
        return "#16a34a"
    if score >= 50:
        return "#d97706"
    return "#dc2626"


def _compute_loss_streak(results):
    streak = 0
    out = []
    for r in results:
        if r == "Loss":
            streak += 1
        else:
            streak = 0
        out.append(streak)
    return out


def _prepare_perf_4h():
    trades = load_trades()
    df = pd.DataFrame(trades)
    if df.empty:
        return pd.DataFrame(), df

    if {"date", "time"}.issubset(df.columns):
        dt = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str), errors="coerce", utc=True)
    elif "datetime" in df.columns:
        dt = pd.to_datetime(df["datetime"], errors="coerce", utc=True)
    else:
        dt = pd.to_datetime(df.get("date", pd.Series(index=df.index, dtype=object)), errors="coerce", utc=True)

    df = df.copy()
    df["datetime"] = dt
    df = df.dropna(subset=["datetime"]).sort_values("datetime")
    if df.empty:
        return pd.DataFrame(), df

    num_cols = ["pnl", "units", "stop_loss_distance", "rr", "risk_pct", "pnl_r", "M_score", "balance_before", "balance_after", "cumulative_pnl", "drawdown_pct"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if "pnl_r" not in df.columns and {"pnl", "units", "stop_loss_distance"}.issubset(df.columns):
        risk_notional = df["units"] * df["stop_loss_distance"]
        df["pnl_r"] = np.where(risk_notional > 0, df["pnl"] / risk_notional, np.nan)

    initial_balance = float(df.get("initial_balance", pd.Series([10000.0])).dropna().iloc[0]) if not df.empty else 10000.0
    if "balance_before" not in df.columns or df["balance_before"].isna().all():
        df["balance_before"] = initial_balance + df["pnl"].fillna(0).cumsum().shift(fill_value=0)
    if "balance_after" not in df.columns or df["balance_after"].isna().all():
        df["balance_after"] = df["balance_before"] + df["pnl"].fillna(0)
    if "drawdown_pct" not in df.columns or df["drawdown_pct"].isna().all():
        peak_balance = df["balance_after"].cummax().clip(lower=initial_balance)
        df["drawdown_pct"] = np.where(peak_balance > 0, ((peak_balance - df["balance_after"]) / peak_balance) * 100.0, 0.0)

    if "rr" in df.columns:
        rr_num = pd.to_numeric(df["rr"], errors="coerce")
        df["rr_violation"] = (rr_num < 1.0).astype(int)
    else:
        df["rr_violation"] = 0

    if "risk_pct" in df.columns:
        risk_num = pd.to_numeric(df["risk_pct"], errors="coerce")
        df["risk_violation"] = (risk_num > 2.0).astype(int)
    else:
        df["risk_violation"] = 0

    df["win"] = (df.get("result", "") == "Win").astype(int)
    df["loss"] = (df.get("result", "") == "Loss").astype(int)

    max_dt = df["datetime"].max()
    min_dt = max_dt - pd.Timedelta(days=30)
    df = df[df["datetime"] >= min_dt].copy()
    if df.empty:
        return pd.DataFrame(), df

    agg = (
        df.set_index("datetime")
        .resample("4h")
        .agg(
            trades=("result", "count"),
            wins=("win", "sum"),
            losses=("loss", "sum"),
            pnl_sum=("pnl", "sum"),
            pnl_r_sum=("pnl_r", "sum"),
            rr_viol=("rr_violation", "sum"),
            risk_viol=("risk_violation", "sum"),
            m_score=("M_score", "mean"),
            balance_last=("balance_after", "last"),
            drawdown_last=("drawdown_pct", "last"),
        )
        .reset_index()
    )

    for col in ["trades", "wins", "losses", "rr_viol", "risk_viol"]:
        agg[col] = agg[col].fillna(0)

    agg["winrate"] = np.where(agg["trades"] > 0, (agg["wins"] / agg["trades"]) * 100.0, np.nan)
    agg["expectancy_r"] = np.where(agg["trades"] > 0, agg["pnl_r_sum"] / agg["trades"], np.nan)
    agg["pnl_avg"] = np.where(agg["trades"] > 0, agg["pnl_sum"] / agg["trades"], np.nan)

    agg["rolling_winrate"] = agg["winrate"].rolling(window=6, min_periods=1).mean()
    agg["rolling_expectancy"] = agg["expectancy_r"].rolling(window=6, min_periods=1).mean()
    agg["rolling_pnl_avg"] = agg["pnl_avg"].rolling(window=6, min_periods=1).mean()

    monthly_pnl_avg = _safe_float(agg["pnl_avg"].mean(), 0.0)
    agg["monthly_pnl_baseline"] = monthly_pnl_avg
    agg["pnl_drift"] = agg["rolling_pnl_avg"] - agg["monthly_pnl_baseline"]

    bin_loss_state = np.where((agg["trades"] > 0) & (agg["pnl_sum"] < 0), "Loss", "Win")
    agg["loss_streak"] = _compute_loss_streak(bin_loss_state)

    agg["quality_viol_rate"] = np.where(
        agg["trades"] > 0,
        (agg["rr_viol"] + agg["risk_viol"]) / np.maximum(1.0, agg["trades"] * 2.0),
        np.nan,
    )

    agg["winrate_score"] = agg["rolling_winrate"].apply(lambda x: _clamp(_safe_float(x, 50.0)))
    agg["expectancy_score"] = agg["rolling_expectancy"].apply(lambda x: _clamp(50.0 + (_safe_float(x, 0.0) * 20.0)))

    drift_denom = abs(monthly_pnl_avg) + 1e-9
    agg["drift_score"] = agg["pnl_drift"].apply(lambda x: _clamp(50.0 + (50.0 * (_safe_float(x, 0.0) / drift_denom))))
    agg["loss_streak_score"] = agg["loss_streak"].apply(lambda x: _clamp(100.0 - (15.0 * _safe_float(x, 0.0))))
    agg["trade_quality_score"] = agg["quality_viol_rate"].apply(lambda x: _clamp(100.0 - (100.0 * _safe_float(x, 0.0))))

    agg["composite_score"] = (
        0.25 * agg["winrate_score"]
        + 0.20 * agg["expectancy_score"]
        + 0.20 * agg["drift_score"]
        + 0.20 * agg["loss_streak_score"]
        + 0.15 * agg["trade_quality_score"]
    )

    agg["execution_score"] = (
        0.40 * agg["winrate_score"]
        + 0.30 * agg["expectancy_score"]
        + 0.30 * agg["trade_quality_score"]
    )

    agg["stability_score"] = 0.60 * agg["loss_streak_score"] + 0.40 * agg["drift_score"]
    agg["performance_score"] = (
        0.50 * agg["composite_score"]
        + 0.25 * agg["execution_score"]
        + 0.25 * agg["stability_score"]
    )

    # Risk regime from market score if available; fallback to neutral risk-off.
    agg["m_score_ffill"] = agg["m_score"].ffill()
    agg["regime"] = np.where(agg["m_score_ffill"] >= 60, "Risk-On", "Risk-Off")

    return agg, df


def _build_regime_overlay(df4h):
    if df4h.empty:
        return pd.DataFrame(columns=["start", "end", "regime"])

    rows = []
    times = df4h["datetime"].tolist()
    regimes = df4h["regime"].tolist()

    if len(times) < 2:
        end = times[0] + pd.Timedelta(hours=4)
        rows.append({"start": times[0], "end": end, "regime": regimes[0]})
        return pd.DataFrame(rows)

    start = times[0]
    current = regimes[0]
    for i in range(1, len(times)):
        if regimes[i] != current:
            rows.append({"start": start, "end": times[i], "regime": current})
            start = times[i]
            current = regimes[i]
    rows.append({"start": start, "end": times[-1] + pd.Timedelta(hours=4), "regime": current})
    return pd.DataFrame(rows)


def _metric_change(series):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 1:
        return 0.0, 0.0
    last = float(s.iloc[-1])
    prev = float(s.iloc[-2]) if len(s) >= 2 else last
    avg = float(s.mean())
    return last - prev, last - avg


def _anomaly_points(df, value_col):
    if df.empty or value_col not in df.columns:
        return pd.DataFrame(columns=["datetime", value_col, "trades"])
    s = pd.to_numeric(df[value_col], errors="coerce")
    mu = s.mean()
    sigma = s.std()
    if pd.isna(sigma) or sigma == 0:
        return pd.DataFrame(columns=["datetime", value_col, "trades"])
    z = (s - mu) / sigma
    mask = z.abs() >= 2.0
    out = df.loc[mask, ["datetime", value_col, "trades"]].copy()
    return out


def _time_chart(df4h, value_col, title, baseline_col=None):
    if df4h.empty or value_col not in df4h.columns:
        st.caption("No 4H data available for this metric in the last month.")
        return

    plot_df = df4h[["datetime", "trades", value_col]].copy()
    plot_df[value_col] = pd.to_numeric(plot_df[value_col], errors="coerce")
    plot_df = plot_df.dropna(subset=[value_col])

    if plot_df.empty:
        st.caption("No plottable values for this metric in the last month.")
        return

    overlay = _build_regime_overlay(df4h)
    anomalies = _anomaly_points(plot_df, value_col)

    y_min = float(plot_df[value_col].min())
    y_max = float(plot_df[value_col].max())
    if y_min == y_max:
        y_min -= 1.0
        y_max += 1.0
    pad = (y_max - y_min) * 0.1
    y_domain = [y_min - pad, y_max + pad]

    base = alt.Chart(plot_df).encode(
        x=alt.X("datetime:T", title="Datetime (4H)", axis=alt.Axis(format="%b %d", labelAngle=-28))
    )

    regime_rect = (
        alt.Chart(overlay)
        .mark_rect(opacity=0.12)
        .encode(
            x="start:T",
            x2="end:T",
            color=alt.Color("regime:N", scale=alt.Scale(domain=["Risk-On", "Risk-Off"], range=["#1f5d39", "#7a3434"]), legend=None),
        )
    )

    rolling_line = base.mark_line(color="#22c1f1", strokeWidth=2).encode(
        y=alt.Y(f"{value_col}:Q", title=title, scale=alt.Scale(domain=y_domain)),
        tooltip=[
            alt.Tooltip("datetime:T", title="Timestamp", format="%Y-%m-%d %H:%M"),
            alt.Tooltip(f"{value_col}:Q", title="Value", format=".4f"),
            alt.Tooltip("trades:Q", title="# Trades", format="d"),
        ],
    )

    layers = [regime_rect, rolling_line]

    if baseline_col and baseline_col in df4h.columns:
        baseline_df = df4h[["datetime", baseline_col]].copy().dropna()
        baseline_line = (
            alt.Chart(baseline_df)
            .mark_line(color="#f5c542", strokeDash=[5, 4])
            .encode(x="datetime:T", y=alt.Y(f"{baseline_col}:Q"))
        )
        layers.append(baseline_line)

    if not anomalies.empty:
        anomaly_layer = (
            alt.Chart(anomalies)
            .mark_point(color="#ff5b5b", filled=True, size=90)
            .encode(
                x="datetime:T",
                y=alt.Y(f"{value_col}:Q"),
                tooltip=[
                    alt.Tooltip("datetime:T", title="Timestamp", format="%Y-%m-%d %H:%M"),
                    alt.Tooltip(f"{value_col}:Q", title="Outlier Value", format=".4f"),
                    alt.Tooltip("trades:Q", title="# Trades", format="d"),
                ],
            )
        )
        layers.append(anomaly_layer)

    st.altair_chart(alt.layer(*layers).properties(height=245), use_container_width=True)


def _flatten(node, index):
    index[node["id"]] = node
    for child in node.get("children", []):
        _flatten(child, index)


def _contains_selected(node, selected_id):
    if node["id"] == selected_id:
        return True
    return any(_contains_selected(c, selected_id) for c in node.get("children", []))


def _render_tree(node):
    current_selected = st.session_state.get("perf_selected_node", "perf")

    if not node.get("children"):
        if st.button(node["name"], key=f"perf_btn_{node['id']}", use_container_width=True):
            st.session_state["perf_selected_node"] = node["id"]
        return

    with st.expander(node["name"], expanded=_contains_selected(node, current_selected)):
        if st.button(f"Select {node['name']}", key=f"perf_sel_{node['id']}", use_container_width=True):
            st.session_state["perf_selected_node"] = node["id"]
        for child in node["children"]:
            st.markdown("<div class='level-pad'>", unsafe_allow_html=True)
            _render_tree(child)
            st.markdown("</div>", unsafe_allow_html=True)


def _build_perf_tree(df4h, overall_perf=None):
    if df4h.empty:
        return None

    latest = df4h.iloc[-1]

    def score_of(col, default=50.0):
        return _safe_float(latest.get(col, default), default)

    def metric_node(node_id, name, score_col, series_col, baseline_col, formula, contribution, interpretation, actions, children=None, breakdown=None):
        return {
            "id": node_id,
            "name": name,
            "score": _clamp(score_of(score_col, 50.0)),
            "series_col": series_col,
            "baseline_col": baseline_col,
            "formula": formula,
            "contribution": contribution,
            "interpretation": interpretation,
            "actions": actions,
            "children": children or [],
            "breakdown": breakdown or [],
        }

    node_winrate = metric_node(
        "perf.composite.winrate",
        "Winrate",
        "winrate_score",
        "rolling_winrate",
        "winrate",
        r"Winrate=100\cdot\frac{Wins}{Trades},\; WinrateScore=\mathrm{clamp}(RollingWinrate,0,100)",
        "0.25 x Composite",
        [
            "Tracks directional hit-rate consistency over rolling 4H windows.",
            "Falling winrate with rising trade count often signals setup quality decay.",
            "Improvement is stronger when accompanied by stable expectancy.",
        ],
        {
            "primary": ["Reduce position size when winrate trend breaks down.", "Focus only on A+ setups until recovery."],
            "secondary": ["Re-check entry filters and timing windows.", "Pause low-conviction discretionary overrides."],
            "avoid": ["Adding frequency to compensate for losses.", "Judging edge from one or two bins."],
        },
    )

    node_expectancy = metric_node(
        "perf.composite.expectancy",
        "Expectancy",
        "expectancy_score",
        "rolling_expectancy",
        None,
        r"Expectancy_R=\frac{\sum pnl_R}{Trades},\; ExpectancyScore=\mathrm{clamp}(50+20\cdot RollingExpectancy,0,100)",
        "0.20 x Composite",
        [
            "Shows edge-per-trade quality, independent of pure winrate.",
            "Negative expectancy with high winrate can imply poor payoff ratio.",
            "Sustained positive expectancy supports scaling plans.",
        ],
        {
            "primary": ["Prioritize setups with better payoff asymmetry.", "Cut trades that degrade expectancy."],
            "secondary": ["Improve stop/target structuring.", "Review partial take-profit logic."],
            "avoid": ["Chasing winrate at the expense of R-multiple.", "Ignoring slippage/fee impact."],
        },
    )

    node_drift = metric_node(
        "perf.composite.drift",
        "PnL Drift",
        "drift_score",
        "pnl_drift",
        "monthly_pnl_baseline",
        r"PnLDrift=RollingPnL_{4H}-MonthlyAvgPnL,\; DriftScore=\mathrm{clamp}\left(50+50\cdot\frac{Drift}{|MonthlyAvgPnL|+\epsilon},0,100\right)",
        "0.20 x Composite",
        [
            "Compares recent 4H profitability to monthly baseline.",
            "Negative drift flags weakening edge or changing market fit.",
            "Positive drift with low anomaly count indicates robust adaptation.",
        ],
        {
            "primary": ["Reduce risk when drift stays negative across multiple bins.", "Increase selectivity until drift stabilizes."],
            "secondary": ["Recalibrate strategy to current regime.", "Segment performance by setup type."],
            "avoid": ["Treating negative drift as random noise if persistent.", "Scaling up in a degrading drift regime."],
        },
    )

    node_loss = metric_node(
        "perf.composite.loss_streak",
        "Loss Streak",
        "loss_streak_score",
        "loss_streak",
        None,
        r"LossStreakScore=\mathrm{clamp}(100-15\cdot ConsecutiveLossBins,0,100)",
        "0.20 x Composite",
        [
            "Consecutive loss bins reveal stability stress and behavioral risk.",
            "Rising streak with low trade count can still be statistically meaningful.",
            "Fast recovery after streak is a key resilience signal.",
        ],
        {
            "primary": ["Auto-cut risk tier after predefined streak threshold.", "Pause new setups until objective reset criteria met."],
            "secondary": ["Use checklist-based re-entry process.", "Require one clean win before normal sizing."],
            "avoid": ["Revenge trading after streak extension.", "Increasing leverage to recover faster."],
        },
    )

    node_quality = metric_node(
        "perf.composite.trade_quality",
        "Trade Quality",
        "trade_quality_score",
        "trade_quality_score",
        None,
        r"TradeQualityScore=\mathrm{clamp}(100-100\cdot ViolationRate,0,100)",
        "0.15 x Composite",
        [
            "Measures process discipline through RR and risk% violations.",
            "Falling quality often precedes P-score deterioration.",
            "Quality recovery usually improves expectancy persistence.",
        ],
        {
            "primary": ["Enforce hard RR and max-risk constraints.", "Reject trades violating process rules."],
            "secondary": ["Audit recurring violation patterns weekly.", "Refine pre-trade checklist strictness."],
            "avoid": ["Normalizing frequent rule breaches.", "Expanding rules to justify bad trades."],
        },
    )

    composite = metric_node(
        "perf.composite",
        "Composite",
        "composite_score",
        "composite_score",
        None,
        r"Composite=0.25\cdot Winrate+0.20\cdot Expectancy+0.20\cdot Drift+0.20\cdot LossStreak+0.15\cdot TradeQuality",
        "0.50 x Performance Score",
        [
            "Core blended performance health indicator.",
            "Requires agreement across edge, discipline, and stability dimensions.",
            "Divergence between components identifies what to fix first.",
        ],
        {
            "primary": ["Use Composite as primary go/no-go gate.", "Scale risk only when composite trend and execution align."],
            "secondary": ["Drill into weakest sub-component before adjusting strategy.", "Monitor anomaly clusters for instability."],
            "avoid": ["Acting on score level without trend context.", "Ignoring component divergence."],
        },
        children=[node_winrate, node_expectancy, node_drift, node_loss, node_quality],
        breakdown=[
            {"component": "Winrate", "contribution": 0.25 * score_of("winrate_score")},
            {"component": "Expectancy", "contribution": 0.20 * score_of("expectancy_score")},
            {"component": "PnL Drift", "contribution": 0.20 * score_of("drift_score")},
            {"component": "Loss Streak", "contribution": 0.20 * score_of("loss_streak_score")},
            {"component": "Trade Quality", "contribution": 0.15 * score_of("trade_quality_score")},
        ],
    )

    execution = metric_node(
        "perf.execution",
        "Execution",
        "execution_score",
        "execution_score",
        None,
        r"Execution=0.40\cdot Winrate+0.30\cdot Expectancy+0.30\cdot TradeQuality",
        "0.25 x Performance Score",
        [
            "Execution isolates decision and process quality.",
            "A drop here typically means entries/exits degraded before strategy edge fully fails.",
            "Execution recovery is often fastest lever for P-score rebound.",
        ],
        {
            "primary": ["Tighten execution protocol immediately when score slips.", "Reduce discretionary overrides."],
            "secondary": ["Replay recent executions to detect pattern drift.", "Refine timing and order-type rules."],
            "avoid": ["Blaming market regime alone for execution errors.", "Increasing trade count to force recovery."],
        },
        breakdown=[
            {"component": "Winrate", "contribution": 0.40 * score_of("winrate_score")},
            {"component": "Expectancy", "contribution": 0.30 * score_of("expectancy_score")},
            {"component": "Trade Quality", "contribution": 0.30 * score_of("trade_quality_score")},
        ],
    )

    stability = metric_node(
        "perf.stability",
        "Stability",
        "stability_score",
        "stability_score",
        None,
        r"Stability=0.60\cdot LossStreak+0.40\cdot Drift",
        "0.25 x Performance Score",
        [
            "Stability tracks smoothness and drawdown pressure.",
            "Sharp drops usually correspond to clustered anomalies.",
            "Stable metrics allow gradual risk scaling.",
        ],
        {
            "primary": ["Cut risk when stability trend deteriorates.", "Prioritize capital-preservation mode in unstable periods."],
            "secondary": ["Increase confirmation thresholds.", "Shorten holding windows until stability recovers."],
            "avoid": ["Aggressive scaling during unstable clusters.", "Ignoring recurrent negative outliers."],
        },
        breakdown=[
            {"component": "Loss Streak", "contribution": 0.60 * score_of("loss_streak_score")},
            {"component": "PnL Drift", "contribution": 0.40 * score_of("drift_score")},
        ],
    )

    root_score = _safe_float((overall_perf or {}).get("P_score", score_of("performance_score", 50.0)), 50.0)
    root = metric_node(
        "perf",
        "Performance Score",
        "P_score",
        "performance_score",
        None,
        r"P=0.25\cdot Winrate+0.20\cdot LossStreak+0.20\cdot Drift+0.20\cdot TradeQuality+0.15\cdot Expectancy",
        "Single source of truth used by risk engine",
        [
            "This is the authoritative Performance Score used by the risk engine.",
            "Use the 4H trend chart and child nodes to understand why it changed.",
            "Do not confuse this with derived dashboard health metrics.",
        ],
        {
            "primary": ["Scale risk only when P-score trend and sub-metrics improve together.", "Use the weakest child as the first place to intervene."],
            "secondary": ["Recheck execution quality when P falls.", "Reduce size during negative drift or rising loss streaks."],
            "avoid": ["Using the dashboard health score as a substitute for P.", "Ignoring a falling P even if one child is strong."],
        },
        children=[composite, execution, stability],
        breakdown=[
            {"component": "Composite", "contribution": 0.50 * score_of("composite_score")},
            {"component": "Execution", "contribution": 0.25 * score_of("execution_score")},
            {"component": "Stability", "contribution": 0.25 * score_of("stability_score")},
        ],
    )
    root["score"] = root_score

    return root


def _build_runtime_tree():
    df4h, trades_df = _prepare_perf_4h()
    if df4h.empty:
        return None, None, None

    from performance_layer import compute_performance_layer

    overall_perf = compute_performance_layer(trades_df, initial_balance=float(st.session_state.get("initial_balance", 10000.0)))
    root = _build_perf_tree(df4h, overall_perf=overall_perf)
    index = {}
    _flatten(root, index)

    if "perf_selected_node" not in st.session_state:
        st.session_state["perf_selected_node"] = "perf"

    return root, index, df4h


def _render_breakdown(rows):
    if not rows:
        return
    df = pd.DataFrame(rows)
    chart = (
        alt.Chart(df)
        .mark_bar(size=18)
        .encode(
            x=alt.X("contribution:Q", title="Contribution (pts)"),
            y=alt.Y("component:N", sort="-x", title=None),
            color=alt.Color(
                "contribution:Q",
                scale=alt.Scale(domain=[0, 50, 100], range=["#b33a3a", "#6d7a88", "#2f7f50"]),
                legend=None,
            ),
            tooltip=["component:N", alt.Tooltip("contribution:Q", format=".2f")],
        )
        .properties(height=175)
    )
    st.altair_chart(chart, use_container_width=True)


def render_performance_sidebar_navigation():
    root, _, _ = _build_runtime_tree()
    if root is None:
        st.sidebar.caption("No trades in last month to build 4H performance tree.")
        return

    with st.sidebar:
        st.markdown("---")
        st.markdown("**Performance Layer Tree**")
        st.markdown("<div class='tree-note'>4H recursive drill-down (last 30 days).</div>", unsafe_allow_html=True)
        _render_tree(root)


def render_performance_dashboard(show_embedded_nav: bool = True):
    st.markdown(PERF_CSS, unsafe_allow_html=True)
    st.title("Performance Layer Terminal")

    root, index, df4h = _build_runtime_tree()
    if root is None:
        st.info("No trades found in the last month to compute 4H performance metrics.")
        return

    selected_id = st.session_state.get("perf_selected_node", "perf")
    node = index.get(selected_id, root)

    if show_embedded_nav:
        left, center, right = st.columns([0.22, 0.53, 0.25], gap="small")
    else:
        center, right = st.columns([0.70, 0.30], gap="small")

    if show_embedded_nav:
        with left:
            st.markdown("<div class='terminal-wrap'><div class='terminal-head'>Navigation Tree</div>", unsafe_allow_html=True)
            st.markdown("<div class='tree-note'>Select any performance metric node.</div>", unsafe_allow_html=True)
            _render_tree(root)
            st.markdown("</div>", unsafe_allow_html=True)

    with center:
        score = _safe_float(node.get("score", 50.0), 50.0)
        state_text, state_class = _state(score)
        chg_4h, chg_month = _metric_change(df4h.get(node["series_col"], pd.Series(dtype=float)))

        st.markdown("<div class='terminal-wrap'><div class='terminal-head'>Explainability Panel</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-title'>{node['name']}</div>", unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns([0.30, 0.24, 0.24, 0.22])
        with m1:
            score_color = _score_color(score)
            st.markdown(f"<div class='metric-score' style='color:{score_color};'>{score:.1f}</div>", unsafe_allow_html=True)
        with m2:
            st.metric("Change (last 4H)", f"{chg_4h:+.2f}")
        with m3:
            st.metric("vs Monthly Avg", f"{chg_month:+.2f}")
        with m4:
            st.markdown(f"<span class='state-pill {state_class}'>{state_text}</span>", unsafe_allow_html=True)

        st.markdown("<div class='dense-rule'></div>", unsafe_allow_html=True)

        st.write("**Time-Series (Last 1 Month, 4H)**")
        _time_chart(df4h, node["series_col"], node["name"], baseline_col=node.get("baseline_col"))

        if node.get("breakdown"):
            st.write("**Component Breakdown**")
            _render_breakdown(node["breakdown"])

        st.write("**Interpretation**")
        for b in node.get("interpretation", [])[:4]:
            st.write(f"- {b}")

        st.write("**Formula and Contribution**")
        st.latex(node.get("formula", r"\text{N/A}"))
        st.write(f"Contribution to P-score: {node.get('contribution', 'N/A')}")

        st.write("**Interpretation Table**")
        table_rows = [
            ("70-100", "Good", "Scale selectively; maintain process discipline."),
            ("50-69", "Neutral", "Trade smaller; wait for stronger confirmation."),
            ("0-49", "Poor", "De-risk and prioritize recovery protocol."),
        ]
        st.dataframe(pd.DataFrame(table_rows, columns=["Score Range", "Meaning", "Trading Implication"]), use_container_width=True, hide_index=True)

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='terminal-wrap'><div class='terminal-head'>Trader Action Panel</div>", unsafe_allow_html=True)
        st.markdown("<div class='action-title'>Primary Actions</div>", unsafe_allow_html=True)
        for item in node["actions"]["primary"]:
            st.write(f"- {item}")

        st.markdown("<div class='action-title'>Secondary Actions</div>", unsafe_allow_html=True)
        for item in node["actions"]["secondary"]:
            st.write(f"- {item}")

        st.markdown("<div class='action-title'>Avoid</div>", unsafe_allow_html=True)
        for item in node["actions"]["avoid"]:
            st.write(f"- {item}")

        st.markdown("<div class='dense-rule'></div>", unsafe_allow_html=True)
        st.markdown("<div class='small-note'>Action panel remains visible while drilling metrics.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
