# ================= ai_engines.py =================
from typing import List, Dict
import json


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

    # Deterministic fallback — always shows meaningful info
    def _risk_fallback():
        p_label = "strong" if P >= 70 else "average" if P >= 50 else "below average"
        m_label = "supportive" if M >= 70 else "neutral" if M >= 50 else "challenging"
        return (
            f"Your recommended risk is {acceptable_risk_pct:.2f}% per trade. "
            f"This is based on a Performance Score of {P:.1f} ({p_label}) and a Market Score of {M:.1f} ({m_label}). "
            f"When P and M are both high, the engine allows more risk because conditions favour continuation. "
            f"When either score drops, risk is reduced automatically to protect your account during weaker conditions. "
            f"The Behavior Score is currently held at 50 (neutral) pending its full implementation."
        )

    try:
        import openai
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
        )
        text = response.choices[0].message["content"].strip()
        return text if text else _risk_fallback()
    except Exception:
        return _risk_fallback()


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


# ---------------------------------------------------------
# AI PERFORMANCE ATTRIBUTE SUMMARIES
# ---------------------------------------------------------
def _fallback_performance_summaries(perf: Dict, regime: Dict = None) -> Dict[str, str]:
    p_score = float(perf.get("P_score", 50))
    winrate = float(perf.get("winrate", 0))
    loss_streak = int(perf.get("loss_streak", 0))
    drift = float(perf.get("drift", 0))
    quality = float(perf.get("trade_quality_score", 50))
    expectancy = float(perf.get("expectancy_r", 0))

    regime_score = float(regime.get("M_score", 50)) if regime else 50
    regime_mode = regime.get("market_risk_mode", "Unavailable") if regime else "Unavailable"

    return {
        "composite": (
            f"Composite performance is {'strong' if p_score >= 70 else 'balanced' if p_score >= 50 else 'fragile'} "
            f"with P-Score {p_score:.1f}. Focus on maintaining score stability rather than chasing short-term spikes."
        ),
        "winrate": (
            f"Winrate is {winrate:.1f}%, which {'supports' if winrate >= 50 else 'does not yet confirm'} a stable hit-rate profile. "
            "Use this with expectancy, since winrate alone can be misleading."
        ),
        "loss_streak": (
            f"Maximum loss streak is {loss_streak}. {'Risk throttling is important right now.' if loss_streak >= 3 else 'Streak pressure is currently manageable.'} "
            "Pause or reduce size when consecutive losses accelerate."
        ),
        "drift": (
            f"PnL drift is {drift:.2f}, meaning recent trade quality is {'improving' if drift > 0 else 'softening' if drift < 0 else 'flat'} versus baseline. "
            "A persistent negative drift often signals execution or regime mismatch."
        ),
        "quality": (
            f"Trade quality score is {quality:.1f}. {'Rule discipline is solid.' if quality >= 70 else 'Rule violations are meaningfully impacting consistency.'} "
            "Prioritize reducing preventable RR and risk-limit breaches."
        ),
        "expectancy": (
            f"Expectancy is {expectancy:.2f}R, indicating {'positive edge' if expectancy > 0 else 'fragile edge' if expectancy > -0.2 else 'negative edge'}. "
            "Expectancy should stay positive before increasing size."
        ),
        "regime": (
            f"Market regime reads {regime_mode} with score {regime_score:.1f}. "
            "Align risk exposure with regime quality rather than forcing constant sizing."
        ),
    }


def generate_performance_attribute_summaries(perf: Dict, regime: Dict = None) -> Dict[str, str]:
    """
    Returns short AI summaries for each performance attribute section.
    Keys: composite, winrate, loss_streak, drift, quality, expectancy, regime
    """
    fallback = _fallback_performance_summaries(perf, regime)

    prompt = f"""
You are writing concise, beginner-friendly performance insights for a trading dashboard.

Performance metrics:
{json.dumps(perf, default=str)}

Regime metrics:
{json.dumps(regime or {}, default=str)}

Return ONLY valid JSON with these keys:
- composite
- winrate
- loss_streak
- drift
- quality
- expectancy
- regime

Rules:
- Each value must be 1-2 short sentences.
- Plain language, no predictions, no financial advice.
- Mention current metric state and one practical focus point.
"""

    try:
        import openai
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=450,
        )
        raw = response.choices[0].message["content"].strip()

        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return fallback

        data = json.loads(raw[start:end + 1])
        for k, v in fallback.items():
            if k not in data or not isinstance(data[k], str) or not data[k].strip():
                data[k] = v
        return data
    except Exception:
        return fallback


