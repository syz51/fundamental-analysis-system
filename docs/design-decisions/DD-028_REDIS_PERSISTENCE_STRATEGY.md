# DD-028: Redis Persistence Strategy

## Status

Accepted

## Context

The fundamental analysis system uses a 3-tier memory architecture (L1 Working Memory, L2 Specialized Cache, L3 Global Knowledge) where Redis serves as the hot/warm storage layer. Different memory tiers have fundamentally different durability vs performance requirements:

**L1 Working Memory (Hot)**:
- Contains agent execution state during active "thinking" loops
- Stores intermediate analysis results not yet persisted to Neo4j/PostgreSQL
- Expensive to recompute (hours of LLM API calls, complex financial calculations)
- **Checkpoint requirement**: Save state after every subtask completion (4-5 times per analysis)
- **Multi-day pause requirement**: Preserve state for up to 14 days during workflow pauses
- **Recovery requirement**: <5 seconds from Redis, <30 seconds from PostgreSQL fallback

**L2 Specialized Cache (Warm)**:
- Caches domain-specific patterns retrieved from Elasticsearch/Neo4j
- Contains recent agent findings for cross-agent reference
- **Rebuildable** from source databases (Elasticsearch, Neo4j)
- **Performance-critical**: Sub-10ms access during agent queries
- **Recovery tolerance**: Temporary cache miss acceptable (degrades to source query)

The challenge: **L1 requires maximum durability while maintaining sub-millisecond latency**, whereas **L2 prioritizes performance over durability**.

### Previous Approach

Tech requirements (v2.0) specified persistence needs but deferred technology and configuration decisions:
- "Snapshot-based backup (RDB equivalent)"
- "Append-only log (AOF equivalent)"
- "Technology Options: [Redis, Memcached + persistence layer, Dragonfly] - Decision: TBD Phase 2"

DD-027 selected Redis 7+ for L1 working memory but did not specify persistence strategy.

### The Problem

A single persistence strategy cannot satisfy both L1 and L2 requirements:

- **AOF `always` fsync**: Maximum durability (zero data loss) but ~10x write latency penalty → breaks L1 sub-ms requirement
- **AOF disabled**: Maximum performance but lose all inter-checkpoint work on crash → violates L1 durability
- **RDB-only**: Fast writes but lose 5+ minutes of work on crash → exceeds acceptable RPO for L1
- **Unified config**: Treating L1 and L2 identically wastes resources (over-protecting cache or under-protecting state)

## Decision

We will use a **tiered persistence strategy** with separate Redis instances for L1 and L2, each optimized for its specific durability-performance tradeoff.

### 1. L1 Working Memory: Hybrid RDB + AOF

**Configuration**:
```redis
# Continuous Protection (Inter-Checkpoint)
appendonly yes
appendfsync everysec              # Async fsync every 1 second (balanced)
auto-aof-rewrite-percentage 100   # Rewrite when AOF doubles in size
auto-aof-rewrite-min-size 64mb    # Minimum size before rewrite

# Background Snapshots (Safety Net)
save 300 1                        # Every 5min if ≥1 key changed
save 60 100                       # Every 1min if ≥100 keys (burst checkpoint activity)
save 10 10000                     # Every 10sec if ≥10K keys (extreme burst)

# Checkpoint Durability (Critical)
stop-writes-on-bgsave-error yes   # Block writes if RDB save fails
rdbcompression yes                # Compress RDB files (storage efficiency)
rdbchecksum yes                   # Verify RDB integrity on load

# Memory Management
maxmemory-policy noeviction       # Never evict L1 data (24h TTL managed by app)
maxmemory 64gb                    # Size per tech requirements (500GB-1TB total capacity)
```

