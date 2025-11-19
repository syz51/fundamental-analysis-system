# DD-026: Macro Reports Format & Delivery

**Status**: Approved
**Date**: 2025-11-19
**Decider(s)**: System Architecture Team
**Related Docs**:

- [Human Integration](../operations/02-human-integration.md)
- [Analysis Pipeline](../operations/01-analysis-pipeline.md)
- [Data Management](../operations/03-data-management.md)

**Related Decisions**:

- [DD-022: Macro Analyst Agent](DD-022_MACRO_ANALYST_AGENT.md) - Macro Analyst deliverables
- [DD-001: Gate 6 Learning Validation](DD-001_GATE_6_LEARNING_VALIDATION.md) - Human gate structure

---

## Context

### The Problem

DD-022 defines Macro Analyst Agent but leaves report specifications under-defined:

**Format Questions**:
- What exactly goes in each report section?
- How detailed should economic indicator analysis be?
- What visualizations are required in dashboard?
- PDF vs interactive format tradeoffs?

**Delivery Questions**:
- Which reports go to which human gates?
- When to send full report vs summary?
- How to trigger ad-hoc reports (regime changes, Fed announcements)?
- What's the information hierarchy (what human sees first)?

**Integration Questions**:
- How do agents consume macro reports (API? Neo4j query? PDF parsing)?
- How to present macro context in gate dashboards?
- How to handle report versioning (monthly updates, corrections)?

**Impact of Under-Specification**:

Without clear report specs:
- Implementation teams make inconsistent decisions
- Gate dashboards show different information layouts
- Report generation logic becomes ad-hoc (technical debt)
- Human gates receive inconsistent macro context

### Real-World Report Standards

**Professional Macro Reports**:

- **Goldman Sachs Top of Mind**: 20-30 pages, quarterly, covers 1 major theme in depth
- **JPMorgan Global Data Watch**: 40-50 pages, weekly, comprehensive indicator review
- **BCA Research**: 15-25 pages, monthly, regime analysis + asset allocation

