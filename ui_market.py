# ================= ui_market.py =================
import streamlit as st
import feedparser

from market_snapshot import update_market_snapshot
from market_layer import compute_market_layer, MarketConfig
from ai_engines import (
    summarize_headline_ai,
    generate_market_alerts,
    generate_daily_market_brief,
)


NOVICE_CSS = """
<style>
.section-title {
    font-size: 22px !important;
    font-weight: 700 !important;
    margin-top: 20px;
}
.sub-title {
    font-size: 18px !important;
    font-weight: 600 !important;
    margin-top: 10px;
}
.metric-box {
    padding: 12px;
    border-radius: 8px;
    background-color: #111111;
    border: 1px solid #333333;
}
</style>
"""


# ---------------------------------------------------------
# NEWS FETCHER (RSS)
# ---------------------------------------------------------
def fetch_news():
    feeds = [
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://www.reuters.com/finance/markets/rss",
        "https://www.investing.com/rss/news_25.rss",
    ]

    items = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                items.append(
                    {
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.get("published", ""),
                    }
                )
        except Exception:
            pass

    return items[:10]


# ---------------------------------------------------------
# FOREXFACTORY EVENTS (RSS)
# ---------------------------------------------------------
def fetch_events():
    url = "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.xml"
    feed = feedparser.parse(url)

    events = []
    for entry in feed.entries[:10]:
        events.append(
            {
                "title": entry.title,
                "impact": entry.get("ff:impact", "Medium"),
                "time": entry.get("ff:date", ""),
                "link": entry.link,
            }
        )
    return events


# ---------------------------------------------------------
# MAIN DASHBOARD
# ---------------------------------------------------------
def render_market_dashboard():
    st.markdown(NOVICE_CSS, unsafe_allow_html=True)
    st.title("📊 Market Score (Novice Mode)")

    if st.button("🔄 Refresh Market Snapshot"):
        update_market_snapshot(force=True)
        st.rerun()

    snapshot = st.session_state.get("market_snapshot", {})
    if not snapshot:
        st.error("Market snapshot unavailable.")
        return

    cfg = MarketConfig()
    market = compute_market_layer(snapshot, cfg)
    score = market["M_score"]

    # 1. SINGLE SCORE
    st.markdown("<div class='section-title'>Overall Market Score</div>", unsafe_allow_html=True)

    mode = (
        "Strong Risk‑On" if score >= 80
        else "Constructive" if score >= 60
        else "Neutral" if score >= 40
        else "Risk‑Off"
    )

    st.metric("Market Score", f"{score:.1f}", mode)
    st.progress(score / 100)
    st.write("This score summarizes the entire market environment into a single number.")

    st.markdown("---")

    # 2. COMPONENTS
    st.markdown("<div class='section-title'>Market Components</div>", unsafe_allow_html=True)

    components = [
        ("Price Structure & Volatility", market["price_score"], "Trend, volatility, structure."),
        ("Macro & Cross‑Asset", market["macro_score"], "Yields, equities, macro pressure."),
        ("Positioning & Flow", market["flow_score"], "Funding, OI, ETF flows."),
        ("Sentiment & Narrative", market["sentiment_score"], "Fear & Greed, news tone."),
    ]

    for name, val, desc in components:
        with st.expander(f"{name} — {val:.1f}"):
            st.write(desc)
            st.progress(val / 100)

    st.markdown("---")

    # 3. DRILL-DOWN PANELS
    st.markdown("<div class='section-title'>Detailed Breakdown</div>", unsafe_allow_html=True)

    with st.expander("📈 Price Structure & Volatility — Details"):
        st.write(f"Trend Score: {snapshot.get('regime_ema_slope_score', 'N/A')}")
        st.write(f"ATR: {snapshot.get('btc_atr_current', 'N/A')}")
        st.write(f"Compression Score: {snapshot.get('regime_compression_score', 'N/A')}")

    with st.expander("🌍 Macro & Cross‑Asset — Details"):
        st.write(f"US 10Y Yield: {snapshot.get('us10y_current', 'N/A')}%")
        st.write(f"CPI Surprise Z: {snapshot.get('cpi_z_surprise', 'N/A')}")

    with st.expander("💰 Positioning & Flow — Details"):
        st.write(f"Funding Z: {snapshot.get('funding_z', 'N/A')}")
        st.write(f"OI Z: {snapshot.get('oi_z', 'N/A')}")
        st.write(f"Stablecoin 30D %: {snapshot.get('stable_30d_change_pct', 'N/A')}%")

    with st.expander("🧠 Sentiment & Narrative — Details"):
        st.write(f"Fear & Greed: {snapshot.get('fear_greed', 'N/A')}")
        st.write(f"News Tone: {snapshot.get('headline_sentiment', 'N/A')}")

    st.markdown("---")

    # 4. NEWS PANEL (RSS + AI SUMMARIES)
    st.markdown("<div class='section-title'>Latest News</div>", unsafe_allow_html=True)

    news = fetch_news()
    for item in news:
        title = item["title"]
        link = item["link"]
        source = link.split("/")[2] if "://" in link else "news"

        st.write(f"🔗 [{title}]({link})")
        summary = summarize_headline_ai(title, source)
        st.write(f"🧠 *{summary}*")
        st.write("---")

    st.markdown("---")

    # 5. EVENTS PANEL (RSS + AI SUMMARIES)
    st.markdown("<div class='section-title'>Upcoming Events</div>", unsafe_allow_html=True)

    events = fetch_events()
    for e in events:
        title = e["title"]
        impact = e["impact"]
        link = e["link"]

        st.write(f"📅 **{title}** — {impact}")
        ev_summary = summarize_headline_ai(title, "forexfactory")
        st.write(f"🧠 *{ev_summary}*")
        st.write(f"[View Details]({link})")
        st.write("---")

    st.markdown("---")

    # 6. AI MARKET ALERTS
    st.markdown("<div class='section-title'>AI Market Alerts</div>", unsafe_allow_html=True)

    conditions, ai_summary = generate_market_alerts(snapshot, market)
    st.write("### ⚠️ Key Conditions")
    for c in conditions:
        st.write(f"- {c}")

    st.write("### 🧠 AI Summary")
    st.info(ai_summary)

    st.markdown("---")

    # 7. AI DAILY MARKET BRIEF
    st.markdown("<div class='section-title'>📅 Daily Market Brief</div>", unsafe_allow_html=True)

    brief = generate_daily_market_brief(snapshot, market, news, events)
    st.write(brief)
