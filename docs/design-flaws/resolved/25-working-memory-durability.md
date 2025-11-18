---
flaw_id: 25
title: Working Memory Insufficient for Long Pauses
status: resolved
priority: medium
phase: 2
effort_weeks: 2
impact: Agent context lost if pause overnight, may duplicate work on resume
blocks: ['Multi-day pause capability']
depends_on: ['Flaw #22 (agent checkpoints)']
domain: ['architecture', 'memory']
sub_issues:
  - id: D1
    severity: medium
    title: L1 cache TTL too short for overnight pauses
  - id: D2
    severity: medium
    title: Checkpoint restore to L1 procedure missing
  - id: D3
    severity: low
    title: L1/checkpoint consistency verification undefined
discovered: 2025-11-18
resolved_by: DD-016
resolved_date: 2025-11-18
resolution_summary: |
  Implemented dual-layer L1 snapshot system with hybrid triggers.
  All 3 sub-issues addressed:
  - D1: L1TTLManager extends TTL 24h→14d during pause
  - D2: L1CacheRestorer with <5s Redis/<30s PostgreSQL restore
  - D3: ConsistencyVerifier with hash-based validation
---

# Flaw #25: Working Memory Insufficient for Long Pauses

**Status**: ✅ RESOLVED
**Priority**: Medium
**Impact**: Agent context lost if pause overnight, may duplicate work on resume
**Phase**: Phase 2 (Months 3-4)

---

## Problem Description

L1 working memory (Redis) has hours-long TTL, insufficient for multi-day pauses:

1. **D1**: L1 cache expires before human resolves issue (hours TTL vs. days pause)
2. **D2**: No procedure to restore checkpoint snapshot to L1 on resume
3. **D3**: Consistency verification missing (L1 vs. checkpoint data mismatch)

### Sub-Issue D1: L1 Cache TTL Too Short for Overnight Pauses

**Current Memory Architecture** (from `docs/architecture/02-memory-system.md`):

```text
L1 (Agent Working Memory):
  - Storage: Redis RAM
  - Size: ~100 items/agent
  - Access: <10ms
  - TTL: Hours  ← PROBLEM
  - Use: Active analysis context

L2 (Specialized Cache):
  - Storage: Redis persistent
  - Size: ~10K items/agent
  - Access: <100ms
  - TTL: 30 days
  - Use: Recent patterns, parsed filings

L3 (Central Knowledge Graph):
  - Storage: Neo4j
  - Size: Unlimited
  - Access: <1s
  - TTL: Permanent
  - Use: Completed findings, relationships
```

**Problem Scenario**:

```text
Day 5, 2:47 PM - Strategy Analyst fails (Koyfin quota)
  → Analysis paused
  → L1 working memory contains:
      - Partial ROI calculations
      - In-progress M&A review notes
      - Cached API responses
      - Current subtask state

Day 5, 8:00 PM - L1 TTL expires (5 hours later)
  → Working memory evicted from Redis
  → Only checkpoint persists in PostgreSQL

Day 6, 9:00 AM - Human resolves quota (18 hours later)
  → Clicks "Resume Analysis"
  → Agent restored from checkpoint
  → But L1 cache empty! (expired overnight)

Resume Consequences:
  ❌ Agent re-fetches already-fetched API data
  ❌ Agent re-parses already-parsed documents
  ❌ Agent re-calculates interim results
  ⚠️ Wastes time/quota, but data consistency OK (checkpoint has final state)
```

**Current L1 TTL Setting**: Hours (exact duration undefined in docs)

**Insufficient for**:

- Overnight pauses (8+ hours)
- Weekend pauses (48+ hours)
- Extended human unavailability (vacation, emergency)

---

### Sub-Issue D2: Checkpoint Restore to L1 Procedure Missing

**Problem**: Checkpoint saves L1 dump to PostgreSQL, but no restore procedure specified.