**Rationale**:
- **AOF `everysec`**: Balances durability (max 1-second data loss) with performance (async fsync doesn't block writes). Protects work **between subtask checkpoints** (agent calculations, intermediate results).
- **RDB intervals**: Provides general safety net and enables AOF compaction. Not relied upon for checkpoint recovery (explicit saves handle that).
- **`stop-writes-on-bgsave-error yes`**: Critical for checkpoint integrity. If Redis cannot save (disk full, I/O error), fail fast rather than continue with false confidence.
- **`maxmemory-policy noeviction`**: L1 data never evicted by LRU. Expiration handled by application-managed TTLs (24h active, 14d paused per DD-016).

### 2. L2 Specialized Cache: RDB-Only

**Configuration**:
```redis
# Background Snapshots Only
appendonly no                     # No AOF (cache data is recoverable)
save 3600 1                       # Every 1 hour if any change
save 86400 1                      # Daily fallback (if low activity)

# Durability (Minimal)
stop-writes-on-bgsave-error no    # Continue serving reads even if save fails
rdbcompression yes
rdbchecksum yes

# Memory Management
maxmemory-policy allkeys-lru      # Evict least-recently-used when memory full
maxmemory 256gb                   # Cache capacity (per tech requirements)
ttl 2592000                       # 30-day default TTL (app-managed via L2 tier spec)
```

**Rationale**:
- **No AOF**: L2 data is **rebuildable** from source (Elasticsearch patterns, Neo4j relationships). Cache miss triggers source query (slower but correct).
- **Hourly RDB**: Minimizes cache rebuild time after restart (1 hour max rebuild vs full reconstruction).
- **`stop-writes-on-bgsave-error no`**: Cache availability prioritized over persistence. If save fails, continue serving cached data.
- **LRU eviction**: Natural cache management. Hot patterns stay in memory, cold patterns evicted when space needed.

### 3. Checkpoint System Integration

**How Checkpoints Work** (per DD-011, DD-016):

Checkpoints are **explicit synchronous saves** triggered after each subtask completion, **not relying on RDB intervals**:

```
Agent completes subtask → L1CacheSnapshotter.snapshot_on_checkpoint()
                       ├─ Serialize all L1 keys for this agent
                       ├─ BGSAVE to Redis secondary instance (forced)
                       ├─ INSERT checkpoint record to PostgreSQL
                       ├─ Compute SHA256 hash for consistency verification
                       └─ Block until both saves succeed (dual durability)
```

**3-Layer Durability Strategy**:

| Layer | Purpose | Coverage | Recovery Time | Data Loss Tolerance |
|:------|:--------|:---------|:--------------|:--------------------|
| **AOF** | Inter-checkpoint protection | Every L1 write | Continuous | Max 1 second |
| **Checkpoint** | Per-subtask state | After each subtask | <5s (Redis), <30s (PostgreSQL) | Zero (synchronous save) |
| **RDB** | General backup | Time-based intervals | Minutes | 5+ minutes (acceptable fallback) |

**Example Timeline**:
```
00:00 - Financial Analyst starts Subtask 1 (10-K parsing)
00:05 - Subtask 1 completes → CHECKPOINT SAVE
        ├─ Explicit BGSAVE to Redis secondary (L1 snapshot)
        └─ INSERT to checkpoints table in PostgreSQL

00:06 - Subtask 2 starts (ratio calculation)
00:08 - **CRASH** during Subtask 2

Recovery:
├─ DualRecoveryStrategy.recover_agent_state()
├─ Load checkpoint from 00:05 (Subtask 1 complete)
├─ Replay AOF entries 00:06-00:08 (partial Subtask 2 work, max 1s loss)
└─ Resume Subtask 2 from last consistent state
```

### 4. Multi-Day Pause Handling

**Pause Event** (per DD-012, DD-016):

When analysis pauses (overnight, human gates, failures):

1. **L1TTLManager extends TTL**: `24h` (active) → `14 days` (paused)
2. **Force dual checkpoint save**:
   - Redis secondary: `BGSAVE` (forced synchronous)
   - PostgreSQL: `INSERT checkpoint` with 14-day expiry marker
3. **Agent stops**, workflow status: `PAUSED`

**Resume Event** (Day 1-14):

```
DualRecoveryStrategy attempts 3-tier recovery:

Tier 1 (Fastest): L1 keys still exist in Redis?
├─ Check namespace: L1:{agent_id}:working:*
├─ If found → Restore 24h active TTL
└─ Recovery time: <1 second

Tier 2 (Fast): Redis secondary snapshot available?
├─ Load checkpoint from Redis secondary
├─ L1CacheRestorer.restore_from_snapshot()
├─ Restore all keys with type/TTL preservation
├─ ConsistencyVerifier checks SHA256 hash
└─ Recovery time: <5 seconds

Tier 3 (Durable): PostgreSQL checkpoint fallback
├─ SELECT checkpoint WHERE agent_id=X ORDER BY created DESC LIMIT 1
├─ Deserialize L1 state from checkpoint.data (JSONB)
├─ Restore to Redis L1 namespace
└─ Recovery time: <30 seconds
```

**Timeout Escalation** (per DD-012):
- **Day 0**: Pause → Alert sent
- **Day 3**: Reminder
- **Day 7**: Warning
- **Day 14**: Auto-expiration → Status: `STALE`, L1 TTL expires
- **Day 30**: Hard purge from active tables (audit log retained)

## Consequences

### Positive

**Durability**:
- L1 protected by 3-layer strategy: AOF (1s RPO) + Checkpoint (zero loss per subtask) + RDB (fallback)
- Multi-day pauses supported via dual storage (Redis + PostgreSQL) with 14-day retention
- Checkpoint integrity guaranteed via `stop-writes-on-bgsave-error` and hash verification

**Performance**:
- L1 maintains sub-ms latency via AOF `everysec` (async fsync)
- L2 optimized for speed with no AOF overhead
- Cache misses degrade gracefully to source queries (Elasticsearch/Neo4j)

**Operational Simplicity**:
- Clear separation: L1 instance (durability-focused) vs L2 instance (performance-focused)
- Tiered recovery strategy with automatic fallback (Redis → PostgreSQL)
- Self-healing: RDB provides recovery for AOF corruption scenarios

**Cost Efficiency**:
- L2 RDB-only reduces disk I/O and storage (no AOF growth)
- AOF rewriting prevents unbounded disk usage for L1
- LRU eviction in L2 naturally manages cache size

### Negative

**Operational Complexity**:
- Requires running separate Redis instances for L1 and L2 (vs unified cache)
- Monitoring must track two persistence strategies with different health metrics
- Backup procedures differ per tier (L1 dual storage, L2 RDB-only)

**Recovery Tradeoffs**:
- AOF `everysec` means max 1-second data loss mid-subtask (vs `always` zero loss)
- L2 cache cold start after crash (vs AOF instant restoration)
- Checkpoint restore latency depends on L1 state size (100MB → ~1s, 10GB → ~10s)

**Tuning Complexity**:
- RDB save intervals require tuning based on checkpoint frequency and workload
- AOF rewrite thresholds need adjustment to prevent disk space exhaustion
- L2 eviction policy may require tuning if cache hit rates drop

### Trade-offs Accepted

1. **1-second data loss for L1**: Acceptable because subtasks are idempotent (can restart mid-subtask) and checkpoints provide zero-loss recovery points every 5-15 minutes.
2. **L2 cache rebuild on crash**: Acceptable because cache miss falls back to source query (<500ms from Neo4j/Elasticsearch) vs permanent data loss.
3. **Dual Redis instances**: Additional operational cost justified by clear durability/performance separation (mixing concerns would compromise both).

## Implementation Notes

### Deployment Architecture

**L1 Working Memory Redis**:
- **Instance name**: `redis-l1-working-memory`
- **Port**: 6379
- **Persistence**: RDB + AOF hybrid
- **Namespace**: `L1:{agent_id}:working:*`
- **TTL management**: Application-controlled (24h active, 14d paused)
- **Monitoring**: Track checkpoint save latency, AOF size growth, RDB completion times

**L2 Specialized Cache Redis**:
- **Instance name**: `redis-l2-specialized-cache`
- **Port**: 6380
- **Persistence**: RDB-only
- **Namespace**: `L2:{agent_id}:specialized:*`
- **TTL management**: 30-day default with LRU eviction
- **Monitoring**: Track cache hit rate, eviction count, rebuild frequency

**Redis Secondary (Checkpoint Storage)**:
- **Instance name**: `redis-checkpoint-secondary`
- **Port**: 6381
- **Persistence**: RDB + AOF hybrid (maximum durability)
- **Namespace**: `CHECKPOINT:{agent_id}:{timestamp}:*`
- **Retention**: 7-day TTL for checkpoints (audit trail in PostgreSQL permanent)

### Verification and Testing

**Checkpoint Integrity Tests**:
1. Save checkpoint mid-analysis → Kill Redis → Restore → Verify SHA256 hash matches
2. Pause analysis → Wait 7 days → Resume → Verify L1 state restored correctly
3. Simultaneous checkpoint saves (10 agents) → Verify no race conditions or data corruption

**Durability Tests**:
1. Kill Redis during subtask execution → Verify AOF replay recovers partial work (max 1s loss)
2. Corrupt AOF file → Verify RDB fallback restores last snapshot
3. Disk full during checkpoint save → Verify `stop-writes-on-bgsave-error` blocks and alerts

**Performance Tests**:
1. L1 write latency with AOF `everysec` → Target: p95 <1ms, p99 <5ms
2. L2 read latency with LRU eviction → Target: p95 <1ms (cache hit), <100ms (cache miss + source query)
3. Checkpoint save latency → Target: <100ms for 100MB L1 state, <1s for 1GB state

### Monitoring Metrics

**L1 Working Memory**:
- `redis_l1_aof_current_size_bytes`: AOF file size (alert if >10GB, trigger rewrite)
- `redis_l1_rdb_last_save_time`: Seconds since last RDB save (alert if >600s)
- `redis_l1_bgsave_in_progress`: Boolean (alert if stuck >60s)
- `redis_l1_aof_last_rewrite_duration_sec`: AOF rewrite time (alert if >300s)
- `checkpoint_save_latency_ms`: Time to save checkpoint (p95, p99)
- `checkpoint_save_errors_total`: Failed checkpoint saves (alert immediately)

**L2 Specialized Cache**:
- `redis_l2_evicted_keys_total`: LRU eviction count (trend analysis)
- `redis_l2_keyspace_hits_total / _misses_total`: Cache hit rate (alert if <80%)
- `redis_l2_used_memory_bytes`: Memory usage (alert if >90% maxmemory)
- `redis_l2_rdb_last_save_time`: Hours since last RDB (alert if >25h)

**Checkpoint System**:
- `checkpoint_restore_latency_ms`: Time to restore from checkpoint (p95, p99)
- `checkpoint_consistency_errors_total`: SHA256 hash mismatches (alert immediately)
- `dual_recovery_tier_used`: Which tier succeeded (Redis vs PostgreSQL) - track fallback frequency

### Configuration Management

Store Redis configurations in version control (`config/redis-l1.conf`, `config/redis-l2.conf`, `config/redis-checkpoint.conf`) with environment-specific overrides:

```bash
# Development: Relaxed persistence for faster iteration
appendfsync everysec
save 3600 1

# Staging: Match production persistence
appendfsync everysec
save 300 1

# Production: Maximum durability
appendfsync everysec
save 300 1
save 60 100
save 10 10000
```

### Disaster Recovery Playbook

**L1 Data Loss Scenarios**:

1. **Redis crash with corrupted AOF**:
   - Attempt: `redis-check-aof --fix`
   - Fallback: Restore from last RDB snapshot + PostgreSQL checkpoint
   - Data loss: Max 5 minutes (last RDB interval)

2. **Disk full during checkpoint save**:
   - Alert: `stop-writes-on-bgsave-error` blocks all writes
   - Action: Free disk space or expand volume
   - Prevention: Monitor disk usage, alert at 80% full

3. **Both Redis and PostgreSQL checkpoint corruption**:
   - Fallback: Restart agent from beginning of current analysis
   - Data loss: Entire analysis progress (hours of work)
   - Prevention: Checksum verification, separate disk volumes for Redis/PostgreSQL

**L2 Cache Loss**:
- Impact: Degraded performance (source queries slower than cache hits)
- Recovery: Automatic cache rebuild as agents query patterns
- No data loss (cache is ephemeral)

## Related Decisions

- **DD-011**: Agent Checkpoint System (defines checkpoint triggers and content)
- **DD-012**: Workflow Pause/Resume (defines multi-day pause handling)
- **DD-016**: L1 Memory Durability (defines dual-layer snapshot system)
- **DD-027**: Unified Hybrid Search Architecture (selects Redis for L1 memory tier)

## References

- Redis Persistence Documentation: https://redis.io/docs/management/persistence/
- AOF vs RDB tradeoffs: https://redis.io/docs/management/persistence/#aof-advantages
- Checkpoint system architecture: `docs/architecture/02-memory-system.md`
- Tech requirements: `docs/implementation/02-tech-requirements.md`
