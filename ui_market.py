import altair as alt
import pandas as pd
import streamlit as st

from ai_engines import generate_market_attribute_summaries
from market_layer import MarketConfig, compute_market_layer
from market_snapshot import update_market_snapshot


BLOOMBERG_CSS = """
<style>
.terminal-wrap { background:#0a0d10; border:1px solid #2d3237; border-radius:0; padding:10px; }
.terminal-head { font-size:11px; color:#8a939f; letter-spacing:0.06em; text-transform:uppercase; margin-bottom:6px; }
.metric-title { font-size:24px; font-weight:700; color:#e8edf2; margin-bottom:2px; }
.metric-score { font-size:42px; font-weight:800; line-height:1.0; color:#f5f7fa; }
.state-pill { display:inline-block; padding:4px 10px; font-size:12px; font-weight:700; border-radius:0; }
.state-green { background:#0f3b22; color:#7fe6aa; border:1px solid #1f5d39; }
.state-yellow { background:#4a3810; color:#ffd27a; border:1px solid #7a5f24; }
.state-red { background:#4c1f1f; color:#ff9090; border:1px solid #7a3434; }
.dense-rule { border-top:1px solid #2d3237; margin:8px 0 10px 0; }
.action-title { font-size:14px; font-weight:700; margin:2px 0 4px 0; color:#e8edf2; }
.tree-note { font-size:11px; color:#97a4b1; margin-bottom:8px; }
.small-note { font-size:11px; color:#97a4b1; }
.level-pad { margin-left: 10px; }
</style>
"""


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x)))


def _value(snapshot: dict, key: str, default=0.0):
    try:
        return float(snapshot.get(key, default))
    except Exception:
        return float(default)


def _state(score: float):
    if score >= 70:
        return "GREEN", "state-green"
    if score >= 45:
        return "YELLOW", "state-yellow"
    return "RED", "state-red"


def _confidence(data_rows):
    live = sum(1 for r in data_rows if r[2] == "LIVE")
    partial = sum(1 for r in data_rows if r[2] == "PARTIAL")
    placeholder = sum(1 for r in data_rows if r[2] == "PLACEHOLDER")
    return int(max(35, min(97, 50 + live * 10 + partial * 4 - placeholder * 10)))


def _header_status(data_rows):
    statuses = {r[2] for r in data_rows}
    if "PLACEHOLDER" in statuses:
        return "PLACEHOLDER"
    if "PARTIAL" in statuses:
        return "PARTIAL"
    return "LIVE"


def _data_row(snapshot: dict, label: str, key: str, proxy_keys: set, default="N/A"):
    raw = snapshot.get(key, default)
    if key not in snapshot or snapshot.get(key) is None:
        status = "PLACEHOLDER"
    elif key in proxy_keys:
        status = "PARTIAL"
    else:
        status = "LIVE"
    return (label, raw, status, key)


def _node(
    node_id: str,
    name: str,
    score: float,
    definition: str,
    purpose: str,
    formula: str,
    interpretation: list,
    data_used: list,
    bands: list,
    actions: dict,
    children=None,
    breakdown=None,
):
    return {
        "id": node_id,
        "name": name,
        "score": _clamp(score),
        "definition": definition,
        "purpose": purpose,
        "formula": formula,
        "interpretation": interpretation,
        "data_used": data_used,
        "bands": bands,
        "actions": actions,
        "children": children or [],
        "breakdown": breakdown or [],
    }


