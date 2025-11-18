# L1 Memory Durability

**Status**: Approved
**Date**: 2025-11-18
**Decider(s)**: System Architect
**Related Docs**: [Memory System](../architecture/02-memory-system.md), [Analysis Pipeline](../operations/01-analysis-pipeline.md), [Data Management](../operations/03-data-management.md)
**Related Decisions**: [DD-011 Agent Checkpoint System](DD-011_AGENT_CHECKPOINT_SYSTEM.md), [DD-012 Workflow Pause/Resume Infrastructure](DD-012_WORKFLOW_PAUSE_RESUME.md)

---

## Context

L1 working memory (Redis) has hours-long TTL, insufficient for multi-day pauses. When agents pause during analysis (overnight, weekends, extended human unavailability), L1 cache expires before resume. On resume, agents must re-fetch API data (wasting quota), re-parse documents (wasting time), and re-calculate interim results.

**Current State**:

- L1 TTL: Hours (exact duration undefined)
- Checkpoint saves L1 dump to PostgreSQL (DD-011) but no restore procedure
- No consistency verification between checkpoint and restored L1
- DD-012 extends TTL (24h → 14d) during pause but lacks restore/verification

**Why Address Now**:

- Blocks multi-day pause capability (overnight 8h+, weekend 48h+, vacation)
- DD-012 partially addresses via TTL extension but incomplete without restore
- Production deployment requires zero duplicate work on resume
- Phase 2 implementation requires reliable pause/resume for failure recovery

**Example Impact**: Strategy Analyst analyzing AAPL pauses Day 5 at 2:47 PM (Koyfin quota exhausted). Human resolves quota Day 6 at 9:00 AM (18 hours later). L1 expired overnight → agent re-fetches Koyfin data (quota waste), re-parses 10-K (time waste), re-calculates partial ROI (redundant work).

---

## Decision

**Implement dual-layer per-agent L1 snapshot system with hybrid trigger strategy: Redis secondary (fast recovery) + PostgreSQL checkpoint (durability), triggered by checkpoint events during active analysis and forced dual snapshot on pause.**

System provides:

- **L1TTLManager**: Dynamic TTL (24h active → 14d paused)
- **L1CacheSnapshotter**: Per-agent snapshots to Redis secondary + PostgreSQL
- **L1CacheRestorer**: Restore from snapshot with type preservation (<5s Redis / <30s PostgreSQL)
- **ConsistencyVerifier**: Hash-based validation on restore
- **DualRecoveryStrategy**: Fallback chain (L1 → Redis secondary → PostgreSQL)

---

## Options Considered

### Option 1: TTL Extension Only (Current DD-012 Approach)

**Description**: Extend L1 TTL from 24h → 14d during pause, no additional persistence.

**Pros**:

- Simple implementation
- Minimal overhead
- No additional storage

**Cons**:

- No recovery from Redis crashes
- No restore procedure defined
- No consistency checks
- Vulnerable to Redis evictions during memory pressure

**Estimated Effort**: Low (1 week)

---

### Option 2: Always Persist to PostgreSQL

**Description**: Immediately persist all L1 changes to PostgreSQL, no Redis secondary.

**Pros**:

- Maximum durability
- Single storage location
- Survives all Redis failures

**Cons**:

- Slow restore (<30s typical)
- Unnecessary overhead during active analysis
- PostgreSQL latency for every L1 update
- Not suitable for high-frequency working memory updates

**Estimated Effort**: Medium (2 weeks)

---

### Option 3: Dual-Layer Snapshots (CHOSEN)

**Description**: Per-agent snapshots to Redis secondary (fast access) + PostgreSQL checkpoint (durability). Hybrid trigger: piggyback on DD-011 checkpoint events during analysis, force dual snapshot on pause.

**Pros**:

- Fast restore (<5s Redis fallback)
- Crash recovery (PostgreSQL fallback)
- Zero duplicate work on resume
- Minimal overhead (Redis-to-Redis copy during analysis)
- Maximum durability for long pauses

**Cons**:

- Storage overhead (2x Redis + PostgreSQL)
- Restore complexity (deserialization, type preservation)
- Snapshot overhead on checkpoint events (mitigated by Redis speed)

