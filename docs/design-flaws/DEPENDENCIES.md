# Design Flaws - Dependencies & Critical Path

This document tracks the dependency relationships between design flaws to help plan implementation order.

---

## Critical Path

```text
Foundation (Phase 1) ✅ COMPLETE
├── Flaw #1 ✅ → Gate 6 Learning Validation
└── Flaw #2 ✅ → Event-Driven Memory Sync
    │
    ├── Phase 2: Core Systems (CRITICAL - 3 ACTIVE BLOCKERS)
    │   ├── Flaw #8 ✅ → Debate Deadlock Resolution
    │   ├── Flaw #11 ✅ → Algorithm Specs (specs documented)
    │   ├── Flaw #14 🔴 → Statistical Reliability (blocks #8 auto-resolution)
    │   ├── Flaw #16 🔴 → Timeline Conflicts (restructure needed)
    │   └── Flaw #19 🔴 → Partial Failures (blocks multi-agent)
    │       │
    │       └── Phase 3: Quality & Learning (4 RESOLVED, 2 ACTIVE)
    │           ├── Flaw #3 ✅ → Pattern Validation (depends on #1)
    │           ├── Flaw #7 ✅ → Scalability Validation (depends on #2)
    │           ├── Flaw #12 ✅ → Archive Lifecycle (DD-013 implemented)
    │           ├── Flaw #13 ✅ → Validation Gaps (DD-014 implemented)
    │           ├── Flaw #15 🔴 → Failure Modes (blocks memory reliability)
    │           └── Flaw #20 🔴 → Access Control (security)
    │               │
    │               └── Phase 4: Optimization (PRODUCTION READINESS)
    │                   ├── Flaw #9 ✅ → Negative Feedback (depends on #1, #3)
    │                   ├── Flaw #4 ✅ → Credibility Temporal Decay
    │                   ├── Flaw #5 ✅ → Data Retention
    │                   ├── Flaw #17 🔴 → Data Tier Management
    │                   └── Flaw #21 🔴 → Scalability (CRITICAL - blocks 1000+ stocks)
    │                       │
    │                       └── Phase 5: Refinement
    │                           ├── Flaw #6 🟢 → Dynamic Expertise Routing
    │                           └── Flaw #18 🟢 → Learning Asymmetry (subset of #6)
```

---

## Dependency Matrix

| Flaw   | Depends On                       | Blocks                             | Phase | Status   |
| ------ | -------------------------------- | ---------------------------------- | ----- | -------- |
| #1 ✅  | -                                | #3, #9                             | 1     | RESOLVED |
| #2 ✅  | -                                | #7, #8                             | 1     | RESOLVED |
| #3 ✅  | #1                               | #9                                 | 3     | RESOLVED |
| #4 ✅  | Operational agents               | -                                  | 4     | RESOLVED |
| #5 ✅  | Pattern storage                  | -                                  | 4     | RESOLVED |
| #6 🟢  | Human gate data                  | -                                  | 5     | DEFERRED |
| #7 ✅  | #2, operational agents           | -                                  | 3     | RESOLVED |
| #8 ✅  | #2                               | ~~Core agent testing~~ (unblocked) | 2     | RESOLVED |
| #9 ✅  | #1, #3                           | -                                  | 4     | RESOLVED |
| #10 ✅ | #1 (Gate 6)                      | -                                  | 4     | RESOLVED |
| #11 ✅ | #8 (debate protocol)             | ~~Implementation pending~~         | 2     | RESOLVED |
| #12 ✅ | DD-009, #9 (post-mortem)         | ~~Post-mortem~~ (unblocked)        | 3     | RESOLVED |
| #13 🔴 | Gate 6, DD-007 (pattern val)     | Auto-approval deployment           | 3     | ACTIVE   |
| #14 🔴 | Agent perf data, debate protocol | Auto-resolution (#8)               | 2-3   | ACTIVE   |
| #15 🔴 | Memory system (DD-005, DD-002)   | Memory reliability                 | 3     | ACTIVE   |
| #16 🔴 | - (roadmap only)                 | Phase 2 implementation             | 2     | ACTIVE   |
| #17 🔴 | DD-009, Neo4j                    | Production reliability             | 4     | ACTIVE   |
| #18 🟢 | Human gate data, #6              | -                                  | 5     | DEFERRED |
| #19 🔴 | Multi-agent workflows            | Multi-agent reliability            | 2     | ACTIVE   |
| #20 🔴 | Memory system (L1/L2/L3)         | Production security                | 3     | ACTIVE   |
| #21 🔴 | Neo4j, DD-004 auto-approval      | Scale to 1000+ stocks              | 4     | ACTIVE   |

---

## Blocking Analysis

### What Each Resolved Flaw Unblocked

- **#1 (Gate 6)** unblocked → #3 (Pattern Validation), #9 (Negative Feedback)
- **#2 (Memory Sync)** unblocked → #7 (Memory Scalability), #8 (Debate Deadlock)
- **#3 (Pattern Validation)** unblocked → #9 (Negative Feedback)
- **#8 (Debate Deadlock)** unblocked → Core agent testing (now operational)
- **#11 (Algorithm Specs)** unblocked → Implementation of C1/M3/G5 algorithms (Phase 2+)
- **#12 (Archive Lifecycle)** unblocked → Post-mortem investigation with full evidence, pattern re-validation with historical data

### What Active Flaws Are Blocking

