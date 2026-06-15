# ================= ai_engines.py =================
from typing import List, Dict


# ---------------------------------------------------------
# AI SUMMARY FOR HEADLINES / EVENTS
# ---------------------------------------------------------
def summarize_headline_ai(title: str, source: str = "") -> str:
    """
    Generates a short, safe AI summary of a news headline or event.
    Uses only the title + source, never article text.
    """
    prompt = (
        f"Summarize this market/crypto headline for a beginner:\n"
        f"Headline: {title}\n"
        f"Source: {source}\n\n"
        f"Rules:\n"
        f"- Explain in simple terms.\n"
        f"- Do NOT quote article text.\n"
        f"- Do NOT invent details.\n"
        f"- Keep it under 2 sentences.\n"
    )

    try:
        import openai
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
        )
        return response.choices[0].message["content"].strip()
    except Exception:
        return "Summary unavailable."


# ---------------------------------------------------------
# AI MARKET ALERT ENGINE
# ---------------------------------------------------------
def generate_market_alerts(snapshot: Dict, market: Dict):
    """
    Creates AI-generated alerts based on real market conditions.
    Uses only snapshot + scoring data.
    """

    conditions: List[str] = []

    # Trend weakening
    if snapshot.get("regime_ema_slope_score", 50) < 40:
        conditions.append("Trend is weakening and momentum is slowing.")

    # Volatility expansion
    if (
        "btc_atr_current" in snapshot
        and "btc_atr_30d" in snapshot
        and snapshot["btc_atr_current"] > snapshot["btc_atr_30d"] * 1.2
    ):
        conditions.append("Volatility is expanding and candles may widen.")

    # Compression squeeze
    if snapshot.get("regime_compression_score", 50) > 70:
        conditions.append("Market is in volatility compression; a breakout may occur.")

    # Funding elevated
    if snapshot.get("funding_z", 0) > 1.5:
        conditions.append("Funding is elevated; long positions may be crowded.")

    # OI rising fast
    if snapshot.get("oi_z", 0) > 1.5:
        conditions.append("Open interest is rising quickly; leverage is building.")

    # Macro pressure
    if (
        "us10y_current" in snapshot
        and "us10y_avg_5d" in snapshot
        and snapshot["us10y_current"] > snapshot["us10y_avg_5d"] * 1.05
    ):
        conditions.append("Yields are rising; macro pressure is increasing.")

    # Sentiment shift
    if snapshot.get("fear_greed", 50) < 30:
        conditions.append("Sentiment is fearful; risk appetite is low.")

    if not conditions:
        conditions.append("No major risks detected. Market conditions appear stable.")

    prompt = (
        "Summarize these market conditions for a beginner in 2–3 sentences:\n"
        f"{conditions}\n\n"
        "Rules:\n"
        "- Use simple language.\n"
        "- Do NOT predict price.\n"
        "- Explain what the trader should be aware of.\n"
        "- No financial advice.\n"
    )

    try:
        import openai
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
        )
        ai_summary = response.choices[0].message["content"].strip()
    except Exception:
        ai_summary = "Unable to generate AI alert summary."

    return conditions, ai_summary


