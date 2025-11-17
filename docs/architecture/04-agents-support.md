# Support Agents

## Overview

Support agents provide infrastructure and operational capabilities that enable specialist agents to focus on analysis. These agents handle data acquisition, real-time monitoring, quality control, and institutional memory management.

The four support agents are:

1. Data Collector Agent - Data acquisition and storage
2. News & Events Monitor Agent - Real-time development tracking
3. Quality Control Agent - Analysis integrity verification
4. Knowledge Base Agent - Institutional memory management

---

## 1. Data Collector Agent

### Purpose

Manage data acquisition and storage

### Responsibilities

- Interface with data APIs (SEC EDGAR, financial providers)
- Parse and structure documents (filings, transcripts)
- Maintain data freshness and update schedules
- Handle API rate limiting and retries
- Ensure data quality and validation
- Version control for data changes

### Data Sources

**Primary Sources**:

- SEC EDGAR (10-K, 10-Q, 8-K, proxies)
- Financial data providers (Koyfin, Bloomberg, Refinitiv)
- Company websites and investor relations
- Industry reports and research
- Alternative data sources

---

## 2. News & Events Monitor Agent

### Purpose

Track real-time developments

### Responsibilities

- Monitor news feeds (Reuters, Bloomberg, specialized publications)
- Identify material events (earnings, M&A, regulatory)
- Assess impact on investment thesis
- Trigger re-analysis when needed
- Provide context for price volatility
- Track competitor announcements

### Alert Triggers

- Material financial events
- Management changes
- Regulatory actions
- Competitive threats
- Macro developments affecting sector

---

## 3. Quality Control Agent

### Purpose

Ensure analysis integrity

### Responsibilities

- Cross-verify findings across agents
- Identify contradictions in analysis
- Seek opposing viewpoints
- Validate assumptions and data
- Ensure checklist completion
- Flag inconsistencies for human review

### Quality Checks

- Data source verification
- Calculation validation
- Logic consistency
- Completeness of analysis
- Adherence to standards

---

## 4. Knowledge Base Agent (NEW in v2.0)

### Purpose

Manage institutional memory and pattern recognition

### Responsibilities

- Index and organize all analyses and outcomes
- Identify cross-domain patterns
- Calculate agent accuracy scores
- Surface relevant precedents
- Maintain lessons learned database
- Perform post-mortem analyses

### Core Functions

**Note**: Code samples referenced here have been omitted from architecture docs. See `/examples/` directory for implementation examples.

Key capabilities include:

**Find Precedents**:

- Search for similar historical situations
- Return analyses with similarity scores
- Provide outcomes and lessons learned
- Rank by relevance to current context

**Get Agent Track Record**:

- Query agent's historical performance
- Filter by similar contexts
- Calculate average accuracy
- Aggregate lessons learned

**Identify Patterns** (with 3-Tier Validation - see [DD-007](../../design-decisions/DD-007_PATTERN_VALIDATION_ARCHITECTURE.md)):

- Discover candidate patterns from historical outcomes
- Run hold-out validation (train/val/test split)
- Perform blind testing (6-month shadow analysis, agents unaware)
- Execute control group comparison (statistical significance testing)
- Manage pattern lifecycle: candidate → statistically_validated → human_approved (Gate 6) → active
- Quarantine unvalidated patterns (never broadcast to agents)
- Track validation metadata (p-values, accuracy scores, test dates)
- Deprecate patterns showing degraded performance
- Alert relevant agents only to active (validated + approved) patterns

**Validation Requirements**: Patterns must pass ALL three tests before deployment:

1. Hold-out: Performance on unseen data within 20% of training accuracy
2. Blind testing: Pattern helps >1.5x more than hurts when agents unaware
3. Statistical significance: p < 0.05 improvement vs control group

This prevents confirmation bias loops and self-fulfilling prophecies (see [Flaw #3](../../docs/design-flaws/03-pattern-validation.md)).

---

## Related Documentation

- [System Overview](./01-system-overview.md) - Overall architecture
- [Memory System](./02-memory-system.md) - Knowledge graph and memory layers
- [Specialist Agents](./03-agents-specialist.md) - Core analysis agents
- [Coordination Agents](./05-agents-coordination.md) - Workflow orchestration
- [Output Agents](./06-agents-output.md) - Report and watchlist generation