def _build_market_tree(snapshot: dict, market: dict, summaries: dict):
    proxy_like = {
        "cpi_z_surprise",
        "dxy_score",
        "equities_score",
        "etf_flow",
        "headline_sentiment",
    }

    ema_slope = _value(snapshot, "regime_ema_slope_score", 50.0)
    adx = _value(snapshot, "regime_adx_score", 50.0)
    structure = _value(snapshot, "regime_structure_score", 50.0)
    compression = _value(snapshot, "regime_compression_score", 50.0)

    atr_now = _value(snapshot, "btc_atr_current", 1.0)
    atr_30d = max(_value(snapshot, "btc_atr_30d", 1.0), 1.0)
    atr_norm = _clamp((atr_now / atr_30d) * 50.0)

    rates_raw = (snapshot.get("us10y_avg_5d", 4) - snapshot.get("us10y_current", 4)) * 10
    rates_score = _clamp(50 + rates_raw)
    inflation_score = _clamp(100 - abs(snapshot.get("cpi_z_surprise", 0)) * 20)
    dollar_score = _clamp(snapshot.get("dxy_score", 50))
    equities_score = _clamp(snapshot.get("equities_score", 50))

    funding_z = _value(snapshot, "funding_z", 0)
    oi_z = _value(snapshot, "oi_z", 0)
    etf_flow = _value(snapshot, "etf_flow", 0)
    stable_30d = _value(snapshot, "stable_30d_change_pct", 0)

    funding_score = _clamp(50 - funding_z * 20)
    oi_score = _clamp(50 - oi_z * 20)
    etf_score = _clamp(50 + etf_flow * 25)
    liquidity_score = _clamp(50 + stable_30d * 5)

    fear_greed = _clamp(snapshot.get("fear_greed", 50))
    social_sentiment = _clamp(50 + _value(snapshot, "headline_sentiment", 0) * 30)
    narrative_score = _clamp((fear_greed * 0.6) + (equities_score * 0.4))

    node_ema = _node(
        "market.price.regime.ema_slope",
        "EMA Slope",
        ema_slope,
        "Normalized EMA20 vs EMA50 slope score.",
        "Measures directional trend pressure.",
        r"EMA_{slope}=\mathrm{clamp}\left(50+200\cdot\frac{EMA_{20}-EMA_{50}}{EMA_{50}},0,100\right)",
        [
            "High values indicate stronger directional trend quality.",
            "Mid values indicate transition or neutral slope.",
            "Low values indicate trend deterioration.",
        ],
        [_data_row(snapshot, "EMA slope score", "regime_ema_slope_score", proxy_like)],
        [
            ("70-100", "Strong trend slope", "Favor trend continuation entries."),
            ("45-69", "Moderate slope", "Trade smaller with confirmation."),
            ("0-44", "Weak slope", "Avoid aggressive continuation trades."),
        ],
        {
            "primary": ["Trade with dominant trend direction.", "Require pullback + reclaim confirmation."],
            "secondary": ["Trim faster if slope softens.", "Use smaller initial size in transition."],
            "avoid": ["Counter-trend entries without catalyst.", "Late entries after extension."],
        },
    )

    node_adx = _node(
        "market.price.regime.adx",
        "ADX",
        adx,
        "Trend strength proxy normalized from ADX regime score.",
        "Separates strong trend from noisy range.",
        r"ADX_{score}=\mathrm{clamp}(ADX\times3,0,100)",
        [
            "High ADX score supports continuation strategies.",
            "Mid ADX score supports selective trend trades.",
            "Low ADX score implies range/chop risk.",
        ],
        [_data_row(snapshot, "ADX score", "regime_adx_score", proxy_like)],
        [
            ("68-100", "Strong trend", "Breakout-following is favored."),
            ("42-67", "Transition", "Confirm with structure before entry."),
            ("0-41", "Weak trend", "Prefer mean-reversion or stand aside."),
        ],
        {
            "primary": ["Use ADX as trend-strength gate.", "Trade breakouts only in stronger ADX states."],
            "secondary": ["Reduce target distance in mid ADX.", "Tighten invalidation in low ADX."],
            "avoid": ["Assuming trend persistence in low ADX.", "Overleveraging on weak trend strength."],
        },
    )

    node_structure = _node(
        "market.price.regime.structure",
        "Structure",
        structure,
        "Higher-high/higher-low structure quality score.",
        "Validates whether price action confirms directional hypothesis.",
        r"Structure=\begin{cases}80,&HH\land HL\ intact\\40,&otherwise\end{cases}",
        [
            "High structure score confirms cleaner continuation context.",
            "Broken structure increases failed breakout probability.",
            "Structure is a high-signal quality filter.",
        ],
        [_data_row(snapshot, "Structure score", "regime_structure_score", proxy_like)],
        [
            ("70-100", "Intact structure", "Continuation setups are statistically cleaner."),
            ("45-69", "Mixed structure", "Trade selectively with tighter risk."),
            ("0-44", "Broken structure", "Defensive posture; avoid aggressive continuation."),
        ],
        {
            "primary": ["Require intact structure for trend continuation.", "Use local swing invalidation."],
            "secondary": ["Scale in only after structure reclaim.", "Prefer lower leverage in mixed structure."],
            "avoid": ["Ignoring structure breaks.", "Averaging into broken market structure."],
        },
    )

    node_compression = _node(
        "market.price.regime.compression",
        "Compression",
        compression,
        "Bollinger bandwidth compression/expansion proxy score.",
        "Detects squeeze and expansion states that shape execution timing.",
        r"Compression=\mathrm{map}(BBW)\in[0,100]",
        [
            "High score suggests expansion-ready conditions.",
            "Mid score implies balanced volatility.",
            "Low score warns of noisy and directionless movement.",
        ],
        [_data_row(snapshot, "Compression score", "regime_compression_score", proxy_like)],
        [
            ("70-100", "Expansion-ready", "Look for breakout confirmation."),
            ("45-69", "Balanced", "Use normal execution rules."),
            ("0-44", "Noisy/choppy", "Avoid forced breakout entries."),
        ],
        {
            "primary": ["Time entries around confirmed expansion.", "Align compression with trend and structure."],
            "secondary": ["Wait for trigger candle when compressed.", "Trade smaller before expansion confirms."],
            "avoid": ["Anticipatory breakout chasing.", "Oversizing in low-quality compression states."],
        },
    )

    node_regime = _node(
        "market.price.regime",
        "Regime",
        market.get("regime_score", 50.0),
        "Composite market regime quality classifier.",
        "Determines strategy fit: trend, range, or stand-aside.",
        r"Regime=0.35\cdot EMA_{slope}+0.30\cdot ADX+0.20\cdot Structure+0.15\cdot Compression",
        [
            f"Current label: {market.get('regime_label', 'Unknown')}.",
            "High regime score favors trend-continuation systems.",
            "Mid regime score favors selective/mean-reversion behavior.",
            "Low regime score demands defensive execution.",
        ],
        [
            _data_row(snapshot, "EMA slope", "regime_ema_slope_score", proxy_like),
            _data_row(snapshot, "ADX", "regime_adx_score", proxy_like),
            _data_row(snapshot, "Structure", "regime_structure_score", proxy_like),
            _data_row(snapshot, "Compression", "regime_compression_score", proxy_like),
        ],
        [
            ("68-100", "Trending", "Deploy continuation systems."),
            ("42-67", "Ranging", "Use selective mean-reversion tactics."),
            ("0-41", "Choppy", "Reduce exposure and avoid forcing trades."),
        ],
        {
            "primary": ["Map strategy to regime before trade entry.", "Use continuation systems only in trending regime."],
            "secondary": ["Reduce hold time in ranging regime.", "Use time stops in choppy regime."],
            "avoid": ["Applying one strategy across all regimes.", "Ignoring regime transitions near thresholds."],
        },
        children=[node_ema, node_adx, node_structure, node_compression],
        breakdown=[
            {"component": "EMA Slope", "contribution": 0.35 * ema_slope},
            {"component": "ADX", "contribution": 0.30 * adx},
            {"component": "Structure", "contribution": 0.20 * structure},
            {"component": "Compression", "contribution": 0.15 * compression},
        ],
    )

    node_trend = _node(
        "market.price.trend",
        "Trend",
        ema_slope,
        "Directional momentum from EMA slope normalization.",
        "Provides directional bias filter for execution.",
        r"Trend=\mathrm{clamp}\left(50+200\cdot\frac{EMA_{20}-EMA_{50}}{EMA_{50}},0,100\right)",
        [
            "High score supports directional continuation.",
            "Mid score suggests transition state.",
            "Low score warns of weak directional edge.",
        ],
        [_data_row(snapshot, "Trend input", "regime_ema_slope_score", proxy_like)],
        [
            ("60-100", "Directional", "Trade with trend direction."),
            ("40-59", "Neutral", "Trade smaller and faster."),
            ("0-39", "Weak", "Avoid aggressive trend trades."),
        ],
        {
            "primary": ["Align position direction to trend score.", "Require pullback structure before entry."],
            "secondary": ["Tighten stop if trend decays.", "Scale in only after confirmation."],
            "avoid": ["Counter-trend momentum entries.", "Oversized entries in neutral trend zone."],
        },
    )

    node_volatility = _node(
        "market.price.volatility",
        "Volatility",
        market.get("volatility_score", 50.0),
        "Blended ATR and compression volatility quality metric.",
        "Calibrates stop distance and expansion probability.",
        r"Volatility=0.50\cdot \left(\frac{ATR_{now}}{ATR_{30d}}\times50\right)+0.50\cdot Compression",
        [
            "High score means active tape and potential follow-through.",
            "Mid score supports standard setups.",
            "Low score implies caution and trigger dependence.",
        ],
        [
            _data_row(snapshot, "ATR current", "btc_atr_current", proxy_like),
            _data_row(snapshot, "ATR 30D", "btc_atr_30d", proxy_like),
            _data_row(snapshot, "Compression", "regime_compression_score", proxy_like),
        ],
        [
            ("70-100", "Expansion", "Momentum setups favored."),
            ("45-69", "Balanced", "Use normal risk controls."),
            ("0-44", "Compressed/Noisy", "Wait for clean trigger."),
        ],
        {
            "primary": ["Set stop width by volatility regime.", "Execute only after expansion confirmation."],
            "secondary": ["Scale in slower when compressed.", "Adjust target distance to current ATR."],
            "avoid": ["Using tight static stops in high volatility.", "Chasing late expansion candles."],
        },
        breakdown=[
            {"component": "ATR normalized", "contribution": 0.50 * atr_norm},
            {"component": "Compression", "contribution": 0.50 * compression},
        ],
    )

    node_price = _node(
        "market.price",
        "Price",
        market.get("price_score", 50.0),
        "Composite of Trend, Volatility, and Regime quality.",
        "Assesses whether price action supports continuation or fakeouts.",
        r"Price=0.40\cdot Trend+0.30\cdot Volatility+0.30\cdot Regime",
        [
            "Trend carries highest weight inside Price score.",
            "Volatility and Regime act as quality filters.",
            "Price score is a core directional execution anchor.",
            summaries.get("price", "AI summary unavailable."),
        ],
        [
            _data_row(snapshot, "Trend score", "regime_ema_slope_score", proxy_like),
            _data_row(snapshot, "ATR current", "btc_atr_current", proxy_like),
            _data_row(snapshot, "ATR 30D", "btc_atr_30d", proxy_like),
            _data_row(snapshot, "Regime score", "regime_adx_score", proxy_like),
        ],
        [
            ("75-100", "Strong", "Continuation setups favored."),
            ("55-74", "Constructive", "Selective continuation with confirmation."),
            ("0-54", "Mixed/Weak", "Reduce size and wait for cleaner structure."),
        ],
        {
            "primary": ["Favor trend-aligned continuation trades.", "Gate entries by regime quality."],
            "secondary": ["Scale around pullbacks into structure.", "Reduce hold time if score decays."],
            "avoid": ["Breakout chasing in weak regime.", "Oversized entries into compressed tape."],
        },
        children=[node_trend, node_volatility, node_regime],
        breakdown=[
            {"component": "Trend", "contribution": 0.40 * ema_slope},
            {"component": "Volatility", "contribution": 0.30 * market.get("volatility_score", 50.0)},
            {"component": "Regime", "contribution": 0.30 * market.get("regime_score", 50.0)},
        ],
    )

    node_rates = _node(
        "market.macro.rates",
        "Rates",
        rates_score,
        "Rates pressure score from US10Y drift.",
        "Measures bond-yield impact on risk-asset appetite.",
        r"Rates=\mathrm{clamp}(50+10\cdot(US10Y_{5d}-US10Y_{now}),0,100)",
        [
            "Falling yields tend to support risk assets.",
            "Rising yields can compress crypto multiples.",
            "Use rates state as top-down risk filter.",
        ],
        [
            _data_row(snapshot, "US10Y current", "us10y_current", proxy_like),
            _data_row(snapshot, "US10Y 5D avg", "us10y_avg_5d", proxy_like),
        ],
        [
            ("70-100", "Supportive", "Risk-on posture more acceptable."),
            ("45-69", "Neutral", "Need confirmation from other pillars."),
            ("0-44", "Restrictive", "Reduce gross exposure."),
        ],
        {
            "primary": ["Respect rate regime before sizing risk.", "Trade lighter in restrictive rates state."],
            "secondary": ["Shorten hold windows under rates stress.", "Use hedge overlays into macro events."],
            "avoid": ["Ignoring yield spikes.", "Max leverage during hostile rates regime."],
        },
    )

    node_inflation = _node(
        "market.macro.inflation",
        "Inflation",
        inflation_score,
        "Inflation surprise quality score.",
        "Captures inflation shock risk to policy and liquidity expectations.",
        r"Inflation=\mathrm{clamp}(100-20\cdot |CPI_z|,0,100)",
        [
            "Large CPI surprises increase policy uncertainty.",
            "Lower surprise supports steadier risk sentiment.",
            "Use inflation state around macro event windows.",
        ],
        [_data_row(snapshot, "CPI z surprise", "cpi_z_surprise", proxy_like)],
        [
            ("70-100", "Calm inflation", "Event risk lower; trend trades cleaner."),
            ("45-69", "Moderate", "Keep event-aware risk controls."),
            ("0-44", "Shock risk", "De-risk around macro releases."),
        ],
        {
            "primary": ["Reduce size around high inflation-shock states.", "Wait for post-event direction confirmation."],
            "secondary": ["Use tighter invalidation around event candles.", "Prefer shorter duration trades."],
            "avoid": ["Holding oversized positions into CPI events.", "Assuming prior trend will survive surprise prints."],
        },
    )

    node_dxy = _node(
        "market.macro.dxy",
        "Dollar (DXY)",
        dollar_score,
        "Dollar strength score proxy.",
        "Tracks USD pressure that can suppress crypto risk appetite.",
        r"DXY_{score}=\mathrm{normalize}(DXY)\in[0,100]",
        [
            "Stronger dollar often weighs on crypto beta.",
            "Weakening dollar can support risk assets.",
            "Use as macro headwind/tailwind filter.",
        ],
        [_data_row(snapshot, "DXY score", "dxy_score", proxy_like)],
        [
            ("70-100", "Strong USD", "Reduce aggressive risk-on exposure."),
            ("45-69", "Neutral USD", "Use normal macro weighting."),
            ("0-44", "Weak USD", "Macro tailwind for risk assets."),
        ],
        {
            "primary": ["Adjust crypto beta to dollar regime.", "Demand stronger setup quality under strong USD."],
            "secondary": ["Trim faster when DXY rises abruptly.", "Scale only with confirming flow and price signals."],
            "avoid": ["Ignoring dollar spikes.", "Overtrading risk-on setups in strong-USD environments."],
        },
    )

    node_equities = _node(
        "market.macro.equities",
        "Equities",
        equities_score,
        "Equities risk appetite confirmation score.",
        "Measures broader risk-on or risk-off context spillover.",
        r"Equities_{score}=\mathrm{normalize}(equity\ trend,volatility)",
        [
            "Higher score supports broader risk-on posture.",
            "Lower score warns of cross-asset stress.",
            "Use as confirmation, not single trigger.",
        ],
        [_data_row(snapshot, "Equities score", "equities_score", proxy_like)],
        [
            ("70-100", "Risk-on", "Supports continuation risk-taking."),
            ("45-69", "Neutral", "Use selective execution."),
            ("0-44", "Risk-off", "Defensive allocation favored."),
        ],
        {
            "primary": ["Use equities regime as a risk-on check.", "Lower size in risk-off states."],
            "secondary": ["Look for divergence with crypto before scaling.", "Tighten risk when equities weaken."],
            "avoid": ["Ignoring broad risk-off signals.", "Assuming crypto decouples without evidence."],
        },
    )

    node_macro = _node(
        "market.macro",
        "Macro",
        market.get("macro_score", 50.0),
        "Macro and cross-asset backdrop composite.",
        "Determines if top-down conditions support crypto risk-taking.",
        r"Macro=\mathrm{clamp}(Rates+Inflation+0.5\cdot DXY+0.5\cdot Equities,0,100)",
        [
            "Macro can amplify or suppress otherwise valid setups.",
            "Rates and inflation shocks dominate short-term risk repricing.",
            "Dollar and equities provide cross-asset confirmation.",
            summaries.get("macro", "AI summary unavailable."),
        ],
        [
            _data_row(snapshot, "US10Y current", "us10y_current", proxy_like),
            _data_row(snapshot, "US10Y avg 5D", "us10y_avg_5d", proxy_like),
            _data_row(snapshot, "CPI surprise z", "cpi_z_surprise", proxy_like),
            _data_row(snapshot, "DXY score", "dxy_score", proxy_like),
            _data_row(snapshot, "Equities score", "equities_score", proxy_like),
        ],
        [
            ("70-100", "Tailwind", "Macro supports directional risk deployment."),
            ("50-69", "Neutral", "Need stronger micro confirmation."),
            ("0-49", "Headwind", "Reduce gross and tighten controls."),
        ],
        {
            "primary": ["Respect macro state before execution sizing.", "Align directional bias with macro pressure."],
            "secondary": ["Use event-aware position management.", "Prefer shorter holding periods in weak macro states."],
            "avoid": ["Ignoring macro event risk.", "Overleveraging in macro headwinds."],
        },
        children=[node_rates, node_inflation, node_dxy, node_equities],
        breakdown=[
            {"component": "Rates", "contribution": 0.30 * rates_score},
            {"component": "Inflation", "contribution": 0.20 * inflation_score},
            {"component": "Dollar (DXY)", "contribution": 0.25 * dollar_score},
            {"component": "Equities", "contribution": 0.25 * equities_score},
        ],
    )

    node_funding = _node(
        "market.flow.funding",
        "Funding Rates",
        funding_score,
        "Funding crowding pressure score.",
        "Flags crowded leverage conditions and squeeze risk.",
        r"Funding=\mathrm{clamp}(50-20\cdot Funding_z,0,100)",
        [
            "High positive funding-z lowers score and raises unwind risk.",
            "Balanced funding supports healthier trend continuation.",
            "Use as crowding risk filter.",
        ],
        [_data_row(snapshot, "Funding z", "funding_z", proxy_like)],
        [
            ("70-100", "Uncrowded", "Cleaner leverage context."),
            ("45-69", "Balanced", "Normal execution discipline."),
            ("0-44", "Crowded", "High unwind risk; reduce aggression."),
        ],
        {
            "primary": ["Reduce size in crowded funding states.", "Require extra confirmation under crowding."],
            "secondary": ["Prefer staggered entries.", "Tighten invalidation in low score states."],
            "avoid": ["Late entries in extreme positive funding.", "Ignoring squeeze risk."],
        },
    )

    node_oi = _node(
        "market.flow.oi",
        "Open Interest",
        oi_score,
        "Open-interest crowding score.",
        "Tracks leverage build-up and deleveraging risk.",
        r"OI=\mathrm{clamp}(50-20\cdot OI_z,0,100)",
        [
            "Rising OI-z can increase cascade susceptibility.",
            "Balanced OI improves market stability.",
            "Use with funding for crowding confirmation.",
        ],
        [_data_row(snapshot, "OI z", "oi_z", proxy_like)],
        [
            ("70-100", "Low crowding", "Healthier flow environment."),
            ("45-69", "Balanced", "Use normal controls."),
            ("0-44", "Crowded", "Defensive sizing recommended."),
        ],
        {
            "primary": ["Lower gross exposure in crowded OI states.", "Wait for unwind stabilization before scaling."],
            "secondary": ["Use tighter targets under elevated OI-z.", "Avoid adding into cascade conditions."],
            "avoid": ["High leverage during OI crowding spikes.", "Averaging into forced-unwind moves."],
        },
    )

    node_etf = _node(
        "market.flow.etf",
        "ETF Flows",
        etf_score,
        "Institutional ETF demand proxy score.",
        "Captures directional persistence from institutional capital flow.",
        r"ETF=\mathrm{clamp}(50+25\cdot ETF_{flow},0,100)",
        [
            "Positive ETF flow supports persistent demand.",
            "Negative flow can cap upside continuation.",
            "Use with price for trend durability checks.",
        ],
        [_data_row(snapshot, "ETF flow", "etf_flow", proxy_like)],
        [
            ("70-100", "Net inflow", "Supports directional continuation."),
            ("45-69", "Flat", "Neutral contribution."),
            ("0-44", "Net outflow", "Increases caution for long exposure."),
        ],
        {
            "primary": ["Favor long continuation when ETF flow is supportive.", "De-risk when sustained outflows appear."],
            "secondary": ["Monitor flow trend across sessions.", "Pair with regime for conviction upgrades."],
            "avoid": ["Ignoring persistent ETF outflows.", "Assuming weak flow can support aggressive longs."],
        },
    )

    node_liquidity = _node(
        "market.flow.liquidity",
        "Liquidity",
        liquidity_score,
        "Stablecoin liquidity impulse score.",
        "Proxies deployable crypto dry powder.",
        r"Liquidity=\mathrm{clamp}(50+5\cdot Stable_{30d\%},0,100)",
        [
            "Rising stablecoin supply can support risk allocation.",
            "Falling liquidity warns of weaker demand base.",
            "Use as medium-term flow context.",
        ],
        [_data_row(snapshot, "Stablecoin 30D %", "stable_30d_change_pct", proxy_like)],
        [
            ("70-100", "Growing liquidity", "Supports medium-term continuation."),
            ("45-69", "Stable", "Neutral liquidity support."),
            ("0-44", "Contracting liquidity", "Lower conviction for risk-on trades."),
        ],
        {
            "primary": ["Increase selectivity when liquidity contracts.", "Prefer setups with stronger confirmation."],
            "secondary": ["Track liquidity trend before scaling swings.", "Adjust hold horizon by liquidity regime."],
            "avoid": ["Aggressive swing sizing in contracting liquidity.", "Ignoring liquidity deterioration signals."],
        },
    )

    node_flow = _node(
        "market.flow",
        "Flow",
        market.get("flow_score", 50.0),
        "Composite of leverage crowding and capital-flow pressure.",
        "Detects squeeze/cascade risk and demand persistence.",
        r"Flow=\mathrm{clamp}(-10\cdot Funding_z-10\cdot OI_z+5\cdot ETF_{flow}+2\cdot Stable_{30d\%},0,100)",
        [
            "Flow differentiates healthy continuation from crowded risk.",
            "Funding and OI diagnose fragility in positioning.",
            "ETF and liquidity proxy demand durability.",
            summaries.get("flow", "AI summary unavailable."),
        ],
        [
            _data_row(snapshot, "Funding z", "funding_z", proxy_like),
            _data_row(snapshot, "OI z", "oi_z", proxy_like),
            _data_row(snapshot, "ETF flow", "etf_flow", proxy_like),
            _data_row(snapshot, "Stablecoin 30D %", "stable_30d_change_pct", proxy_like),
        ],
        [
            ("65-100", "Healthy", "Supportive flow and cleaner leverage."),
            ("40-64", "Balanced", "Neutral flow regime."),
            ("0-39", "Fragile", "Crowded and unstable; de-risk."),
        ],
        {
            "primary": ["Reduce size when flow turns fragile.", "Require additional confirmation in crowded states."],
            "secondary": ["Stagger entries around high-risk zones.", "Monitor flow trend persistence before scaling."],
            "avoid": ["Late trend entries into crowded flow states.", "Ignoring unwind risk signals."],
        },
        children=[node_funding, node_oi, node_etf, node_liquidity],
        breakdown=[
            {"component": "Funding Rates", "contribution": 0.25 * funding_score},
            {"component": "Open Interest", "contribution": 0.25 * oi_score},
            {"component": "ETF Flows", "contribution": 0.25 * etf_score},
            {"component": "Liquidity", "contribution": 0.25 * liquidity_score},
        ],
    )

    node_fng = _node(
        "market.sentiment.fear_greed",
        "Fear & Greed",
        fear_greed,
        "Fear & Greed sentiment index.",
        "Quantifies crowd psychology extremes.",
        r"FearGreed\in[0,100]",
        [
            "Extreme greed can precede pullbacks.",
            "Extreme fear can precede reflexive bounces.",
            "Use as contrarian context, not stand-alone trigger.",
        ],
        [_data_row(snapshot, "Fear & Greed", "fear_greed", proxy_like)],
        [
            ("70-100", "Greed", "Manage reversal risk carefully."),
            ("45-69", "Balanced", "No strong sentiment edge."),
            ("0-44", "Fear", "Look for stabilization before entries."),
        ],
        {
            "primary": ["Use extremes as warning, not immediate trigger.", "Require price/flow confirmation for contrarian trades."],
            "secondary": ["Tighten risk in extreme greed.", "Scale cautiously in extreme fear."],
            "avoid": ["Blindly fading momentum.", "Ignoring trend context at sentiment extremes."],
        },
    )

    node_social = _node(
        "market.sentiment.social",
        "Social Sentiment",
        social_sentiment,
        "Headline/social sentiment proxy score.",
        "Captures near-term narrative tone shifts.",
        r"Social=\mathrm{clamp}(50+30\cdot Headline_{sentiment},0,100)",
        [
            "Sharp social tone shifts can precede volatility bursts.",
            "Positive tone supports continuation only when flow confirms.",
            "Use with caution in crowded regimes.",
        ],
        [_data_row(snapshot, "Headline sentiment", "headline_sentiment", proxy_like)],
        [
            ("70-100", "Positive tone", "Supports continuation if structure confirms."),
            ("45-69", "Neutral", "Limited standalone edge."),
            ("0-44", "Negative tone", "Higher downside/whipsaw risk."),
        ],
        {
            "primary": ["Use social tone as secondary confirmation.", "Demand stronger setup quality in negative tone states."],
            "secondary": ["Reduce hold time in rapidly shifting sentiment.", "Pair with flow for better timing."],
            "avoid": ["Trading on headlines alone.", "Ignoring conflicting price/flow evidence."],
        },
    )

    node_narrative = _node(
        "market.sentiment.narrative",
        "Narrative",
        narrative_score,
        "Narrative persistence score from sentiment and cross-asset context.",
        "Evaluates whether market story supports sustained positioning.",
        r"Narrative=0.60\cdot FearGreed+0.40\cdot Equities",
        [
            "Strong narrative can support trend persistence.",
            "Weak narrative raises fade/whipsaw risk.",
            "Use to avoid overconfidence in isolated moves.",
        ],
        [
            _data_row(snapshot, "Fear & Greed", "fear_greed", proxy_like),
            _data_row(snapshot, "Equities score", "equities_score", proxy_like),
        ],
        [
            ("70-100", "Supportive narrative", "Allows selective trend continuation bias."),
            ("45-69", "Mixed narrative", "Use balanced execution."),
            ("0-44", "Fragile narrative", "De-risk and wait for clarity."),
        ],
        {
            "primary": ["Align narrative with price/flow before adding risk.", "Prefer selective execution in mixed narratives."],
            "secondary": ["Scale out faster when narrative weakens.", "Use tighter invalidation in fragile narratives."],
            "avoid": ["Overcommitting to single-theme narratives.", "Ignoring contradictory macro/flow conditions."],
        },
    )

    node_sentiment = _node(
        "market.sentiment",
        "Sentiment",
        market.get("sentiment_score", 50.0),
        "Composite psychology and narrative tone signal.",
        "Measures whether trader behavior is stretched or balanced.",
        r"Sentiment=0.60\cdot FearGreed+20\cdot Headline+0.20\cdot Equities",
        [
            "Sentiment is a confirmation layer, not a primary trigger.",
            "Extremes raise reversal probability.",
            "Combine with flow and regime for stronger decisions.",
            summaries.get("sentiment", "AI summary unavailable."),
        ],
        [
            _data_row(snapshot, "Fear & Greed", "fear_greed", proxy_like),
            _data_row(snapshot, "Headline sentiment", "headline_sentiment", proxy_like),
            _data_row(snapshot, "Equities score", "equities_score", proxy_like),
        ],
        [
            ("70-100", "Greed", "Continuation possible; watch reversal risk."),
            ("45-69", "Balanced", "Neutral sentiment contribution."),
            ("0-44", "Fear", "Contrarian opportunities only with confirmation."),
        ],
        {
            "primary": ["Use sentiment to confirm, not lead, execution.", "Fade extremes only with structure + flow agreement."],
            "secondary": ["Reduce hold time in extreme sentiment.", "Scale gradually in uncertain sentiment states."],
            "avoid": ["Blindly buying euphoria.", "Blindly shorting panic without stabilization."],
        },
        children=[node_fng, node_social, node_narrative],
        breakdown=[
            {"component": "Fear & Greed", "contribution": 0.50 * fear_greed},
            {"component": "Social Sentiment", "contribution": 0.25 * social_sentiment},
            {"component": "Narrative", "contribution": 0.25 * narrative_score},
        ],
    )

    root = _node(
        "market",
        "Market Score",
        market.get("M_score", 50.0),
        "Top-level composite of Price, Macro, Flow, and Sentiment.",
        "Provides immediate market regime quality and risk posture.",
        r"M_{score}=0.30\cdot Price+0.30\cdot Macro+0.25\cdot Flow+0.15\cdot Sentiment",
        [
            f"Current market mode: {market.get('market_risk_mode', 'Unknown')}.",
            "Use this as first-pass directional and sizing filter.",
            "Drill recursively to identify weakest supporting pillar.",
            "Trade only when top-down and bottom-up signals align.",
        ],
        [
            _data_row(snapshot, "Price score input", "regime_ema_slope_score", proxy_like),
            _data_row(snapshot, "Macro score input", "us10y_current", proxy_like),
            _data_row(snapshot, "Flow score input", "funding_z", proxy_like),
            _data_row(snapshot, "Sentiment score input", "fear_greed", proxy_like),
        ],
        [
            ("80-100", "Strong Risk-On", "Directional continuation with normal/aggressive risk."),
            ("60-79", "Constructive", "Selective continuation with normal controls."),
            ("0-59", "Neutral/Risk-Off", "Defensive risk posture and tighter filters."),
        ],
        {
            "primary": ["Trade with dominant top-level regime.", "Size by volatility and conviction alignment."],
            "secondary": ["Scale entries around liquidity levels.", "Hedge when pillar divergence appears."],
            "avoid": ["Counter-regime discretionary forcing.", "Ignoring weak sub-component warnings."],
        },
        children=[node_price, node_macro, node_flow, node_sentiment],
        breakdown=[
            {"component": "Price", "contribution": 0.30 * market.get("price_score", 50.0)},
            {"component": "Macro", "contribution": 0.30 * market.get("macro_score", 50.0)},
            {"component": "Flow", "contribution": 0.25 * market.get("flow_score", 50.0)},
            {"component": "Sentiment", "contribution": 0.15 * market.get("sentiment_score", 50.0)},
        ],
    )

    return root