def generate_performance_brief(perf: Dict, regime: Dict = None, summaries: Dict[str, str] = None) -> str:
    """
    Builds a short top-level AI brief from performance + regime context.
    Returns a concise 3-5 sentence dashboard narrative.
    """
    summaries = summaries or _fallback_performance_summaries(perf, regime)

    p_score = float(perf.get("P_score", 50))
    expectancy = float(perf.get("expectancy_r", 0))
    loss_streak = int(perf.get("loss_streak", 0))
    regime_score = float(regime.get("M_score", 50)) if regime else 50
    regime_mode = regime.get("market_risk_mode", "Unavailable") if regime else "Unavailable"

    fallback = (
        f"Performance currently reads {'strong' if p_score >= 70 else 'balanced' if p_score >= 50 else 'fragile'} "
        f"with P-Score {p_score:.1f}. Expectancy is {expectancy:.2f}R and loss streak is {loss_streak}. "
        f"Market regime is {regime_mode} ({regime_score:.1f}). "
        "Focus on preserving process quality and adjusting size when streak pressure or regime quality weakens."
    )

    prompt = f"""
Write a concise daily performance brief for a trading dashboard in 3-5 short sentences.

Performance metrics:
{json.dumps(perf, default=str)}

Regime metrics:
{json.dumps(regime or {}, default=str)}

Attribute summaries:
{json.dumps(summaries, default=str)}

Rules:
- Simple language for a beginner trader.
- No price predictions and no financial advice.
- Mention current state + one risk-control focus.
"""

    try:
        import openai
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=180,
        )
        text = response.choices[0].message["content"].strip()
        return text if text else fallback
    except Exception:
        return fallback


# ---------------------------------------------------------
# AI MARKET ATTRIBUTE SUMMARIES
# ---------------------------------------------------------
def _fallback_market_summaries(market: Dict, snapshot: Dict = None) -> Dict[str, str]:
    snapshot = snapshot or {}
    price = float(market.get("price_score", 50))
    macro = float(market.get("macro_score", 50))
    flow = float(market.get("flow_score", 50))
    sentiment = float(market.get("sentiment_score", 50))
    m_score = float(market.get("M_score", 50))

    return {
        "price": (
            f"Price structure reads {'strong uptrend' if price >= 70 else 'constructive' if price >= 50 else 'weak'}. "
            f"ATR and compression data {'support expansion risk' if price >= 60 else 'suggest caution'}."
        ),
        "macro": (
            f"Macro backdrop is {'supportive' if macro >= 60 else 'neutral' if macro >= 40 else 'hostile'}. "
            "Rates, equities, and DXY pressure will shape volatility today."
        ),
        "flow": (
            f"Positioning flows read {'healthy' if flow >= 60 else 'balanced' if flow >= 40 else 'crowded'}. "
            "Monitor funding and OI for reversal signals."
        ),
        "sentiment": (
            f"Market sentiment is {'bullish' if sentiment >= 60 else 'neutral' if sentiment >= 40 else 'fearful'}. "
            "Fear/greed and headline tone align with macro pressures."
        ),
        "overall": (
            f"Overall market score {m_score:.1f} indicates "
            f"{'strong risk-on' if m_score >= 80 else 'constructive' if m_score >= 60 else 'neutral' if m_score >= 40 else 'risk-off'} conditions. "
            "Size and directional bias should respect this regime."
        ),
    }


def generate_market_attribute_summaries(market: Dict, snapshot: Dict = None) -> Dict[str, str]:
    """
    Returns short AI summaries for each market attribute section.
    Keys: price, macro, flow, sentiment, overall
    """
    fallback = _fallback_market_summaries(market, snapshot)

    prompt = f"""
You are writing concise, beginner-friendly market insights for a dashboard.

Market metrics:
{json.dumps(market, default=str)}

Market snapshot:
{json.dumps(snapshot or {}, default=str)}

Return ONLY valid JSON with these keys:
- price
- macro
- flow
- sentiment
- overall

Rules:
- Each value must be 1-2 short sentences.
- Plain language, no predictions, no financial advice.
- Mention current state and one actionable observation.
"""

    try:
        import openai
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )
        raw = response.choices[0].message["content"].strip()

        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return fallback

        data = json.loads(raw[start:end + 1])
        for k, v in fallback.items():
            if k not in data or not isinstance(data[k], str) or not data[k].strip():
                data[k] = v
        return data
    except Exception:
        return fallback


def generate_market_brief(market: Dict, snapshot: Dict = None, summaries: Dict[str, str] = None) -> str:
    """
    Builds a short top-level AI brief from market context.
    Returns a concise 3-5 sentence market narrative.
    """
    summaries = summaries or _fallback_market_summaries(market, snapshot)
    m_score = float(market.get("M_score", 50))
    mode = market.get("market_risk_mode", "Unavailable")

    fallback = (
        f"Market regime is {mode} with score {m_score:.1f}. "
        f"Price structure, macro, flow, and sentiment all factor into this reading. "
        "Use this to calibrate size and risk exposure; avoid forcing trades against regime."
    )

    prompt = f"""
Write a concise daily market brief for a trading dashboard in 3-5 short sentences.

Market metrics:
{json.dumps(market, default=str)}

Market snapshot:
{json.dumps(snapshot or {}, default=str)}

Attribute summaries:
{json.dumps(summaries, default=str)}

Rules:
- Simple language for a beginner trader.
- No price predictions and no financial advice.
- Mention current regime + one risk-control focus.
"""

    try:
        import openai
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=180,
        )
        text = response.choices[0].message["content"].strip()
        return text if text else fallback
    except Exception:
        return fallback
