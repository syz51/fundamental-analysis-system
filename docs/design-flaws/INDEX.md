# Design Flaws Index

## At a Glance

- **Total**: 26 flaws + 6 minor issues
- **Active**: 3 (1 critical, 1 high, 1 medium, 2 deferred)
- **Resolved**: 21
- **Deferred**: 2

---

## 🚨 Critical Active Flaws (1)

Blocks MVP or production deployment:

| # | Flaw | Impact | Phase | Effort | Dependencies |
|---|------|--------|-------|--------|--------------|
| [21](active/21-scalability.md) | Scalability Architecture Bottlenecks | Cannot scale to 1000+ stocks without redesign | 4 | 8w | Neo4j operational, DD-004 auto-approval |

---

## High Priority Active Flaws (1)

<details>
<summary><b>Should fix before MVP</b></summary>

| # | Flaw | Impact | Phase | Effort | Dependencies |
|---|------|--------|-------|--------|--------------|
| [17](active/17-data-tier-mgmt.md) | Data Tier Management Gaps | Performance degradation, no corruption recovery | 4 | 4w | DD-009 tiered storage, Neo4j operational |

</details>

---

## Medium Priority (1)

<details>
<summary><b>Post-MVP improvements</b></summary>

| # | Flaw | Impact | Phase | Effort |
|---|------|--------|-------|--------|
| [20](active/20-access-control.md) | Memory System Access Control Undefined | Data integrity risk from unrestricted modifications | 3 | 4w |

</details>

---

## Low Priority & Deferred (2)

<details>
<summary><b>Future optimization</b></summary>

| # | Flaw | Status | Phase | Notes |
|---|------|--------|-------|-------|
| [6](active/06-expertise-routing.md) | Static Human Expertise Routing | Deferred | 5 | Marginal improvement in expertise matching |
| [18](active/18-learning-asymmetry.md) | Learning Asymmetry - Human Expertise Not Tracked | Deferred | 5 | Suboptimal human-AI task division |

</details>

---

## ✅ Resolved Flaws by Phase (21)

<details>
<summary><b>Phase 1: Foundation (2 resolved)</b></summary>

| # | Flaw | Resolution | Completed |
|---|------|-----------|-----------|
| [1](resolved/01-missing-human-gate.md) | Missing Human Gate for Learning Validation | DD-001 Gate 6 Learning Validation | 2025-11-17 |
| [2](resolved/02-memory-sync-timing.md) | Memory Sync Timing Incompatible with Debate Protocol | DD-002 Event-Driven Memory Synchronization | 2025-11-17 |

</details>

<details>
<summary><b>Phase 2: Core Systems (9 resolved)</b></summary>

| # | Flaw | Resolution | Completed |
|---|------|-----------|-----------|
| [8](resolved/08-debate-deadlock.md) | Debate Resolution Deadlock Scenario | 5-level tiered escalation system | 2025-11-17 |
| [11](resolved/11-algorithm-specs.md) | Missing Algorithm Specifications | All algorithms documented in main architecture docs | 2025-11-17 |
| [16](resolved/16-timeline-conflicts.md) | Timeline & Dependency Conflicts | N/A | 2025-11-18 |
| [19](resolved/19-partial-failures.md) | Partial Failure Handling Undefined | Hard-stop approach via DD-011/DD-012/DD-015 (G1), DD-010 (M6), tech-agnostic spec (G2) | 2025-11-18 |
| [22](resolved/22-agent-checkpoints.md) | Agent Checkpoint System Missing | Design Decision DD-011 addresses all sub-issues | 2025-11-18 |
| [23](resolved/23-workflow-pause-resume.md) | Workflow Pause/Resume Infrastructure Undefined | N/A | 2025-11-18 |
| [24](resolved/24-agent-failure-alerts.md) | Agent Failure Human Alerts Missing | N/A | 2025-11-18 |
| [25](resolved/25-working-memory-durability.md) | Working Memory Insufficient for Long Pauses | N/A | N/A |
| [26](resolved/26-multi-stock-batching.md) | Multi-Stock Failure Batching Undefined | DD-017: Failure Correlation System | 2025-11-18 |

</details>

<details>
<summary><b>Phase 2-3: Phase 2-3 (1 resolved)</b></summary>