def _flatten_tree(node, out):
    out[node["id"]] = node
    for child in node["children"]:
        _flatten_tree(child, out)


def _contains_selected(node, selected_id: str):
    if node["id"] == selected_id:
        return True
    return any(_contains_selected(child, selected_id) for child in node["children"])


def _render_tree(node):
    current_selected = st.session_state.get("market_selected_node", "market")

    if not node["children"]:
        if st.button(node["name"], key=f"btn_{node['id']}", use_container_width=True):
            st.session_state["market_selected_node"] = node["id"]
        return

    expanded = _contains_selected(node, current_selected)
    with st.expander(node["name"], expanded=expanded):
        if st.button(f"Select {node['name']}", key=f"sel_{node['id']}", use_container_width=True):
            st.session_state["market_selected_node"] = node["id"]
        for child in node["children"]:
            st.markdown("<div class='level-pad'>", unsafe_allow_html=True)
            _render_tree(child)
            st.markdown("</div>", unsafe_allow_html=True)


def _build_runtime_tree():
    snapshot = st.session_state.get("market_snapshot", {})
    if not snapshot:
        return None, None

    cfg = MarketConfig()
    market = compute_market_layer(snapshot, cfg)
    summaries = generate_market_attribute_summaries(market, snapshot)
    root = _build_market_tree(snapshot, market, summaries)

    index = {}
    _flatten_tree(root, index)

    if "market_selected_node" not in st.session_state:
        st.session_state["market_selected_node"] = "market"

    return root, index