- **#8 (resolved)** + **#14 (active)** blocks → Auto-resolution implementation
- **#13** blocks → Auto-approval deployment (95% accuracy target)
- **#14** blocks → Auto-resolution never triggers (n=5 sample size too low)
- **#15** blocks → Memory reliability (infinite recursion risk)
- **#16** blocks → Phase 2 implementation START (credibility circular dependency)
- **#17** blocks → Production reliability (corruption recovery missing)
- **#19** blocks → Multi-agent reliability (undefined failure behavior)
- **#20** blocks → Production security (no access control)
- **#21** blocks → Scale to 1000+ stocks (need 18 FTE without fix)

### DD-013 Archive Lifecycle Dependencies

**Flaw #12 Resolution** (DD-013) introduces:

**Infrastructure:**

- Redis/ElasticSearch for cached archive index (5-10MB, negligible cost)
- S3/cloud storage for cold archives (extends DD-009 tiered storage)
- Regime detection service (FRED API for interest rates, macro indicators)

**Components:**

- `ArchiveIndexService` - Fast archive metadata lookups
- `ArchiveQueryService` - Archive search and retrieval
- `PromotionEngine` - Auto-promote archives on regime changes
- `PromotionAlertService` - Human override notifications
- `TieredStorageManager` - Extended from DD-009 with archive tier
- `PatternLifecycleManager` - 18-month retention windows

**Dependencies:**

- Extends DD-009 (Data Retention & Pattern Evidence)
- Requires DD-005 (Memory Scalability) for pattern storage
- Integrates with DD-007 (Pattern Validation) for lifecycle states

**Unblocks:**

- Post-mortem investigation with full historical evidence (DD-006)
- Pattern re-validation across market regimes (DD-007)

---

## Dependency Chains (Longest Paths)

### Chain 1: Learning System

```text
#1 (Gate 6) ✅
  → #3 (Pattern Validation) ✅
    → #9 (Negative Feedback) ✅
      → #12 (Archive Lifecycle) ✅
```

**Status**: 4/4 complete ✅ (DD-013 archive lifecycle implemented)

### Chain 2: Memory System

```text
#2 (Memory Sync) ✅
  → #7 (Memory Scalability) ✅
  → #8 (Debate Deadlock) ✅
    → #14 (Statistical Reliability) 🔴
      → Auto-resolution implementation
```

**Status**: 3/4 complete, #14 blocks auto-resolution

### Chain 3: Scalability

```text
#7 (Memory Scalability) ✅
  → #12 (Archive Lifecycle) ✅
    → #17 (Data Tier Mgmt) 🔴
      → #21 (Scalability Bottlenecks) 🔴
```

**Status**: 2/4 complete, 2 active blockers in series (#17 → #21)

---

## Parallel Workstreams

These flaws can be worked on in parallel (no inter-dependencies):

**_Stream A: Memory Reliability_**

- #15 (Failure Modes) - 4 weeks
- #20 (Access Control) - 4 weeks

**_Stream B: Agent Systems_**

- #14 (Statistical Reliability) - 4 weeks
- #19 (Partial Failures) - 4 weeks

**_Stream C: Timeline & Planning_**

- #16 (Timeline Conflicts) - 2 weeks _(unblocked, can start immediately)_

**_Stream D: Validation_**

- #13 (Validation Gaps) - 6 weeks _(after Gate 6 + DD-007)_

---

## Implementation Sequence Recommendation

### Immediate (Next 4 Weeks)

**Week 1-2:**

- [x] #16 (Timeline Conflicts) - 2w **[HIGHEST PRIORITY - unblocks Phase 2]**

**Week 3-6 (Parallel):**

- [ ] #14 (Statistical Reliability) - 4w
- [ ] #19 (Partial Failures) - 4w
- [ ] #15 (Failure Modes) - 4w _(can overlap)_

### Phase 3 (Months 5-6)

**Weeks 7-10 (Parallel):**

- [ ] #13 (Validation Gaps) - 6w
- [ ] #20 (Access Control) - 4w

### Phase 4 (Months 7-8)

**Weeks 18-21:**

- [ ] #17 (Data Tier Mgmt) - 4w

**Weeks 22-29:**

- [ ] #21 (Scalability) - 8w **[CRITICAL - production readiness]**

---

## Risk Assessment

### Highest Risk if Unfixed (CRITICAL)

1. **Flaw #21** (Scalability Bottlenecks) - blocks 1000+ stock target, need 18 FTE without fix
2. **Flaw #16** (Timeline Conflicts) - blocks Phase 2 implementation START

### High Risk (Should Fix Before MVP)

1. **Flaw #14** (Statistical Reliability) - auto-resolution never triggers at n=5
2. **Flaw #19** (Partial Failures) - undefined behavior when agents fail
3. **Flaw #12** (Archive Lifecycle) - data loss risk for post-mortem evidence
4. **Flaw #15** (Failure Modes) - system hangs from infinite recursion

### Medium Risk (Fix Before Production)

1. **Flaw #17** (Data Tier Management) - performance degradation, corruption recovery
2. **Flaw #20** (Access Control) - security/integrity risk

### Can Defer Safely

1. **Flaw #6** (Expertise Routing) - marginal improvement
2. **Flaw #18** (Learning Asymmetry) - subset of Flaw #6

---

**Last Updated**: 2025-11-18
**Related**: [INDEX.md](INDEX.md) | [ROADMAP.md](ROADMAP.md) | [README.md](README.md)
