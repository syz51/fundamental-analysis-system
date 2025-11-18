---
flaw_id: 15
title: Query & Sync Failure Modes
status: active
priority: critical
phase: 3
effort_weeks: 4
impact: System hangs from infinite recursion, memory overflow
blocks: ["Memory reliability"]
depends_on: ["DD-005 memory system", "DD-002 event-driven sync"]
domain: ["memory"]
sub_issues:
  - id: C5
    severity: critical
    title: Query timeout fallback infinite recursion risk
  - id: A4
    severity: high
    title: Event-driven sync no backpressure mechanism
  - id: M5
    severity: medium
    title: Regime detection/credibility recalc race condition
discovered: 2025-11-17
---

# Flaw #15: Query & Sync Failure Modes

**Status**: 🔴 ACTIVE
**Priority**: Critical
**Impact**: System hangs from infinite recursion, memory overflow from unbounded sync
**Phase**: Phase 3 (Months 5-6)

---

## Problem Description

Memory system (DD-005, DD-002) lacks failure mode handling:

1. **C5**: Query timeout fallback could cause infinite recursion
2. **A4**: Event-driven sync has no backpressure mechanism
3. **M5**: Regime detection and credibility recalc race condition

### Sub-Issue C5: Timeout Fallback Infinite Recursion

**Files**: `docs/architecture/02-memory-system.md:949-960`, `design-decisions/DD-005:99-119`

**Problem**: Fallback strategies for timed-out queries may also timeout, causing recursion.

**Current State**:
```yaml
Fallback Strategies (when timeout exceeded):
  - Return approximate result (e.g., top-5 instead of top-10)
  - Return cached result with staleness indicator
  - Sample-based results (50% sample)
```

**Recursion Risk**:
```text
Query times out (>500ms)
  → Fallback: Return cached result
  → Cache query ALSO times out
    → Fallback: Return approximate result
    → Approximation ALSO times out
      → Fallback: ???

MISSING: Max recursion depth, ultimate fallback
```

**Solution**: Hard limit on fallback depth, ultimate fallback returns empty with error flag

### Sub-Issue A4: No Backpressure for Event-Driven Sync

**Files**: `docs/architecture/02-memory-system.md:812-870`, `design-decisions/DD-002`

**Problem**: Critical/high priority sync events push updates but no throttling if receiver overwhelmed.

**Overflow Scenario**:
```text
Debate generates 10 critical findings simultaneously
Each triggers critical sync to 5 agents
= 50 concurrent critical sync operations
Each agent L1 working memory: 100-item capacity

Agent receives:
  - 10 critical syncs (must process within 2s)
  - L1 at 95/100 capacity
  - Overflow: Drop updates or queue?

MISSING: Backpressure signaling, queue depth limits, priority-based dropping
```

**Solution**: Queue depth limits, backpressure to sender, priority-based eviction

### Sub-Issue M5: Regime Detection Race Condition

**Files**:
- `docs/implementation/05-credibility-system.md:107-149`
- `docs/learning/02-feedback-loops.md:296-309`

**Problem**: Regime detection runs "daily" and credibility recalc "triggered daily" - no synchronization.

**Race**:
```text
00:00 - Regime detection starts
01:00 - Credibility recalc triggered (uses yesterday's regime - stale)
02:00 - Regime detection completes (new regime detected)
02:30 - New outcome recorded, recalc triggered (uses 2hr-old regime)
```

**Solution**: Sequencing guarantee - regime detection → cache update → credibility recalc

---

## Recommended Solution

### C5: Fallback Recursion Prevention

```python
class QueryWithFallback:
    """Query with bounded fallback attempts"""

    MAX_FALLBACK_DEPTH = 2
    ULTIMATE_FALLBACK_TIMEOUT_MS = 50

    def query_with_fallback(self, query, timeout_ms=500, depth=0):
        """Execute query with fallback on timeout"""

        if depth > self.MAX_FALLBACK_DEPTH:
            # Ultimate fallback: return empty with error
            return QueryResult(
                data=[],
                status='failed_max_retries',
                error=f'Exceeded max fallback depth ({self.MAX_FALLBACK_DEPTH})'
            )

        try:
            result = self.execute_query(query, timeout_ms)
            return result

        except TimeoutError:
            # Try fallback strategies
            if depth == 0:
                # First fallback: Try cache
                return self.query_with_fallback(
                    query.to_cache_query(),
                    timeout_ms=200,
                    depth=depth + 1
                )
            elif depth == 1:
                # Second fallback: Approximation
                return self.query_with_fallback(
                    query.to_approximate(),
                    timeout_ms=100,
                    depth=depth + 1
                )
            else:
                # Ultimate fallback: Empty result
                return QueryResult(
                    data=[],
                    status='timeout_all_fallbacks',
                    original_timeout=timeout_ms
                )
```

### A4: Backpressure System

```python
class MemorySyncWithBackpressure:
    """Event-driven sync with backpressure"""

    MAX_QUEUE_DEPTH = 50
    CRITICAL_QUEUE_DEPTH = 10

    def sync_memory(self, agent_id, update, priority='normal'):
        """Sync with backpressure"""

        queue_depth = self.get_queue_depth(agent_id)

        # Check capacity
        if queue_depth >= self.MAX_QUEUE_DEPTH:
            if priority == 'critical':
                # Evict lowest priority item
                self.evict_lowest_priority(agent_id)
            else:
                # Signal backpressure to sender
                raise BackpressureError(
                    agent_id=agent_id,
                    queue_depth=queue_depth,
                    retry_after_ms=500
                )

        # Check critical queue
        if priority == 'critical' and self.count_critical(agent_id) >= self.CRITICAL_QUEUE_DEPTH:
            # Too many critical items, temporarily downgrade
            priority = 'high'

        # Enqueue update
        self.enqueue(agent_id, update, priority)

    def evict_lowest_priority(self, agent_id):
        """Evict item when queue full"""

        queue = self.get_queue(agent_id)

        # Priority order: normal < high < critical
        for priority in ['normal', 'high']:
            items = [i for i in queue if i.priority == priority]
            if items:
                # Evict oldest of this priority
                self.dequeue(items[0])
                return
```

### M5: Sequenced Regime Detection

```python
class SequencedRegimeDetection:
    """Ensure regime detection completes before credibility calc"""

    def daily_update_sequence(self):
        """Run daily updates in sequence"""

        # Step 1: Detect market regime
        new_regime = self.detect_market_regime()

        # Step 2: Update regime cache FIRST
        self.update_regime_cache(new_regime)

        # Step 3: THEN trigger credibility recalculation
        self.trigger_credibility_recalc()

        # Step 4: Log sequence completion
        self.log_sequence_completion(new_regime)
```

---

## Implementation Plan

**Week 1**: C5 fallback recursion limits
**Week 2**: A4 backpressure system
**Week 3**: M5 sequenced regime detection
**Week 4**: Testing & validation

---

## Success Criteria

- ✅ C5: Zero infinite recursion (100 timeout scenarios tested)
- ✅ A4: Queue overflow handled gracefully (no memory leaks)
- ✅ M5: Regime staleness <5min (99th percentile)

---

## Dependencies

- **Blocks**: Memory system reliability (DD-005), Sync reliability (DD-002)
- **Depends On**: Memory system operational, regime detection active
- **Related**: Flaw #7 (Memory Scalability - RESOLVED), DD-002, DD-005, DD-008
