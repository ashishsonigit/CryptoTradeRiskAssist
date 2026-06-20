# Prompt To Regenerate TradePlanner 3.0

Use this prompt in a coding model to regenerate the app from scratch.

---

Build a production-style Streamlit trading application named TradePlanner 3.0 with the following architecture and behavior.

## 1) Tech Stack
- Python 3.10+
- Streamlit
- pandas
- numpy
- altair
- requests
- JSON file persistence

## 2) Required Files
Create these modules:
- app.py
- storage.py
- settings.py
- market_snapshot.py
- market_layer.py
- performance_layer.py
- risk_engine.py
- ui_trade.py
- ui_market.py
- ui_perf.py
- ui_history.py
- ai_engines.py
- trade_history.json

## 3) App Navigation
Sidebar pages:
- Trade Planner
- Market Layer
- Performance Layer
- Trade History
- Settings

`app.py` must:
- configure page layout
- trigger market snapshot scheduling on startup
- route each page renderer
- support sidebar navigation trees for Market and Performance pages

## 4) Core Scoring System
### 4.1 Market score (M)
Implement `compute_market_layer(snapshot, cfg)` using 4 pillars:
- Price structure and volatility
- Macro and cross-asset
- Positioning and flow
- Sentiment and narrative

Include regime sub-score using:
- EMA slope score
- ADX score
- Structure score
- Compression score

Return:
- pillar scores
- regime score and label
- final `M_score`
- `market_risk_mode`

### 4.2 Performance score (P)
Implement `compute_performance_layer(df, initial_balance)`.
Compute:
- winrate score
- loss streak score
- pnl drift score
- trade quality score
- expectancy score
- balance-aware metrics:
  - equity_return_pct
  - recent_return_pct
  - max_drawdown_pct
  - current_drawdown_pct
  - growth_score
  - drawdown_score
  - balance_efficiency_score

Return canonical `P_score` plus component metrics.

## 5) Risk Engine
Implement `compute_risk_and_perf(trades, state)`.
Risk percent must depend on:
- P score
- M score
- base risk percent
- risk mode multiplier
- market gate
- upside boost
- balance ratio (current_balance / initial_balance)
- drawdown protection

Use formula shape:
- combined signal = 0.60*P + 0.40*M
- base scaling term around `(0.50 + combined/100)`
- clamp final recommended risk to safe range (for example 0.10% to 5.00%)

Return:
- acceptable_risk_pct
- P_score
- M_score
- perf and market payloads
- rich `risk_breakdown`

## 6) Balance Tracking (Mandatory)
Implement canonical balance utilities in storage:
- get initial balance from session state with default 10000
- compute balance history from trade list
- get current balance
- get peak balance

Persist per trade:
- initial_balance
- balance_before
- balance_after
- cumulative_pnl

State flow must be:
Initial Balance -> Trades -> PnL -> Updated Balance -> Risk Calculation -> Performance

## 7) Trade Planner UX
### 7.1 Top action panel (first visible)
Show prominently:
- Balance
- Recommended Risk %
- Performance Score
- Market Score
- Net PnL
- plain-language explanation
- balance status message:
  - if growing: "Account growing - risk scaling appropriately"
  - if drawdown: "Drawdown detected - risk reduced to protect capital"

### 7.2 Trade configuration
- Symbol dropdown inside Trade Configuration
- symbols: BTC, ETH, SOL, BNB, XRP
- auto-fetch symbol price when symbol changes
- auto-update dependent fields:
  - entry
  - stop
  - sl distance
  - default exit seed

### 7.3 Plan trade section
- include direction, entry, stop, exit
- Exit Price must be configurable
- remove RR input from Plan section
- calculate RR when Plan is pressed:
  - `rr = abs(exit - entry) / abs(entry - stop)`

### 7.4 Position sizing
- risk amount = current_balance * risk_pct
- units = risk_amount / sl_distance

### 7.5 Outcome styling
- winning trade badge in green
- losing trade badge in red
- pnl value color-coded green/red

## 8) Settings Page
Include:
- Initial Balance input
- Current Balance metric
- Risk mode
- Base Risk %
- Market pillar weight sliders
- Performance tuning controls
- reset button that clears trades and resets state

## 9) Trade History Page
Show:
- styled table with green profit rows and red loss rows
- columns including Trade #, pnl, cumulative pnl, balance
- PnL chart with red/green points
- separate chart titled `Balance vs Trade Number`
  - X axis: trade index
  - Y axis: balance line
  - optional overlay: pnl bars

## 10) Market and Performance Dashboards
Both dashboards should:
- use high-contrast score values
- color score values by threshold:
  - >= 70 green
  - 50-69 amber
  - < 50 red
- provide recursive explainability trees
- include trader action panel content

## 11) Data and Error Handling
- robustly parse numeric fields from older trades
- support backward compatibility when new fields are missing
- avoid hard crashes on API failures, fallback gracefully
- keep deterministic fallbacks for AI summaries

## 12) Acceptance Criteria
The generated app is complete when:
- all pages render
- trade planning and saving work
- balance updates after each trade
- recommended risk responds to drawdown/equity changes
- performance score includes balance-aware metrics
- history displays balance progression
- no compile errors in key modules

Also provide:
- a short run guide
- a list of required pip dependencies
- a quick validation checklist

---

End of prompt.
