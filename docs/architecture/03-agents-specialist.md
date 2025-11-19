# Specialist Agents

## Overview

Specialist agents perform the core analytical work of the system. Each agent has deep domain expertise in a specific area of fundamental analysis, maintains a local memory cache of domain-specific patterns, and leverages historical context to improve accuracy over time.

The six specialist agents are:

1. Screening Agent - Initial filtering and candidate identification
2. Business Research Agent - Business model and competitive analysis
3. Financial Analyst Agent - Quantitative financial analysis
4. Strategy Analyst Agent - Strategic direction and capital allocation
5. Valuation Agent - Fair value determination and price targets
6. Macro Analyst Agent - Top-down macroeconomic analysis (Phase 2+)

---

## 1. Screening Agent (Memory-Enhanced)

### Purpose

Initial filtering and candidate identification with historical awareness

### Core Responsibilities

- Monitor financial screeners (Finviz, custom screeners)
- Apply quantitative filters:
  - 10-year revenue CAGR
  - Operating profit margin
  - Net debt/EBITDA ratios
- Generate one-page company summaries
- Prioritize candidates for deeper analysis

### Checkpoint Subtask Structure

For execution state persistence and failure recovery ([DD-011](../design-decisions/DD-011_AGENT_CHECKPOINT_SYSTEM.md)):

| Subtask               | Deliverable                | Storage         | Est. Duration |
| --------------------- | -------------------------- | --------------- | ------------- |
| `screener_data_fetch` | Raw screener results       | PostgreSQL      | 5 min         |
| `quantitative_filter` | Filtered candidate list    | PostgreSQL      | 3 min         |
| `summary_generation`  | One-page summaries         | PostgreSQL      | 10 min        |
| `priority_ranking`    | Ranked recommendation list | Neo4j + Message | 2 min         |

Checkpoint saved after each subtask completes, enabling resume from last completed subtask on failure.

### Memory Capabilities

- Track screening pattern success rates by sector
- Remember false positives/negatives and root causes
- Learn which metrics predict success in different market conditions
- Cache frequently screened companies with historical outcomes

### Key Metrics Tracked

- Screening efficiency rate (candidates → successful analyses)
- False positive/negative rates with pattern attribution
- Time to identify opportunities
- Pattern accuracy by sector and market regime

### Local Memory Structure

```yaml
screening_patterns:
  - pattern_id: 'value_trap_tech'
    description: 'Low P/E tech often value trap'
    success_rate: 0.23
    learned_from:
      ['INTC_2020', 'IBM_2019', 'CSCO_2018', 'ORCL_2021', 'HPQ_2019']
    sectors: ['Technology']

failed_screens:
  - company: 'XYZ'
    reason: 'Missed accounting irregularity'
    lesson: 'Add cash flow quality check'
    date: '2024-03-15'
```

---

## 2. Business Research Agent (Memory-Enhanced)

### Purpose

Deep understanding of business operations with historical context

### Core Responsibilities

- Analyze SEC filings (10-K, 10-Q, 8-K)
- Evaluate business segments and revenue streams
- Assess geographic exposure and concentration risks
- Identify competitive advantages (moats)
- Maintain SWOT analysis framework
- Track key performance indicators (KPIs)

### Research Framework

```text
Strengths    | Weaknesses
-------------|-------------
- Moats      | - Risks
- Market pos.| - Dependencies

Opportunities| Threats
-------------|-------------
- Growth     | - Competition
- Expansion  | - Regulation
```

### Checkpoint Subtask Structure

For execution state persistence and failure recovery ([DD-011](../design-decisions/DD-011_AGENT_CHECKPOINT_SYSTEM.md)):

| Subtask                   | Deliverable                | Storage    | Est. Duration |
| ------------------------- | -------------------------- | ---------- | ------------- |
| `sec_filing_parsing`      | Parsed 10-K/10-Q sections  | PostgreSQL | 20 min        |
| `business_model_analysis` | Revenue streams, segments  | Neo4j      | 15 min        |
| `swot_analysis`           | SWOT framework             | Neo4j      | 15 min        |
| `moat_evaluation`         | Competitive advantages     | Neo4j      | 10 min        |
| `kpi_tracking`            | Key performance indicators | PostgreSQL | 5 min         |

Checkpoint saved after each subtask completes, enabling resume from last completed subtask on failure.

### Memory Capabilities

- Store business model patterns and success rates
- Track competitive advantage durability over time
- Remember management track records across companies
- Identify recurring industry themes and cycles
- Cache similar business model outcomes

