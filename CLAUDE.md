# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent fundamental analysis system for stock analysis. Uses autonomous AI agents to perform comprehensive investment research, mimicking human analyst teams. System designed around parallel processing, collaborative intelligence, and human-in-the-loop oversight at key decision gates.

## Architecture

**Full design documentation**: [docs/README.md](docs/README.md)

### Current Focus: Architecture & Planning

- **Status**: Design Phase (v3.0). Implementation has not started.
- **Active Plans**: Check `plans/` for design tasks (e.g., `macro-industry-analysis-plan.md`).
- **Roadmap**: [docs/implementation/01-roadmap.md](docs/implementation/01-roadmap.md)
- **Latest ADR**: DD-026 Macro Reports.

### 5-Layer System (v3.0)

- **Human Interface**: Dashboard, notifications, feedback loop, analytics
- **Memory & Learning**: Central knowledge graph, learning engine, pattern recognition
- **Coordination**: Lead coordinator, debate facilitator, QC agent
- **Specialist Agents**: Screening, business, financial, strategy, valuation, macro, industry (with memory)
- **Support**: Data collector, news monitor, knowledge base agent, report writer

### 14 Agent Types

1. **Screening**: Initial filtering, quantitative screens (10Y revenue CAGR, margins, debt ratios)
2. **Business Research**: SEC filings, SWOT, competitive moats, KPIs
3. **Financial Analyst**: Statement analysis, ratios (ROE/ROA/ROIC), peer comparisons, red flags
4. **Strategy Analyst**: Capital allocation, management track record, M&A review
5. **Valuation**: DCF modeling, relative valuation (P/E, EV/EBITDA), scenarios
6. **Macro Analyst**: Market regime analysis, economic indicators, sector favorability (NEW v3.0)
7. **Data Collector**: API interfaces, document parsing, data quality
8. **News Monitor**: Real-time tracking, event impact assessment
9. **QC Agent**: Cross-verification, contradiction detection
10. **Knowledge Base Agent**: Memory management, pattern recognition, institutional knowledge
11. **Lead Coordinator**: Workflow orchestration, conflict resolution
12. **Debate Facilitator**: Structured arguments, consensus building
13. **Report Writer**: Investment memos, documentation
14. **Watchlist Manager**: Position monitoring, alerts

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

### Infrastructure & Reliability (v2.0, Phase 4+)

**Neo4j High Availability** (DD-021, resolves Flaw #21):

- 3 core servers (Raft consensus) + 2 read replicas
- Automatic failover <10s, zero data loss
- 99.95% availability (46hr downtime reduction annually)
- Cross-region backup (AWS S3 + GCP Cloud Storage)
- Cost: $2,250/mo ($1,700 premium over single instance)
- Implementation: Phase 4
- See [DD-021: Neo4j HA](docs/design-decisions/DD-021_NEO4J_HA.md)

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

**Hybrid Approach** (DD-032): Different data sources for different pipeline stages

**Screening Stage (Days 1-2)**:

- **Financial data API** (TBD): 10Y financial metrics for S&P 500 (revenue, EPS, margins, ROE/ROA/ROIC)
- Purpose: Fast quantitative screening
- Cost: TBD
- Fallback: SEC EDGAR if primary unavailable

**Deep Analysis Stage (Days 3-7, post-Gate 1)**:

- **SEC EDGAR** (primary): Full 10-K/10-Q/8-K parsing with multi-tier recovery (EdgarTools + custom tiers)
- Purpose: Qualitative data (MD&A, risk factors), amendment tracking, 98.55% data quality
- Cost: $3-$6/month for 10-20 approved companies
- On-demand only (not bulk backfill)

**Other Sources**:

- Financial providers (Koyfin, Bloomberg, Refinitiv) - future consideration
- News feeds (Reuters, Bloomberg) - News Monitor Agent
- Alternative data (web traffic, social sentiment) - future consideration
- Macro data (FRED, IMF, OECD, CBOE) - Macro Analyst

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

### Phase 1: Foundation

- Data infrastructure, data collector agent
- Screening agent, basic dashboard
- Message protocols

### Phase 2: Core Agents

- Financial analyst, business research agents
- Debate facilitator, human gate system
- Integration testing

### Phase 3: Advanced

- Strategy analyst, valuation agent
- QC, report writer
- Full system testing

### Phase 4: Optimization

- Parameter tuning, workflow optimization
- Learning loops, benchmarking
- Production deployment

### Key Milestones

- MVP: Initial stocks end-to-end
- Beta: Expanded workload, 80% accuracy
- Production: Operational workload, <24hr
- Scale: Large-scale coverage

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
- **[docs/design-decisions/](docs/design-decisions/)** - Architectural decisions (ADRs DD-001 to DD-026)
- **[docs/archive/](docs/archive/)** - Historical design docs and resolved flaws
- **[plans/](plans/)** - Active implementation plans (e.g. Macro Analyst)
- **[examples/](examples/)** - Code samples (to be populated)

Quick links: [System Overview](docs/architecture/01-system-overview.md) | [Roadmap](docs/implementation/01-roadmap.md)