# ---------------------------------------------------------
# AI DAILY MARKET BRIEF
# ---------------------------------------------------------
def generate_daily_market_brief(snapshot: Dict, market: Dict, news: List[Dict], events: List[Dict]) -> str:
    """
    Creates a full morning market brief for beginners.
    Uses snapshot + scoring + headlines + event titles.
    """

    M = market.get("M_score", 50)
    price = market.get("price_score", 50)
    macro = market.get("macro_score", 50)
    flow = market.get("flow_score", 50)
    sentiment = market.get("sentiment_score", 50)

    headline_list = [n.get("title", "") for n in news[:5]]
    event_list = [e.get("title", "") for e in events[:5]]

    prompt = f"""
Write a beginner-friendly morning market brief based on the following data.

Market Score: {M}
Price Score: {price}
Macro Score: {macro}
Flow Score: {flow}
Sentiment Score: {sentiment}

Key Metrics:
- Trend Score: {snapshot.get('regime_ema_slope_score', 'N/A')}
- ATR: {snapshot.get('btc_atr_current', 'N/A')}
- Compression: {snapshot.get('regime_compression_score', 'N/A')}
- Funding Z: {snapshot.get('funding_z', 'N/A')}
- OI Z: {snapshot.get('oi_z', 'N/A')}
- US10Y: {snapshot.get('us10y_current', 'N/A')}
- CPI Surprise Z: {snapshot.get('cpi_z_surprise', 'N/A')}
- Fear & Greed: {snapshot.get('fear_greed', 'N/A')}
- News Tone: {snapshot.get('headline_sentiment', 'N/A')}

Recent Headlines:
{headline_list}

Upcoming Events:
{event_list}

Rules:
- Explain everything in simple language.
- No predictions or financial advice.
- No copying article text.
- Keep it to 3–4 short paragraphs.
- Focus on what traders should be aware of today.
"""

    try:
        import openai
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=350,
        )
        return response.choices[0].message["content"].strip()
    except Exception:
        return "Daily brief unavailable."


# ---------------------------------------------------------
# AI RISK RECOMMENDATION ENGINE
# ---------------------------------------------------------
def generate_risk_recommendation(perf: Dict, market: Dict, acceptable_risk_pct: float) -> str:
    """
    Explains how P–M–B influenced the final risk %.
    Beginner-friendly, no predictions, no advice.
    """

    P = perf.get("P_score", 50)
    M = market.get("M_score", 50)
    B = 50  # placeholder until Behavior Layer is added

    prompt = f"""
Explain to a beginner how their recommended risk percentage was calculated.

Performance Score (P): {P}
Market Score (M): {M}
Behavior Score (B): {B}
Final Acceptable Risk %: {acceptable_risk_pct}

Rules:
- Explain in simple language.
- No predictions or financial advice.
- Focus on awareness, not instructions.
- Keep it to 2–3 paragraphs.
- Explain what increased or decreased the risk %.
"""

    try:
        import openai
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
        )
        return response.choices[0].message["content"].strip()
    except Exception:
        return "Risk explanation unavailable."


# ---------------------------------------------------------
# AI TRADE JOURNALING ENGINE
# ---------------------------------------------------------
def generate_trade_journal_entry(trade: Dict) -> str:
    """
    Creates a beginner-friendly journal entry for a single trade.
    Uses only the trade's own data.
    """

    symbol = trade.get("symbol", "Unknown")
    direction = trade.get("direction", "Long")
    entry = trade.get("entry", 0)
    exit_price = trade.get("exit", 0)
    pnl_r = trade.get("pnl_r", 0)
    pnl = trade.get("pnl", 0)
    rr = trade.get("rr", 0)
    risk_pct = trade.get("risk_pct", 0)
    result = trade.get("result", "Unknown")
    stop_price = trade.get("stop_price", 0)
    planned_entry = trade.get("planned_entry", entry)
    planned_exit = trade.get("planned_exit", exit_price)

    prompt = f"""
Write a beginner-friendly trade journal entry based on the following trade:

Symbol: {symbol}
Direction: {direction}
Entry: {entry}
Exit: {exit_price}
Planned Entry: {planned_entry}
Planned Exit: {planned_exit}
Stop Loss: {stop_price}
PnL (R): {pnl_r}
PnL ($): {pnl}
RR: {rr}
Risk %: {risk_pct}
Result: {result}

Rules:
- Explain what happened in simple language.
- Highlight execution quality (good or bad).
- Identify any behavioral patterns (chasing, hesitation, discipline).
- Suggest 1–2 improvements.
- Suggest 2–3 tags (e.g., "Good RR", "Chased Entry", "Over-Risked").
- No predictions or financial advice.
- Keep it to 2–3 short paragraphs.
"""

    try:
        import openai
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        return response.choices[0].message["content"].strip()
    except Exception:
        return "AI journal entry unavailable."
