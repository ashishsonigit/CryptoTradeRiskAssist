# ================= ui_history.py =================
import streamlit as st
import pandas as pd
import altair as alt

from storage import compute_balance_history, load_trades
from ai_engines import generate_trade_journal_entry


def render_history():
    st.title("📚 Trade History")

    trades = load_trades()
    initial_balance = float(trades[0].get("initial_balance", 10000.0)) if trades else 10000.0
    balance_history = compute_balance_history(trades, initial_balance)
    df = pd.DataFrame(balance_history)

    if df.empty:
        st.info("No trades recorded yet.")
        return

    st.subheader("Trades Table")

    if "pnl" in df.columns:
        df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce")

    def _row_style(row):
        result = str(row.get("result", "")).lower()
        pnl = row.get("pnl", 0)
        is_loss = result == "loss" or (pd.notna(pnl) and float(pnl) < 0)
        if is_loss:
            return ["background-color: #fee2e2; color: #991b1b; font-weight: 700;"] * len(row)
        return ["background-color: #dcfce7; color: #166534; font-weight: 700;"] * len(row)

    plot_df = df.copy().reset_index(drop=True)
    plot_df["trade_index"] = range(1, len(plot_df) + 1)
    display_cols = [
        "trade_index", "date", "symbol", "result", "pnl", "cumulative_pnl", "balance_after"
    ]
    remaining_cols = [col for col in plot_df.columns if col not in display_cols]
    ordered = plot_df[display_cols + remaining_cols]
    ordered = ordered.rename(columns={"trade_index": "Trade #", "balance_after": "Balance"})

    st.dataframe(ordered.style.apply(_row_style, axis=1), use_container_width=True)

    if "pnl" in df.columns:
        st.subheader("PnL by Trade")
        plot_df["outcome"] = plot_df["pnl"].apply(lambda x: "Profit" if pd.notna(x) and float(x) >= 0 else "Loss")

        chart = (
            alt.Chart(plot_df)
            .mark_line(color="#334155", point=False)
            .encode(
                x=alt.X("trade_index:Q", title="Trade #", axis=alt.Axis(format="d", tickMinStep=1)),
                y=alt.Y("pnl:Q", title="PnL"),
            )
        )

        dots = (
            alt.Chart(plot_df)
            .mark_circle(size=90)
            .encode(
                x="trade_index:Q",
                y="pnl:Q",
                color=alt.Color(
                    "outcome:N",
                    scale=alt.Scale(domain=["Profit", "Loss"], range=["#16a34a", "#dc2626"]),
                    legend=alt.Legend(title="Outcome"),
                ),
                tooltip=[
                    alt.Tooltip("trade_index:Q", title="Trade #", format="d"),
                    alt.Tooltip("symbol:N", title="Symbol"),
                    alt.Tooltip("outcome:N", title="Outcome"),
                    alt.Tooltip("pnl:Q", title="PnL", format=".2f"),
                ],
            )
        )

        st.altair_chart((chart + dots).properties(height=250), use_container_width=True)

    if "Balance" in ordered.columns:
        st.subheader("Balance vs Trade Number")
        balance_line = (
            alt.Chart(ordered)
            .mark_line(color="#0f172a", strokeWidth=3, point=True)
            .encode(
                x=alt.X("Trade #:Q", title="Trade #", axis=alt.Axis(format="d", tickMinStep=1)),
                y=alt.Y("Balance:Q", title="Balance"),
                tooltip=[
                    alt.Tooltip("Trade #:Q", title="Trade #", format="d"),
                    alt.Tooltip("Balance:Q", title="Balance", format=",.2f"),
                    alt.Tooltip("cumulative_pnl:Q", title="Cumulative PnL", format=",.2f"),
                ],
            )
        )
        pnl_bars = (
            alt.Chart(ordered)
            .mark_bar(opacity=0.28)
            .encode(
                x=alt.X("Trade #:Q", title="Trade #"),
                y=alt.Y("pnl:Q", title="PnL"),
                color=alt.Color(
                    "result:N",
                    scale=alt.Scale(domain=["Win", "Loss"], range=["#16a34a", "#dc2626"]),
                    legend=None,
                ),
            )
        )
        st.altair_chart(alt.layer(pnl_bars, balance_line).resolve_scale(y="independent").properties(height=260), use_container_width=True)

    st.markdown("## 🧠 AI Trade Journaling")

    for trade in trades:
        label = f"{trade.get('symbol', 'Unknown')} — {trade.get('result', '')} — {trade.get('pnl_r', 0)}R"
        with st.expander(label):
            journal = generate_trade_journal_entry(trade)
            st.write(journal)
