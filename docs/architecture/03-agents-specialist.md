# Specialist Agents

## Overview

Specialist agents perform the core analytical work of the system. Each agent has deep domain expertise in a specific area of fundamental analysis, maintains a local memory cache of domain-specific patterns, and leverages historical context to improve accuracy over time.

The five specialist agents are:

1. Screening Agent - Initial filtering and candidate identification
2. Business Research Agent - Business model and competitive analysis
3. Financial Analyst Agent - Quantitative financial analysis
4. Strategy Analyst Agent - Strategic direction and capital allocation
5. Valuation Agent - Fair value determination and price targets

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
    learned_from: ['INTC_2020', 'IBM_2019']
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

## Related Documentation

- [System Overview](./01-system-overview.md) - Overall architecture
- [Memory System](./02-memory-system.md) - Memory architecture details
- [Support Agents](./04-agents-support.md) - Data and infrastructure agents
- [Coordination Agents](./05-agents-coordination.md) - Workflow orchestration
- [Collaboration Protocols](./07-collaboration-protocols.md) - Inter-agent communication