| # | Flaw | Resolution | Completed |
|---|------|-----------|-----------|
| [14](resolved/14-statistical-reliability.md) | Statistical Reliability Issues | N/A | 2025-11-18 |

</details>

<details>
<summary><b>Phase 3: Quality & Learning (4 resolved)</b></summary>

| # | Flaw | Resolution | Completed |
|---|------|-----------|-----------|
| [3](resolved/03-pattern-validation.md) | Pattern Validation Confirmation Bias Loop | DD-007 Pattern Validation Architecture | 2025-11-17 |
| [7](resolved/07-memory-scalability.md) | Memory Scalability vs Performance Targets | DD-005 Memory Scalability Optimization | 2025-11-17 |
| [13](resolved/13-validation-gaps.md) | Learning System Validation Gaps | N/A | N/A |
| [15](resolved/15-failure-modes.md) | Query & Sync Failure Modes | DD-018: Memory System Failure Resilience | 2025-11-18 |

</details>

<details>
<summary><b>Phase 3-4: Phase 3-4 (1 resolved)</b></summary>

| # | Flaw | Resolution | Completed |
|---|------|-----------|-----------|
| [12](resolved/12-archive-lifecycle.md) | Pattern Archive Lifecycle Gaps | DD-013: Pattern Archive Lifecycle Management | 2025-11-18 |

</details>

<details>
<summary><b>Phase 4: Optimization (4 resolved)</b></summary>

| # | Flaw | Resolution | Completed |
|---|------|-----------|-----------|
| [4](resolved/04-credibility-scoring.md) | Agent Credibility Scoring - No Temporal Decay | DD-008 Agent Credibility System | 2025-11-17 |
| [5](resolved/05-data-retention.md) | Data Retention Policy Conflict | DD-009 Data Retention & Pattern Evidence Architecture | 2025-11-17 |
| [9](resolved/09-negative-feedback.md) | Learning Loop - No Negative Feedback Mechanism | DD-006 Negative Feedback System | 2025-11-17 |
| [10](resolved/10-gate-6-parameters.md) | Gate 6 Parameter Optimization | DD-004 Gate 6 Parameter Optimization | 2025-11-17 |

</details>

---

## 🏷️ Domain View

Navigate by system component:

<details>
<summary><b>Memory System (8 flaws: 2 active, 6 resolved)</b></summary>

