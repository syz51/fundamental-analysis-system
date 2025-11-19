# DD-022: Macro Analyst Agent

**Status**: Approved
**Date**: 2025-11-19
**Decider(s)**: System Architecture Team
**Related Docs**:

- [System Overview](../architecture/01-system-overview.md)
- [Specialist Agents](../architecture/03-agents-specialist.md)
- [Analysis Pipeline](../operations/01-analysis-pipeline.md)
- [Human Integration](../operations/02-human-integration.md)
- [Data Management](../operations/03-data-management.md)
- [Roadmap](../implementation/01-roadmap.md)

**Related Decisions**:

- [DD-008: Agent Credibility System](DD-008_AGENT_CREDIBILITY_SYSTEM.md) - Reuses regime detection
- [DD-011: Agent Checkpoint System](DD-011_AGENT_CHECKPOINT_SYSTEM.md) - Checkpoint subtask structure

---

## Context

### The Problem

Current system lacks systematic top-down macro analysis:

**No Macro Context**:

- Economic conditions (GDP, inflation, rates) not systematically analyzed
- Interest rate environment not integrated into valuation (discount rates)
- Sector rotation dynamics ignored
- Market regimes detected (DD-008) but not analyzed for investment decisions

**Bottom-Up Only**:

- Screening Agent selects stocks without macro/sector context
- Valuation Agent uses arbitrary discount rates (no macro guidance)
- No systematic sector favorability scoring
- Company analysis occurs in vacuum (ignoring economic backdrop)

**Reactive Not Proactive**:

- News Monitor alerts on events but no systematic macro analysis
- No monthly macro reports for context
- Human gates lack macro framework for decision-making

### Impact on Investment Decisions

This gap undermines investment quality:

**Example 1: Valuation Sensitivity**

```text
Target Company: SaaS company with 30% growth
Valuation Agent DCF: Uses 8% discount rate (arbitrary default)

Reality:
  Fed Funds Rate = 5.5% (high rates regime)
  Risk-free rate = 4.5% (10Y Treasury)
  Appropriate discount rate = 10-12% (risk-free + equity premium)

Impact:
  8% DCF valuation: $50/share
  12% DCF valuation: $32/share (-36% valuation difference)

Without macro guidance, Valuation Agent systematically overvalues in high-rate environments.
```

**Example 2: Sector Timing**

```text
Screening Results: 3 tech stocks, 2 consumer discretionary, 1 healthcare

Market Regime: BEAR_HIGH_RATES (2022-2023)
  - Fed raising rates aggressively
  - Growth stocks underperforming
  - Defensive sectors outperforming

Reality:
  Tech (growth): -30% sector performance
  Consumer Disc (cyclical): -25% sector performance
  Healthcare (defensive): +5% sector performance

Without sector favorability scoring, Screening Agent presents 5 poor-timing candidates vs 1 well-timed candidate.
```

**Example 3: Human Gate Inefficiency**

```text
Gate 1 (Screening Validation):
  Human receives: 10 stock candidates across 5 sectors
  Missing context: Current regime, sector favorability rankings

Human decision process:
  - Manually checks macro environment (30min)
  - Manually looks up sector performance (20min)
  - Manually adjusts screening results (15min)
  Total: 65min overhead per gate

With macro report: Context pre-loaded, decision in <15min (50min saved, 75% efficiency gain)
```

### Real-World Professional Practice

**Top-Down IS Fundamental Analysis**:

Professional investment firms combine both approaches:

- **Top-Down**: Macro → Sector → Stock (asset allocation, timing)
- **Bottom-Up**: Company fundamentals (stock selection, valuation)

**Firm Examples**:

- Goldman Sachs: Macro Strategy team provides regime analysis, sector allocations
- Dodge & Cox: Integrates macro view with bottom-up research
- Piper Sandler: Macro team publishes monthly economic outlook

**NOT separate strategies** - best practice uses BOTH together for:

- **Quality**: Bottom-up company analysis
- **Timing**: Top-down macro/sector context
- **Risk Management**: Avoid concentrated sector bets in wrong regimes

### Existing Asset: DD-008 Regime Detection

**Already Implemented** (DD-008:184-199):

6 market regimes with daily monitoring:

1. BULL_LOW_RATES (S&P +10%+, Fed <3%, VIX <20)
2. BULL_HIGH_RATES (S&P +10%+, Fed ≥3%)
3. BEAR_HIGH_RATES (S&P negative, Fed ≥3%, VIX >25)
4. BEAR_LOW_RATES (S&P negative, Fed <3%)
5. HIGH_VOLATILITY (VIX >30)
6. NORMAL (default)

**Current Use**: Agent credibility scoring only

**Gap**: Regimes DETECTED but not ANALYZED for investment implications

**Opportunity**: Reuse detection infrastructure, add analysis layer (no rebuild needed)

### Why This Needs Resolution Now

Phase 2 (Core Agents) establishes specialist agent layer. Macro Analyst is foundational for:

- **Valuation accuracy**: Discount rates must reflect current rate environment
- **Screening effectiveness**: Sector favorability improves candidate quality
- **Human gate efficiency**: Pre-loaded macro context reduces decision time 50%+
- **Top-down + bottom-up integration**: Mirrors professional firm best practices

**Blocking Dependencies**:

- Data infrastructure (Phase 1): Needed for FRED, IMF, OECD API integration
- Memory system (DD-005, DD-011): Macro Analyst needs memory for regime patterns

---

## Decision

**Deploy Macro Analyst as 6th specialist agent with regime analysis, economic indicator monitoring, sector favorability scoring, and monthly macro reports. Reuse DD-008 regime detection as input, add analysis layer for investment decisions.**

The agent calculates macro context as:

```python
macro_context = {
    'current_regime': regime_detection.get_current(),  # Reuse DD-008
    'regime_confidence': regime_analysis.calculate_confidence(),
    'sector_favorability': sector_scoring.rank_sectors(regime),
    'discount_rate_guidance': discount_rates.calculate_by_regime(regime),
    'transition_probabilities': regime_analysis.forecast_transitions(),
    'economic_indicators': indicators.get_current_snapshot(),
    'risks_catalysts': risk_monitor.identify_current()
}
```

### Core Components

**1. Regime Analysis (Reuses DD-008 Detection)**

Input: Current regime from DD-008 (BULL_LOW_RATES, BEAR_HIGH_RATES, etc.)

Analysis layer:

```python
def analyze_regime_implications(current_regime):
    """
    Analyzes investment implications of detected regime

    Input: Regime classification from DD-008 regime detection
    Output: Investment implications (sector favorability, discount rates, scenarios)
    """

    # Historical regime performance lookup
    historical_stats = get_regime_statistics(current_regime)

    # Sector favorability by regime
    sector_scores = calculate_sector_favorability(
        regime=current_regime,
        historical_performance=historical_stats['sector_returns'],
        current_valuations=get_current_sector_valuations()
    )

    # Discount rate guidance
    discount_rates = calculate_discount_rates(
        risk_free_rate=get_fed_funds_rate(),
        equity_premium=historical_stats['average_premium'],
        regime_adjustment=historical_stats['volatility_premium']
    )

    # Regime transition probabilities
    transitions = forecast_regime_transitions(
        current_regime=current_regime,
        leading_indicators=get_leading_indicators(),
        historical_transitions=historical_stats['transition_matrix']
    )

    return {
        'regime': current_regime,
        'confidence': calculate_regime_confidence(),
        'sector_favorability': sector_scores,  # Dict: {sector: score 0-100}
        'discount_rates': discount_rates,      # Dict: {sector: rate}
        'transition_probs': transitions,       # Dict: {next_regime: probability}
        'scenarios': generate_scenarios()      # List[Scenario]
    }
```

**Benefits**:

- No regime detection rebuild (reuses DD-008)
- Adds investment-relevant analysis layer
- Sector favorability scores guide screening
- Discount rates calibrated to regime

**2. Economic Indicator Monitoring**

Track 5 categories of indicators:

```python
class EconomicIndicators:
    GROWTH = ['GDP', 'ISM Manufacturing PMI', 'ISM Services PMI', 'Retail Sales',
              'Industrial Production', 'Employment', 'Initial Jobless Claims',
              'Durable Goods Orders', 'Housing Starts', 'Leading Economic Index']
    INFLATION = ['CPI', 'PPI', 'PCE', 'Wage Growth']
    MONETARY = ['Fed Funds Rate', '10Y Treasury', 'Yield Curve', 'Fed Balance Sheet']
    CREDIT = ['Corporate Spreads', 'High Yield Spreads', 'Credit Growth']
    SENTIMENT = ['Consumer Confidence', 'VIX', 'Put/Call Ratio']

def analyze_indicators():
    """
    Analyzes economic indicators for regime context

    Returns indicator snapshot with direction/significance
    """
    indicators = {}

    for category in [GROWTH, INFLATION, MONETARY, CREDIT, SENTIMENT]:
        for indicator in category:
            current_value = fetch_indicator(indicator)
            historical_percentile = calculate_percentile(indicator, current_value)
            trend = calculate_3mo_trend(indicator)

            indicators[indicator] = {
                'current': current_value,
                'percentile': historical_percentile,  # 0-100 (50=median)
                'trend': trend,                       # 'rising'/'falling'/'stable'
                'significance': 'high' if abs(historical_percentile - 50) > 30 else 'normal'
            }

    return indicators
```

**Data Sources**:

- FRED (Federal Reserve Economic Data): GDP, CPI, unemployment, Fed rates - free
- IMF (International Monetary Fund): Global macro data - free
- OECD: 27 EU countries, 700 indicators - free
- CBOE: VIX, volatility indices - free

**Update Frequency**: Daily monitoring, monthly comprehensive analysis

**3. Sector Favorability Scoring**

Ranks 11 GICS sectors by attractiveness in current regime:

```python
def calculate_sector_favorability(regime, historical_performance, current_valuations):
    """
    Scores sectors 0-100 based on regime suitability

    Factors:
    - Historical sector performance in regime (40% weight)
    - Current valuations vs historical (30% weight)
    - Sector sensitivity to regime factors (20% weight)
    - Momentum (3-month trend) (10% weight)
    """

    sector_scores = {}

    for sector in GICS_SECTORS:  # 11 sectors
        # Historical performance in regime
        regime_returns = get_sector_returns_in_regime(sector, regime)
        performance_score = percentile_rank(regime_returns) * 0.40

        # Valuation relative to history
        current_pe = get_sector_pe(sector)
        historical_pe = get_sector_historical_pe(sector)
        valuation_score = (1 - (current_pe / historical_pe)) * 0.30  # Lower = better

        # Regime sensitivity (predefined sensitivities)
        sensitivity_score = REGIME_SECTOR_SENSITIVITY[regime][sector] * 0.20

        # Momentum (3-month trend)
        momentum_score = calculate_sector_momentum(sector) * 0.10

        sector_scores[sector] = (
            performance_score + valuation_score +
            sensitivity_score + momentum_score
        ) * 100  # Scale to 0-100

    return sector_scores  # Dict: {'Technology': 78, 'Healthcare': 65, ...}
```

**Output**: Sector rankings used by Screening Agent

**Example Output**:

```python
{
    'Technology': 78,        # High favorability
    'Healthcare': 72,        # High favorability
    'Consumer Staples': 65,  # Medium favorability
    'Financials': 55,        # Medium favorability
    'Energy': 45,            # Low favorability
    'Real Estate': 32        # Low favorability (high rates regime)
}
```

**4. Discount Rate Guidance**

Provides sector-specific discount rates for Valuation Agent:

```python
def calculate_discount_rates(risk_free_rate, equity_premium, regime_adjustment):
    """
    Calculates sector discount rates based on risk-free rate + premiums

    Formula: Discount Rate = Risk-Free + Equity Premium + Regime Premium + Sector Premium
    """

    discount_rates = {}

    for sector in GICS_SECTORS:
        base_rate = risk_free_rate                    # 10Y Treasury (e.g., 4.5%)
        base_premium = equity_premium                 # Historical average (e.g., 5%)
        regime_premium = regime_adjustment            # Regime volatility premium (e.g., 1-2%)
        sector_premium = SECTOR_BETA[sector] * 0.5   # Sector risk premium

        discount_rates[sector] = (
            base_rate + base_premium +
            regime_premium + sector_premium
        )

    return discount_rates  # Dict: {'Technology': 11.2%, 'Utilities': 8.5%, ...}
```

**Integration**: Valuation Agent queries Macro Analyst for discount rates instead of using arbitrary defaults

**5. Monthly Macro Report**

Format: 8-12 page PDF + interactive dashboard

**Structure**:

1. **Executive Summary** (1 page)

   - Current regime, confidence, key drivers
   - Month-over-month changes
   - Key takeaways for investment decisions

2. **Economic Indicators** (2-3 pages)

   - GDP, employment, inflation, monetary policy, credit
   - Indicator heatmap (green/yellow/red)
   - Trend analysis (3-month direction)

3. **Regime Analysis** (2 pages)

   - Historical context (how long in regime, comparisons to past episodes)
   - Leading indicators (signals for regime transition)
   - Transition probabilities (scenarios for next 3-6 months)

4. **Sector Implications** (2-3 pages)

   - Sector favorability rankings
   - Overweight/underweight recommendations
   - Sector rotation matrix
   - Macro sensitivities by sector

5. **Risks & Catalysts** (1-2 pages)

   - Upside risks (potential positive surprises)
   - Downside risks (threats to current regime)
   - Policy uncertainties (Fed, fiscal policy)
   - Event calendar (upcoming data releases, Fed meetings)

6. **Appendix**
   - Data tables (all indicators, historical values)
   - Indicator time series charts
   - Forecast comparisons (vs consensus)

**Dashboard Components**:

- Real-time regime probability gauge
- Indicator heatmap (color-coded by percentile)
- Yield curve visualization
- Sector rotation matrix (interactive)
- Economic calendar (upcoming events)

**Frequency**:

- Monthly report (1st week of month)
- Ad-hoc updates (regime change, major Fed announcement)

**Recipients**:

- Gate 1 (if regime impacts screening priorities)
- Gate 2 (if regime shift affects research priorities)
- Gate 5 (final decision context)
- All agents (background context)

**6. Memory System Integration**

Checkpoint subtask structure (DD-011 compatible):

```python
class MacroAnalystMemory:
    # L1 Working Memory (24h volatile)
    working_memory = {
        'current_indicators': {},           # Latest economic data
        'today_market_data': {},            # S&P, VIX, yields
        'pending_alerts': []                # Regime changes, threshold breaches
    }

    # L2 Context Memory (30d cache, Neo4j)
    context_memory = {
        'regime_history': [],               # Last 30 days regime classifications
        'indicator_history': {},            # 30-day time series for all indicators
        'sector_scores_history': {},        # 30-day sector favorability trends
        'recent_analyses': []               # Last month's macro analyses
    }

    # L3 Institutional Memory (permanent, Neo4j)
    institutional_memory = {
        'regime_patterns': {},              # Historical regime statistics (accuracy, duration, transitions)
        'sector_performance': {},           # Sector returns by regime (historical)
        'indicator_regimes': {},            # Which indicators predicted regime changes
        'forecast_accuracy': {},            # Track forecast vs actual outcomes
        'human_overrides': []               # When humans disagreed with macro view
    }
```

**Checkpoint Subtasks**:

1. Regime detection checkpoint (daily)
2. Indicator analysis checkpoint (daily)
3. Sector scoring checkpoint (weekly)
4. Monthly report checkpoint (monthly)

**Memory Queries**:

- "What was sector performance last time we were in BEAR_HIGH_RATES regime?"
- "Which indicators preceded the last regime transition?"
- "What was forecast accuracy for GDP last 6 months?"

---

## Options Considered

### Option 1: Extend Existing Agents (Rejected)

**Description**: Add macro analysis to existing Screening and Valuation agents instead of new agent

**Pros**:

- No new agent (maintain 13 agents)
- Simpler architecture (fewer coordination points)
- Lower memory overhead (no new agent memory)

**Cons**:

- **Scope creep**: Screening Agent already has 5 responsibilities, adding macro = 6
- **Different expertise**: Company screening ≠ macroeconomic analysis
- **Different cadence**: Macro updated monthly/weekly, screening per-stock
- **No centralization**: Each agent would duplicate macro analysis (inefficient)
- **Violates single responsibility**: Agents should specialize, not generalize

**Estimated Effort**: Medium (1-2 weeks, but adds complexity to 2 agents)

**Rejection Rationale**: Professional firms separate macro teams from equity analysts for good reason - different expertise, different update cycles. Extending existing agents violates single responsibility principle.

---

### Option 2: Macro Analyst Without Memory (Partial Solution - Rejected)

**Description**: Create Macro Analyst but make it stateless (no memory system)

**Pros**:

- Simpler implementation (skip memory integration)
- Lower storage requirements
- Faster MVP delivery (2 weeks faster)

**Cons**:

- **Can't learn**: No ability to track forecast accuracy, improve over time
- **No pattern recognition**: Can't identify which indicators predict regime changes
- **No human override tracking**: Can't learn from Gate 1/2 disagreements
- **Inconsistent with v2.0**: All specialist agents have memory (DD-005, DD-011)
- **Limited credibility scoring**: DD-008 requires memory for credibility calculation

**Estimated Effort**: Medium (2 weeks, but incomplete solution)

**Rejection Rationale**: Memory is core to v2.0 architecture. Macro Analyst needs to learn from forecast accuracy, regime transition predictions, human overrides. Stateless agent can't improve over time.

---

### Option 3: Macro Analyst with Memory (Selected)

**Description**: Full specialist agent with regime analysis, indicator monitoring, sector scoring, monthly reports, and memory system integration

```python
macro_analyst = {
    'responsibilities': [
        'Regime analysis (reuse DD-008 detection)',
        'Economic indicator monitoring (FRED, IMF, OECD)',
        'Sector favorability scoring (11 GICS sectors)',
        'Discount rate guidance (for Valuation Agent)',
        'Monthly macro reports (8-12 pages + dashboard)',
        'Ad-hoc regime change alerts'
    ],
    'memory': {
        'L1_working': '24h volatile',
        'L2_context': '30d cache (regime history, indicators, sector scores)',
        'L3_institutional': 'Permanent (regime patterns, forecast accuracy)'
    },
    'integrations': [
        'Screening Agent (sector favorability scores)',
        'Valuation Agent (discount rate guidance)',
        'Gates 1/2/5 (macro reports)',
        'DD-008 regime detection (input)',
        'DD-011 checkpoint system (subtasks)'
    ],
    'data_sources': ['FRED', 'IMF', 'OECD', 'CBOE'],  # All free
    'update_cadence': {
        'regime_detection': 'Daily',
        'indicator_monitoring': 'Daily',
        'sector_scoring': 'Weekly',
        'macro_report': 'Monthly + ad-hoc'
    }
}
```

**Pros**:

- **Mirrors professional firms**: Separate macro team, centralized analysis
- **Centralized reuse**: 1 macro analysis used across 1000+ stocks (efficient)
- **Memory-enabled learning**: Tracks forecast accuracy, improves over time
- **Consistent with v2.0**: All specialist agents have memory
- **Enables credibility scoring**: DD-008 can track regime forecast accuracy
- **Future-proof**: Phase 3 can add LLM layer to regime analysis

**Cons**:

- **14th agent**: Increases agent count (13 → 14)
- **Implementation complexity**: Memory integration, checkpoint subtasks
- **Data infrastructure**: FRED/IMF/OECD API integration needed
- **Monthly overhead**: 2-4 hours report generation

**Estimated Effort**: High (3-4 weeks implementation + 1 week testing)

**Selected**: Full-featured specialist agent provides centralized macro analysis, reusable across all stocks, consistent with v2.0 memory architecture. Mirrors professional firm structure (proven model).

---

## Rationale

### Why Option 3 (Macro Analyst with Memory) Was Selected

**1. Centralized Analysis Efficiency**

Macro analysis done once, reused across portfolio:

```text
Without Macro Analyst:
  - Screen 1000 stocks → each Screening Agent duplicates macro lookup (1000× overhead)
  - Valuation Agent queries external data per stock (1000× API calls)
  - Human gates lack consistent macro framework

With Macro Analyst:
  - 1 monthly macro report → cached for all analyses
  - 1 sector favorability ranking → used by all screening
  - 1 discount rate table → used by all valuations
  - Result: 1000× efficiency gain, consistent framework
```

**2. Professional Firm Best Practices**

Investment firms separate macro from equity analysis:

- **Goldman Sachs**: Macro Strategy team (separate from equity research)
- **Dodge & Cox**: Macro views inform sector allocation
- **Piper Sandler**: Monthly macro outlook distributed to all analysts

**Why separate?**:

- Different expertise (economist vs equity analyst)
- Different update cycle (monthly macro vs per-stock research)
- Centralized reuse (1 macro view for 1000s of stocks)

**3. Enables Top-Down + Bottom-Up Integration**

Professional fundamental analysis combines both:

- **Top-Down**: Macro → Sector → Industry (timing, asset allocation)
- **Bottom-Up**: Company fundamentals (stock selection, valuation)

Current system: Bottom-up only (missing half the equation)

Macro Analyst: Adds top-down layer, completes integration

**4. Reuses DD-008 Regime Detection (No Rebuild)**

DD-008 already detects 6 market regimes daily:

- Macro Analyst uses regime as input
- Adds analysis layer (sector favorability, discount rates, scenarios)
- No detection rebuild needed (infrastructure reuse)

**5. Memory Enables Learning**

```text
Without Memory:
  - Forecast GDP growth: 2.5%
  - Actual: 1.8%
  - Error: 0.7%
  - No learning (repeat same mistakes)

With Memory:
  - Forecast GDP: 2.5%
  - Actual: 1.8%
  - Store: Overestimated by 0.7% in BEAR_HIGH_RATES regime
  - Learn: Adjust future forecasts in similar regimes
  - Next time: Forecast 2.3% (learned from error)
```

**6. Tradeoffs Deemed Acceptable**

**14th Agent vs Efficiency**: Adding 1 agent increases coordination complexity, but centralized macro analysis saves 1000× duplicate effort

**Implementation Time vs Long-Term Value**: 3-4 weeks upfront investment, but provides macro foundation for all future analyses

**Data Infrastructure vs Free Sources**: FRED/IMF/OECD APIs require integration, but all free (no recurring costs)

---

## Consequences

### Positive Impacts

**1. Valuation Accuracy Improvement**

- **Before**: Valuation Agent uses 8% default discount rate
- **After**: Valuation Agent uses regime-calibrated rates (8-12% depending on Fed policy)
- **Benefit**: Valuations reflect interest rate environment, reducing systematic over/under-valuation

**Example**:

```text
BEAR_HIGH_RATES regime (Fed Funds 5.5%):
  Risk-free: 4.5%
  Equity premium: 5%
  Regime premium: 2% (high volatility)
  Discount rate: 11.5%

vs arbitrary 8% default:
  Company DCF at 8%: $50/share
  Company DCF at 11.5%: $34/share
  Difference: -32% (major valuation correction)
```

**2. Screening Effectiveness Improvement**

- **Before**: Screening Agent selects stocks without sector context
- **After**: Screening Agent weights candidates by sector favorability scores
- **Benefit**: Higher-quality candidates (well-timed sectors prioritized)

**Example**:

```text
BEAR_HIGH_RATES regime:
  Technology (growth): Favorability 45/100 (low)
  Healthcare (defensive): Favorability 78/100 (high)

Screening results weighted:
  Tech stock (excellent fundamentals): 45% sector × 90% fundamentals = 40.5 final score
  Healthcare stock (good fundamentals): 78% sector × 75% fundamentals = 58.5 final score

Healthcare prioritized despite weaker fundamentals (better timing)
```

**3. Human Gate Efficiency Gain**

- **Before**: Human manually checks macro context (65min overhead per gate)
- **After**: Macro report pre-loaded (macro context in <5min)
- **Benefit**: 60min saved per gate, 92% efficiency gain

**Gate 1 (Screening)**:

- Pre-loaded: Current regime, sector favorability rankings
- Human validates screening aligned with macro context
- Decision time: 65min → 15min (50min saved)

**4. Consistent Macro Framework**

- **Before**: Each analyst may have different macro view
- **After**: Single macro report, consistent framework across all analyses
- **Benefit**: Reduced conflicts, faster debate resolution

**5. Enables Future Enhancements**

- **Phase 3**: Add LLM layer to regime analysis (hybrid rule-based + LLM)
- **Phase 4**: International macro coverage (Europe, Asia macro regimes)
- **Phase 4**: Alternative data integration (credit card spending, web traffic)

### Negative Impacts / Tradeoffs

**1. Implementation Complexity**

- **Agent count**: 13 → 14 agents (coordination complexity)
- **Memory integration**: L1/L2/L3 memory setup, checkpoint subtasks
- **Data infrastructure**: FRED/IMF/OECD API integration, daily data fetching
- **Report generation**: PDF rendering, dashboard creation
- **Estimated effort**: 3-4 weeks implementation + 1 week testing

**2. Monthly Overhead**

- **Report generation**: 2-4 hours monthly (automated batch processing)
- **Indicator monitoring**: Daily data fetching (5-10 minutes)
- **Sector scoring**: Weekly recalculation (15-20 minutes)
- **Total**: ~6 hours/month ongoing maintenance

**3. Data Dependencies**

- **FRED API**: Free but rate-limited (120 requests/minute)
- **IMF/OECD**: Free but update lag (monthly vs real-time)
- **Market data**: S&P 500, VIX (need reliable source)
- **Mitigation**: Cache aggressively, batch fetch, fallback sources

**4. Forecast Accuracy Risk**

- **Macro forecasting is hard**: Even professional economists miss major shifts
- **Regime transitions**: Lagging indicators (regime detected after transition starts)
- **False signals**: Indicators can send conflicting signals
- **Mitigation**: Human validation at gates, confidence intervals, scenario planning