**Common Elements**:
1. Executive summary (1-2 pages, key takeaways)
2. Indicator dashboard (heatmap, time series charts)
3. Regime/cycle analysis (where we are, where we're going)
4. Sector/asset implications (investment recommendations)
5. Risk scenarios (upside/downside cases)

**Report Length**: 10-30 pages typical (shorter = monthly updates, longer = quarterly deep dives)

**Format**: PDF + Excel data tables + interactive dashboards

### Why This Needs Resolution Now

Phase 2 implementation of Macro Analyst (DD-022) requires:

- Report templates for automated generation
- Dashboard wireframes for UI team
- Integration specs for agent consumption
- Clear deliverables for testing/validation

**Blocking Dependencies**:
- DD-022 implementation starts Week 1 (needs report templates)
- Gate dashboard UI design (needs layout specs)
- Agent integration testing (needs API specs)

---

## Decision

**Standardize macro reports in 3 formats: (1) Monthly Macro Report (PDF, 8-12 pages, comprehensive), (2) Macro Dashboard (interactive, real-time), (3) API endpoints for agent consumption. Reports delivered to Gates 1/2/5 based on decision needs, with full reports monthly + ad-hoc summaries on regime changes.**

### Monthly Macro Report Format

**Format**: PDF, 8-12 pages
**Frequency**: Monthly (1st week of month) + ad-hoc (regime changes, major Fed events)
**Distribution**: All human gates (1/2/5), all agents (background context)

**Structure**:

**Page 1: Executive Summary**

```
┌─────────────────────────────────────────────────────────┐
│ MACRO OUTLOOK - [MONTH YEAR]                           │
├─────────────────────────────────────────────────────────┤
│ CURRENT REGIME: [BEAR_HIGH_RATES]                      │
│ Confidence: [85%]                                       │
│ Duration: [8 months]                                    │
│ vs Last Month: [No change]                             │
├─────────────────────────────────────────────────────────┤
│ KEY TAKEAWAYS:                                          │
│                                                         │
│ 1. Fed maintaining restrictive policy (5.5% Fed Funds) │
│    - Inflation declining but above target (3.2% CPI)   │
│    - No rate cuts expected until Q3 2025               │
│                                                         │
│ 2. Growth slowing but avoiding recession               │
│    - GDP: 1.8% (Q4 2024), down from 2.5% (Q3)         │
│    - Labor market cooling (unemployment 4.1%)          │
│                                                         │
│ 3. Sector rotation favors defensives                   │
│    - Overweight: Healthcare (78), Utilities (72)       │
│    - Underweight: Tech (45), Real Estate (32)          │
│                                                         │
│ 4. Transition risk: 30% probability NORMAL by Q2       │
│    - Leading indicators: Yield curve steepening        │
│    - Watch: Fed rhetoric shift, inflation trajectory   │
├─────────────────────────────────────────────────────────┤
│ MONTH-OVER-MONTH CHANGES:                              │
│ • Regime: No change (BEAR_HIGH_RATES since Mar 2024)  │
│ • Sector rankings: Healthcare +5pts, Tech -3pts        │
│ • Discount rates: +0.2% (Fed raised rates 0.25%)      │
│ • Risk level: Elevated → High (VIX +4pts to 28)       │
└─────────────────────────────────────────────────────────┘
```

**Content**:
- Current regime classification + confidence level
- Regime duration (how long in current regime)
- 3-5 key takeaways (bullet points, investment-relevant)
- Month-over-month changes (what shifted)

**Length**: 1 page (strict)

**Pages 2-3: Economic Indicators**

```
┌─────────────────────────────────────────────────────────┐
│ ECONOMIC INDICATORS DASHBOARD                           │
├──────────────┬──────────┬──────────┬─────────┬─────────┤
│ Indicator    │ Current  │ %ile     │ 3mo Δ   │ Signal  │
├──────────────┼──────────┼──────────┼─────────┼─────────┤
│ GROWTH                                                  │
│ GDP (QoQ)    │ 1.8%     │ 35th     │ -0.7%   │ 🟡      │
│ Ind Prod     │ 102.5    │ 48th     │ +0.3    │ 🟢      │
│ Unemployment │ 4.1%     │ 58th     │ +0.2%   │ 🟡      │
│                                                         │
│ INFLATION                                               │
│ CPI (YoY)    │ 3.2%     │ 75th     │ -0.4%   │ 🟡      │
│ PCE          │ 2.8%     │ 72nd     │ -0.3%   │ 🟡      │
│ Wages        │ 4.5%     │ 68th     │ -0.1%   │ 🟢      │
│                                                         │
│ MONETARY                                                │
│ Fed Funds    │ 5.50%    │ 92nd     │ +0.25%  │ 🔴      │
│ 10Y Treasury │ 4.65%    │ 85th     │ +0.15%  │ 🟡      │
│ Yield Curve  │ +0.25%   │ 45th     │ +0.10%  │ 🟢      │
│                                                         │
│ CREDIT                                                  │
│ Corp Spreads │ 125bps   │ 55th     │ +10bps  │ 🟡      │
│ HY Spreads   │ 425bps   │ 68th     │ +25bps  │ 🔴      │
│                                                         │
│ SENTIMENT                                               │
│ VIX          │ 28.5     │ 78th     │ +4.2    │ 🔴      │
│ Consumer Conf│ 98.5     │ 42nd     │ -2.1    │ 🟡      │
└──────────────┴──────────┴──────────┴─────────┴─────────┘

Legend:
%ile = Historical percentile (0-100, 50=median)
3mo Δ = 3-month change
Signal = 🟢 Positive, 🟡 Neutral, 🔴 Concerning

[TIME SERIES CHARTS - 4 panels]
- Panel 1: GDP growth (quarterly, 5Y history)
- Panel 2: Inflation indicators (CPI, PCE, monthly, 2Y history)
- Panel 3: Yield curve (current vs 3mo ago vs 1yr ago)
- Panel 4: VIX (daily, 1Y history with regime markers)
```

**Content**:
- Indicator table (15-20 key indicators across 5 categories)
- Historical percentile ranking (context: is this high/low/normal?)
- 3-month trend (direction: rising/falling/stable)
- Signal color coding (green/yellow/red)
- Time series charts (4-6 key indicators, visual trends)

**Length**: 2-3 pages

**Pages 4-5: Regime Analysis**

```
┌─────────────────────────────────────────────────────────┐
│ REGIME ANALYSIS: BEAR_HIGH_RATES                       │
├─────────────────────────────────────────────────────────┤
│ CHARACTERISTICS:                                        │
│ • Market: S&P -12% YoY, sector dispersion high         │
│ • Policy: Fed Funds 5.5% (restrictive territory)       │
│ • Volatility: VIX 28.5 (elevated)                      │
│ • Duration: 8 months (Mar 2024 - present)              │
│                                                         │
│ HISTORICAL CONTEXT:                                     │
│ Similar episodes (Fed tightening cycles):               │
│ • 2018 (Q4): 3 months, S&P -14%, ended with Fed pivot  │
│ • 2022-2023: 12 months, S&P -18%, ended with disinfl   │
│ • 1994: 8 months, S&P -9%, soft landing               │
│                                                         │
│ Current episode comparison:                             │
│ • Duration: 8 months (median: 6 months)                │
│ • S&P decline: -12% (median: -10%)                     │
│ • Fed peak rate: 5.5% (2022 peak: 5.25%)              │
│ • Inflation path: 7.0% → 3.2% (2022: 9.1% → 3.1%)    │
├─────────────────────────────────────────────────────────┤
│ LEADING INDICATORS FOR REGIME TRANSITION:               │
│                                                         │
│ [SIGNAL STRENGTH BARS]                                  │
│ Yield curve steepening    ████████░░  80% (strong)     │
│ Inflation decline         ███████░░░  70% (strong)     │
│ Fed rhetoric shift        ████░░░░░░  40% (weak)       │
│ Credit spreads stable     ██████░░░░  60% (moderate)   │
│ Leading indicators (LEI)  ███░░░░░░░  30% (weak)       │
│                                                         │
│ Overall transition signal: 56% (moderate)               │
├─────────────────────────────────────────────────────────┤
│ REGIME TRANSITION PROBABILITIES (Next 3 Months):        │
│                                                         │
│ [PROBABILITY CHART]                                     │
│ BEAR_HIGH_RATES (stay)     ████████████████ 55%        │
│ NORMAL (transition)        ██████████░░░░░░ 30%        │
│ BULL_HIGH_RATES (unlikely) ██░░░░░░░░░░░░░░ 10%        │
│ BEAR_LOW_RATES (unlikely)  █░░░░░░░░░░░░░░░  5%        │
├─────────────────────────────────────────────────────────┤
│ SCENARIOS (6-Month Forward):                            │
│                                                         │
│ BASE CASE (60%): Fed holds, disinflation continues      │
│ • S&P: +3% to +8% (modest gains)                       │
│ • Transition to NORMAL by Q2 2025                      │
│ • Catalysts: Inflation 2.5%, Fed signals pause         │
│                                                         │
│ BULL CASE (25%): Fed cuts early (March 2025)           │
│ • S&P: +12% to +18% (strong rally)                     │
│ • Transition to BULL_HIGH_RATES by Q1 2025             │
│ • Catalysts: Recession fears, sudden inflation drop    │
│                                                         │
│ BEAR CASE (15%): Inflation re-accelerates              │
│ • S&P: -8% to -15% (continued decline)                 │
│ • Stay BEAR_HIGH_RATES through 2025                    │
│ • Catalysts: Wage-price spiral, geopolitical shock     │
└─────────────────────────────────────────────────────────┘
```

**Content**:
- Current regime characteristics (market, policy, volatility, duration)
- Historical context (similar past episodes, comparison)
- Leading indicators (signals for regime transition)
- Transition probabilities (next 3-6 months)
- Scenarios (base/bull/bear cases with probabilities, catalysts)

**Length**: 2 pages

**Pages 6-8: Sector Implications**

```
┌─────────────────────────────────────────────────────────┐
│ SECTOR POSITIONING FOR BEAR_HIGH_RATES REGIME          │
├──────────────┬───────┬──────────┬───────────┬─────────┤
│ Sector       │ Score │ Rec      │ Rationale │ Δ MoM   │
├──────────────┼───────┼──────────┼───────────┼─────────┤
│ Healthcare   │ 78    │ OW ★★★   │ Defensive │ +5      │
│ Utilities    │ 72    │ OW ★★    │ Yields    │ +2      │
│ Cons Staples │ 68    │ OW ★★    │ Recession │ +1      │
│ Financials   │ 58    │ N        │ Rates     │ -2      │
│ Industrials  │ 52    │ N        │ Cyclical  │ -1      │
│ Energy       │ 48    │ N        │ Demand    │ +3      │
│ Cons Disc    │ 42    │ UW ★     │ Consumer  │ -4      │
│ Tech         │ 45    │ UW ★     │ Multiples │ -3      │
│ Comm Svcs    │ 40    │ UW ★★    │ Ad spend  │ -2      │
│ Materials    │ 38    │ UW ★★    │ Growth    │ -1      │
│ Real Estate  │ 32    │ UW ★★★   │ Rates     │ -2      │
└──────────────┴───────┴──────────┴───────────┴─────────┘

Legend:
Score = Sector favorability (0-100)
Rec = Recommendation (OW=Overweight, N=Neutral, UW=Underweight)
★★★ = Strong conviction
Δ MoM = Month-over-month score change

[SECTOR ROTATION MATRIX]
       │ Improving │ Deteriorating
───────┼───────────┼──────────────
Strong │ Healthcare│ (empty)
       │ Energy    │
───────┼───────────┼──────────────
Weak   │ Utilities │ Tech
       │           │ Real Estate
       │           │ Cons Disc

[HISTORICAL SECTOR PERFORMANCE IN BEAR_HIGH_RATES]
(Bar chart: avg 3mo returns by sector in past BEAR_HIGH_RATES episodes)

OVERWEIGHT RATIONALE:

1. Healthcare (Score: 78, +5 MoM)
   - Historical: +4.2% avg in BEAR_HIGH_RATES regimes
   - Current: Trading at 16.5x P/E (vs 18.0x historical avg) = attractive
   - Macro sensitivity: Low (defensive, inelastic demand)
   - Momentum: Outperforming S&P by +6% last 3 months
   - Risks: Policy changes, drug pricing pressures
   - Conviction: High ★★★

2. Utilities (Score: 72, +2 MoM)
   - Historical: +3.8% avg in BEAR_HIGH_RATES regimes
   - Current: Yield curve steepening benefits long-duration assets
   - Macro sensitivity: Moderate (rate-sensitive but defensive)
   - Momentum: Stable performance, +2% vs S&P
   - Risks: If Fed raises rates further, long-duration hurts
   - Conviction: Medium ★★

UNDERWEIGHT RATIONALE:

1. Real Estate (Score: 32, -2 MoM)
   - Historical: -7.2% avg in BEAR_HIGH_RATES regimes
   - Current: REITs highly rate-sensitive (5.5% Fed Funds major headwind)
   - Macro sensitivity: Very high (leverage, financing costs)
   - Momentum: Underperforming S&P by -12% last 3 months
   - Risks: If Fed cuts earlier than expected, could reverse
   - Conviction: High ★★★

2. Technology (Score: 45, -3 MoM)
   - Historical: -4.5% avg in BEAR_HIGH_RATES regimes
   - Current: High multiples (25x P/E) vulnerable to rate increases
   - Macro sensitivity: High (long-duration growth stocks)
   - Momentum: Underperforming S&P by -8% last 3 months
   - Risks: AI narrative could drive outperformance despite rates
   - Conviction: Low-Medium ★

MACRO SENSITIVITIES:

[TABLE: How sectors react to regime factors]
Sector       │ Fed Funds ↑ │ GDP ↓ │ VIX ↑
─────────────┼─────────────┼───────┼──────
Healthcare   │ -0.2        │ +0.1  │ -0.3
Utilities    │ -0.5        │ +0.2  │ -0.2
Tech         │ -0.8        │ -0.6  │ -0.9
Real Estate  │ -1.2        │ -0.4  │ -0.7

(Coefficients: sensitivity of sector returns to 1% change in factor)
```

**Content**:
- Sector favorability rankings (11 GICS sectors, scored 0-100)
- Recommendations (overweight/neutral/underweight with conviction stars)
- Rationale per sector (historical performance, current valuation, sensitivities, risks)
- Sector rotation matrix (improving/deteriorating × strong/weak)
- Historical sector performance in current regime (backtested data)
- Macro sensitivities table (how sectors react to regime factors)

**Length**: 2-3 pages

**Pages 9-10: Risks & Catalysts**

```
┌─────────────────────────────────────────────────────────┐
│ RISK FACTORS & CATALYSTS                                │
├─────────────────────────────────────────────────────────┤
│ UPSIDE RISKS (Scenarios better than base case):         │
│                                                         │
│ 1. Disinflation accelerates faster than expected (25%)  │
│    • Trigger: Inflation falls to 2.5% by Feb 2025      │
│    • Impact: Fed signals cuts as early as March        │
│    • Sector winners: Tech (+15%), Cons Disc (+12%)     │
│    • Probability: 25% (moderate)                       │
│    • Monitoring: Monthly CPI, Fed rhetoric             │
│                                                         │
│ 2. Soft landing confirms (20%)                         │
│    • Trigger: Unemployment stabilizes below 4.5%       │
│    • Impact: Recession fears fade, multiples expand    │
│    • Sector winners: Industrials (+10%), Financials    │
│    • Probability: 20% (low-moderate)                   │
│    • Monitoring: NFP, jobless claims, GDP              │
│                                                         │
│ 3. Geopolitical de-escalation (10%)                    │
│    • Trigger: Major conflict resolution                │
│    • Impact: Energy prices fall, inflation eases       │
│    • Sector winners: Cons Disc, Energy (paradox)       │
│    • Probability: 10% (low)                            │
│    • Monitoring: Geopolitical news, oil prices         │
├─────────────────────────────────────────────────────────┤
│ DOWNSIDE RISKS (Scenarios worse than base case):        │
│                                                         │
│ 1. Inflation re-acceleration (15%)                      │
│    • Trigger: Wage-price spiral, oil shock >$100/bbl   │
│    • Impact: Fed forced to raise rates to 6%+          │
│    • Sector losers: Real Estate (-20%), Tech (-15%)    │
│    • Probability: 15% (low-moderate)                   │
│    • Monitoring: Wage growth, oil prices, CPI          │
│                                                         │
│ 2. Hard landing / recession (20%)                      │
│    • Trigger: Unemployment jumps above 5%              │
│    • Impact: Earnings collapse, credit spreads widen   │
│    • Sector losers: Cons Disc (-25%), Financials       │
│    • Probability: 20% (low-moderate)                   │
│    • Monitoring: LEI, jobless claims, ISM PMI          │
│                                                         │
│ 3. Credit event / financial stress (10%)               │
│    • Trigger: Major corporate default, banking stress  │
│    • Impact: VIX spike, flight to quality              │
│    • Sector losers: Financials (-30%), HY bonds        │
│    • Probability: 10% (low)                            │
│    • Monitoring: HY spreads, bank stocks, repo rates   │
├─────────────────────────────────────────────────────────┤
│ POLICY UNCERTAINTIES:                                   │
│ • Fed policy path (cuts delayed beyond Q3 2025?)       │
│ • Fiscal policy (government shutdown, debt ceiling?)   │
│ • Regulatory changes (antitrust, ESG rules?)           │
│ • Trade policy (tariffs, China relations?)             │
├─────────────────────────────────────────────────────────┤
│ EVENT CALENDAR (Next 3 Months):                         │
│                                                         │
│ HIGH PRIORITY:                                          │
│ • Jan 31: FOMC meeting (rate decision + Fed rhetoric)  │
│ • Feb 14: CPI release (Jan inflation data)             │
│ • Feb 28: GDP advance estimate (Q4 2024)               │
│ • Mar 20: FOMC meeting (potential first cut?)          │
│                                                         │
│ MEDIUM PRIORITY:                                        │
│ • Feb 2: NFP (Jan employment data)                     │
│ • Feb 15: Retail sales (consumer strength)             │
│ • Mar 1: ISM Manufacturing (growth indicators)         │
│                                                         │
│ WATCH LIST:                                             │
│ • Earnings season (Jan 15 - Feb 15): Margin trends     │
│ • China PMI (monthly): Global growth proxy             │
│ • ECB meetings: Global policy coordination             │
└─────────────────────────────────────────────────────────┘
```

**Content**:
- Upside risks (3-5 scenarios better than base case, with probabilities)
- Downside risks (3-5 scenarios worse than base case, with probabilities)
- Policy uncertainties (Fed, fiscal, regulatory, trade)
- Event calendar (next 3 months, high/medium priority events)
- Monitoring indicators (what to watch for each risk)

**Length**: 1-2 pages

**Page 11-12: Appendix**

```
[DATA TABLES]
- Full indicator table (30+ indicators, monthly values, 12-month history)
- Sector performance matrix (11 sectors × 6 regimes, historical returns)
- Discount rates by sector (current recommended rates)
- Transition probability matrix (regime × regime probabilities)

[TIME SERIES CHARTS]
- All economic indicators (15 charts, 5-year history)
- Sector relative performance (vs S&P 500)
- Yield curve evolution (last 12 months)

[FORECAST COMPARISONS]
- Macro Analyst forecast vs consensus (GDP, inflation, unemployment)
- Previous month forecast vs actual (accuracy tracking)
```

**Content**:
- Detailed data tables (full indicator values, historical data)
- Additional charts (time series, sector performance)
- Forecast comparisons (system vs consensus, accuracy tracking)

**Length**: 1-2 pages

---

### Macro Dashboard Specifications

**Format**: Interactive web dashboard (Plotly Dash / Streamlit / Tableau)
**Update Frequency**: Real-time (data refreshed daily at 5am)
**Access**: Human gates (embedded in gate dashboards), all agents (API access)

**Layout** (4 quadrants):

```
┌──────────────────────────┬──────────────────────────┐
│ REGIME GAUGE             │ INDICATOR HEATMAP        │
│                          │                          │
│   [Circular gauge]       │ [15×5 grid]              │
│   BEAR_HIGH_RATES        │ Growth │ Infl │ Mon │ Cr│
│   Confidence: 85%        │ ────────────────────────│
│                          │ GDP    🟡  CPI   🟡    │
│   [Prob bars]            │ IndPrd 🟢  PCE   🟡    │
│   Stay: ████████ 55%     │ Unemp  🟡  Wage  🟢    │
│   →NORMAL: ████ 30%      │ ...                     │
│   →BULL: █ 10%           │                          │
│                          │                          │
└──────────────────────────┴──────────────────────────┘
│ SECTOR ROTATION MATRIX   │ YIELD CURVE              │
│                          │                          │
│ [Quadrant scatter]       │ [Line chart]             │
│ Y-axis: Favorability     │ 4 lines:                 │
│ X-axis: Momentum         │ • Current                │
│                          │ • 3mo ago                │
│ • Healthcare (78,+6%)    │ • 1yr ago                │
│ • Tech (45,-8%)          │ • Historical avg         │
│ • RE (32,-12%)           │                          │
│                          │ [Inversion highlight]    │
└──────────────────────────┴──────────────────────────┘
```

**Components**:

**1. Regime Gauge (Top-Left)**:
- Circular gauge showing current regime
- Confidence level (%)
- Regime duration (months)
- Transition probability bars (next 3 months)
- Color-coded by regime type (green=BULL, red=BEAR, yellow=NORMAL)

**2. Indicator Heatmap (Top-Right)**:
- 15×5 grid (15 indicators × 5 categories)
- Cell color: 🟢 Green (positive), 🟡 Yellow (neutral), 🔴 Red (concerning)
- Cell value: Current value + 3-month change arrow (↑/↓/→)
- Tooltip: Indicator name, current, historical percentile, trend
- Interactive: Click cell → full time series chart

**3. Sector Rotation Matrix (Bottom-Left)**:
- Scatter plot: Y-axis = sector favorability score (0-100), X-axis = 3-month momentum (%)
- 11 sectors plotted as bubbles (size = market cap)
- Quadrants labeled: Strong/Improving (top-right, green), Weak/Deteriorating (bottom-left, red)
- Interactive: Click sector → sector detail page (performance, rationale, holdings)

**4. Yield Curve (Bottom-Right)**:
- Line chart: X-axis = maturity (3mo, 1Y, 2Y, 5Y, 10Y, 30Y), Y-axis = yield (%)
- 4 lines: Current, 3 months ago, 1 year ago, historical average
- Inversion highlight (if 10Y < 2Y, shade red)
- Tooltip: Maturity, yield, change vs 3mo ago

**Additional Tabs**:

**Tab 2: Economic Calendar**:
- Next 30 days of scheduled data releases
- FOMC meetings, CPI/PPI releases, NFP, GDP
- Priority color-coded (high=red, medium=yellow, low=green)
- Countdown timer to next high-priority event

**Tab 3: Scenario Analysis**:
- 3 scenario panels (base/bull/bear)
- Probability gauge per scenario
- S&P forecast range
- Sector winners/losers
- Key catalysts

**Tab 4: Historical Regime Performance**:
- Table: 6 regimes × avg duration, S&P return, sector returns
- Chart: Regime timeline (last 10 years, color-coded bars)
- Transition matrix heatmap (from regime → to regime probabilities)

---

### API Endpoints for Agent Consumption

Agents query Macro Analyst via API (RESTful or Neo4j Cypher):

**Endpoint 1: Get Current Regime**

```python
GET /api/macro/regime/current

Response:
{
  "regime": "BEAR_HIGH_RATES",
  "confidence": 0.85,
  "duration_months": 8,
  "transition_probabilities": {
    "BEAR_HIGH_RATES": 0.55,  # Stay
    "NORMAL": 0.30,
    "BULL_HIGH_RATES": 0.10,
    "BEAR_LOW_RATES": 0.05
  },
  "as_of_date": "2025-01-15"
}
```

**Endpoint 2: Get Sector Favorability**

```python
GET /api/macro/sectors/favorability

Response:
{
  "as_of_date": "2025-01-15",
  "scores": {
    "Technology": 45,
    "Healthcare": 78,
    "Financials": 58,
    "Consumer Discretionary": 42,
    "Consumer Staples": 68,
    "Energy": 48,
    "Utilities": 72,
    "Real Estate": 32,
    "Materials": 38,
    "Industrials": 52,
    "Communication Services": 40
  },
  "recommendations": {
    "overweight": ["Healthcare", "Utilities", "Consumer Staples"],
    "underweight": ["Real Estate", "Technology", "Communication Services"]
  }
}
```

**Endpoint 3: Get Discount Rates**

```python
GET /api/macro/discount_rates?sector=Technology

Response:
{
  "sector": "Technology",
  "discount_rate": 0.115,  # 11.5%
  "components": {
    "risk_free_rate": 0.045,       # 10Y Treasury
    "equity_premium": 0.050,       # Historical average
    "regime_premium": 0.015,       # BEAR_HIGH_RATES volatility
    "sector_premium": 0.005        # Tech beta adjustment
  },
  "as_of_date": "2025-01-15",
  "valid_until": "2025-02-15"  # Monthly refresh
}
```

**Endpoint 4: Get Latest Report**

```python
GET /api/macro/reports/latest?format=summary

Response:
{
  "report_id": "2025-01-macro",
  "published_date": "2025-01-07",
  "type": "monthly",
  "summary": {
    "regime": "BEAR_HIGH_RATES",
    "key_takeaways": [
      "Fed maintaining restrictive policy (5.5% Fed Funds)",
      "Growth slowing but avoiding recession (GDP 1.8%)",
      "Sector rotation favors defensives (Healthcare 78, Tech 45)",
      "30% probability transition to NORMAL by Q2 2025"
    ],
    "top_risks": [
      "Inflation re-acceleration (15% probability)",
      "Hard landing / recession (20% probability)"
    ]
  },
  "pdf_url": "/reports/2025-01-macro.pdf",
  "dashboard_url": "/dashboards/macro"
}
```

**Endpoint 5: Get Economic Indicators**

```python
GET /api/macro/indicators?category=INFLATION

Response:
{
  "category": "INFLATION",
  "as_of_date": "2025-01-15",
  "indicators": {
    "CPI": {
      "current": 0.032,  # 3.2%
      "percentile": 75,
      "trend_3mo": "falling",
      "signal": "yellow"
    },
    "PCE": {
      "current": 0.028,  # 2.8%
      "percentile": 72,
      "trend_3mo": "falling",
      "signal": "yellow"
    },
    "Wage_Growth": {
      "current": 0.045,  # 4.5%
      "percentile": 68,
      "trend_3mo": "stable",
      "signal": "green"
    }
  }
}
```

---

### Report Delivery Matrix

Which reports go to which human gates:

| Gate   | Full Report | Summary | Dashboard | Update Trigger                  |
| ------ | ----------- | ------- | --------- | ------------------------------- |
| Gate 1 | No          | Yes     | Yes       | Monthly + regime change         |
| Gate 2 | No          | Yes     | Yes       | Monthly + regime change         |
| Gate 5 | Yes         | N/A     | Yes       | Every decision (full context)   |
| Agents | No          | API     | API       | Daily cache refresh + on-demand |

**Rationale**:
- **Gate 1 (Screening)**: Needs sector favorability rankings (summary sufficient)
- **Gate 2 (Research)**: Needs regime context for research priorities (summary sufficient)
- **Gate 5 (Final Decision)**: Needs full context (company + sector + macro) = full report
- **Agents**: Query specific data points via API (no PDF needed)

**Ad-Hoc Report Triggers**:

1. **Regime Change** (confidence >80%):
   - Alert all gates + agents
   - 2-3 page summary: What changed, why, implications
   - Updated dashboard
   - Sent within 2 hours of detection

2. **Major Fed Announcement** (rate change, policy shift):
   - Alert all gates + agents
   - 1-2 page summary: Fed action, market reaction, sector implications
   - Updated discount rates
   - Sent within 4 hours of announcement

3. **Threshold Breach** (indicator moves to extreme percentile >95th or <5th):
   - Alert agents only (unless sustained for 3 days → alert gates)
   - 1 page note: Indicator, value, historical context, watch list

---

### Report Versioning & Corrections

**Versioning Scheme**: `YYYY-MM-{type}-v{version}`

Example: `2025-01-monthly-v1.pdf`

**Correction Protocol**:

1. **Minor Error** (typo, chart label):
   - Publish corrected version: `2025-01-monthly-v2.pdf`
   - Email notification: "Correction published (cosmetic)"
   - No re-decision required

2. **Material Error** (wrong sector score, incorrect regime):
   - Publish corrected version: `2025-01-monthly-v2.pdf`
   - Email notification + Gate alert: "Material correction - please review"
   - Flag affected decisions for human review

3. **Forecast Update** (new data changes outlook mid-month):
   - Publish supplemental report: `2025-01-supplement-v1.pdf`
   - Email notification: "Forecast updated based on new data"
   - No version increment on original report

**Audit Trail**:
- All report versions stored in `/outputs/macro_reports/archive/`
- Neo4j tracks which decisions used which report version
- Correction log maintained (what changed, why, impact)

---

## Options Considered

### Option 1: Minimal Text Reports Only (Rejected)

**Description**: PDF reports only (no dashboards), basic format (5 pages, text-heavy)

**Pros**:
- Simple to implement (PDF generation only)
- Low development time (1 week)
- No dashboard infrastructure needed

**Cons**:
- **Not interactive**: Humans can't drill down into indicators
- **Stale data**: PDF published monthly, no real-time updates
- **Poor agent integration**: Agents would parse PDF (fragile, slow)
- **Limited accessibility**: Text-heavy, hard to scan quickly

**Estimated Effort**: Low (1 week)

**Rejection Rationale**: Professional firms use interactive dashboards for a reason - real-time data, drill-down capability. Text-only reports insufficient for fast decision-making.

---

### Option 2: Dashboard Only (No PDF Reports) (Rejected)

**Description**: Interactive dashboards only, no static PDF reports

**Pros**:
- Real-time data (always current)
- Interactive (drill-down, filtering)
- Modern UX (better than PDFs)

**Cons**:
- **No offline access**: Can't review report without internet
- **No archival**: Hard to compare month-over-month (dashboards update, old data lost)
- **No narrative**: Dashboards show data, but lack synthesized takeaways/rationale
- **Human gates prefer documents**: Many investors want readable reports (not just charts)

**Estimated Effort**: Medium (2-3 weeks dashboard development)

**Rejection Rationale**: Dashboards complement reports, don't replace them. Narrative analysis (why sectors ranked this way, what risks matter) requires written explanations. Archival/versioning difficult with live dashboards.

---

### Option 3: PDF Reports + Interactive Dashboards (Selected)

**Description**: Monthly PDF reports (8-12 pages, comprehensive) + real-time interactive dashboards + API endpoints for agents

**Pros**:
- **Best of both**: Narrative analysis (PDF) + real-time data (dashboard)
- **Offline access**: PDF downloadable, shareable
- **Archival**: PDFs versioned, stored, auditable
- **Interactive**: Dashboard for drill-down, real-time monitoring
- **Agent-friendly**: API endpoints for programmatic access
- **Professional standard**: Mirrors Goldman Sachs, JPMorgan practices

**Cons**:
- **Implementation complexity**: 3 output formats (PDF, dashboard, API)
- **Maintenance overhead**: Keep PDF + dashboard in sync
- **Development time**: 3-4 weeks (PDF generation + dashboard + APIs)

**Estimated Effort**: High (3-4 weeks)

**Selected**: Provides comprehensive solution - PDF for narrative/archival, dashboard for real-time/interactive, API for agents. Mirrors professional firm standards.

---

## Rationale

### Why Option 3 (PDF + Dashboard + API) Was Selected

**1. Professional Firm Best Practices**

Goldman Sachs, JPMorgan, BCA Research all use hybrid approach:
- PDF reports: Monthly/quarterly, comprehensive, narrative analysis
- Dashboards: Real-time data, interactive charts, monitoring
- APIs: Data feeds for portfolio management systems

**Why all 3?**:
- PDFs: Archival, offline, comprehensive (human decision-making)
- Dashboards: Real-time, drill-down, monitoring (daily tracking)
- APIs: Programmatic access (agent consumption, automation)

**2. Different Use Cases Require Different Formats**

```text
Use Case 1: Gate 5 final decision (human needs context)
→ PDF report (full 12 pages, narrative, rationale, scenarios)

Use Case 2: Daily monitoring (is regime changing?)
→ Dashboard (real-time regime gauge, indicator heatmap)

Use Case 3: Screening Agent needs sector scores
→ API endpoint (/api/macro/sectors/favorability)

Use Case 4: Historical comparison (how did we do last month?)
→ PDF archive (2024-12-monthly-v1.pdf vs 2025-01-monthly-v1.pdf)
```

**3. Archival & Audit Requirements**

Investment decisions need audit trail:
- Which macro report version was used?
- What were sector favorability scores at decision time?
- Did regime change between screening and final decision?

PDFs provide versioned snapshots (dashboard updates lose history)

**4. Agent Integration Efficiency**

Agents don't need full 12-page PDF:
- Screening Agent: Needs sector scores only → API call (200ms)
- Valuation Agent: Needs discount rates only → API call (200ms)
- Parsing PDFs: Slow (5-10s), fragile (format changes break parsing), inefficient

APIs optimized for programmatic access

**5. Human Gate Efficiency**

Gate 1 (Screening): Doesn't need full 12-page report
- Solution: Dashboard embedded in gate UI (regime gauge + sector rankings visible)
- Human scans in <30 seconds

Gate 5 (Final Decision): Needs full context
- Solution: Full PDF report + dashboard (comprehensive view)
- Human reviews in 10-15 minutes

---

## Consequences

### Positive Impacts

**1. Clear Implementation Roadmap**

- PDF template: 8-12 pages, 6 sections defined
- Dashboard spec: 4 quadrants, component layouts defined
- API endpoints: 5 RESTful endpoints specified
- Deliverables clear for development team

**2. Consistent Macro Context Across Gates**

- All gates receive same macro framework (no inconsistencies)
- Versioned reports ensure decisions use same data
- Audit trail: Which report influenced which decision

**3. Agent Integration Optimized**

- API endpoints tailored to agent needs (sector scores, discount rates, regime)
- Fast (<200ms response time)
- No PDF parsing (fragile, slow)

**4. Professional Quality Output**

- PDF reports match Goldman Sachs / JPMorgan standards
- Interactive dashboards enable drill-down
- Real-time monitoring (regime changes, indicator shifts)

**5. Enables Learning & Improvement**

- Forecast accuracy tracking (appendix table: forecast vs actual)
- Historical regime performance (validate scoring methodology)
- Human override tracking (when gates disagreed with macro view)

### Negative Impacts / Tradeoffs

**1. Implementation Complexity**

- **3 output formats**: PDF generation, dashboard development, API endpoints
- **Synchronization**: Keep PDF + dashboard data in sync
- **Testing**: Validate all 3 formats produce consistent data
- **Estimated effort**: 3-4 weeks (vs 1 week for PDF-only)

**2. Maintenance Overhead**

- **Monthly PDF generation**: 2-4 hours automated batch processing
- **Dashboard updates**: Daily data refresh (5am batch job)
- **API endpoint monitoring**: Uptime, latency, error rates
- **Total**: ~8 hours/month ongoing maintenance

**3. Data Synchronization Risk**

- **Potential inconsistency**: PDF shows sector score 78, dashboard shows 75 (stale cache)
- **Mitigation**: Single source of truth (Neo4j), both PDF + dashboard query same data
- **Validation**: Automated tests ensure PDF + dashboard + API return identical data

**4. Dashboard Tool Decision Deferred**

- **Unresolved**: Build (Plotly Dash) vs Buy (Tableau)?
- **Impact**: Implementation can't start until tool selected
- **Timeline**: Decision needed by Week 1 of Macro Analyst implementation

**5. Report Generation Performance**

- **PDF rendering**: 2-4 hours monthly (acceptable for batch processing)
- **If too slow**: Risk missing 1st week of month publication target
- **Mitigation**: Parallelize chart generation, pre-compute heavy calculations

### Affected Components

**Report Generation Pipeline**:

```python
# Monthly batch job (1st week of month, 5am)
1. Fetch economic indicators (FRED, IMF, OECD) - 30min
2. Analyze regime (transition probabilities, scenarios) - 1hr
3. Calculate sector favorability (11 sectors × 4 factors) - 30min
4. Generate charts (15 indicator time series, sector matrix) - 1hr
5. Render PDF (8-12 pages, embed charts) - 30min
6. Publish (store in /outputs/, update Neo4j) - 10min
Total: ~3.5 hours
```

**Dashboard Infrastructure**:

- **Backend**: Flask/FastAPI (API endpoints)
- **Frontend**: Plotly Dash / Streamlit / Tableau (dashboard UI)
- **Database**: Neo4j (single source of truth)
- **Caching**: Redis (cache API responses, dashboard data)
- **Deployment**: Docker container, auto-scaling

**Human Gate UI Integration**:

- **Gate 1 Dashboard**: Embed macro dashboard (iframe or component)
- **Gate 2 Dashboard**: Embed macro summary + regime gauge
- **Gate 5 Dashboard**: Full PDF viewer + dashboard side-by-side

**Documentation**:

- ✅ `docs/operations/02-human-integration.md`: Gate macro context specs
- ✅ `DD-022_MACRO_ANALYST_AGENT.md`: Report deliverables reference DD-026

---

## Implementation Notes

### Critical Constraints

**1. Performance Target**: <4 hours monthly report generation

- Pre-compute intensive calculations (sector favorability, regime analysis)
- Parallelize chart generation (15 charts in parallel)
- Cache indicator data (fetch once, reuse across PDF + dashboard)

**2. Data Consistency**: PDF + Dashboard + API return identical data

- Single source of truth: Neo4j query layer
- Validation tests: Assert PDF data == dashboard data == API data
- Timestamp synchronization: All 3 formats show same `as_of_date`

**3. Dashboard Tool Selection**: Decide Week 1

**Options**:
- **Plotly Dash** (build): Python-based, full control, 2-3 weeks dev
- **Streamlit** (build): Python-based, simpler, 1-2 weeks dev
- **Tableau** (buy): Enterprise features, $70-$150/user/mo, 1 week setup

**Decision criteria**:
- Budget (buy = recurring cost)
- Customization needs (build = full control)
- Team skills (Python proficiency)
- Timeline (build = longer)

**4. Archival Storage**: Permanent PDF storage

- Store all versions: `/outputs/macro_reports/archive/YYYY-MM-{type}-v{version}.pdf`
- Retention: Permanent (audit requirements)
- Compression: PDF/A format (long-term archival standard)

### Integration Points

**1. PDF Generation**

```python
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, PageBreak, Image

def generate_monthly_macro_report(month, year):
    # Fetch data
    regime = macro_analyst.get_regime_analysis(month, year)
    indicators = macro_analyst.get_indicators(month, year)
    sectors = macro_analyst.get_sector_favorability(month, year)
    risks = macro_analyst.get_risks_catalysts(month, year)

    # Create PDF
    pdf_path = f"/outputs/macro_reports/{year}-{month:02d}-monthly-v1.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    story = []

    # Page 1: Executive Summary
    story.append(Paragraph(f"MACRO OUTLOOK - {month}/{year}", title_style))
    story.append(Paragraph(f"Current Regime: {regime['name']}", heading_style))
    story.append(Paragraph(f"Confidence: {regime['confidence']:.0%}", body_style))
    # ... (add all executive summary content)

    # Page 2-3: Economic Indicators
    story.append(PageBreak())
    indicator_table_data = [[ind['name'], ind['current'], ind['percentile'], ind['trend']]
                            for ind in indicators]
    story.append(Table(indicator_table_data, colWidths=[2*inch, 1*inch, 1*inch, 1*inch]))
    # ... (add indicator charts)

    # Build PDF
    doc.build(story)
    return pdf_path
```

**2. Dashboard Components**

```python
import plotly.graph_objects as go
from dash import Dash, dcc, html

# Regime gauge
regime_gauge = go.Figure(go.Indicator(
    mode = "gauge+number",
    value = regime_confidence * 100,
    domain = {'x': [0, 1], 'y': [0, 1]},
    title = {'text': regime_name},
    gauge = {
        'axis': {'range': [None, 100]},
        'bar': {'color': regime_color},
        'steps': [
            {'range': [0, 50], 'color': "lightgray"},
            {'range': [50, 80], 'color': "gray"},
            {'range': [80, 100], 'color': "darkgray"}
        ],
        'threshold': {
            'line': {'color': "red", 'width': 4},
            'thickness': 0.75,
            'value': 80
        }
    }
))

# Indicator heatmap
indicator_heatmap = go.Figure(data=go.Heatmap(
    z=indicator_signals,  # 15×5 matrix (-1, 0, 1 for red, yellow, green)
    x=categories,  # ['Growth', 'Inflation', 'Monetary', 'Credit', 'Sentiment']
    y=indicators,  # 15 indicator names
    colorscale=[[0, 'red'], [0.5, 'yellow'], [1, 'green']],
    text=indicator_values,  # Display values in cells
    texttemplate='%{text}',
    textfont={"size": 10}
))
```

**3. API Endpoint Implementation**

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/api/macro/regime/current")
def get_current_regime():
    regime_data = macro_analyst.get_current_regime()
    return {
        "regime": regime_data['name'],
        "confidence": regime_data['confidence'],
        "duration_months": regime_data['duration'],
        "transition_probabilities": regime_data['transitions'],
        "as_of_date": regime_data['date'].isoformat()
    }

@app.get("/api/macro/sectors/favorability")
def get_sector_favorability():
    sector_data = macro_analyst.get_sector_scores()
    return {
        "as_of_date": sector_data['date'].isoformat(),
        "scores": sector_data['scores'],  # Dict: {sector: score}
        "recommendations": {
            "overweight": [s for s, score in sector_data['scores'].items() if score > 65],
            "underweight": [s for s, score in sector_data['scores'].items() if score < 45]
        }
    }
```

### Testing Requirements

**1. Data Consistency Validation**

```python
def test_data_consistency():
    # Generate all 3 outputs
    pdf_data = generate_pdf_report('2025-01')
    dashboard_data = fetch_dashboard_data()
    api_data = requests.get('/api/macro/sectors/favorability').json()

    # Extract sector scores from each
    pdf_sector_scores = parse_pdf_sector_scores(pdf_data)
    dashboard_sector_scores = dashboard_data['sector_scores']
    api_sector_scores = api_data['scores']

    # Assert all identical
    assert pdf_sector_scores == dashboard_sector_scores == api_sector_scores
```

**2. PDF Generation Performance**

```python
def test_pdf_generation_performance():
    start_time = time()
    pdf_path = generate_monthly_macro_report(1, 2025)
    generation_time = time() - start_time

    # Target: <4 hours (14400 seconds)
    assert generation_time < 14400

    # Validate PDF completeness
    pdf = PyPDF2.PdfFileReader(pdf_path)
    assert pdf.numPages >= 8  # Minimum 8 pages
    assert pdf.numPages <= 12  # Maximum 12 pages
```

**3. Dashboard Rendering**

```python
def test_dashboard_renders():
    # Start dashboard server
    dashboard_server = start_dashboard()

    # Fetch dashboard HTML
    response = requests.get('http://localhost:8050/')

    # Assert page loads
    assert response.status_code == 200

    # Assert all 4 quadrants present
    assert 'regime-gauge' in response.text
    assert 'indicator-heatmap' in response.text
    assert 'sector-rotation' in response.text
    assert 'yield-curve' in response.text
```

**4. API Endpoint Validation**

```python
def test_api_endpoints():
    # Test all 5 endpoints
    endpoints = [
        '/api/macro/regime/current',
        '/api/macro/sectors/favorability',
        '/api/macro/discount_rates?sector=Technology',
        '/api/macro/reports/latest',
        '/api/macro/indicators?category=INFLATION'
    ]

    for endpoint in endpoints:
        response = requests.get(f'http://localhost:8000{endpoint}')

        # Assert successful response
        assert response.status_code == 200

        # Assert JSON response
        data = response.json()
        assert 'as_of_date' in data  # All endpoints include timestamp
```

### Rollback Strategy

**Phase 1: PDF Reports Only** (Week 1-2)

- Generate PDF reports, manually review quality
- Distribute to human gates for feedback
- No automated integration yet
- Validate content, formatting, completeness

**Phase 2: Add Dashboard** (Week 3-4)

- Deploy dashboard (alpha version)
- Parallel mode: PDF + dashboard both available
- Human gates optionally use dashboard
- Validate data consistency (PDF vs dashboard)

**Phase 3: Add API Endpoints** (Week 5)

- Deploy API endpoints
- Agents query APIs (shadow mode - results logged, not used)
- Validate API responses match PDF + dashboard

**Phase 4: Full Integration** (Week 6)

- Agents use API responses in decisions
- Dashboards embedded in gate UIs
- Monitor for regressions (data inconsistencies, performance issues)

**Rollback Trigger**: If reports show:

- Data inconsistencies >5% (PDF vs dashboard vs API)
- PDF generation time >6 hours
- Dashboard rendering failures >20%
- API endpoint errors >10%

**Rollback Procedure**:

1. Disable automated report generation (manual mode)
2. Investigate root cause (data fetch? Chart rendering? PDF generation?)
3. Fix in development environment, re-validate
4. Re-deploy with fixes

---

**Estimated Implementation Effort**: 3-4 weeks

**Breakdown**:

- Week 1: PDF report generation (template, chart rendering, data fetching)
- Week 2: Dashboard development (4 quadrants, interactive charts, tabs)
- Week 3: API endpoints (5 RESTful endpoints, data serialization, caching)
- Week 4: Testing, validation, integration with human gates

**Dependencies**:

**Must Be Completed First**:

- [DD-022: Macro Analyst Agent](DD-022_MACRO_ANALYST_AGENT.md) - Core logic (regime analysis, sector scoring)
- Data infrastructure (FRED, IMF, OECD APIs integrated)
- Neo4j schema (macro data storage structure)

**Dashboard Tool Decision Required**:

- Week 1: Select Plotly Dash vs Streamlit vs Tableau
- Impacts development timeline, cost, customization

---

## Open Questions

**1. Dashboard tool selection?**

**Options**:
- A) Plotly Dash (build, 2-3 weeks, full control, $0)
- B) Streamlit (build, 1-2 weeks, simpler, $0)
- C) Tableau (buy, 1 week setup, enterprise features, $70-$150/user/mo)

**Decision**: Deferred to implementation phase (user to decide budget vs customization)

**2. PDF rendering library?**

**Options**:
- A) ReportLab (Python, mature, complex API)
- B) WeasyPrint (Python, HTML→PDF, simpler)
- C) LaTeX (high quality, steep learning curve)

**Recommendation**: B (WeasyPrint) - write HTML templates, convert to PDF (easier than ReportLab, better quality than basic libraries)

**3. Chart generation tool?**

**Options**:
- A) Matplotlib (Python, static charts, 10+ years mature)
- B) Plotly (Python, interactive charts, can embed in PDF as static)

**Recommendation**: B (Plotly) - same library for dashboard + PDF charts (consistency)

**Blocking**: No - reasonable defaults available, can switch libraries if needed

---

## References

**Internal Documentation**:

- [Macro & Industry Analysis Plan](../../plans/macro-industry-analysis-plan.md) - Report specifications
- [DD-022: Macro Analyst Agent](DD-022_MACRO_ANALYST_AGENT.md) - Macro Analyst deliverables
- [Human Integration](../operations/02-human-integration.md) - Human gate requirements

**External Research**:

- **Goldman Sachs Top of Mind**: Macro report format reference
- **JPMorgan Global Data Watch**: Indicator dashboard format
- **BCA Research Monthly**: Regime analysis structure
- **ReportLab Documentation**: PDF generation library
- **Plotly Dash Documentation**: Interactive dashboard framework

---

## Status History

| Date       | Status   | Notes                                              |
| ---------- | -------- | -------------------------------------------------- |
| 2025-11-19 | Proposed | Initial proposal based on DD-022 requirements      |
| 2025-11-19 | Approved | Approved for implementation with Macro Analyst (DD-022) |

**Next Steps**:

1. Week 1: Select dashboard tool (Plotly Dash vs Streamlit vs Tableau)
2. Week 1-2: Implement PDF report generation (template, charts, data integration)
3. Week 2-3: Develop interactive dashboard (4 quadrants, tabs)
4. Week 3-4: Deploy API endpoints, testing, validation

---

## Notes

**Design Philosophy**: This decision prioritizes **multiple output formats** to serve different use cases - PDFs for archival/comprehensive analysis, dashboards for real-time monitoring, APIs for agent automation.

**Key Insight**: Professional firms use all 3 formats for good reason:
- **PDFs**: Narrative synthesis, offline access, audit trail
- **Dashboards**: Real-time data, interactivity, monitoring
- **APIs**: Programmatic access, automation, integration

**Efficiency Gain**: Consistent macro framework across all gates (no duplicate macro research by humans)

**Quality Standard**: 8-12 pages matches Goldman Sachs / JPMorgan macro report length (comprehensive without overwhelming)

**Integration Points**:
- Human Gates: PDF reports + embedded dashboards
- Agents: API endpoints (fast, structured data)
- Archival: Versioned PDFs, permanent storage

**Future Enhancements**:
- Email distribution (auto-send reports to stakeholders)
- Customizable dashboard views (user preferences, saved layouts)
- Report comparisons (side-by-side, month-over-month changes)
- Natural language generation (auto-write report sections from data)
