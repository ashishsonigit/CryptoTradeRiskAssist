# ================= ui_perf.py =================
import streamlit as st
import pandas as pd
import altair as alt

from storage import load_trades
from performance_layer import compute_performance_layer


PERF_CSS = """
<style>
.section-title {
    font-size: 22px !important;
    font-weight: 700 !important;
    margin-top: 20px;
}
.metric-box {
    padding: 12px;
    border-radius: 8px;
    background-color: #111111;
    border: 1px solid #333333;
}
</style>
"""


def render_performance_dashboard():
    st.markdown(PERF_CSS, unsafe_allow_html=True)
    st.title("📈 Performance Layer")

    trades = load_trades()
    df = pd.DataFrame(trades)

    perf = compute_performance_layer(df)

    # ---------------------------------------------------------
    # TOP: P-SCORE GAUGE
    # ---------------------------------------------------------
    st.markdown("<div class='section-title'>Performance Score</div>", unsafe_allow_html=True)

    P = perf["P_score"]
    label = (
        "Strong" if P >= 70 else
        "Balanced" if P >= 50 else
        "Weak"
    )

    st.metric("P‑Score", f"{P:.1f}", label)

    st.markdown("---")

    # ---------------------------------------------------------
    # WINRATE
    # ---------------------------------------------------------
    st.markdown("<div class='section-title'>Winrate</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Winrate", f"{perf['winrate']:.1f}%")
    c2.metric("Score", f"{perf['winrate_score']:.1f}")
    c3.metric("Window", "Last 20 trades")

    if len(df) > 1:
        df["wl"] = df["result"].apply(lambda x: 1 if x == "Win" else 0)
        spark = (
            alt.Chart(df.tail(20))
            .mark_line()
            .encode(x="index:Q", y="wl:Q")
            .properties(height=80)
        )
        st.altair_chart(spark, use_container_width=True)

    st.markdown("---")

    # ---------------------------------------------------------
    # LOSS STREAK
    # ---------------------------------------------------------
    st.markdown("<div class='section-title'>Loss Streak</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    c1.metric("Current Streak", perf["loss_streak"])
    c2.metric("Penalty Score", f"{perf['loss_streak_score']:.1f}")

    st.info("Recommendation: Reduce size or pause after 3 consecutive losses.")

    st.markdown("---")

    # ---------------------------------------------------------
    # PNL DRIFT
    # ---------------------------------------------------------
    st.markdown("<div class='section-title'>PnL Trend</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    c1.metric("Drift Score", f"{perf['drift_score']:.1f}")
    c2.metric("Expectancy (R)", f"{perf['expectancy_r']:.2f}")

    if "pnl" in df:
        df["index"] = range(len(df))
        chart = (
            alt.Chart(df)
            .mark_line()
            .encode(x="index", y="pnl")
            .properties(height=120)
        )
        st.altair_chart(chart, use_container_width=True)

    st.markdown("---")

    # ---------------------------------------------------------
    # TRADE QUALITY
    # ---------------------------------------------------------
    st.markdown("<div class='section-title'>Trade Quality</div>", unsafe_allow_html=True)

    st.metric("Quality Score", f"{perf['trade_quality_score']:.1f}")

    st.write("Recent violations:")
    st.write("- RR < 1.0")
    st.write("- Risk > 2%")
    st.write("- Execution deviations")

    st.markdown("---")

    # ---------------------------------------------------------
    # EXPECTANCY
    # ---------------------------------------------------------
    st.markdown("<div class='section-title'>Expectancy</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    c1.metric("Expectancy (R)", f"{perf['expectancy_r']:.2f}")
    c2.metric("Score", f"{perf['expectancy_score']:.1f}")

    label = (
        "Healthy" if perf["expectancy_r"] > 0 else
        "Fragile" if perf["expectancy_r"] > -0.2 else
        "Negative Edge"
    )
    st.info(f"Strategy Health: {label}")