**5. Explanation Complexity**

- **Sector favorability formula**: 4 factors (performance, valuation, sensitivity, momentum) may be hard to explain to users
- **Discount rate calculation**: Risk-free + equity premium + regime premium + sector premium (multi-component)
- **Mitigation**: Provide breakdowns in UI, highlight dominant factors

### Affected Components

**Database Schema** (Memory System):

```cypher
// Macro Analyst Memory Node
CREATE (m:AgentMemory {
  agent_id: 'macro_analyst',

  // L1 Working Memory (24h)
  current_regime: 'BEAR_HIGH_RATES',
  regime_confidence: 0.85,
  today_indicators: {...},

  // L2 Context Memory (30d)
  regime_history_30d: [...],
  indicator_history_30d: {...},
  sector_scores_history_30d: {...},

  // L3 Institutional Memory (permanent)
  regime_statistics: {...},
  forecast_accuracy: {...},
  human_overrides: [...]
})

// Relationships
CREATE (m)-[:ANALYZES_REGIME]->(r:Regime {name: 'BEAR_HIGH_RATES'})
CREATE (m)-[:MONITORS_INDICATOR]->(i:Indicator {name: 'Fed_Funds_Rate'})
CREATE (m)-[:SCORES_SECTOR]->(s:Sector {name: 'Technology'})
```

**Agent Integrations**:

- **Screening Agent**: Queries `get_sector_favorability()` for sector weights
- **Valuation Agent**: Queries `get_discount_rates(sector)` for DCF models
- **All Agents**: Access macro report for background context
- **DD-008 Regime Detection**: Provides regime classification to Macro Analyst

**Human Interface**:

- **Gate 1 Dashboard**: Display current regime, sector favorability rankings
- **Gate 2 Dashboard**: Display macro report highlights, regime transition probabilities
- **Gate 5 Dashboard**: Full macro report + company analysis (holistic view)
- **Macro Report Viewer**: PDF viewer + interactive dashboard

**Documentation**:

- ✅ `docs/architecture/01-system-overview.md`: Agent count 13 → 14
- ✅ `docs/architecture/03-agents-specialist.md`: Add Section 6 (Macro Analyst)
- ✅ `docs/operations/01-analysis-pipeline.md`: Add Phase 0 (async macro analysis)
- ✅ `docs/operations/02-human-integration.md`: Add macro context to gates
- ✅ `docs/operations/03-data-management.md`: Add macro data sources
- ✅ `docs/implementation/01-roadmap.md`: Add Phase 2 deliverable
- ✅ `docs/implementation/02-tech-requirements.md`: Add APIs, storage
- ✅ `CLAUDE.md`: Update agent list (13 → 14)

---

## Implementation Notes

### Critical Constraints

**1. Performance Target**: <200ms macro context retrieval

- Cache sector favorability scores (invalidate weekly)
- Cache discount rates (invalidate on Fed rate change)
- Cache regime analysis (invalidate on regime change)
- Batch fetch indicators (daily 5am, not per-request)

**2. Data Requirements**: Free data sources only (Phase 2)

- FRED API: Fed Funds Rate, GDP, CPI, unemployment (free)
- IMF WEO Database: Global macro forecasts (free)
- OECD Stats: 700 indicators, 27 EU countries (free)
- CBOE: VIX data (free via API or scraping)

**3. Regime Detection**: Reuse DD-008 (no rebuild)

```python
# Macro Analyst queries DD-008 for regime
current_regime = regime_detector.get_current_regime()  # DD-008

# Macro Analyst adds analysis layer
regime_analysis = analyze_regime_implications(current_regime)
```

**4. Graceful Degradation**: Handle data source failures