**Estimated Effort**: Medium (2 weeks)

---

### Option 4: No Persistence (Status Quo)

**Description**: Rely only on L1 TTL extension, accept re-work on expiration.

**Pros**:

- No implementation needed
- No storage overhead

**Cons**:

- Unacceptable work/quota waste
- Poor user experience (long re-work delays)
- Blocks production deployment

**Estimated Effort**: None

---

## Rationale

**Option 3 (dual-layer) chosen** because:

1. **Balances speed and durability**: Redis secondary provides <5s restore for typical cases, PostgreSQL fallback ensures no data loss on Redis crashes.

2. **Minimal overhead during analysis**: Piggyback on DD-011 checkpoint events (already saving to PostgreSQL). Snapshot to Redis secondary is Redis-to-Redis copy (fast, <100ms).

3. **Zero duplicate work**: Agents resume from exact L1 state, never re-fetch API data or re-parse documents. Critical for quota-limited APIs (Koyfin, Bloomberg).

4. **Hybrid trigger strategy**:
   - During analysis: Snapshot to Redis secondary only (fast)
   - On pause: Force dual snapshot to Redis + PostgreSQL (durability)
   - Optimizes for common case (analysis continues) while protecting long pauses

5. **Unblocks Flaw #25**: All 3 sub-issues resolved:
   - D1: L1TTLManager extends TTL 24h → 14d
   - D2: L1CacheRestorer with restore procedure
   - D3: ConsistencyVerifier with hash validation

**Acceptable tradeoffs**:

- Storage overhead: 2x Redis + PostgreSQL justified by API quota savings
- Restore complexity: abstracted behind clean AgentMemory interface
- Snapshot overhead: negligible given Redis-to-Redis speed (~100ms per checkpoint)

---

## Consequences

### Positive Impacts

- ✅ Zero duplicate work on resume (agents continue from exact state)
- ✅ API quota savings (no re-fetch on resume)
- ✅ Fast resume (<5s typical, <30s worst-case)
- ✅ Resilient to mid-analysis crashes (Redis secondary survives most failures)
- ✅ Multi-day pause support (up to 14 days)
- ✅ Unblocks production deployment (reliable pause/resume)

### Negative Impacts / Tradeoffs

- ❌ Storage overhead: 2x Redis for secondary + PostgreSQL checkpoint
  - Estimate: ~100 KB per agent × 5 agents/stock × 200 stocks = 100 MB total
  - Mitigated by: TTL-based cleanup (14d max), constant memory per agent

- ❌ Restore complexity: deserialization, type preservation, consistency verification
  - Mitigated by: Clean abstraction (L1CacheRestorer class), comprehensive testing

- ❌ Snapshot overhead: Redis-to-Redis copy on checkpoint events
  - Mitigated by: Fast Redis operations (~100ms), only on checkpoint boundaries

- ❌ Consistency verification latency: hash computation on restore
  - Mitigated by: Parallel restore + verification, <1s overhead

### Affected Components

**New Components**:

- `L1TTLManager` class (dynamic TTL management)
- `L1CacheSnapshotter` class (snapshot creation)
- `L1CacheRestorer` class (restore with type preservation)
- `ConsistencyVerifier` class (hash-based validation)
- `DualRecoveryStrategy` class (fallback chain)
- Redis keys: `fas:l1_snapshot:{agent_id}:{key}`, `fas:l1_snapshot_meta:{agent_id}`
- PostgreSQL: extend `agent_checkpoints` table (add `l1_snapshot`, `l1_snapshot_hash`)

**Modified Components**:

- `CheckpointManager` (DD-011): Hook L1 snapshot on checkpoint save
- `PauseManager` (DD-012): Trigger L1TTLManager + full dual snapshot on pause
- `AgentMemory`: Expose L1 snapshot/restore interface
- `base_agent.py`: Per-agent L1 key namespacing

**Documentation Updates**:

- `02-memory-system.md`: Add L1 durability section
- `01-analysis-pipeline.md`: Add L1 restore to pause/resume workflow
- `03-data-management.md`: Add L1 snapshot retention policy

---