### Memory Queries During Analysis

**Note**: Code samples referenced here have been omitted from architecture docs. See `/examples/` directory for implementation examples.

Key memory queries performed:

- Check if company previously analyzed
- Find similar business models
- Get management track record across companies
- Synthesize current data with historical context and pattern matches

---

## 3. Financial Analyst Agent (Memory-Enhanced)

### Purpose

Quantitative analysis of financial health with prediction tracking

### Core Responsibilities

- Process financial statements (10-K, 10-Q)
- Calculate growth rates (5/10/15-year CAGR)
- Generate common-size statements
- Compute financial ratios:
  - **Profitability**: ROE, ROA, ROIC
  - **Efficiency**: Asset turnover, working capital ratios
  - **Leverage**: Debt/equity, interest coverage
  - **Liquidity**: Current ratio, quick ratio
- Perform peer comparisons and benchmarking
- Identify accounting red flags

### Red Flag Detection

- Related-party transactions
- Excessive management compensation
- Aggressive accounting policies
- Unusual non-recurring adjustments
- Cash flow vs. earnings mismatches

### Checkpoint Subtask Structure

For execution state persistence and failure recovery ([DD-011](../design-decisions/DD-011_AGENT_CHECKPOINT_SYSTEM.md)):

| Subtask              | Deliverable                    | Storage    | Est. Duration |
| -------------------- | ------------------------------ | ---------- | ------------- |
| `10k_parsing`        | Financial statements JSON      | PostgreSQL | 15 min        |
| `ratio_calculation`  | Ratio table (ROE/ROA/ROIC/etc) | PostgreSQL | 5 min         |
| `peer_comparison`    | Comparison matrix              | Redis L2   | 10 min        |
| `red_flag_detection` | Red flag findings              | Neo4j      | 20 min        |

Checkpoint saved after each subtask completes, enabling resume from last completed subtask on failure.

### Memory Capabilities

- Track accuracy of financial projections by metric and sector
- Store sector-specific ratio norms and their evolution
- Learn accounting red flag patterns from historical cases
- Remember peer comparison contexts and outcomes
- Maintain prediction error patterns for calibration

### Prediction Tracking

```json
{
  "prediction_id": "AAPL_2024_margins",
  "predicted": {
    "gross_margin": 0.44,
    "operating_margin": 0.3
  },
  "actual": {
    "gross_margin": 0.45,
    "operating_margin": 0.29
  },
  "accuracy_score": 0.96,
  "lessons": "Supply chain improvements underestimated",
  "calibration_update": "Reduce conservatism on Apple by 2%"
}
```

---

## 4. Strategy Analyst Agent (Memory-Enhanced)

### Purpose

Evaluate strategic direction and execution with pattern recognition

### Core Responsibilities

- Analyze capital allocation decisions
- Review management track record
- Process earnings call transcripts
- Evaluate M&A strategy and execution
- Assess strategic priorities alignment
- Monitor capital expenditure plans and ROI

### Evaluation Metrics

- Historical ROI (5/10/15-year averages)
- Return on Capital Employed (ROCE)
- Return on Invested Capital (ROIC)
- Execution success rate on stated initiatives
- M&A value creation track record

### Checkpoint Subtask Structure

For execution state persistence and failure recovery ([DD-011](../design-decisions/DD-011_AGENT_CHECKPOINT_SYSTEM.md)):

| Subtask                      | Deliverable               | Storage         | Est. Duration |
| ---------------------------- | ------------------------- | --------------- | ------------- |
| `historical_roi`             | 10Y ROI timeseries        | PostgreSQL      | 10 min        |
| `ma_review`                  | M&A track record findings | Neo4j           | 25 min        |
| `mgmt_compensation`          | Compensation analysis     | Neo4j           | 15 min        |
| `capital_allocation_scoring` | Final score               | Neo4j + Message | 5 min         |

Checkpoint saved after each subtask completes, enabling resume from last completed subtask on failure.

### Memory Capabilities

- Management credibility scoring by executive and company
- Capital allocation pattern matching across industries
- M&A success rate tracking with deal characteristics
- Strategic pivot outcome history (success factors)
- Track record of guidance accuracy

---

## 5. Valuation Agent (Memory-Enhanced)

### Purpose

Determine fair value and price targets with model calibration

### Core Responsibilities

**Relative valuation**:

- P/E, EV/EBITDA, FCF yield comparisons
- Forward and trailing multiples
- Peer group analysis

**Absolute valuation**:

- DCF modeling with detailed assumptions
- Sensitivity analysis on key drivers
- Scenario planning (base/bull/bear)

**Additional Analysis**:

- Incorporate current events impact on valuation
- Set price targets and entry points
- Technical analysis for timing considerations

### Checkpoint Subtask Structure

For execution state persistence and failure recovery ([DD-011](../design-decisions/DD-011_AGENT_CHECKPOINT_SYSTEM.md)):

| Subtask                | Deliverable                     | Storage    | Est. Duration |
| ---------------------- | ------------------------------- | ---------- | ------------- |
| `dcf_assumptions`      | Assumption table                | PostgreSQL | 10 min        |
| `cash_flow_projection` | 10Y FCF model                   | PostgreSQL | 15 min        |
| `wacc_calculation`     | WACC inputs/result              | PostgreSQL | 5 min         |
| `terminal_value`       | Terminal value calc             | PostgreSQL | 5 min         |
| `sensitivity_analysis` | Scenario table (base/bull/bear) | Neo4j      | 15 min        |

Checkpoint saved after each subtask completes, enabling resume from last completed subtask on failure.

### Memory Capabilities

- Track valuation model accuracy by sector and market regime
- Store multiple expansion/contraction patterns with triggers
- Learn macro sensitivity factors and their predictive power
- Remember scenario outcome probabilities
- Calibrate discount rates based on historical accuracy
- Track terminal value assumption performance

---

## 6. Macro Analyst Agent (Memory-Enhanced)

### Purpose

Provides top-down macroeconomic analysis to complement bottom-up company research. Analyzes market regimes, economic indicators, and sector dynamics to guide screening priorities and valuation assumptions.

**Deployment**: Phase 2 (Core Agents)

**Related Decisions**:

- [DD-022: Macro Analyst Agent](../design-decisions/DD-022_MACRO_ANALYST_AGENT.md)
- [DD-026: Macro Reports](../design-decisions/DD-026_MACRO_REPORTS.md)
- [DD-008: Agent Credibility System](../design-decisions/DD-008_AGENT_CREDIBILITY_SYSTEM.md) - Reuses regime detection

### Core Responsibilities

1. **Regime Analysis**

   - Reuses DD-008 regime detection (6 market regimes)
   - Analyzes investment implications of current regime
   - Forecasts regime transition probabilities (next 3-6 months)
   - Generates macro scenarios (base/bull/bear cases)

2. **Economic Indicator Monitoring**

   - Tracks 15-20 key indicators across 5 categories:
     - Growth: GDP, industrial production, employment
     - Inflation: CPI, PCE, wage growth
     - Monetary: Fed Funds, 10Y Treasury, yield curve
     - Credit: Corporate spreads, high yield spreads
     - Sentiment: VIX, consumer confidence
   - Daily monitoring, monthly comprehensive analysis
   - Identifies threshold breaches (>95th or <5th percentile)

3. **Sector Favorability Scoring**

   - Ranks 11 GICS sectors 0-100 based on:
     - Historical performance in current regime (40% weight)
     - Current valuations vs historical (30% weight)
     - Sector sensitivity to regime factors (20% weight)
     - 3-month momentum (10% weight)
   - Updated weekly, used by Screening Agent for sector weighting

4. **Discount Rate Guidance**

   - Calculates sector-specific discount rates for DCF models
   - Formula: Risk-free + Equity premium + Regime premium + Sector premium
   - Reflects current rate environment (vs arbitrary defaults)
   - Updated monthly or on Fed rate changes

5. **Monthly Macro Reports**
   - 8-12 page PDF reports (1st week of month)
   - Sections: Executive summary, indicators, regime analysis, sector implications, risks/catalysts
   - Interactive dashboard (real-time regime gauge, indicator heatmap, sector rotation matrix)
   - Ad-hoc updates on regime changes or major Fed announcements
   - See DD-026 for full format specifications

### Memory Structure

**L1 Working Memory** (24h volatile):

- Current economic indicators (latest FRED/IMF/OECD data)
- Today's market data (S&P, VIX, yields)
- Pending alerts (regime changes, threshold breaches)

**L2 Context Memory** (30d cache, Redis):

- Regime history (last 30 days classifications)
- Indicator time series (30-day history for all 23-28 indicators)
- Sector favorability trends (30-day scoring history)
- Recent macro analyses

**L3 Institutional Memory** (permanent, Neo4j):