- FRED down → fallback to IMF/OECD
- All sources down → use last cached values (with staleness warning)
- Indicator missing → skip from analysis (don't block report)

### Integration Points

**1. Screening Agent Integration**

```python
# Screening Agent queries Macro Analyst for sector weights
sector_scores = macro_analyst.get_sector_favorability()

# Apply sector weighting to screening results
for candidate in screening_results:
    sector = candidate.sector
    fundamental_score = candidate.score  # 0-100
    sector_weight = sector_scores[sector] / 100  # Normalize to 0-1

    final_score = fundamental_score * sector_weight
    candidate.final_score = final_score

# Sort by final score (sector-weighted fundamentals)
screening_results.sort(key=lambda x: x.final_score, reverse=True)
```

**2. Valuation Agent Integration**

```python
# Valuation Agent queries Macro Analyst for discount rate
sector = company.sector
discount_rate = macro_analyst.get_discount_rate(sector)

# Use in DCF model
fcf_projections = project_free_cash_flows(company, years=10)
terminal_value = calculate_terminal_value(fcf_projections[-1], discount_rate, perpetual_growth=0.025)

dcf_value = sum([fcf / (1 + discount_rate)**year for year, fcf in enumerate(fcf_projections, 1)])
dcf_value += terminal_value / (1 + discount_rate)**10
```

**3. Human Gate Integration**

```python
# Gate 1 (Screening Validation)
gate1_context = {
    'screening_results': candidates,
    'macro_context': {
        'regime': macro_analyst.get_current_regime(),
        'sector_favorability': macro_analyst.get_sector_favorability(),
        'key_risks': macro_analyst.get_top_risks(n=3)
    }
}

# Gate 2 (Research Direction)
gate2_context = {
    'company': company,
    'research_topics': proposed_topics,
    'macro_context': {
        'regime_report': macro_analyst.get_latest_report(summary=True),
        'transition_probabilities': macro_analyst.get_regime_transitions(),
        'sector_outlook': macro_analyst.get_sector_outlook(company.sector)
    }
}
```

**4. Memory System Integration**

```python
# Checkpoint subtasks (DD-011)
macro_analyst_checkpoints = [
    {
        'id': 'regime_detection',
        'frequency': 'daily',
        'duration': '5min',
        'stores': ['current_regime', 'regime_confidence', 'transition_probs']
    },
    {
        'id': 'indicator_analysis',
        'frequency': 'daily',
        'duration': '10min',
        'stores': ['economic_indicators', 'indicator_trends', 'significance_flags']
    },
    {
        'id': 'sector_scoring',
        'frequency': 'weekly',
        'duration': '20min',
        'stores': ['sector_favorability', 'sector_valuations', 'sector_momentum']
    },
    {
        'id': 'macro_report',
        'frequency': 'monthly',
        'duration': '2-4hr',
        'stores': ['monthly_report_pdf', 'dashboard_data', 'forecast_updates']
    }
]
```

### Testing Requirements

**1. Regime Analysis Accuracy**

Backtest on 2020-2024 data:

```python
# For each month in 2020-2024
for month in date_range('2020-01', '2024-12'):
    # Get regime as of that month
    regime = get_historical_regime(month)

    # Get Macro Analyst sector favorability scores
    sector_scores = macro_analyst.calculate_sector_favorability(regime)

    # Measure actual sector performance next 3 months
    actual_returns = get_sector_returns(month, months=3)

    # Correlation between scores and actual returns
    correlation = calculate_correlation(sector_scores, actual_returns)

# Target: correlation > 0.6 (sector scores predictive of performance)
assert mean(correlations) > 0.6
```

**2. Discount Rate Calibration**

Validate discount rates vs realized returns:

```python
# For each year in 2015-2024
for year in range(2015, 2025):
    # Get Macro Analyst discount rates by sector
    discount_rates = macro_analyst.get_discount_rates_historical(year)

    # Get actual sector returns that year
    actual_returns = get_sector_returns(year)

    # Discount rates should approximate realized returns
    error = abs(discount_rates - actual_returns)

# Target: mean error < 3% (discount rates within 3% of realized returns)
assert mean(errors) < 0.03
```

**3. Report Generation Performance**

```python
# Monthly report generation
start_time = time()
report = macro_analyst.generate_monthly_report()
generation_time = time() - start_time

# Target: <4 hours (automated batch processing)
assert generation_time < 4 * 3600

# Report completeness
assert report.has_section('executive_summary')
assert report.has_section('economic_indicators')
assert report.has_section('regime_analysis')
assert report.has_section('sector_implications')
assert len(report.pages) >= 8
```

**4. Data Source Resilience**

```python
# Test fallback behavior
def test_data_source_failure():
    # Simulate FRED API down
    mock_fred_api(status='unavailable')

    # Macro Analyst should fallback to IMF/OECD
    indicators = macro_analyst.get_indicators()

    # Should still get most indicators (maybe missing 1-2)
    assert len(indicators) >= 12  # Out of 15 total

    # Should include staleness warning
    assert indicators.metadata.staleness_warning == True
    assert indicators.metadata.source == 'IMF'  # Fallback source
```

### Rollback Strategy

**Phase 1: Shadow Mode** (Week 1-2)

- Macro Analyst generates reports but not used in decisions
- Agents use current logic (no macro context)
- Human gates optionally review macro reports (feedback collection)
- Validate report quality, data accuracy

**Phase 2: Partial Integration** (Week 3-4)

- Enable sector favorability in Screening Agent (50% weight)
- Enable discount rate guidance in Valuation Agent (optional override)
- Monitor for regressions (screening quality, valuation accuracy)

**Phase 3: Full Integration** (Week 5)

- Full sector weighting (100%)
- Mandatory discount rates (no overrides)
- Macro reports integrated in all gates
- Monitor for 30 days (rollback option available)

**Rollback Trigger**: If Macro Analyst shows:

- Sector favorability correlation <0.4 (vs target >0.6)
- Discount rate error >5% (vs target <3%)
- Report generation failures >20%
- Human gate rejection rate >40%

**Rollback Procedure**:

1. Disable Macro Analyst integrations (config flag)
2. Agents revert to previous logic (no sector weighting, default discount rates)
3. Investigate root cause (data quality? Formula errors? Regime detection?)
4. Fix in shadow mode, re-validate
5. Re-attempt integration after validation

---

**Estimated Implementation Effort**: 3-4 weeks

**Breakdown**:

- Week 1: Core logic (regime analysis, indicator monitoring, sector scoring, discount rates)
- Week 2: Memory integration (L1/L2/L3 setup, checkpoint subtasks), data infrastructure (FRED/IMF/OECD APIs)
- Week 3: Report generation (PDF rendering, dashboard creation), agent integrations (Screening, Valuation)
- Week 4: Testing (backtesting, calibration, resilience), documentation updates

**Dependencies**:

**Must Be Completed First**:

- Phase 1 data infrastructure (API integration capabilities)
- [DD-005: Memory Scalability](DD-005_MEMORY_SCALABILITY_OPTIMIZATION.md) - Macro Analyst needs memory system
- [DD-011: Agent Checkpoint System](DD-011_AGENT_CHECKPOINT_SYSTEM.md) - Checkpoint subtask structure
- [DD-008: Agent Credibility System](DD-008_AGENT_CREDIBILITY_SYSTEM.md) - Regime detection (reuse)

**External APIs Required**:

- **FRED API** (Federal Reserve Economic Data): Free, register for key at <https://fred.stlouisfed.org/>
- **IMF WEO API**: Free, <https://www.imf.org/external/datamapper/api/help>
- **OECD Stats API**: Free, <https://data.oecd.org/api/>
- **CBOE VIX**: Free via API or web scraping

---

## Open Questions

**1. Regime confidence threshold for alerts?**

When should Macro Analyst send ad-hoc regime change alerts?

**Options**:

- A) Confidence >0.7 (aggressive, more alerts)
- B) Confidence >0.8 (balanced)
- C) Confidence >0.9 (conservative, fewer alerts)