## Implementation Notes

### Component 1: L1TTLManager

**Purpose**: Manage dynamic TTL for L1 working memory based on analysis state.

```python
class L1TTLManager:
    """Manage L1 TTL for paused vs. active analyses"""

    ACTIVE_TTL_HOURS = 24   # Active analysis
    PAUSED_TTL_DAYS = 14    # Paused analysis (per DD-012)

    def extend_ttl_on_pause(self, agent_id: str):
        """Extend L1 TTL when analysis pauses"""
        l1_pattern = f"L1:{agent_id}:working:*"
        l1_keys = redis.keys(l1_pattern)

        for key in l1_keys:
            redis.expire(key, self.PAUSED_TTL_DAYS * 24 * 3600)

        logger.info(f"Extended L1 TTL to {self.PAUSED_TTL_DAYS}d for {agent_id}")

    def restore_active_ttl_on_resume(self, agent_id: str):
        """Restore normal TTL when analysis resumes"""
        l1_pattern = f"L1:{agent_id}:working:*"
        l1_keys = redis.keys(l1_pattern)

        for key in l1_keys:
            redis.expire(key, self.ACTIVE_TTL_HOURS * 3600)

        logger.info(f"Restored L1 TTL to {self.ACTIVE_TTL_HOURS}h for {agent_id}")
```

### Component 2: L1CacheSnapshotter

**Purpose**: Create per-agent L1 snapshots to Redis secondary and/or PostgreSQL.

**Snapshot Strategy (Hybrid)**:

1. **During active analysis**: Piggyback on DD-011 checkpoint events
   - Snapshot to Redis secondary only (fast)
   - Enables mid-analysis crash recovery
   - Minimal overhead (Redis-to-Redis copy)

2. **On pause**: Force full dual snapshot
   - Snapshot to both Redis secondary AND PostgreSQL
   - Extend TTL: 24h → 14d
   - Maximum durability for long pause

3. **Storage policy**:
   - Latest snapshot only (overwrite on new checkpoint)
   - Constant memory usage per agent
   - TTL matches L1: 24h active / 14d paused
   - PostgreSQL checkpoint persists permanently (audit trail)

```python
class L1CacheSnapshotter:
    """Snapshot L1 working memory to durable storage"""

    def snapshot_on_checkpoint(self, agent_id: str, checkpoint_id: UUID,
                               dual_write: bool = False):
        """Save L1 state on checkpoint (piggyback)"""

        # Get all L1 keys for this agent
        l1_pattern = f"L1:{agent_id}:working:*"
        l1_keys = redis.keys(l1_pattern)

        # Dump to structured format with type preservation
        snapshot = {}
        for key in l1_keys:
            clean_key = key.replace(f"L1:{agent_id}:working:", "")
            value_type = redis.type(key)

            snapshot[clean_key] = {
                'value': self._serialize_by_type(key, value_type),
                'type': value_type,
                'ttl': redis.ttl(key)
            }

        # Compute hash for consistency verification
        snapshot_hash = self._compute_snapshot_hash(snapshot)

        # Always save to Redis secondary (fast recovery)
        redis.setex(
            f"fas:l1_snapshot:{agent_id}",
            14 * 24 * 3600,  # 14-day TTL
            json.dumps(snapshot)
        )
        redis.setex(
            f"fas:l1_snapshot_meta:{agent_id}",
            14 * 24 * 3600,
            json.dumps({
                'timestamp': datetime.utcnow().isoformat(),
                'hash': snapshot_hash,
                'checkpoint_id': str(checkpoint_id),
                'key_count': len(l1_keys)
            })
        )

        # Optionally save to PostgreSQL (on pause only)
        if dual_write:
            db.execute(
                "UPDATE agent_checkpoints "
                "SET l1_snapshot = %s, l1_snapshot_hash = %s "
                "WHERE id = %s",
                (json.dumps(snapshot), snapshot_hash, checkpoint_id)
            )

        logger.info(f"L1 snapshot saved: {len(l1_keys)} keys for {agent_id}")

        return snapshot_hash

    def _serialize_by_type(self, key: str, value_type: str):
        """Serialize Redis value based on type"""
        if value_type == 'string':
            return redis.get(key)
        elif value_type == 'list':
            return redis.lrange(key, 0, -1)
        elif value_type == 'hash':
            return redis.hgetall(key)
        elif value_type == 'set':
            return list(redis.smembers(key))
        elif value_type == 'zset':
            return redis.zrange(key, 0, -1, withscores=True)
        else:
            raise ValueError(f"Unsupported Redis type: {value_type}")

    def _compute_snapshot_hash(self, snapshot: dict) -> str:
        """Compute SHA256 hash of snapshot for consistency verification"""
        import hashlib

        # Sort keys for deterministic hash
        sorted_keys = sorted(snapshot.keys())
        hash_input = json.dumps({k: snapshot[k] for k in sorted_keys}, sort_keys=True)

        return hashlib.sha256(hash_input.encode()).hexdigest()
```