def render_market_sidebar_navigation():
    root, _ = _build_runtime_tree()
    if root is None:
        st.sidebar.caption("Market snapshot unavailable.")
        return

    with st.sidebar:
        st.markdown("---")
        st.markdown("**Market Layer Tree**")
        st.markdown("<div class='tree-note'>Recursive drill-down navigation.</div>", unsafe_allow_html=True)
        _render_tree(root)


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
        .properties(height=170)
    )
    st.altair_chart(chart, use_container_width=True)


def render_market_dashboard(show_embedded_nav: bool = True):
    st.markdown(BLOOMBERG_CSS, unsafe_allow_html=True)
    st.title("Market Layer Terminal")

    if st.button("Refresh Snapshot"):
        update_market_snapshot(force=True)
        st.rerun()

    root, index = _build_runtime_tree()
    if root is None or index is None:
        st.error("Market snapshot unavailable.")
        return

    selected_id = st.session_state.get("market_selected_node", "market")
    node = index.get(selected_id, root)

    if show_embedded_nav:
        left, center, right = st.columns([0.22, 0.53, 0.25], gap="small")
    else:
        center, right = st.columns([0.68, 0.32], gap="small")

    with center:
        state_text, state_class = _state(node["score"])
        confidence = _confidence(node["data_used"])
        data_status = _header_status(node["data_used"])

        st.markdown("<div class='terminal-wrap'><div class='terminal-head'>Explainability Panel</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-title'>{node['name']}</div>", unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns([0.34, 0.22, 0.22, 0.22])
        with c1:
            st.markdown(f"<div class='metric-score'>{node['score']:.1f}</div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<span class='state-pill {state_class}'>{state_text}</span>", unsafe_allow_html=True)
        with c3:
            st.metric("Confidence", f"{confidence}%")
        with c4:
            st.metric("Data", data_status)

        st.markdown("<div class='dense-rule'></div>", unsafe_allow_html=True)

        st.write(f"**Definition:** {node['definition']}")
        st.write(f"**Purpose:** {node['purpose']}")

        st.write("**Interpretation**")
        for bullet in node["interpretation"][:4]:
            st.write(f"- {bullet}")

        if node["breakdown"]:
            st.write("**Component Breakdown**")
            _render_breakdown(node["breakdown"])

        st.write("**Formula**")
        st.latex(node["formula"])

        st.write("**Data Used**")
        df_data = pd.DataFrame(node["data_used"], columns=["Input", "Value", "Status", "Snapshot Key"])
        st.dataframe(df_data, use_container_width=True, hide_index=True)

        st.write("**Interpretation Table**")
        df_bands = pd.DataFrame(node["bands"], columns=["Score Range", "Meaning", "Trading Implication"])
        st.dataframe(df_bands, use_container_width=True, hide_index=True)

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
        st.markdown(
            "<div class='small-note'>Action panel stays visible while drilling through nested components.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
