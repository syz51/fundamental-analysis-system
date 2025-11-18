# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent fundamental analysis system for stock analysis. Uses autonomous AI agents to perform comprehensive investment research, mimicking human analyst teams. System designed around parallel processing, collaborative intelligence, and human-in-the-loop oversight at key decision gates.

## Architecture

**Full design documentation**: [docs/README.md](docs/README.md)

### 5-Layer System (v2.0)

- **Human Interface**: Dashboard, notifications, feedback loop, analytics
- **Memory & Learning**: Central knowledge graph, learning engine, pattern recognition
- **Coordination**: Lead coordinator, debate facilitator, QC agent
- **Specialist Agents**: Screening, business, financial, strategy, valuation (with memory)
- **Support**: Data collector, news monitor, knowledge base agent, report writer

### 13 Agent Types

1. **Screening**: Initial filtering, quantitative screens (10Y revenue CAGR, margins, debt ratios)
2. **Business Research**: SEC filings, SWOT, competitive moats, KPIs
3. **Financial Analyst**: Statement analysis, ratios (ROE/ROA/ROIC), peer comparisons, red flags
4. **Strategy Analyst**: Capital allocation, management track record, M&A review
5. **Valuation**: DCF modeling, relative valuation (P/E, EV/EBITDA), scenarios
6. **Data Collector**: API interfaces, document parsing, data quality
7. **News Monitor**: Real-time tracking, event impact assessment
8. **QC Agent**: Cross-verification, contradiction detection
9. **Knowledge Base Agent**: Memory management, pattern recognition, institutional knowledge (NEW in v2.0)
10. **Lead Coordinator**: Workflow orchestration, conflict resolution
11. **Debate Facilitator**: Structured arguments, consensus building
12. **Report Writer**: Investment memos, documentation
13. **Watchlist Manager**: Position monitoring, alerts

### Analysis Pipeline (12-day cycle)

1. **Screening** (Days 1-2): Identify candidates → Human Gate 1
2. **Parallel Analysis** (Days 3-7): Business/Financial/Strategy/News research
3. **Debate & Synthesis** (Days 8-9): Agent findings challenged → Human Gate 2
4. **Valuation** (Days 10-11): DCF, scenarios → Human Gate 3
5. **Documentation** (Day 12): Reports, watchlists → Human Gate 4 & 5

### Human Decision Gates (6 total in v2.0)

- **Gate 1**: Screening validation with history (24h, approve candidates)
- **Gate 2**: Research direction with precedents (12h, focus areas)
- **Gate 3**: Assumption validation with calibration (24h, model parameters)
- **Gate 4**: Debate arbitration with context (6h, resolve disagreements)
- **Gate 5**: Final decision with full context (blocking, investment/sizing)
- **Gate 6**: Learning validation (async, anti-confirmation bias) (NEW in v2.0)

See [Human Integration](docs/operations/02-human-integration.md) for details.

## Tech Stack

### Required Components

- **Backend**: Agent services, API layer
- **Frontend**: Dashboard, visualization interface
- **Orchestration**: Workflow management
- **Analysis**: Data processing, statistical analysis, time series forecasting
- **AI**: Agent framework, LLM integration

### Infrastructure Needs

- **Compute**: Scalable processing for parallel agent execution
- **Database**: Structured data storage, document storage
- **Message Queue**: Inter-agent communication
- **APIs**: External data access, internal services

### Data Sources

- SEC EDGAR (10-K, 10-Q, 8-K, proxies)
- Financial providers (Koyfin, Bloomberg, Refinitiv)
- News feeds (Reuters, Bloomberg)
- Alternative data (web traffic, social sentiment)

## Project Setup

### Prerequisites

- Python 3.14+ (current requirement in pyproject.toml)
- Dependencies managed via pyproject.toml

### Initial Setup

```bash
# Install dependencies (once dependencies are added to pyproject.toml)
uv sync

# Run main entry point
python main.py
```

## Data Structure