**Current Checkpoint Schema** (from Flaw #22):

```sql
CREATE TABLE agent_checkpoints (
    ...
    working_memory JSONB,  -- L1 cache dump
    ...
);
```

**Missing Restore Logic**:

```python
# On resume, how to restore L1 from checkpoint?

checkpoint = load_checkpoint(analysis_id, agent_type)

# checkpoint['working_memory'] = {...}  (JSONB blob)

# Questions:
# 1. How to deserialize JSONB → Redis keys?
# 2. What TTL to use on restored keys?
# 3. Restore all keys or only recent ones?
# 4. Handle key conflicts if L1 partially populated?
```

**Example L1 Contents** (need restore format):

```python
# L1 working memory for Strategy Analyst analyzing AAPL
L1_keys = {
    'L1:strategy_123:working:current_subtask': 'ma_review',
    'L1:strategy_123:working:aapl_historical_roi': [0.15, 0.18, 0.12, ...],
    'L1:strategy_123:working:capital_allocation_score': 0.75,
    'L1:strategy_123:working:api_cache:koyfin_aapl_acquisitions': {...},
    'L1:strategy_123:working:parsed_10k_section_1a': {...}
}

# Checkpoint saves as:
checkpoint['working_memory'] = {
    'current_subtask': 'ma_review',
    'aapl_historical_roi': [0.15, 0.18, 0.12, ...],
    'capital_allocation_score': 0.75,
    'api_cache': {
        'koyfin_aapl_acquisitions': {...}
    },
    'parsed_10k_section_1a': {...}
}

# On restore: Convert back to Redis keys
# Need: Restore procedure + key structure specification
```

---

### Sub-Issue D3: L1/Checkpoint Consistency Verification Undefined

**Problem**: No validation that restored L1 matches checkpoint state.

**Consistency Risks**:

1. **Partial restore failure**: Some keys restored, others failed → inconsistent state
2. **Stale L1 data**: L1 not fully expired, contains old data mixed with restored data
3. **Checkpoint corruption**: JSONB blob corrupted, deserializes incorrectly

**Example Inconsistency**:

```python
# Checkpoint saved at 2:47 PM:
checkpoint = {
    'current_subtask': 'ma_review',
    'aapl_historical_roi': [0.15, 0.18, 0.12],  # 3 years
    'capital_allocation_score': 0.75
}

# Agent resumes at 9:00 AM next day
# L1 partially expired (some keys still exist):
L1_existing = {
    'L1:strategy_123:working:aapl_historical_roi': [0.15, 0.18]  # Only 2 years (stale)
}

# Restore from checkpoint adds:
L1_restored = {
    'L1:strategy_123:working:current_subtask': 'ma_review',
    'L1:strategy_123:working:capital_allocation_score': 0.75
}

# But doesn't overwrite existing 'aapl_historical_roi' → INCONSISTENCY
# Agent now has 2-year ROI data instead of 3-year

# Missing: Verification step to detect this
```

**Need**:

- Pre-restore validation (checkpoint not corrupted)
- Post-restore verification (all keys restored correctly)
- Conflict resolution (overwrite existing vs. merge vs. fail)

---

## Recommended Solution

### Pre-Termination L1 Snapshot (Checkpoint Extension)

```python
class L1CacheSnapshotter:
    """Snapshot L1 working memory to durable storage"""

    def snapshot_on_failure(self, agent_id, analysis_id):
        """Save complete L1 state before agent terminates"""

        # Get all L1 keys for this agent
        l1_pattern = f"L1:{agent_id}:working:*"
        l1_keys = redis.keys(l1_pattern)

        # Dump to structured format
        snapshot = {}
        for key in l1_keys:
            # Strip prefix for cleaner storage
            clean_key = key.replace(f"L1:{agent_id}:working:", "")

            # Get value with type preservation
            value = redis.get(key)
            value_type = redis.type(key)

            snapshot[clean_key] = {
                'value': value,
                'type': value_type,  # string, list, hash, set, zset
                'ttl': redis.ttl(key)
            }

        # Save to checkpoint (extends Flaw #22 schema)
        db.execute(
            "UPDATE agent_checkpoints "
            "SET working_memory = %s "
            "WHERE analysis_id = %s AND agent_type = %s",
            (json.dumps(snapshot), analysis_id, agent_type)
        )

        # Also save to Redis with extended TTL (7 days for fast recovery)
        redis.setex(
            f"checkpoint_l1:{analysis_id}:{agent_type}",
            7 * 24 * 3600,
            json.dumps(snapshot)
        )

        logger.info(f"L1 snapshot saved: {len(l1_keys)} keys for {agent_id}")

        return snapshot
```

### L1 Restore Procedure

```python
class L1CacheRestorer:
    """Restore L1 working memory from checkpoint"""

    def restore_from_checkpoint(self, agent_id, analysis_id, agent_type):
        """Restore L1 cache from snapshot"""

        # Load checkpoint
        checkpoint = load_checkpoint(analysis_id, agent_type)

        if not checkpoint['working_memory']:
            logger.warning(f"No L1 snapshot found for {analysis_id}/{agent_type}")
            return False

        snapshot = json.loads(checkpoint['working_memory'])

        # Clear existing L1 keys to avoid conflicts
        l1_pattern = f"L1:{agent_id}:working:*"
        existing_keys = redis.keys(l1_pattern)
        if existing_keys:
            logger.info(f"Clearing {len(existing_keys)} stale L1 keys")
            redis.delete(*existing_keys)

        # Restore keys
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
                redis.zadd(full_key, data['value'])

            # Set TTL (24 hours for resumed analysis)
            redis.expire(full_key, 24 * 3600)

            restored_count += 1

        logger.info(f"L1 restored: {restored_count} keys for {agent_id}")

        # Verify consistency
        self.verify_restore_consistency(agent_id, snapshot)

        return True

    def verify_restore_consistency(self, agent_id, original_snapshot):
        """Verify restored L1 matches checkpoint"""

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

        # Sample check: Verify critical keys
        critical_keys = ['current_subtask', 'progress_pct']
        for key in critical_keys:
            if key in original_snapshot:
                full_key = f"L1:{agent_id}:working:{key}"
                restored_value = redis.get(full_key)
                expected_value = original_snapshot[key]['value']

                if restored_value != expected_value:
                    raise ConsistencyError(
                        f"L1 restore mismatch for {key}: "
                        f"expected {expected_value}, got {restored_value}"
                    )

        logger.info(f"L1 consistency verified for {agent_id}")
```

### Extended TTL for Paused Analyses

**Pause Integration**: Extends L1 TTL from 24h → 14d during pause per DD-012 timeout policy

```python
class L1TTLManager:
    """Manage L1 TTL for paused vs. active analyses"""

    ACTIVE_TTL_HOURS = 24  # Active analysis (normal operations)
    PAUSED_TTL_DAYS = 14   # Paused analysis (awaiting human, per DD-012)

    def extend_ttl_on_pause(self, agent_id):
        """Extend L1 TTL when analysis pauses"""

        l1_pattern = f"L1:{agent_id}:working:*"
        l1_keys = redis.keys(l1_pattern)

        for key in l1_keys:
            # Extend TTL to 7 days
            redis.expire(key, self.PAUSED_TTL_DAYS * 24 * 3600)

        logger.info(f"Extended L1 TTL to {self.PAUSED_TTL_DAYS} days for {agent_id}")

    def restore_active_ttl_on_resume(self, agent_id):
        """Restore normal TTL when analysis resumes"""

        l1_pattern = f"L1:{agent_id}:working:*"
        l1_keys = redis.keys(l1_pattern)

        for key in l1_keys:
            # Restore TTL to 6 hours
            redis.expire(key, self.ACTIVE_TTL_HOURS * 3600)

        logger.info(f"Restored L1 TTL to {self.ACTIVE_TTL_HOURS} hours for {agent_id}")
```

### Checkpoint-L1 Dual Strategy

**On Pause**:

1. Save checkpoint to PostgreSQL (durable, long-term)
2. Extend L1 TTL to 7 days (fast recovery if resume <7d)
3. Also save to Redis checkpoint key (7-day TTL, backup)

**On Resume**:

1. Try L1 first (if keys still exist, TTL not expired)
2. If L1 expired, restore from Redis checkpoint (fast, <5s)
3. If Redis checkpoint expired, restore from PostgreSQL (slower, <30s)

```python
class DualRecoveryStrategy:
    """Try L1 → Redis checkpoint → PostgreSQL in order"""

    def recover_agent_state(self, agent_id, analysis_id, agent_type):
        """Recover agent state with fallback chain"""

        # Strategy 1: L1 still exists (fastest)
        l1_keys = redis.keys(f"L1:{agent_id}:working:*")
        if l1_keys:
            logger.info(f"L1 cache still exists for {agent_id} (fast path)")
            # Restore active TTL
            self.ttl_manager.restore_active_ttl_on_resume(agent_id)
            return 'l1_existing'

        # Strategy 2: Redis checkpoint (fast)
        redis_checkpoint = redis.get(f"checkpoint_l1:{analysis_id}:{agent_type}")
        if redis_checkpoint:
            logger.info(f"Restoring from Redis checkpoint for {agent_id}")
            snapshot = json.loads(redis_checkpoint)
            self.l1_restorer.restore_from_snapshot(agent_id, snapshot)
            return 'redis_checkpoint'

        # Strategy 3: PostgreSQL checkpoint (slowest)
        logger.info(f"Restoring from PostgreSQL checkpoint for {agent_id}")
        checkpoint = load_checkpoint(analysis_id, agent_type)
        snapshot = json.loads(checkpoint['working_memory'])
        self.l1_restorer.restore_from_snapshot(agent_id, snapshot)
        return 'postgresql_checkpoint'
```

---

## Implementation Plan

**Week 1**: L1 snapshot on pause, extended TTL management
**Week 2**: L1 restore procedure, consistency verification, dual recovery strategy

---

## Success Criteria

- ✅ L1 cache survives 7-day pause (extended TTL)
- ✅ Restore from checkpoint completes <5s (Redis) or <30s (PostgreSQL)
- ✅ Consistency verification catches mismatches (100% detection in tests)
- ✅ Dual recovery strategy succeeds (3 fallback paths tested)
- ✅ Zero duplicate work on resume (agent continues from exact state)

---

## Dependencies

- **Blocks**: Multi-day pause capability
- **Depends On**: Flaw #22 (agent checkpoints - storage mechanism)
- **Related**: Flaw #23 (workflow pause/resume - triggers L1 extension)

---

## Files Affected

**New Files**:

- `src/memory/l1_snapshotter.py` - L1 snapshot/restore logic
- `src/memory/l1_ttl_manager.py` - TTL extension on pause

**Modified Files**:

- `src/agents/checkpoint.py` - Add L1 snapshot to checkpoint save
- `src/coordination/pause_manager.py` - Extend L1 TTL on pause, restore on resume
- `docs/architecture/02-memory-system.md` - Document L1 TTL policies, restore procedure