### Component 3: L1CacheRestorer

**Purpose**: Restore L1 working memory from snapshot with type preservation.

```python
class L1CacheRestorer:
    """Restore L1 working memory from snapshot"""

    def restore_from_snapshot(self, agent_id: str, analysis_id: UUID,
                             agent_type: str) -> bool:
        """Restore L1 cache from most recent snapshot"""

        # Try Redis secondary first (fast <5s)
        snapshot_json = redis.get(f"fas:l1_snapshot:{agent_id}")
        meta_json = redis.get(f"fas:l1_snapshot_meta:{agent_id}")

        if snapshot_json and meta_json:
            snapshot = json.loads(snapshot_json)
            meta = json.loads(meta_json)
            logger.info(f"Restoring from Redis secondary for {agent_id}")
        else:
            # Fallback to PostgreSQL (<30s)
            logger.warning(f"Redis secondary miss, falling back to PostgreSQL")
            checkpoint = db.query(
                "SELECT l1_snapshot, l1_snapshot_hash FROM agent_checkpoints "
                "WHERE analysis_id = %s AND agent_type = %s "
                "ORDER BY checkpoint_time DESC LIMIT 1",
                (analysis_id, agent_type)
            ).one()

            if not checkpoint or not checkpoint['l1_snapshot']:
                logger.warning(f"No L1 snapshot found for {agent_id}")
                return False

            snapshot = json.loads(checkpoint['l1_snapshot'])
            meta = {'hash': checkpoint['l1_snapshot_hash']}

        # Clear existing L1 keys to avoid conflicts
        l1_pattern = f"L1:{agent_id}:working:*"
        existing_keys = redis.keys(l1_pattern)
        if existing_keys:
            logger.info(f"Clearing {len(existing_keys)} stale L1 keys")
            redis.delete(*existing_keys)

        # Restore keys with type preservation
        restored_count = 0
        for clean_key, data in snapshot.items():
            full_key = f"L1:{agent_id}:working:{clean_key}"

            # Restore value based on type
            if data['type'] == 'string':
                redis.set(full_key, data['value'])
            elif data['type'] == 'list':
                redis.rpush(full_key, *data['value'])
            elif data['type'] == 'hash':
                redis.hset(full_key, mapping=data['value'])
            elif data['type'] == 'set':
                redis.sadd(full_key, *data['value'])
            elif data['type'] == 'zset':
                redis.zadd(full_key, dict(data['value']))

            # Set TTL (24 hours for resumed analysis)
            redis.expire(full_key, 24 * 3600)

            restored_count += 1

        logger.info(f"L1 restored: {restored_count} keys for {agent_id}")

        # Verify consistency
        self._verify_restore_consistency(agent_id, snapshot, meta['hash'])

        return True

    def _verify_restore_consistency(self, agent_id: str, original_snapshot: dict,
                                   expected_hash: str):
        """Verify restored L1 matches checkpoint"""

        # Get all restored keys
        l1_pattern = f"L1:{agent_id}:working:*"
        restored_keys = redis.keys(l1_pattern)

        # Check count matches
        expected_count = len(original_snapshot)
        actual_count = len(restored_keys)

        if expected_count != actual_count:
            raise ConsistencyError(
                f"L1 restore incomplete: expected {expected_count} keys, "
                f"got {actual_count}"
            )

        # Compute hash of restored data
        restored_snapshot = {}
        for key in restored_keys:
            clean_key = key.replace(f"L1:{agent_id}:working:", "")
            value_type = redis.type(key)
            restored_snapshot[clean_key] = {
                'value': self._serialize_by_type(key, value_type),
                'type': value_type
            }

        # Compare hashes
        import hashlib
        sorted_keys = sorted(restored_snapshot.keys())
        hash_input = json.dumps({k: restored_snapshot[k] for k in sorted_keys},
                               sort_keys=True)
        restored_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        if restored_hash != expected_hash:
            raise ConsistencyError(
                f"L1 restore hash mismatch: expected {expected_hash}, "
                f"got {restored_hash}"
            )

        logger.info(f"L1 consistency verified for {agent_id}")
```

