# Minor Issues - Low Priority Clarifications

**Status**: 🟡 LOW PRIORITY
**Impact**: Ambiguous criteria, minor inconsistencies
**Phase**: Phase 4-5 (Address during optimization)

---

## Overview

Minor issues identified during documentation review. These are ambiguities and clarifications that don't block implementation but should be resolved for consistency.

---

## M1: Probation Extension Progress Ambiguous

**Files**: `docs/operations/02-human-integration.md:440-448`, `design-decisions/DD-004`

**Issue**: Probation extension criteria "50%+ progress toward target" undefined.

**Ambiguity**:

```yaml
Pattern needs 5 more occurrences for validation
After 90 days: Found 2 occurrences

Progress calculation:
  Option A: 2/5 = 40% → Extension DENIED
  Option B: On track for 2.5 at current rate → Extension GRANTED?

UNDEFINED: Occurrence-based vs rate-adjusted progress
```

**Recommendation**: Clarify in DD-004 as occurrence-based (2/5 = 40%)

---

## M2: Cache Hit Rate Measurement Undefined

**Files**: `docs/architecture/02-memory-system.md:881-923`, `design-decisions/DD-005`

**Issue**: Target cache hit rate >80% specified, but "cache hit" definition unclear across L1/L2/L3 tiers.

**Ambiguity**:

```yaml
Query needs Pattern A + Pattern B
  - Pattern A in L2 cache (<50ms) ✓
  - Pattern B not cached, requires L3 query (400ms) ✗
  - Total time: 450ms

Cache hit rate: 50%? 100%? 0%?

Options:
  1. L1-only hits (most restrictive)
  2. L1+L2 hits (typical)
  3. L1+L2+L3 (all cached layers)
  4. Per-item (50% in example)
  5. Per-query (0% - not all items cached)
```

**Recommendation**: Define as L1+L2 hits, per-item basis

---

## M4: Pattern Lifecycle State Transitions Incomplete

**Files**: `docs/learning/01-learning-systems.md:28-39`, `docs/architecture/02-memory-system.md:76-78`

**Issue**: Pattern status lifecycle shows 8 states but only 6 documented transitions.

**Missing Transitions**:

```yaml
States: candidate, statistically_validated, human_approved,
        active, probationary, rejected, deprecated

Missing:
  1. active → probationary (trigger: performance degradation - how severe?)
  2. probationary → deprecated (condition: failure at deadline?)
  3. probationary → active (condition: recovery criteria?)
  4. active → deprecated (when vs. rejected?)

Also: 8 rejection substates shown but lifecycle only shows "rejected"
  - rejected_holdout
  - rejected_blind
  - rejected_statistical
```

**Recommendation**: Add complete state transition diagram to learning-systems.md

---

## M7: Screening False Positive/Negative Definition

**Files**: `docs/architecture/03-agents-specialist.md:40-46`

**Issue**: Screening agent tracks "false positive/negative rates" but determination criteria undefined.

**Ambiguity**:

```text
What constitutes "false positive"?
  Option A: Screened in, rejected at Gate 1?
  Option B: Screened in, rejected at Gate 5?
  Option C: Screened in, bad 365-day outcome?

When determined?
  - Gate 1? (24hr)
  - Gate 5? (12 days)
  - 365-day checkpoint? (1 year)

Who labels?
  - Human at gates?
  - Outcome tracker?
  - Both?
```

**Recommendation**: Define as Gate 5 rejection (conservative - counts analysis pipeline investment)

---

## CS1: Memory Sync Latency vs Access Time

**Files**: Multiple

**Issue**: Clarification needed - sync operation time vs layer access time.

**Potential Confusion**:

```yaml
# CLAUDE.md & memory-system.md:
Critical sync: <2 seconds
High sync: <10 seconds
Normal sync: 5 minutes

# roadmap.md:
L1 access: <100ms
L3 access: <1s

CLARIFY: Sync time is operation latency, access time is query latency
```

**Recommendation**: Add glossary distinguishing "sync latency" vs "access latency"

---

## CS2: Pattern Minimum Occurrence Count

**Files**: Multiple

**Issue**: Inconsistent minimum occurrence requirements.

**Contradictions**:

```yaml
# learning-systems.md L190-193
"Minimum 5 occurrences"

# DD-007 (hold-out validation)
"Must have at least 3 confirming instances"

# agents-specialist.md L57 (example)
learned_from: ['INTC_2020', 'IBM_2019']  # ONLY 2!
```

**Recommendation**: Standardize on 5 minimum occurrences, update example to show 5

---

## Summary

| Issue | Type            | Priority | Effort    |
| ----- | --------------- | -------- | --------- |
| M1    | Clarification   | LOW      | 30 min    |
| M2    | Definition      | LOW      | 1 hour    |
| M4    | Documentation   | MEDIUM   | 2-3 hours |
| M7    | Definition      | MEDIUM   | 1 hour    |
| CS1   | Clarification   | LOW      | 30 min    |
| CS2   | Consistency fix | LOW      | 1 hour    |

**Total Effort**: ~8 hours (1 day)

---

## Implementation Plan

**Phase 4 (Month 8)**: Address during documentation polish

- Update DD-004 (M1)
- Update DD-005 (M2)
- Add state transition diagram (M4)
- Define false positive criteria (M7)
- Add glossary (CS1)
- Fix examples (CS2)

---

## Success Criteria

- ✅ All ambiguous criteria clearly defined
- ✅ Inconsistencies resolved
- ✅ Examples match requirements
- ✅ Glossary added for common terms

---

## Related Documentation

- Pattern validation: learning-systems.md, DD-007
- Memory system: memory-system.md, DD-005
- Human gates: human-integration.md, DD-004
- Agent specs: agents-specialist.md