- Regime statistics (historical regime durations, transitions, sector performance)
- Forecast accuracy tracking (GDP/inflation/unemployment predictions vs actuals)
- Indicator-regime correlations (which indicators predict regime changes)
- Human override patterns (when gates disagreed with macro view)

### Checkpoint Subtask Structure

DD-011 compatible checkpoints:

1. **Regime Detection Checkpoint** (daily, 5min)

   - Query DD-008 for current regime
   - Analyze regime implications
   - Update transition probabilities
   - Store: current_regime, confidence, transition_probs

2. **Indicator Analysis Checkpoint** (daily, 10min)

   - Fetch economic indicators from FRED/IMF/OECD
   - Calculate percentiles, trends, significance
   - Identify threshold breaches
   - Store: indicator_values, percentiles, trends, alerts

3. **Sector Scoring Checkpoint** (weekly, 20min)

   - Calculate sector favorability scores (11 sectors)
   - Update sector valuations
   - Calculate momentum
   - Store: sector_scores, rankings, rationale

4. **Macro Report Checkpoint** (monthly, 2-4hr)
   - Generate full PDF report
   - Update dashboard data
   - Publish to gates and agents
   - Store: report_pdf, dashboard_data, forecast_updates

### Integration Points

**Inputs**:

- DD-008 Regime Detection → Current market regime classification
- FRED API → Economic indicators (GDP, CPI, unemployment, Fed Funds)
- IMF/OECD APIs → Global macro data, international indicators
- CBOE → VIX, volatility indices
- Market Data → S&P 500 returns, sector ETF prices

**Outputs**:

- **To Screening Agent**: Sector favorability scores (dict: {sector: score 0-100})
- **To Valuation Agent**: Discount rates by sector (dict: {sector: rate})
- **To Gates 1/2/5**: Macro reports (PDF, dashboard, API)
- **To All Agents**: Background macro context (regime, indicators, risks)

**Example Integration (Screening Agent)**:

```python
# Screening Agent queries Macro Analyst for sector weights
sector_scores = macro_analyst.get_sector_favorability()

# Apply sector weighting to candidates
for candidate in screening_results:
    sector_weight = sector_scores[candidate.sector] / 100
    candidate.final_score = candidate.fundamental_score * sector_weight
```

**Example Integration (Valuation Agent)**:

```python
# Valuation Agent queries Macro Analyst for discount rate
discount_rate = macro_analyst.get_discount_rate(company.sector)

# Use in DCF model instead of arbitrary default
dcf_value = calculate_dcf(company, discount_rate=discount_rate)
```

### Data Sources

**Free APIs (Phase 2)**:

- **FRED** (Federal Reserve Economic Data): GDP, CPI, unemployment, Fed Funds - free, register at fred.stlouisfed.org
- **IMF WEO Database**: Global macro forecasts - free, api: imf.org/external/datamapper/api/help
- **OECD Stats**: 27 EU countries, 700 indicators - free, api: data.oecd.org/api/
- **CBOE**: VIX data - free via API or web scraping

**Paid Options (Phase 3+, deferred)**:

- Bloomberg Terminal ($32K/yr): Comprehensive macro data, real-time
- FactSet ($12K-$50K/yr): Company data, screening, peer comps

### Performance Targets

- **Regime analysis**: <200ms context retrieval (cached)
- **Sector scoring**: <500ms calculation (weekly batch)
- **Report generation**: <4 hours monthly (automated)
- **API endpoints**: <200ms response time
- **Dashboard refresh**: Daily at 5am (5-10min batch)

### Related Documentation

- [DD-022: Macro Analyst Agent](../design-decisions/DD-022_MACRO_ANALYST_AGENT.md) - Full design decision
- [DD-026: Macro Reports](../design-decisions/DD-026_MACRO_REPORTS.md) - Report format specs
- [Macro & Industry Analysis Plan](../../plans/macro-industry-analysis-plan.md) - Original proposal
- [DD-008: Agent Credibility](../design-decisions/DD-008_AGENT_CREDIBILITY_SYSTEM.md) - Regime detection
- [DD-011: Checkpoint System](../design-decisions/DD-011_AGENT_CHECKPOINT_SYSTEM.md) - Subtask structure

---

## Related Documentation

- [System Overview](./01-system-overview.md) - Overall architecture
- [Memory System](./02-memory-system.md) - Memory architecture details
- [Support Agents](./04-agents-support.md) - Data and infrastructure agents
- [Coordination Agents](./05-agents-coordination.md) - Workflow orchestration
- [Collaboration Protocols](./07-collaboration-protocols.md) - Inter-agent communication