**Active:**
- [#17](active/17-data-tier-mgmt.md) - Data Tier Management Gaps (H, Phase 4)
- [#20](active/20-access-control.md) - Memory System Access Control Undefined (M, Phase 3)

**Resolved:**
- [#2](resolved/02-memory-sync-timing.md)✅ - Memory Sync Timing Incompatible with Debate Protocol
- [#5](resolved/05-data-retention.md)✅ - Data Retention Policy Conflict
- [#7](resolved/07-memory-scalability.md)✅ - Memory Scalability vs Performance Targets
- [#12](resolved/12-archive-lifecycle.md)✅ - Pattern Archive Lifecycle Gaps
- [#15](resolved/15-failure-modes.md)✅ - Query & Sync Failure Modes
- [#25](resolved/25-working-memory-durability.md)✅ - Working Memory Insufficient for Long Pauses

</details>

<details>
<summary><b>Learning System (9 flaws: 0 active, 7 resolved)</b></summary>

**Resolved:**
- [#1](resolved/01-missing-human-gate.md)✅ - Missing Human Gate for Learning Validation
- [#3](resolved/03-pattern-validation.md)✅ - Pattern Validation Confirmation Bias Loop
- [#9](resolved/09-negative-feedback.md)✅ - Learning Loop - No Negative Feedback Mechanism
- [#10](resolved/10-gate-6-parameters.md)✅ - Gate 6 Parameter Optimization
- [#11](resolved/11-algorithm-specs.md)✅ - Missing Algorithm Specifications
- [#13](resolved/13-validation-gaps.md)✅ - Learning System Validation Gaps
- [#14](resolved/14-statistical-reliability.md)✅ - Statistical Reliability Issues

</details>

<details>
<summary><b>Agent System (6 flaws: 0 active, 6 resolved)</b></summary>

**Resolved:**
- [#4](resolved/04-credibility-scoring.md)✅ - Agent Credibility Scoring - No Temporal Decay
- [#8](resolved/08-debate-deadlock.md)✅ - Debate Resolution Deadlock Scenario
- [#11](resolved/11-algorithm-specs.md)✅ - Missing Algorithm Specifications
- [#14](resolved/14-statistical-reliability.md)✅ - Statistical Reliability Issues
- [#19](resolved/19-partial-failures.md)✅ - Partial Failure Handling Undefined
- [#22](resolved/22-agent-checkpoints.md)✅ - Agent Checkpoint System Missing

</details>

<details>
<summary><b>Data System (3 flaws: 1 active, 2 resolved)</b></summary>

**Active:**
- [#17](active/17-data-tier-mgmt.md) - Data Tier Management Gaps (H, Phase 4)

**Resolved:**
- [#5](resolved/05-data-retention.md)✅ - Data Retention Policy Conflict
- [#12](resolved/12-archive-lifecycle.md)✅ - Pattern Archive Lifecycle Gaps

</details>

<details>
<summary><b>Human Gates (5 flaws: 1 active, 2 resolved)</b></summary>

**Active:**
- [#21](active/21-scalability.md) - Scalability Architecture Bottlenecks (C, Phase 4)

**Resolved:**
- [#1](resolved/01-missing-human-gate.md)✅ - Missing Human Gate for Learning Validation
- [#10](resolved/10-gate-6-parameters.md)✅ - Gate 6 Parameter Optimization

</details>

<details>
<summary><b>Architecture (9 flaws: 2 active, 7 resolved)</b></summary>

**Active:**
- [#20](active/20-access-control.md) - Memory System Access Control Undefined (M, Phase 3)
- [#21](active/21-scalability.md) - Scalability Architecture Bottlenecks (C, Phase 4)

**Resolved:**
- [#8](resolved/08-debate-deadlock.md)✅ - Debate Resolution Deadlock Scenario
- [#11](resolved/11-algorithm-specs.md)✅ - Missing Algorithm Specifications
- [#16](resolved/16-timeline-conflicts.md)✅ - Timeline & Dependency Conflicts
- [#19](resolved/19-partial-failures.md)✅ - Partial Failure Handling Undefined
- [#22](resolved/22-agent-checkpoints.md)✅ - Agent Checkpoint System Missing
- [#23](resolved/23-workflow-pause-resume.md)✅ - Workflow Pause/Resume Infrastructure Undefined
- [#25](resolved/25-working-memory-durability.md)✅ - Working Memory Insufficient for Long Pauses

</details>

---

## 📊 Quick Filters

### By Phase

**Phase 3 (Months 5-6):** 1 active
- [20](active/20-access-control.md) Memory System Access Control Undefined (M, 4w)

**Phase 4 (Months 7-8):** 2 active
- [17](active/17-data-tier-mgmt.md) Data Tier Management Gaps (H, 4w)
- [21](active/21-scalability.md) Scalability Architecture Bottlenecks (C, 8w)

### By Effort

**Quick wins (<3 weeks):** 0 flaws

**Medium (3-5 weeks):** 2 flaws
- [17](active/17-data-tier-mgmt.md) - 4w
- [20](active/20-access-control.md) - 4w

**Large (>5 weeks):** 1 flaws
- [21](active/21-scalability.md) - 8w

### By Dependencies

**Unblocked (ready to start):** 0 flaws

**Waiting on 1 dependency:** 1 flaws
- [20](active/20-access-control.md) - Memory system operational (L1/L2/L3)

**Waiting on 2+ dependencies:** 2 flaws
- [17](active/17-data-tier-mgmt.md) - DD-009 tiered storage, Neo4j operational
- [21](active/21-scalability.md) - Neo4j operational, DD-004 auto-approval

---

## 🔗 Related Documentation

- [DEPENDENCIES.md](DEPENDENCIES.md) - Full dependency graph and matrix
- [ROADMAP.md](ROADMAP.md) - Phase timeline and critical path
- [README.md](README.md) - How to navigate and use this folder
- [Minor Issues](MINOR-ISSUES.md) - 6 low-priority clarifications
- [Design Decisions](../design-decisions/) - DD-XXX resolution documents

---

**Last Updated**: Auto-generated from frontmatter (run `python generate_index.py` to refresh)