### Component 4: ConsistencyVerifier

**Purpose**: Hash-based validation on restore to detect corruption or partial failures.

**Detects**:

- Partial restore failures (some keys restored, others failed)
- Stale L1 data (old data mixed with restored data)
- Checkpoint corruption (JSONB blob corrupted, deserializes incorrectly)

**Algorithm**:

- SHA256 hash of sorted L1 keys + values
- Compare restored hash with snapshot metadata hash
- Fail fast if mismatch detected

(Implementation integrated into L1CacheRestorer above)

### Component 5: DualRecoveryStrategy

**Purpose**: Fallback chain for agent state recovery.

```python
class DualRecoveryStrategy:
    """Try L1 → Redis secondary → PostgreSQL in order"""

    def recover_agent_state(self, agent_id: str, analysis_id: UUID,
                           agent_type: str) -> str:
        """Recover agent state with fallback chain"""

        # Strategy 1: L1 still exists (fastest)
        l1_keys = redis.keys(f"L1:{agent_id}:working:*")
        if l1_keys:
            logger.info(f"L1 cache still exists for {agent_id} (fast path)")
            # Restore active TTL
            self.ttl_manager.restore_active_ttl_on_resume(agent_id)
            return 'l1_existing'

        # Strategy 2: Redis secondary (fast)
        redis_snapshot = redis.get(f"fas:l1_snapshot:{agent_id}")
        if redis_snapshot:
            logger.info(f"Restoring from Redis secondary for {agent_id}")
            self.l1_restorer.restore_from_snapshot(agent_id, analysis_id, agent_type)
            return 'redis_secondary'

        # Strategy 3: PostgreSQL checkpoint (slowest)
        logger.info(f"Restoring from PostgreSQL checkpoint for {agent_id}")
        self.l1_restorer.restore_from_snapshot(agent_id, analysis_id, agent_type)
        return 'postgresql_checkpoint'
```

### Redis Data Structures

```
# L1 snapshot keys (per-agent)
fas:l1_snapshot:{agent_id} = <JSONB snapshot>
fas:l1_snapshot_meta:{agent_id} = {timestamp, hash, checkpoint_id, key_count}

# Example:
fas:l1_snapshot:strategy_analyst_123 = {
    "current_subtask": {"value": "ma_review", "type": "string", "ttl": 86400},
    "aapl_historical_roi": {"value": [0.15, 0.18, 0.12], "type": "list", "ttl": 86400},
    "capital_allocation_score": {"value": 0.75, "type": "string", "ttl": 86400}
}

fas:l1_snapshot_meta:strategy_analyst_123 = {
    "timestamp": "2025-11-18T14:47:00Z",
    "hash": "a3f8d9c...",
    "checkpoint_id": "550e8400-e29b-41d4-a716-446655440000",
    "key_count": 3
}
```

### PostgreSQL Schema Extension

```sql
-- Extend existing agent_checkpoints table from DD-011
ALTER TABLE agent_checkpoints ADD COLUMN l1_snapshot JSONB;
ALTER TABLE agent_checkpoints ADD COLUMN l1_snapshot_hash TEXT;

-- Index for snapshot lookup
CREATE INDEX idx_checkpoint_l1_snapshot ON agent_checkpoints(analysis_id, agent_type)
    WHERE l1_snapshot IS NOT NULL;
```

### Integration Points

