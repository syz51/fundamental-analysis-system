# Memory System Failure Resilience

**Status**: Approved
**Date**: 2025-11-18
**Decider(s)**: System Architect
**Related Docs**: [Memory System](../architecture/02-memory-system.md), [Agents Coordination](../architecture/05-agents-coordination.md), [Credibility System](../implementation/05-credibility-system.md)
**Related Decisions**: [DD-005 Memory Scalability](DD-005_MEMORY_SCALABILITY_OPTIMIZATION.md), [DD-002 Event-Driven Sync](DD-002_EVENT_DRIVEN_MEMORY_SYNC.md), [DD-008 Credibility System](DD-008_AGENT_CREDIBILITY_SYSTEM.md)

---

## Context

Memory system (DD-005, DD-002) and credibility system (DD-008) lack failure mode handling. Three critical failure scenarios identified that could cause system hangs, memory overflow, or data staleness.

**Current State**:

- DD-005 defines query timeout (500ms) with fallback strategy (L1 → L2 → L3 → cached → approximation), but no recursion limits
- DD-002 defines event-driven sync with 3-tier priority (critical 2s, high 10s, normal 5min), but no backpressure mechanism
- DD-008 defines credibility recalculation (daily) and regime detection (daily), but no sequencing guarantee
- No protection against infinite fallback recursion during query timeouts
- No throttling when sync events overwhelm agent memory queues
- No synchronization between regime detection and credibility recalc, causing staleness

**Why Address Now**:

- Resolves Flaw #15 (C5, A4, M5) - blocks memory system reliability
- Phase 3 (Months 5-6) - memory system must be production-ready before full agent deployment
- Critical priority - system hangs/overflow/staleness unacceptable in production
- Infrastructure complete (DD-005, DD-002, DD-008), ready for failure handling layer

**Example Impacts**:

1. **C5 Infinite Recursion**: Query times out (500ms) → tries L2 → L2 times out → tries L3 → L3 times out → tries cache → cache times out → system hangs
2. **A4 Queue Overflow**: Debate generates 10 critical findings → 50 concurrent critical syncs (10 findings × 5 agents) → agent L1 memory at 95/100 capacity → overflow, memory leak, agent crashes
3. **M5 Regime Staleness**: Regime detection starts 00:00 → credibility recalc at 01:00 uses yesterday's regime (stale) → regime completes at 02:00 → new outcome at 02:30 uses 2hr-old regime data

---

## Decision

**Implement three failure resilience mechanisms: (1) Query fallback recursion limits with timeout reduction, (2) Event-driven sync backpressure with priority-based eviction, (3) Sequenced regime detection with hybrid parallelism.**

System provides:

- **C5 Query Resilience**: `MAX_FALLBACK_DEPTH=2`, timeout reduction (500ms → 200ms → 100ms), ultimate fallback (empty result + error flag + alert)
- **A4 Sync Backpressure**: Queue limits (`MAX_QUEUE_DEPTH=50`, `CRITICAL_QUEUE_DEPTH=10`), backpressure signaling (`BackpressureError` with exponential backoff), priority-based eviction (drop normal/high before critical)
- **M5 Regime Sequencing**: Hybrid parallelism (parallel across regimes, serial within regime: detection → cache update → credibility recalc), dependency flags (`regime_{id}_updated_today`), staleness target <5min (99th percentile)

---

## Options Considered

### Option 1: Comprehensive Failure Resilience (CHOSEN)

**Description**: Implement all three failure handling mechanisms (recursion limits, backpressure, sequencing) with monitoring and alerts.

**Pros**:

- Prevents all 3 failure modes (infinite recursion, queue overflow, regime staleness)
- Query resilience: <2s worst-case timeout (500ms + 200ms + 100ms + 100ms fallback), zero hangs
- Sync backpressure: graceful degradation under load (drop normal syncs, preserve critical)
- Regime sequencing: <5min staleness (vs 2+ hours), prevents stale credibility scores
- Production-ready: handles edge cases, alerts on failures, supports debugging
- Complete Flaw #15 resolution (C5, A4, M5)

