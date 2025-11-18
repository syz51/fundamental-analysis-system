---
flaw_id: 21
title: Scalability Architecture Bottlenecks
status: active
priority: critical
phase: 4
effort_weeks: 8
impact: Cannot scale to 1000+ stocks without redesign
blocks: ["Scale to 1000+ stocks"]
depends_on: ["Neo4j operational", "DD-004 auto-approval"]
domain: ["human-gates", "architecture"]
sub_issues:
  - id: A1
    severity: high
    title: Central knowledge graph single point of failure
  - id: A2
    severity: high
    title: Human gate synchronous bottleneck
discovered: 2025-11-17
---

# Flaw #21: Scalability Architecture Bottlenecks

**Status**: 🔴 ACTIVE
**Priority**: Critical
**Impact**: Cannot scale to 1000+ stocks without redesign
**Phase**: Phase 4 (Months 7-8, pre-production)

---

## Problem Description

Two architectural bottlenecks prevent scaling to production targets:

1. **A1**: Central knowledge graph single point of failure, no HA strategy
2. **A2**: Human gate synchronous bottleneck (need 18 FTE at 1000 stocks)

### Sub-Issue A1: Knowledge Graph Single Point of Failure

**Files**:
- `docs/architecture/01-system-overview.md:1-77`
- `docs/architecture/02-memory-system.md`

**Problem**: All memory tiers (L1, L2, L3) depend on central Neo4j graph, but no high-availability or failover specified.

**Current Architecture**:
```text
Memory & Learning Layer
│
└── Central Knowledge Graph (Neo4j)
    │
    ├── L1 (working memory) → syncs to L3
    ├── L2 (agent caches) → syncs to L3
    └── L3 (central graph) → SINGLE INSTANCE

If L3 fails → System unavailable
```

**Missing**:
- Neo4j clustering/replication strategy
- Failover procedures (manual? automatic?)
- Read replica configuration
- Backup restoration SLA
- Split-brain prevention

**Availability Impact**:
```text
Neo4j downtime scenarios:
  - Planned maintenance: 1-2hr/month
  - Unplanned outage: 0.5% (99.5% uptime)
  - Backup restoration: 2-6hr

Annual downtime: ~50 hours
Availability: 99.4% (target should be 99.9%+)
```

### Sub-Issue A2: Human Gate Scaling Bottleneck

**Files**:
- `docs/operations/01-analysis-pipeline.md`
- `docs/operations/02-human-integration.md`

**Problem**: Analysis pipeline blocks at 6 human gates. At 1000 stocks/year scale, requires 18 FTE humans.

**Scaling Calculation**:
```yaml
Target: 1000 stocks/year (Month 12)
       = ~20 stocks/week
       = ~4 stocks/day (5-day workweek)

Each stock: 6 gates × 12hr average response time = 72 human-hours

Daily human-hours: 4 stocks × 72hr = 288 hr/day

Even with 50% auto-approval (DD-004 production target):
  288hr × 50% = 144 hr/day human-required
  144hr / 8hr workday = 18 full-time humans

But roadmap assumes single human operator through Phase 4 (Month 8)
```

**Bottleneck**: Synchronous gates block pipeline parallelization

**Current Mitigation**: DD-004 auto-approval targets 50%
**Problem**: Still requires 18 FTE at scale

---

## Recommended Solution

### A1: Neo4j High Availability Architecture

```yaml
Neo4j Cluster (Causal Clustering):
  Core Servers: 3 nodes (quorum-based writes)
    - neo4j-core-1 (leader)
    - neo4j-core-2 (follower)
    - neo4j-core-3 (follower)
    - Consensus: Raft protocol
    - Write quorum: 2 of 3

  Read Replicas: 2 nodes (scale reads)
    - neo4j-replica-1
    - neo4j-replica-2
    - Async replication from core
    - Route read queries here (80% of queries)

Failover:
  - Automatic leader election (Raft)
  - Max failover time: 5-10 seconds
  - Zero data loss (quorum writes)

Backup Strategy:
  - Daily full backup (core-1)
  - Hourly incremental backups
  - Retention: 30 days
  - Recovery time objective (RTO): <1 hour
  - Recovery point objective (RPO): <1 hour

Monitoring:
  - Cluster health checks (every 10s)
  - Replication lag alerts (<5min)
  - Automatic failover triggers
```

**Cost Impact**:
```text
Single instance: $500/mo (r5.2xlarge)
HA cluster:
  - 3 core servers: $1,500/mo
  - 2 read replicas: $600/mo
  - Total: $2,100/mo
  - Premium: $1,600/mo for 99.95% availability
```

### A2: Human Gate Scaling Strategy

Three options to scale human gates:

**Option 1: Increase Auto-Approval to 90%+** (RECOMMENDED)

```yaml
Current Target: 50% auto-approval (DD-004)
Scaling Target: 90% auto-approval

At 90% auto-approval:
  288hr × 10% = 28.8 hr/day human-required
  28.8hr / 8hr = 3.6 FTE ≈ 4 humans (feasible)

Requirements:
  - Validation accuracy >95% (Flaw #13)
  - Longer shadow mode (6 months vs 3 months)
  - More aggressive credibility thresholds
  - Lessons learned auto-approval enabled
```

**Option 2: Parallelize Gates** (ALTERNATIVE)

```yaml
Current: Gates sequential (blocking)
Proposed: Gates parallel (non-blocking)

Gate 1 (Screening) + Gate 2 (Research Direction): Parallel
Gate 3 (Assumptions): After research completion
Gate 4 (Debate): Only if debate occurred
Gate 5 (Final): After valuation
Gate 6 (Learning): Async (already non-blocking)

Parallelization reduces human-hours from 72 → ~40 per stock
  4 stocks × 40hr = 160 hr/day
  160hr × 50% = 80 hr/day
  80hr / 8hr = 10 FTE (better but still high)
```

**Option 3: Reduce Gate Count** (ALTERNATIVE)

```yaml
Merge gates:
  - Gate 1 + 2: Combined screening & direction
  - Gate 3 + 4: Combined assumptions & debate resolution
  - Gate 5: Final decision (unchanged)
  - Gate 6: Learning (async)

Reduced to 4 gates:
  4 gates × 12hr = 48 hr/stock
  4 stocks × 48hr = 192 hr/day
  192hr × 50% = 96 hr/day
  96hr / 8hr = 12 FTE (still high)
```

**Recommendation**: Option 1 (90% auto-approval) is most scalable

---

## Implementation Plan

**Month 7 (Week 1-2)**: A1 Neo4j HA setup
**Month 7 (Week 3-4)**: A1 failover testing & backup validation
**Month 8 (Week 1-3)**: A2 auto-approval validation (shadow mode extension)
**Month 8 (Week 4)**: A2 production deployment with 90% target

---

## Success Criteria

### A1: Knowledge Graph HA
- ✅ Cluster operational (3 core + 2 replica)
- ✅ Automatic failover <10s
- ✅ Availability 99.95% (measured over 30 days)
- ✅ Backup restoration tested (<1hr RTO)

### A2: Human Gate Scaling
- ✅ Auto-approval rate ≥90% in production
- ✅ Auto-approval accuracy >95% (validated)
- ✅ Human team ≤5 FTE at 1000 stocks/year
- ✅ Pipeline throughput: 4+ stocks/day

---

## Dependencies

- **Blocks**: Production scale (1000+ stocks) - Month 12 milestone
- **Depends On**: Neo4j operational, DD-004 auto-approval validated
- **Related**: Flaw #13 (Validation Gaps), DD-004, DD-005