1. **CheckpointManager (DD-011)**:
   - Hook into checkpoint save events
   - Trigger `L1CacheSnapshotter.snapshot_on_checkpoint(dual_write=False)`
   - Include L1 snapshot metadata in checkpoint record

2. **PauseManager (DD-012)**:
   - On pause: Call `L1TTLManager.extend_ttl_on_pause()` + `L1CacheSnapshotter.snapshot_on_checkpoint(dual_write=True)`
   - On resume: Call `L1CacheRestorer.restore_from_snapshot()` + `ConsistencyVerifier` (integrated)

3. **AgentMemory**:
   - Expose L1 snapshot/restore interface
   - Per-agent L1 key namespacing: `L1:{agent_id}:working:*`

### Testing Requirements

- **Save/Restore Round-Trip**: Snapshot → restore → verify identical state
- **Type Preservation**: Verify all Redis types (string, list, hash, set, zset) preserved
- **Consistency Verification**: Inject corruption, verify detection
- **Fast Recovery**: Restore from Redis secondary in <5s (performance test)
- **Fallback**: Redis secondary miss → PostgreSQL fallback in <30s
- **Dual Recovery**: Test all 3 paths (L1 existing, Redis secondary, PostgreSQL)
- **TTL Extension**: Verify 24h → 14d transition on pause

### Rollback Strategy

If L1 durability system has critical bugs:

1. Disable L1 snapshot/restore (agents accept re-work on resume)
2. Fallback to DD-012 TTL extension only (partial protection)
3. Fix bug, re-enable full durability
4. No data loss: system degrades gracefully to partial protection

**Estimated Implementation Effort**: 2 weeks

- Week 1: L1TTLManager, L1CacheSnapshotter, Redis secondary snapshot
- Week 2: L1CacheRestorer, ConsistencyVerifier, DualRecoveryStrategy, testing

**Dependencies**:

- DD-011 checkpoint system (prerequisite - implemented)
- DD-012 pause/resume infrastructure (prerequisite - implemented)
- Redis infrastructure (exists)
- PostgreSQL infrastructure (exists)

---

## Open Questions

**Resolved** (from design discussions):

1. ✅ Snapshot granularity: Per-agent (follows DD-011 checkpoint model)
2. ✅ Snapshot trigger: Hybrid (piggyback on checkpoints + force on pause)
3. ✅ Storage location: Dual-layer (Redis secondary + PostgreSQL)
4. ✅ Restore performance: <5s Redis / <30s PostgreSQL
5. ✅ Consistency verification: SHA256 hash comparison
6. ✅ TTL during pause: 14 days (per DD-012 timeout policy)

**Pending**: None - design is complete, ready for implementation

**Blocking**: No

---

## References

- [Flaw #25: Working Memory Insufficient for Long Pauses](../design-flaws/active/25-working-memory-durability.md) - resolved by DD-016
- [DD-011: Agent Checkpoint System](DD-011_AGENT_CHECKPOINT_SYSTEM.md) - prerequisite, provides checkpoint infrastructure
- [DD-012: Workflow Pause/Resume Infrastructure](DD-012_WORKFLOW_PAUSE_RESUME.md) - prerequisite, provides pause/resume triggers
- [Memory System Architecture](../architecture/02-memory-system.md) - L1/L2/L3 context
- Redis Data Types Documentation: <https://redis.io/docs/data-types/>
- PostgreSQL JSONB Documentation: <https://www.postgresql.org/docs/current/datatype-json.html>

---

## Status History

| Date       | Status   | Notes                                                   |
| ---------- | -------- | ------------------------------------------------------- |
| 2025-11-18 | Approved | Design finalized, resolves Flaw #25 (D1/D2/D3) |

---

## Notes

L1 memory durability is critical for production-grade pause/resume. Without it, system cannot:

- Resume analyses after overnight pauses without duplicate work
- Recover from mid-analysis crashes (L1 lost = restart from checkpoint)
- Efficiently handle API quota limits (re-fetch wastes quota)
- Provide acceptable user experience (long re-work delays)

Priority: High - blocks Phase 2 production readiness, resolves last sub-issue in Flaw #25.