**Cons**:

- Implementation complexity (3 separate mechanisms)
- Testing overhead (edge cases, concurrency, timing)
- Monitoring infrastructure (alerts, metrics)
- Exponential backoff logic (retry coordination)
- Hybrid sequencing (parallel + serial orchestration)

**Estimated Effort**: 4 weeks (Week 1: C5, Week 2: A4, Week 3: M5, Week 4: testing)

---

### Option 2: Minimal Fixes Only

**Description**: Simple recursion limit (`MAX_DEPTH=1`), no backpressure, no sequencing.

**Pros**:

- Fast implementation (1 week)
- Simple recursion check (depth counter only)
- Zero new infrastructure

**Cons**:

- Incomplete: Only resolves C5 (not A4, M5)
- Worse UX: Query fails faster (no timeout reduction, no approximation fallback)
- No queue overflow protection: A4 failure mode remains (agent crashes)
- No regime staleness fix: M5 failure mode remains (2+ hour stale data)
- Partial Flaw #15 resolution (1/3 sub-issues)
- Not production-ready

**Estimated Effort**: 1 week

---

### Option 3: Manual Intervention Required

**Description**: Alert human on query timeout, queue overflow, regime staleness - no automatic handling.

**Pros**:

- No code changes (alert-only)
- Human judgment prevents false positives
- Simple implementation (alert integration)

**Cons**:

- Slow response time (minutes/hours vs subseconds)
- Not scalable (100+ agents → human can't respond fast enough)
- System hangs/crashes before human responds (C5/A4 failures within seconds)
- Defeats automation goal of multi-agent system
- Unusable in production (requires 24/7 human monitoring)
- Does not resolve Flaw #15

**Estimated Effort**: 2 days (alert setup)

---

## Rationale

**Option 1 (Comprehensive Failure Resilience) chosen** because:

1. **C5 Recursion Protection**: `MAX_FALLBACK_DEPTH=2` prevents infinite loops, timeout reduction (500ms → 200ms → 100ms) allows fallback within budget, ultimate fallback (empty + error + alert) prevents hangs while alerting human.

2. **A4 Backpressure Handling**: Queue limits prevent memory overflow, exponential backoff (100ms → 800ms, max 5 retries) allows sender to retry without overwhelming receiver, priority eviction (drop normal before critical) preserves important syncs during debates.

3. **M5 Regime Sequencing**: Hybrid parallelism maximizes throughput (parallel across 5+ regimes) while guaranteeing ordering (serial within regime), <5min staleness vs 2+ hours, dependency flags (`regime_{id}_updated_today`) prevent credibility recalc on stale data.

4. **Production Readiness**: All 3 failure modes resolved, automatic recovery (no manual intervention), monitoring/alerts (human aware of issues), scalable to 100+ agents.

5. **Complete Flaw #15 Resolution**: C5/A4/M5 fully resolved, unblocks Phase 3 memory system deployment.

**Acceptable tradeoffs**:

- 4-week implementation: justified by production reliability (zero hangs/crashes/staleness)
- Complexity: necessary for production-scale system (100+ agents, 200+ stocks)
- Testing overhead: critical for failure mode validation (edge cases rare but catastrophic)
- Alert noise risk: mitigated by severity thresholds (only alert on critical failures, not normal degradation)

---

## Consequences

### Positive Impacts

- ✅ **C5: Zero infinite recursion**: Query timeout handled within 2s (500+200+100+100ms), no system hangs
- ✅ **A4: Graceful queue overflow**: Backpressure prevents crashes, priority eviction preserves critical syncs
- ✅ **M5: Regime staleness <5min**: 99th percentile <5min vs 2+ hours, prevents stale credibility scores
- ✅ **Production reliability**: Automatic recovery from all 3 failure modes
- ✅ **Monitoring**: Alerts on query timeout exhaustion, queue overflow, regime delays
- ✅ **Flaw #15 resolution**: C5/A4/M5 fully resolved, unblocks Phase 3

### Negative Impacts / Tradeoffs

- ❌ **Query UX degradation**: Fallback depth=2 means fewer fallback attempts (L1 → L2 → done), may return empty results faster
- ❌ **Sync message loss**: Priority eviction drops normal/high syncs under load, agents may miss non-critical updates
- ❌ **Regime processing delay**: Hybrid sequencing adds coordination overhead (dependency flags, serial steps)
- ❌ **Alert noise**: Query timeout alerts may fire during transient database slowness
- ❌ **Testing complexity**: Edge cases (concurrent overflow, window boundary timing)

**Mitigations**:

- Query UX: Timeout reduction (500→200→100ms) allows 2 fallbacks within original budget
- Sync loss: Critical syncs never dropped, normal syncs can be re-requested
- Regime delay: Parallel across regimes maintains throughput (only serial within regime)
- Alert noise: Severity thresholds (only alert if 10+ timeouts in 1min)
- Testing: Dedicated failure scenario suite (100 timeout tests, queue overflow sim)

### Affected Components

**New Components**:

- `QueryFallbackGuard` class (recursion tracking, timeout reduction)
- `SyncBackpressureManager` class (queue monitoring, backpressure signaling, eviction)
- `RegimeSequencer` class (dependency flags, hybrid orchestration)
- `memory_failure_alerts` module (alert integration)

**Modified Components**:

- `memory_system.py`: Add QueryFallbackGuard to query_memory() paths
- `event_sync.py`: Add SyncBackpressureManager to push_sync_event()
- `credibility_engine.py`: Replace daily batch with RegimeSequencer
- `base_agent.py`: Handle BackpressureError in memory sync handlers
- `lead_coordinator.py`: Subscribe to failure alerts

**Documentation Updates**:

- `02-memory-system.md`: Add C5 recursion limits, A4 backpressure sections
- `05-credibility-system.md`: Add M5 regime sequencing section
- `05-agents-coordination.md`: Add failure alert subscription
- `15-failure-modes.md`: Move from active/ to resolved/, mark C5/A4/M5 resolved

---

## Implementation Notes

### C5: Query Fallback Recursion Protection

**Purpose**: Prevent infinite fallback loops during query timeouts, ensure <2s worst-case response.

**QueryFallbackGuard API**:

```python
class QueryFallbackGuard:
    """Track query fallback depth and enforce recursion limits"""

    MAX_FALLBACK_DEPTH = 2  # L1 → L2 → done (no further fallback)
    TIMEOUT_REDUCTION_FACTOR = 0.4  # Each level: timeout *= 0.4

    def __init__(self, initial_timeout_ms: int = 500):
        self.initial_timeout_ms = initial_timeout_ms
        self.current_depth = 0
        self.fallback_chain = []  # Track: ['L1', 'L2', 'cached']

    def can_fallback(self) -> bool:
        """Check if another fallback attempt is allowed"""
        return self.current_depth < self.MAX_FALLBACK_DEPTH

    def next_timeout_ms(self) -> int:
        """Calculate timeout for next fallback level"""
        # Level 0: 500ms, Level 1: 200ms, Level 2: 100ms
        timeout = int(self.initial_timeout_ms * (self.TIMEOUT_REDUCTION_FACTOR ** self.current_depth))
        return max(timeout, 100)  # Minimum 100ms

    def record_fallback(self, layer: str):
        """Record fallback attempt"""
        self.current_depth += 1
        self.fallback_chain.append(layer)

    def ultimate_fallback(self) -> QueryResult:
        """Return empty result when all fallbacks exhausted"""
        return QueryResult(
            data=[],
            error=QueryError(
                code='QUERY_TIMEOUT_EXHAUSTED',
                message=f'All fallback layers timed out: {" → ".join(self.fallback_chain)}',
                fallback_chain=self.fallback_chain,
                total_time_ms=sum(self.timeout_history)
            ),
            metadata={'fallback_exhausted': True}
        )
```

**Memory System Integration**:

```python
# In memory_system.py
class MemorySystem:
    def query_memory(self, query: str, timeout_ms: int = 500) -> QueryResult:
        """Query memory with fallback recursion protection"""

        guard = QueryFallbackGuard(initial_timeout_ms=timeout_ms)

        # Level 0: L1 memory (timeout: 500ms)
        try:
            return self._query_l1(query, timeout_ms=guard.next_timeout_ms())
        except TimeoutError:
            guard.record_fallback('L1')

        # Level 1: L2 memory fallback (timeout: 200ms)
        if guard.can_fallback():
            try:
                return self._query_l2(query, timeout_ms=guard.next_timeout_ms())
            except TimeoutError:
                guard.record_fallback('L2')

        # Level 2: Cached approximation fallback (timeout: 100ms)
        if guard.can_fallback():
            try:
                return self._query_cached_approximation(query, timeout_ms=guard.next_timeout_ms())
            except TimeoutError:
                guard.record_fallback('cached')

        # Ultimate fallback: Return empty result + trigger alert
        result = guard.ultimate_fallback()
        self._trigger_timeout_alert(guard)
        return result

    def _trigger_timeout_alert(self, guard: QueryFallbackGuard):
        """Trigger alert on query timeout exhaustion"""
        self.alert_manager.on_query_timeout_exhausted(
            fallback_chain=guard.fallback_chain,
            total_time_ms=sum(guard.timeout_history),
            severity='WARNING'  # Not critical - query returned empty safely
        )
```

**Success Criteria**:

- Zero infinite recursion (100 timeout scenarios tested)
- Worst-case response time <2s (500+200+100+100ms)
- Query returns empty result (not hang) when exhausted
- Alert triggered on timeout exhaustion (severity: WARNING)

---

### A4: Event-Driven Sync Backpressure

**Purpose**: Prevent memory queue overflow during high-priority sync bursts (debates, human gates).

**SyncBackpressureManager API**:

```python
class SyncBackpressureManager:
    """Monitor sync queues and apply backpressure when overwhelmed"""

    MAX_QUEUE_DEPTH = 50  # Total sync queue capacity
    CRITICAL_QUEUE_DEPTH = 10  # Critical-only capacity when backpressure active

    # Exponential backoff: 100ms → 200ms → 400ms → 800ms
    BACKOFF_INITIAL_MS = 100
    BACKOFF_MAX_MS = 800
    BACKOFF_MAX_RETRIES = 5

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.queue = []  # [(priority, message, timestamp), ...]
        self.backpressure_active = False
        self.dropped_stats = {'normal': 0, 'high': 0, 'critical': 0}

    def can_accept_sync(self, priority: str) -> bool:
        """Check if queue can accept new sync"""
        current_depth = len(self.queue)

        # No backpressure: accept all
        if current_depth < self.MAX_QUEUE_DEPTH:
            return True

        # Backpressure active: only accept critical
        if current_depth >= self.MAX_QUEUE_DEPTH:
            self.backpressure_active = True
            return priority == 'critical'

        return False

    def push_sync_event(
        self,
        from_agent: str,
        message: dict,
        priority: str  # 'critical', 'high', 'normal'
    ) -> SyncResult:
        """Push sync event with backpressure handling"""

        # Check capacity
        if not self.can_accept_sync(priority):
            # Backpressure: reject non-critical syncs
            if priority != 'critical':
                return self._apply_backpressure(from_agent, priority)

            # Critical sync + queue full: evict lowest priority
            self._evict_lowest_priority()

        # Accept sync
        self.queue.append((priority, message, datetime.now()))
        return SyncResult(accepted=True, queue_depth=len(self.queue))

    def _apply_backpressure(self, from_agent: str, priority: str) -> SyncResult:
        """Apply backpressure: reject sync with exponential backoff"""

        # Calculate retry delay
        retry_count = self.dropped_stats[priority]
        retry_delay_ms = min(
            self.BACKOFF_INITIAL_MS * (2 ** retry_count),
            self.BACKOFF_MAX_MS
        )

        # Check max retries
        if retry_count >= self.BACKOFF_MAX_RETRIES:
            # Drop permanently, alert human
            self._trigger_sync_drop_alert(from_agent, priority, retry_count)
            self.dropped_stats[priority] += 1
            return SyncResult(
                accepted=False,
                backpressure=True,
                retry_after_ms=None,  # No retry - dropped
                dropped=True
            )

        # Return backpressure with retry delay
        self.dropped_stats[priority] += 1
        return SyncResult(
            accepted=False,
            backpressure=True,
            retry_after_ms=retry_delay_ms,
            dropped=False
        )

    def _evict_lowest_priority(self):
        """Evict lowest priority message to make room for critical sync"""

        # Priority order: normal < high < critical
        for priority in ['normal', 'high']:
            for i, (p, msg, ts) in enumerate(self.queue):
                if p == priority:
                    evicted = self.queue.pop(i)
                    self.dropped_stats[priority] += 1
                    logger.info(f'Evicted {priority} sync to make room for critical')
                    return

        # No normal/high to evict - queue is all critical (shouldn't reach here)
        logger.warning(f'Queue overflow: all critical syncs, cannot evict')

    def _trigger_sync_drop_alert(self, from_agent: str, priority: str, retry_count: int):
        """Alert on permanent sync drop (max retries exceeded)"""
        self.alert_manager.on_sync_dropped(
            agent_id=self.agent_id,
            from_agent=from_agent,
            priority=priority,
            retry_count=retry_count,
            severity='WARNING' if priority == 'normal' else 'HIGH'
        )
```

**Base Agent Integration**:

```python
# In base_agent.py
class BaseAgent:
    def __init__(self, agent_id: str):
        self.backpressure_mgr = SyncBackpressureManager(agent_id)

    def receive_memory_sync(self, from_agent: str, message: dict, priority: str):
        """Receive memory sync with backpressure handling"""

        result = self.backpressure_mgr.push_sync_event(from_agent, message, priority)

        if result.backpressure:
            # Send backpressure signal to sender
            self.send_backpressure_signal(
                to_agent=from_agent,
                retry_after_ms=result.retry_after_ms,
                dropped=result.dropped
            )
            return

        # Process sync normally
        self._apply_memory_sync(message)
```

**Success Criteria**:

- Queue overflow handled gracefully (no crashes, no memory leaks)
- Exponential backoff: 100ms → 200ms → 400ms → 800ms (max 5 retries)
- Priority eviction: normal/high dropped before critical
- Alert triggered on permanent drop (max retries exceeded)

---

### M5: Regime Detection Sequencing (Hybrid)

**Purpose**: Enforce ordering (detection → cache → credibility) while maximizing throughput (parallel across regimes).

**RegimeSequencer API**:

```python
class RegimeSequencer:
    """Orchestrate regime detection with hybrid parallelism"""

    STALENESS_TARGET_MIN = 5  # 99th percentile staleness target

    def __init__(self, cache_manager, credibility_engine):
        self.cache_manager = cache_manager
        self.credibility_engine = credibility_engine
        self.regime_flags = {}  # {regime_id: {'detected_today': bool, 'cache_updated': bool}}

    async def run_daily_regime_update(self, regime_ids: List[str]):
        """
        Run daily regime update with hybrid parallelism

        Parallel: Multiple regimes processed simultaneously
        Serial: Within each regime, steps run in order (detect → cache → credibility)
        """

        # Reset flags for today
        for regime_id in regime_ids:
            self.regime_flags[regime_id] = {
                'detected_today': False,
                'cache_updated': False,
                'credibility_ready': False
            }

        # Launch parallel regime updates
        tasks = [
            self._update_regime_sequential(regime_id)
            for regime_id in regime_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check staleness
        self._check_staleness_sla(results)

    async def _update_regime_sequential(self, regime_id: str):
        """
        Update single regime sequentially: detect → cache → credibility
        """

        start_time = datetime.now()

        # Step 1: Regime detection
        regime_data = await self._detect_regime(regime_id)
        self.regime_flags[regime_id]['detected_today'] = True
        logger.info(f'Regime {regime_id} detected at {datetime.now()}')

        # Step 2: Cache update (wait for detection)
        await self._update_cache(regime_id, regime_data)
        self.regime_flags[regime_id]['cache_updated'] = True
        logger.info(f'Regime {regime_id} cache updated at {datetime.now()}')

        # Step 3: Credibility recalculation (wait for cache)
        await self._recalculate_credibility(regime_id)
        self.regime_flags[regime_id]['credibility_ready'] = True

        duration_min = (datetime.now() - start_time).total_seconds() / 60
        logger.info(f'Regime {regime_id} complete in {duration_min:.1f}min')

        return {'regime_id': regime_id, 'duration_min': duration_min, 'success': True}

    async def _detect_regime(self, regime_id: str) -> dict:
        """Run regime detection algorithm"""
        # Market regime detection logic (existing DD-008)
        return await self.regime_detector.detect(regime_id)

    async def _update_cache(self, regime_id: str, regime_data: dict):
        """Update cache with new regime data"""
        cache_key = f'regime_{regime_id}_current'
        await self.cache_manager.set(cache_key, regime_data, ttl_hours=24)

        # Set dependency flag for credibility recalc
        flag_key = f'regime_{regime_id}_updated_today'
        await self.cache_manager.set(flag_key, True, ttl_hours=24)

    async def _recalculate_credibility(self, regime_id: str):
        """Recalculate credibility scores for regime"""

        # Wait for cache flag (should be immediate, defensive check)
        flag_key = f'regime_{regime_id}_updated_today'
        cache_ready = await self.cache_manager.get(flag_key)

        if not cache_ready:
            logger.warning(f'Regime {regime_id} cache not ready, waiting...')
            await self._wait_for_cache_flag(flag_key, timeout_sec=60)

        # Run credibility recalc (existing DD-008)
        await self.credibility_engine.recalculate_for_regime(regime_id)

    async def _wait_for_cache_flag(self, flag_key: str, timeout_sec: int):
        """Wait for cache flag with timeout (defensive)"""
        start = datetime.now()
        while (datetime.now() - start).total_seconds() < timeout_sec:
            if await self.cache_manager.get(flag_key):
                return
            await asyncio.sleep(1)

        # Timeout: alert human
        logger.error(f'Cache flag {flag_key} timeout after {timeout_sec}s')
        self.alert_manager.on_regime_cache_timeout(
            flag_key=flag_key,
            timeout_sec=timeout_sec,
            severity='HIGH'
        )

    def _check_staleness_sla(self, results: List[dict]):
        """Check if staleness SLA met (99th percentile <5min)"""
        durations = [r['duration_min'] for r in results if r.get('success')]
        if not durations:
            return

        p99_duration = sorted(durations)[int(len(durations) * 0.99)]

        if p99_duration > self.STALENESS_TARGET_MIN:
            logger.warning(
                f'Regime staleness SLA miss: {p99_duration:.1f}min '
                f'(target <{self.STALENESS_TARGET_MIN}min)'
            )
            self.alert_manager.on_regime_staleness_sla_miss(
                p99_duration_min=p99_duration,
                target_min=self.STALENESS_TARGET_MIN,
                severity='WARNING'
            )
```

**Credibility Engine Integration**:

```python
# In credibility_engine.py
class CredibilityEngine:
    def __init__(self):
        self.regime_sequencer = RegimeSequencer(
            cache_manager=self.cache_manager,
            credibility_engine=self
        )

    async def run_daily_batch(self):
        """Run daily credibility batch (replaces independent cron)"""

        # Get all active regimes
        regime_ids = await self.get_active_regime_ids()

        # Run hybrid sequenced update
        await self.regime_sequencer.run_daily_regime_update(regime_ids)

    async def recalculate_for_regime(self, regime_id: str):
        """Recalculate credibility scores for specific regime"""
        # Existing credibility recalc logic (DD-008)
        outcomes = await self.get_outcomes_for_regime(regime_id)
        for agent_id in self.get_agents():
            await self.update_credibility_score(agent_id, regime_id, outcomes)
```

**Success Criteria**:

- Regime staleness <5min (99th percentile)
- Zero stale credibility scores (cache flag prevents recalc on old data)
- Parallel throughput: 5 regimes complete in ~5min (not 25min serial)
- Cache timeout alert if flag not set within 60s

---

### Monitoring & Alerts

**Alert Types**:

| Alert                            | Severity | Trigger Condition                                  | Action Required                     |
| -------------------------------- | -------- | -------------------------------------------------- | ----------------------------------- |
| Query Timeout Exhausted          | WARNING  | All fallbacks timeout (L1/L2/cached)               | Investigate database performance    |
| Sync Queue Overflow              | HIGH     | Queue >50 messages, backpressure active            | Scale agent capacity, reduce sync rate |
| Sync Permanently Dropped         | WARNING/HIGH | Sync dropped after 5 retries (WARNING=normal, HIGH=high priority) | Review sync priority, agent load |
| Regime Cache Timeout             | HIGH     | Cache flag not set within 60s                      | Investigate regime detection hang   |
| Regime Staleness SLA Miss        | WARNING  | 99th percentile duration >5min                     | Optimize regime detection algorithm |

**Metrics**:

- `query_fallback_depth_histogram`: Distribution of fallback depths (0/1/2/exhausted)
- `query_timeout_rate`: % queries that exhaust all fallbacks
- `sync_queue_depth_gauge`: Current queue depth per agent
- `sync_backpressure_active_gauge`: Boolean per agent (0/1)
- `sync_dropped_total_counter`: Count by priority (normal/high/critical)
- `regime_update_duration_histogram`: Duration per regime (target <5min)
- `regime_staleness_p99_gauge`: 99th percentile staleness

---

## Open Questions

**Resolved**:

1. ✅ Backpressure retry strategy: Exponential backoff (100ms → 800ms, max 5 retries)
2. ✅ Regime sequencing approach: Hybrid (parallel across regimes, serial within regime)
3. ✅ Query timeout alert behavior: Trigger alerts (severity: WARNING)

**Pending**: None - design is complete, ready for implementation in Phase 3

**Blocking**: No

---

## References

- [Flaw #15: Memory Failure Modes](../design-flaws/resolved/15-failure-modes.md) - C5/A4/M5 resolved by DD-018
- [DD-005: Memory Scalability](DD-005_MEMORY_SCALABILITY_OPTIMIZATION.md) - Query timeout strategy extended with recursion limits
- [DD-002: Event-Driven Sync](DD-002_EVENT_DRIVEN_MEMORY_SYNC.md) - Priority sync extended with backpressure
- [DD-008: Credibility System](DD-008_AGENT_CREDIBILITY_SYSTEM.md) - Daily batch replaced with sequenced hybrid approach
- [Memory System](../architecture/02-memory-system.md) - L1/L2/L3 query paths
- [Credibility System](../implementation/05-credibility-system.md) - Regime detection schedule

---

## Status History

| Date       | Status   | Notes                                  |
| ---------- | -------- | -------------------------------------- |
| 2025-11-18 | Approved | Design finalized, resolves Flaw #15 C5/A4/M5 |

---

## Notes

Memory system failure resilience is critical for production reliability. Without it, system cannot:

- Prevent query timeout hangs (C5 infinite recursion)
- Handle sync queue overflow during debates (A4 backpressure)
- Prevent credibility score staleness (M5 regime sequencing)
- Scale to 100+ agents (failure modes become frequent at scale)

Priority: Critical - blocks Phase 3 memory system deployment, resolves Flaw #15 (all 3 sub-issues).

Implementation: 4 weeks (Week 1: C5, Week 2: A4, Week 3: M5, Week 4: testing)

Dependencies: DD-005, DD-002, DD-008 (all implemented)