**Tradeoff**: Too aggressive (A) → noise, too conservative (C) → miss important shifts

**Recommendation**: Start with B (0.8), tune based on Phase 2 feedback

**2. Dashboard tool: build vs buy?**

**Options**:

- A) Build custom: Plotly Dash / Streamlit (Python-based, full control, 2-3 weeks dev)
- B) Buy: Tableau / Power BI (enterprise features, $70-$150/user/mo, 1 week setup)

**Decision**: Deferred to implementation phase

**3. Sector favorability formula weights?**

Current: Performance 40%, Valuation 30%, Sensitivity 20%, Momentum 10%

**Question**: Optimal weights? Or make configurable?

**Options**:

- A) Fixed weights (simpler, current proposal)
- B) Regime-dependent weights (e.g., high vol regime → increase sensitivity to 30%)
- C) Backtest-optimized weights (machine learning to find optimal)

**Recommendation**: Start with A (fixed), consider B in Phase 3 if needed

**Blocking**: No - reasonable defaults available, can tune later

---

## References

**Internal Documentation**:

- [Macro & Industry Analysis Plan](../../plans/macro-industry-analysis-plan.md) - Original proposal
- [System Overview](../architecture/01-system-overview.md) - Agent architecture
- [Specialist Agents](../architecture/03-agents-specialist.md) - Specialist agent descriptions
- [Memory System](../architecture/02-memory-system.md) - L1/L2/L3 memory structure
- [DD-008: Agent Credibility System](DD-008_AGENT_CREDIBILITY_SYSTEM.md) - Regime detection
- [DD-011: Agent Checkpoint System](DD-011_AGENT_CHECKPOINT_SYSTEM.md) - Checkpoint subtasks

**External Research**:

- **NBER Business Cycle Dating**: Regime classification methodology
- **Federal Reserve Economic Data (FRED)**: Economic indicator database
- **IMF World Economic Outlook**: Global macro forecasts
- **Professional Firm Practices**: Goldman Sachs macro strategy, Dodge & Cox macro integration

**Data Sources**:

- FRED API Documentation: <https://fred.stlouisfed.org/docs/api/>
- IMF Data API: <https://www.imf.org/external/datamapper/api/help>
- OECD Stats API: <https://data.oecd.org/api/>
- CBOE VIX Methodology: <https://www.cboe.com/tradable_products/vix/>

---

## Status History

| Date       | Status   | Notes                                         |
| ---------- | -------- | --------------------------------------------- |
| 2025-11-19 | Proposed | Initial proposal based on macro-industry plan |
| 2025-11-19 | Approved | Approved for Phase 2 implementation           |

**Next Steps**:

1. Week 1: Implement core logic (regime analysis, indicators, sector scoring, discount rates)
2. Week 2: Memory integration, data infrastructure (FRED/IMF/OECD APIs)
3. Week 3: Report generation, agent integrations
4. Week 4: Testing, validation, documentation

---

## Notes

**Design Philosophy**: This decision adds **top-down macro analysis** to complement existing **bottom-up company analysis**, mirroring professional investment firm best practices.

**Key Insight**: Professional firms separate macro teams from equity analysts for good reason:

- Different expertise (economist vs equity analyst)
- Different update cycle (monthly/quarterly vs per-stock)
- Centralized reuse (1 macro view for 1000s of stocks)

**Efficiency Gain**: 1 macro analysis → reused across 1000 stocks (vs duplicating macro lookup 1000 times)

**Accuracy Gain**: Regime-calibrated discount rates (11.5% in high-rate regime vs 8% arbitrary default) prevent systematic valuation errors

**Integration Points**:

- Screening Agent: Sector favorability scores prioritize well-timed candidates
- Valuation Agent: Discount rate guidance reflects interest rate environment
- Human Gates: Pre-loaded macro context (60min saved per gate)

**Future Enhancements** (Phase 3+):

- Add LLM layer to regime analysis (hybrid rule-based + LLM)
- International macro coverage (Europe, Asia regimes)
- Alternative data integration (credit card spending, web traffic)
- Sector rotation dashboard (interactive visualization)
