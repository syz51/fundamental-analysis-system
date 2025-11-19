# System Overview

## Executive Summary

### Purpose

This document outlines the design for a memory-enhanced multi-agent system that performs comprehensive fundamental analysis on stocks, mimicking and exceeding the capabilities of human analyst teams through institutional memory and continuous learning.

### Key Objectives

- Automate screening and initial analysis of investment opportunities
- Provide thorough fundamental analysis across business, financial, and strategic dimensions
- Integrate top-down macro analysis with bottom-up company research (Phase 2+)
- Build and leverage institutional knowledge through comprehensive memory systems
- Learn from past decisions and continuously improve prediction accuracy
- Enable human oversight and input at critical decision points
- Generate professional investment reports and maintain intelligent watchlists

### Core Principles

- **Parallel Processing**: Multiple agents work simultaneously on different aspects
- **Collaborative Intelligence**: Agents debate and validate each other's findings using historical context
- **Memory-Augmented Decisions**: Every analysis leverages past experiences and outcomes
- **Human Augmentation**: Human expertise enhanced by AI memory and pattern recognition
- **Transparency**: All reasoning, memory queries, and decisions are auditable
- **Continuous Learning**: System actively learns from outcomes and updates knowledge base

---

## High-Level Architecture with Memory Integration

### 5-Layer System Architecture

```text
┌─────────────────────────────────────────────────────────┐
│                   Human Interface Layer                   │
│  Dashboard | AlertManager | Notifications | Feedback | Analytics│
└─────────────────────────────────────────────────────────┘
                              ▲
                              ▼
┌─────────────────────────────────────────────────────────┐
│               Memory & Learning Layer                     │
│   Central Knowledge Graph | Learning Engine | Patterns    │
└─────────────────────────────────────────────────────────┘
                              ▲
                              ▼
┌─────────────────────────────────────────────────────────┐
│                   Coordination Layer                      │
│    Lead Coordinator | Debate Facilitator | QC Agent      │
└─────────────────────────────────────────────────────────┘
                              ▲
                              ▼
┌─────────────────────────────────────────────────────────┐
│                  Specialist Agent Layer                   │
│  Screening | Business | Financial | Strategy | Valuation  │
│                       Macro                               │
│        (Each with Local Memory Cache)                     │
└─────────────────────────────────────────────────────────┘
                              ▲
                              ▼
┌─────────────────────────────────────────────────────────┐
│                     Support Layer                         │
│   Data Collector | News Monitor | Report Writer | KB Agent│
└─────────────────────────────────────────────────────────┘
                              ▲
                              ▼
┌─────────────────────────────────────────────────────────┐
│                    Data Infrastructure                    │
│    APIs | Databases | Document Storage | Memory Storage   │
└─────────────────────────────────────────────────────────┘
```

### Layer Descriptions

#### Human Interface Layer

- Provides dashboard for monitoring pipeline, approvals, and decisions
- **AlertManager** (DD-015): Event-driven alerts for agent failures (multi-channel delivery, acknowledgment tracking, retry mechanism)
- Sends notifications for critical decision gates and scheduled alerts
- Captures human feedback for system learning
- Displays analytics and performance metrics

#### Memory & Learning Layer

- Maintains central knowledge graph of all analyses, patterns, and outcomes
- Runs learning engine to improve agent accuracy over time
- Identifies and validates recurring patterns across analyses
- Synchronizes memories between agents and central storage
- **Infrastructure Resilience** (Phase 4+):
  - Neo4j high-availability cluster prevents single point of failure
  - 99.95% uptime target (automatic failover <10s)
  - Cross-region disaster recovery (<1hr RTO/RPO)
  - Production-ready for 24/7 investment operations
  - See [DD-021: Neo4j HA](../design-decisions/DD-021_NEO4J_HA.md) for complete architecture

#### Coordination Layer

- Lead Coordinator orchestrates workflow and task assignments
- Debate Facilitator structures collaborative analysis and conflict resolution
- QC Agent ensures analysis integrity and identifies contradictions

#### Specialist Agent Layer

- Six specialized agents (Screening, Business, Financial, Strategy, Valuation, Macro)
- Each maintains local memory cache for domain-specific patterns
- Performs deep analysis in respective domains
- Participates in collaborative debates with historical context
- **Macro Analyst**: Provides top-down economic context (regime analysis, sector favorability, discount rates)

#### Support Layer

- Data Collector manages acquisition and storage of external data
- News Monitor tracks real-time developments and material events
- Report Writer synthesizes findings into professional documentation
- Knowledge Base Agent manages institutional memory and pattern recognition