```text
/data
├── /raw                    # Source data
│   ├── /sec_filings
│   ├── /transcripts
│   ├── /market_data
│   └── /news_articles
├── /processed              # Cleaned/transformed
│   ├── /financial_statements
│   ├── /ratios
│   ├── /sentiment_scores
│   └── /peer_comparisons
├── /models                 # Valuation models
│   ├── /dcf_models
│   ├── /relative_valuations
│   └── /sensitivity_analyses
└── /outputs                # Final products
    ├── /reports
    ├── /watchlists
    └── /decision_logs
```

## Inter-Agent Communication

### Memory Sync (v2.0)

Event-driven priority sync replaces fixed 5min intervals:

- **Critical** (2s): Debates, human gates, challenges - force immediate sync
- **High** (10s): Important findings with precedents
- **Normal** (5min): Regular interval-based sync

Triggered by message type to prevent stale data in debates.

### Message Protocol

JSON-based with structure:

- `from_agent`, `to_agent`, `message_type`, `priority`
- `content`: finding/evidence/confidence/impact
- `requires_response`, `timestamp`

### Message Types

- **Finding**: Analytical results
- **Request**: Ask for analysis
- **Challenge**: Dispute conclusions (triggers critical sync)
- **Confirmation**: Validate info
- **Alert**: Urgent attention (triggers critical sync)

### Debate Protocol

5-level tiered escalation (v2.0):

1. **Agent negotiation** (15min): Evidence exchange
2. **Facilitator mediation** (1hr): Auto-resolve if credibility differential >0.25
3. **Human arbitration** (6hr): Expert review, queue max 3 concurrent
4. **Conservative default** (provisional): Most cautious position, continues pipeline
5. **Gate review**: Validate/override provisionals at Gates 3/5

Prevents deadlocks via fallbacks when human unavailable. Challenges include: challenger, challenged, disputed_finding, evidence required.

## Implementation Roadmap

### Phase 1: Foundation (Months 1-2)

- Data infrastructure, data collector agent
- Screening agent, basic dashboard
- Message protocols

### Phase 2: Core Agents (Months 3-4)

- Financial analyst, business research agents
- Debate facilitator, human gate system
- Integration testing

### Phase 3: Advanced (Months 5-6)

- Strategy analyst, valuation agent
- QC, report writer
- Full system testing

### Phase 4: Optimization (Months 7-8)

- Parameter tuning, workflow optimization
- Learning loops, benchmarking
- Production deployment

### Key Milestones

- Month 4: MVP (10 stocks end-to-end)
- Month 6: Beta (50 stocks, 80% accuracy)
- Month 8: Production (200 stocks, <24hr)
- Month 12: Scale (1000+ stocks)

## Key Metrics & Ratios

### Financial Health Indicators

- 10Y revenue CAGR
- Operating margin
- Net debt/EBITDA
- ROE, ROA, ROIC
- Asset turnover, working capital ratios
- Debt/equity, interest coverage
- Current ratio, quick ratio

### Red Flags

- Related-party transactions
- Excessive management comp
- Aggressive accounting policies
- Unusual adjustments

### Strategic Metrics

- Historical ROI (5/10/15Y)
- ROCE, ROIC
- Execution success rate

## Compliance & Governance

### Regulatory

- SEC investment advisor regulations
- GDPR/CCPA for data privacy
- No material non-public info
- Complete audit trails

### Data Governance

- Source verification, timestamp validation
- Consistency checks, outlier detection
- Retention: raw (5Y), processed (3Y), models/reports (permanent)
- Memory-specific: working (24h), cache (30d), central graph (permanent)

## Documentation Structure (v2.0)

Design docs organized into modular files for easier iteration:

- **[docs/README.md](docs/README.md)** - Master navigation
- **[docs/architecture/](docs/architecture/)** - System design, memory, agents, protocols (7 docs)
- **[docs/operations/](docs/operations/)** - Pipeline, human integration, data (3 docs)
- **[docs/learning/](docs/learning/)** - Learning systems, feedback, metrics (3 docs)
- **[docs/implementation/](docs/implementation/)** - Roadmap, tech, compliance (4 docs)
- **[docs/design-decisions/](docs/design-decisions/)** - Architectural decisions with template
- **[examples/](examples/)** - Code samples (to be populated)

Quick links: [System Overview](docs/architecture/01-system-overview.md) | [Roadmap](docs/implementation/01-roadmap.md)