#### Data Infrastructure

- External APIs for market data, SEC filings, news feeds
- Multiple database systems (PostgreSQL, MongoDB, Neo4j, Redis)
- Document storage for filings, transcripts, reports
- Specialized memory storage for knowledge graph and agent caches
- Message queue for inter-agent communication and memory synchronization
  - See [Technical Requirements](../implementation/02-tech-requirements.md#message-queue) for specifications

---

## Enhanced Analysis Pipeline with Memory

### 1. Memory-Informed Screening

- Identify candidates based on financial metrics
- Check if company previously analyzed
- Load historical screening patterns and accuracy
- Apply learned filters based on past successes/failures

### 2. Historical Context Loading

- Pull relevant past analyses and patterns
- Retrieve similar company outcomes
- Load sector-specific historical context
- Identify applicable precedents

### 3. Business Understanding

- Deep dive into operations and business model
- Analyze with awareness of past findings
- Evaluate competitive advantages against historical durability
- Compare to similar business models in memory

### 4. Financial Analysis

- Comprehensive review of statements and metrics
- Compare to historical predictions and accuracy
- Apply sector-specific ratio benchmarks from memory
- Identify red flags based on learned patterns

### 5. Strategic Assessment

- Evaluate management track record and future plans
- Compare against past management assessments
- Review capital allocation with historical ROI data
- Weight by agent accuracy on similar evaluations

### 6. Valuation

- Determine fair value and price targets
- Adjust based on historical model performance
- Apply calibration factors from past prediction errors
- Generate probability-weighted scenarios from historical outcomes

### 7. Documentation

- Generate professional reports and maintain watchlists
- Include confidence scores based on track record
- Highlight historical precedents and pattern matches
- Document consensus with credibility weighting

### 8. Learning & Feedback

- Update knowledge base with new outcomes
- Track predictions for future accuracy measurement
- Identify new patterns for validation
- Update agent credibility scores

---

## System Performance Constraints

To support ambitious scale targets (1000+ stocks, <24hr analysis turnaround), the system implements performance optimization strategies across the memory and coordination layers. See [DD-005](../design-decisions/DD-005_MEMORY_SCALABILITY_OPTIMIZATION.md) for complete design.

### Performance Targets

| Metric               | Target                               | Phase     |
| -------------------- | ------------------------------------ | --------- |
| Analysis turnaround  | <24 hours (end-to-end)               | Phase 4-5 |
| Memory retrieval     | <200ms (cached), <500ms (uncached)   | Phase 3-4 |
| Cache hit rate       | >80%                                 | Phase 3-4 |
| Memory utilization   | >85% of decisions use historical ctx | Phase 2-5 |
| Active graph size    | <50K nodes                           | Phase 4-5 |
| Parallel agent limit | 4-6 concurrent specialist agents     | Phase 2-5 |

### Key Optimizations

**Memory System**:

- Tiered caching (L1: <10ms, L2: <50ms, L3: <500ms)
- Pre-computed similarity indexes (2-5s graph traversal → <50ms lookup)
- Query budget enforcement (500ms timeout with graceful fallbacks)
- Incremental credibility updates (800ms full scan → <10ms incremental)
- Memory pruning (archive >2yr memories, maintain <50K active nodes)

**Coordination**:

- Parallel query execution (5× faster via concurrent memory fetches)
- Event-driven memory sync (2s critical, 10s high, 5min normal)
- Cache warming before analysis (predictive preload reduces cache misses)

**Scalability Validation**:

- Benchmarking at each phase (MVP→Beta→Production→Scale)
- Performance monitoring with alerting (>5% query timeouts triggers optimization)
- Continuous tuning based on operational metrics

See [Memory Architecture](./02-memory-system.md#scalability--performance-optimization) for implementation details.

---

## Related Documentation

- [Memory Architecture](./02-memory-system.md) - Detailed memory system design with scalability optimizations
- [Specialist Agents](./03-agents-specialist.md) - Core analysis agents
- [Support Agents](./04-agents-support.md) - Infrastructure and support agents with query budgets
- [Coordination Agents](./05-agents-coordination.md) - Workflow orchestration agents
- [Output Agents](./06-agents-output.md) - Report and watchlist agents
- [Collaboration Protocols](./07-collaboration-protocols.md) - Inter-agent communication
- [DD-005: Memory Scalability Optimization](../design-decisions/DD-005_MEMORY_SCALABILITY_OPTIMIZATION.md) - Performance optimization design
