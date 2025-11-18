# DD-019: Data Tier Management Operations

**Status**: Approved
**Date**: 2025-11-18
**Decider(s)**: System Architect
**Related Docs**:

- [Memory System](../architecture/02-memory-system.md)
- [Data Management](../operations/03-data-management.md)
- [Tech Requirements](../implementation/02-tech-requirements.md)

**Related Decisions**: DD-009 (Data Retention & Pattern Evidence - extends this decision)

---

## Context

### Problem Statement

**Operational Gaps in DD-009 Tiered Storage**: While DD-009 implements age-based tiered storage (Hot→Warm→Cold), it lacks mechanisms for handling dynamic access patterns and knowledge graph corruption. This creates:

- **Performance Degradation**: Files migrated to slower tiers based on age remain there even when access patterns change, causing analysis timeouts
- **No Corruption Recovery**: Neo4j knowledge graph lacks integrity monitoring and recovery procedures
- **Cost Inefficiency**: Cannot re-promote frequently-accessed historical data to optimize performance
- **Single Point of Failure**: Central knowledge graph has no documented disaster recovery

### Concrete Examples

**Example 1: Pattern Re-Validation Performance**

```text
Year 2.0: Company XYZ financial data in Hot storage (<10ms access)
Year 2.1: Auto-migrated Hot → Warm (age-based rule)
Year 2.2: Pattern re-validation needs XYZ data frequently (10+ times/week)

Expected: <10ms (analysis calibrated for Hot tier)
Actual: 100ms (Warm tier latency)
Result: Analysis timeouts, degraded user experience
```

**Example 2: Graph Corruption Scenario**

```text
Event: Memory sync interrupted during pattern evidence write
Result: Orphaned relationship (Pattern → Evidence with missing Evidence node)
Impact: Pattern validation fails, QC agent reports inconsistency
Current State: No detection, no automated repair, manual intervention required
```

### Why Address Now

- **Phase 4 Production Readiness**: Blocks production deployment without operational robustness
- **Pattern Validation (DD-007)**: Re-validation performance critical for learning system
- **Agent Credibility (DD-008)**: Graph corruption affects credibility score calculations
- **Regulatory Risk**: No disaster recovery for audit trail data
- **Before Scale**: Must solve before 1000+ stocks (Phase 8) when performance issues magnified

---

## Decision

**Implement access-based tier re-promotion system and comprehensive Neo4j integrity monitoring with automated recovery.**

Primary approach adds PostgreSQL-based access tracking to enable dynamic tier promotion (Warm→Hot, Cold→Warm) based on usage patterns, supplemented by hybrid integrity monitoring (real-time alerts + hourly checks + daily comprehensive) with automated repair and PITR backups for Neo4j knowledge graph.

---

## Options Considered

### Option 1: Manual Tier Management

**Description**: Admin manually promotes files when performance issues detected

**Pros**:

- Zero implementation cost
- Full control over tier placement
- Simple to understand

**Cons**:

- Reactive (performance already degraded when detected)
- Requires constant monitoring
- Doesn't scale (200-1000 stocks)
- No SLA for performance recovery

**Estimated Effort**: 0 weeks (no implementation)

---

### Option 2: Predictive Access Patterns (ML-Based)

**Description**: Machine learning model predicts future access patterns, proactively promotes files

**Pros**:

- Proactive (promotes before access spike)
- Optimizes for predicted workload
- Could reduce unnecessary promotions

**Cons**:

- Complex implementation (ML pipeline, training data)
- Requires 6-12 months data for training
- Prediction errors cause thrashing (promote/demote cycles)
- Over-engineered for current scale

**Estimated Effort**: 6 weeks (ML pipeline, model training, integration)

---

### Option 3: Access-Based Re-Promotion (Reactive) - **CHOSEN**

**Description**: Monitor actual file access frequency (7-day windows), promote when thresholds exceeded

**Pros**:

- Simple threshold-based logic (no ML complexity)
- Proven in industry (CDN cache warming, database buffer pools)
- Fast recovery (<24hr from access spike to promotion)
- Cost-effective (only promote truly high-access files)
- Scales well (PostgreSQL handles access log aggregation)

**Cons**:

- Reactive (first few accesses slow before promotion)
- Requires access tracking infrastructure
- Storage cost increases if many files promoted

**Estimated Effort**: 2 weeks (access tracking + re-promotion job)

---

### Option 4: Hybrid (Access-Based + Manual Override) - **CHOSEN**

**Description**: Combine Option 3 automated re-promotion with manual tier pinning capability

**Pros**:

- All benefits of Option 3
- Admin can pin critical files to Hot tier (testing, known workloads)
- Emergency performance optimization capability
- Testing flexibility

**Cons**:

- Slightly more complex (override logic)
- Requires admin UI/API

**Estimated Effort**: 2.5 weeks (Option 3 + override API)

---

### Graph Integrity: Option A vs. B

**Option A: Daily Checks Only**

- Pros: Simple, low overhead
- Cons: 24hr detection window (too slow)

**Option B: Hybrid Monitoring - **CHOSEN\*\*

- Real-time transaction failure alerts
- Hourly lightweight checks (relationship counts, index consistency)
- Daily comprehensive checks (orphaned relationships, missing properties)
- Pros: <1hr detection, multi-layered defense
- Cons: More complex monitoring infrastructure

---

## Rationale

### Why Access-Based Re-Promotion

1. **Industry Standard**: CDNs (Cloudflare, Akamai), databases (PostgreSQL shared_buffers), caching layers all use access frequency for promotion
2. **Cost vs. Performance**: Only promote truly high-access files (10+ access/week), not all historical data
3. **Scalability**: PostgreSQL materialized views handle 1000+ stocks with weekly aggregation
4. **Pattern Validation Needs**: DD-007 re-validation often requires historical data; re-promotion ensures <10ms access
5. **Simple Thresholds Work**: 7-day window smooths temporary spikes, prevents thrashing

### Why Hybrid Integrity Monitoring

1. **Defense in Depth**: Real-time catches transaction failures immediately, hourly catches corruption before propagation, daily ensures comprehensive validation
2. **<1hr Detection**: Hourly checks meet production SLA requirements
3. **Automated Repair**: Common issues (orphaned relationships, missing properties) auto-fixed without human intervention
4. **PITR Backups**: Point-in-time recovery enables rollback to last known good state (<1hr RTO)
5. **Cost-Effective**: Prometheus/Grafana open-source, hourly checks <5min compute

### Why PostgreSQL for Access Tracking

1. **Already in Stack**: System already uses PostgreSQL for metadata, no new infrastructure
2. **Materialized Views**: Weekly aggregation enables fast queries for re-promotion job
3. **Simple Schema**: `(file_id, timestamp, access_type, agent_id)` with weekly rollup
4. **Joins with Metadata**: Easy correlation with file metadata, tier status
5. **Industry Proven**: Database buffer pool management uses similar tracking

---

## Consequences

### Positive Impacts

- **Performance Recovery**: Files promoted within 24hr of access spike, restoring <10ms latency
- **Cost Optimization**: Only 10-20% of historical files promoted (not all), minimal cost increase
- **Pattern Validation Performance**: DD-007 re-validation benefits from fast historical data access
- **Graph Integrity**: <1hr corruption detection, automated repair for common issues
- **Disaster Recovery**: PITR backups enable <1hr recovery from catastrophic graph corruption
- **Production Readiness**: Operational robustness unblocks Phase 4 deployment
- **Scalability**: System handles 1000+ stocks without manual tier management

### Negative Impacts / Tradeoffs

- **Access Tracking Overhead**: 5-10% storage increase (PostgreSQL access log table)
- **Promotion Latency**: First few accesses slow (100ms) before 24hr promotion window
- **Cost Increase**: Estimated $50-100/month for promoted files (vs all-Cold baseline)
- **Two Systems**: Re-promotion + integrity monitoring (increased operational complexity)
- **Monitoring Infrastructure**: Prometheus/Grafana for real-time alerts (setup/maintenance)

### Affected Components

**Services to Implement**:

- `FileAccessTracker`: Log file accesses to PostgreSQL
- `AccessAggregator`: Daily job to update weekly materialized views
- `TierPromotionService`: Check promotion candidates, execute migrations
- `GraphIntegrityMonitor`: Hourly + daily integrity checks
- `GraphRepairService`: Automated repair for common corruption types
- `BackupManager`: PITR backup scheduling, retention management

**Data Pipeline**:

- File access → PostgreSQL access log (real-time)
- Daily aggregation → Materialized view refresh
- Daily promotion job → Identify candidates → Execute tier migrations
- Hourly integrity check → Alert on failures → Trigger repair
- Daily comprehensive check → Generate integrity report → Archive

**Documentation**:

- `docs/operations/03-data-management.md`: Add §4.3 Re-Promotion System
- `docs/architecture/02-memory-system.md`: Add §3.4 Integrity Monitoring
- `docs/implementation/02-tech-requirements.md`: Neo4j recovery procedures, monitoring stack

---

## Implementation Notes

### Access Tracking Architecture

**PostgreSQL Schema**:

```sql
-- Raw access log (append-only, partitioned by week)
CREATE TABLE file_access_log (
    id BIGSERIAL PRIMARY KEY,
    file_id VARCHAR(255) NOT NULL,
    access_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    access_type VARCHAR(50),  -- 'read', 'pattern_validation', 'post_mortem'
    agent_id VARCHAR(100),
    tier_at_access VARCHAR(10)  -- 'hot', 'warm', 'cold'
) PARTITION BY RANGE (access_timestamp);

-- Weekly aggregation (materialized view, refreshed daily)
CREATE MATERIALIZED VIEW file_access_weekly AS
SELECT
    file_id,
    COUNT(*) as access_count_7d,
    MAX(access_timestamp) as last_access,
    current_tier,
    promotion_candidate
FROM file_access_log
WHERE access_timestamp > NOW() - INTERVAL '7 days'
GROUP BY file_id, current_tier;

-- Indexes for performance
CREATE INDEX idx_file_access_timestamp ON file_access_log(access_timestamp);
CREATE INDEX idx_file_id_timestamp ON file_access_log(file_id, access_timestamp DESC);
CREATE INDEX idx_weekly_promotion ON file_access_weekly(promotion_candidate) WHERE promotion_candidate = true;
```

### Re-Promotion Algorithm

**Thresholds**:

```python
ACCESS_THRESHOLD_HOT = 10   # accesses per 7-day window for Warm→Hot
ACCESS_THRESHOLD_WARM = 3   # accesses per 7-day window for Cold→Warm
SAFETY_WINDOW_DAYS = 7      # Keep file in both tiers during migration
```

**Daily Promotion Job**:

```python
class TierPromotionService:
    """Automated file promotion based on access patterns"""

    def daily_promotion_check(self):
        """Identify and execute tier promotions"""

        # Refresh weekly aggregation
        self.db.execute("REFRESH MATERIALIZED VIEW file_access_weekly")

        # Warm → Hot candidates
        warm_candidates = self.db.query("""
            SELECT file_id, access_count_7d, current_tier
            FROM file_access_weekly
            WHERE current_tier = 'warm'
            AND access_count_7d >= %s
            AND tier_override IS NULL
        """, [ACCESS_THRESHOLD_HOT])

        for file in warm_candidates:
            self.promote_file(file.id, from_tier='warm', to_tier='hot')

        # Cold → Warm candidates
        cold_candidates = self.db.query("""
            SELECT file_id, access_count_7d, current_tier
            FROM file_access_weekly
            WHERE current_tier = 'cold'
            AND access_count_7d >= %s
            AND tier_override IS NULL
        """, [ACCESS_THRESHOLD_WARM])

        for file in cold_candidates:
            self.promote_file(file.id, from_tier='cold', to_tier='warm')

    def promote_file(self, file_id, from_tier, to_tier):
        """Execute tier promotion with safety window"""

        # Copy to new tier (async)
        self.storage.copy(file_id, to_tier)

        # Update metadata
        self.db.execute("""
            UPDATE file_metadata
            SET current_tier = %s, promoted_at = NOW()
            WHERE file_id = %s
        """, [to_tier, file_id])

        # Schedule old tier cleanup (7 days)
        self.scheduler.schedule_deletion(
            file_id=file_id,
            tier=from_tier,
            delay_days=7
        )

        # Log promotion
        self.logger.info(f"Promoted {file_id}: {from_tier} → {to_tier}")
```

### Manual Override API

**Schema Extension**:

```sql
ALTER TABLE file_metadata ADD COLUMN tier_override VARCHAR(10);
-- Values: NULL (auto), 'hot', 'warm', 'cold'
```

**Admin API**:

```python
@admin_api.post("/files/{file_id}/tier")
def set_tier_override(file_id: str, tier: str):
    """Manually pin file to specific tier"""

    if tier not in ['hot', 'warm', 'cold', None]:
        raise ValueError("Invalid tier")

    db.execute("""
        UPDATE file_metadata
        SET tier_override = %s
        WHERE file_id = %s
    """, [tier, file_id])

    # If promoting, execute immediately
    if tier in ['hot', 'warm']:
        tier_promotion_service.promote_file(
            file_id,
            from_tier=current_tier,
            to_tier=tier
        )

    return {"status": "success", "tier_override": tier}
```

### Graph Integrity Monitoring

**Hybrid Architecture**:

**1. Real-Time Alerts** (Prometheus + Neo4j metrics)

```yaml
Alerts:
  - name: HighTransactionFailureRate
    expr: rate(neo4j_transaction_failures[5m]) > 0.01
    severity: critical
    action: Alert ops team, trigger integrity check

  - name: ConstraintViolation
    expr: neo4j_constraint_violations > 0
    severity: high
    action: Trigger repair immediately
```

**2. Hourly Lightweight Checks**

```python
class GraphIntegrityMonitor:
    """Hourly + daily integrity checks"""

    def hourly_lightweight_check(self):
        """Fast checks for critical issues"""

        checks = [
            self.check_relationship_count_anomaly(),
            self.check_index_consistency(),
            self.check_recent_write_failures()
        ]

        issues = [c for c in checks if not c.passed]

        if issues:
            self.alert_ops(issues)
            self.trigger_repair(issues)

        return IntegrityReport(checks=checks, issues=issues)

    def check_relationship_count_anomaly(self):
        """Detect sudden drops in relationship counts"""

        current_count = self.neo4j.run("""
            MATCH ()-[r:SUPPORTED_BY_FILE]->()
            RETURN count(r) as count
        """).single()['count']

        expected_range = self.get_historical_range('SUPPORTED_BY_FILE')

        passed = expected_range.min <= current_count <= expected_range.max

        return IntegrityCheck(
            name='relationship_count',
            passed=passed,
            severity='high' if not passed else 'ok',
            details=f"Current: {current_count}, Expected: {expected_range}"
        )
```

**3. Daily Comprehensive Checks**

```python
def daily_comprehensive_check(self):
    """Deep integrity validation"""

    checks = [
        self.check_orphaned_relationships(),
        self.check_missing_required_properties(),
        self.check_pattern_evidence_links(),
        self.check_agent_credibility_scores(),
        self.check_duplicate_nodes(),
        self.check_circular_references()
    ]

    # Generate report
    report = IntegrityReport(
        timestamp=datetime.now(),
        checks=checks,
        issues=[c for c in checks if not c.passed]
    )

    # Archive report
    self.archive_report(report)

    # Trigger repair for auto-fixable issues
    auto_fixable = [i for i in report.issues if i.auto_fixable]
    if auto_fixable:
        self.trigger_repair(auto_fixable)

    return report

def check_orphaned_relationships(self):
    """Find relationships with missing nodes"""

    query = """
    MATCH ()-[r:SUPPORTED_BY_FILE]->()
    WHERE NOT exists((startNode(r))) OR NOT exists((endNode(r)))
    RETURN count(r) as orphaned
    """

    orphaned_count = self.neo4j.run(query).single()['orphaned']

    return IntegrityCheck(
        name='orphaned_relationships',
        passed=orphaned_count == 0,
        severity='high',
        issue_count=orphaned_count,
        auto_fixable=True  # Can delete orphaned relationships
    )
```

### Automated Repair Procedures

```python
class GraphRepairService:
    """Automated repair for common corruption types"""

    def repair_orphaned_relationships(self):
        """Delete relationships with missing nodes"""

        result = self.neo4j.run("""
        MATCH ()-[r:SUPPORTED_BY_FILE]->()
        WHERE NOT exists((startNode(r))) OR NOT exists((endNode(r)))
        DELETE r
        RETURN count(r) as deleted
        """)

        return RepairResult(
            repair_type='orphaned_relationships',
            items_fixed=result.single()['deleted']
        )

    def repair_missing_properties(self):
        """Restore missing required properties with defaults"""

        result = self.neo4j.run("""
        MATCH (p:Pattern)
        WHERE NOT exists(p.confidence_score)
        SET p.confidence_score = 0.0, p.needs_revalidation = true
        RETURN count(p) as fixed
        """)

        return RepairResult(
            repair_type='missing_properties',
            items_fixed=result.single()['fixed']
        )

    def rebuild_indices(self):
        """Rebuild corrupted indices"""

        indices = self.neo4j.run("SHOW INDEXES").values()

        for index in indices:
            if index.state == 'FAILED':
                # Drop and recreate
                self.neo4j.run(f"DROP INDEX {index.name}")
                self.neo4j.run(index.createStatement)

        return RepairResult(
            repair_type='index_rebuild',
            items_fixed=len([i for i in indices if i.state == 'FAILED'])
        )
```

### Backup & Recovery

**PITR Backup Strategy**:

```yaml
Backup Schedule:
  - Frequency: Hourly incremental
  - Full backup: Daily at 02:00 UTC
  - Retention: 30 days
  - Storage: Primary (cross-region), Secondary (separate provider)

Backup Locations:
  Primary:
    Provider: AWS S3
    Region: us-west-2 (production in us-east-1)
    Bucket: neo4j-backups-primary
    Replication: Cross-region replication enabled

  Secondary:
    Provider: GCP Cloud Storage
    Region: us-central1
    Bucket: neo4j-backups-dr
    Purpose: Disaster recovery, provider outage protection
```

**Recovery Procedures**:

```python
class BackupManager:
    """PITR backup and recovery"""

    def restore_to_point_in_time(self, target_time: datetime):
        """Restore Neo4j to specific point in time"""

        # 1. Stop Neo4j service
        self.neo4j.stop()

        # 2. Find nearest backup before target_time
        backup = self.find_backup_before(target_time)

        # 3. Restore from backup
        self.restore_backup(backup)

        # 4. Apply transaction logs to target_time
        self.replay_transactions(
            from_time=backup.timestamp,
            to_time=target_time
        )

        # 5. Start Neo4j service
        self.neo4j.start()

        # 6. Verify integrity
        integrity_check = self.run_integrity_check()

        return RestoreResult(
            target_time=target_time,
            backup_used=backup.id,
            integrity_passed=integrity_check.passed,
            rto_minutes=self.calculate_rto()
        )
```

### Integration Points

**File Access Flow**:

1. Agent requests file from data layer
2. Data layer serves file from current tier
3. **Log access** → PostgreSQL `file_access_log`
4. Return file to agent

**Daily Operations Flow**:

1. **02:00 UTC**: Refresh `file_access_weekly` materialized view
2. **02:10 UTC**: Run tier promotion job
3. **02:30 UTC**: Run daily comprehensive integrity check
4. **03:00 UTC**: Full Neo4j backup to primary storage
5. **03:30 UTC**: Replicate backup to secondary storage

**Hourly Operations Flow**:

1. **:05 minutes**: Run lightweight integrity check
2. **:10 minutes**: Incremental Neo4j backup
3. If issues detected → Trigger repair → Alert ops team

### Testing Requirements

- **Access Tracking**: Verify PostgreSQL inserts, materialized view refresh, aggregation accuracy
- **Re-Promotion**: Test threshold triggers, safety window, override priority
- **Tier Migration**: Verify copy → metadata update → cleanup sequence
- **Integrity Checks**: Test all check types, false positive rate, detection latency
- **Automated Repair**: Verify orphaned cleanup, property restoration, index rebuild
- **PITR Recovery**: Test backup restore, transaction replay, RTO <1hr
- **Cost Tracking**: Monitor promotion costs, access log storage, backup storage

### Rollback Strategy

If re-promotion causes issues:

1. Disable automated promotion job (manual mode only)
2. If thrashing detected: Increase thresholds (10→20 for Hot, 3→5 for Warm)
3. If cost overruns: Lower thresholds or disable Warm→Hot promotions
4. Full rollback: Return to pure age-based tiering (DD-009 baseline)

If integrity monitoring causes issues:

1. Disable automated repair (alert-only mode)
2. Reduce check frequency (hourly→daily)
3. If false positives: Tune threshold ranges
4. Full rollback: Remove monitoring, rely on Neo4j built-in resilience

**Estimated Implementation Effort**: 4 weeks

**Week 1**: Access tracking infrastructure (PostgreSQL schema, logging, aggregation)
**Week 2**: Re-promotion algorithm (promotion job, manual override API)
**Week 3**: Integrity check suite (real-time alerts, hourly checks, daily comprehensive)
**Week 4**: Automated repair & backup (repair procedures, PITR, testing)

**Dependencies**:

- DD-009 tiered storage operational
- PostgreSQL database operational
- Neo4j knowledge graph operational
- Prometheus/Grafana monitoring stack
- Cloud storage for backups (AWS S3 + GCP Cloud Storage)

---

## Open Questions

None - all critical questions resolved during design:

1. ✅ Access tracking backend: PostgreSQL with weekly aggregation
2. ✅ Re-promotion thresholds: 10 (Hot), 3 (Warm) per 7-day window
3. ✅ Manual override: Yes, via admin API with tier pinning
4. ✅ Integrity monitoring: Hybrid (real-time + hourly + daily)
5. ✅ Detection SLA: <1hr for critical corruption
6. ✅ Backup strategy: PITR with cross-region + separate provider
7. ✅ Recovery RTO: <1hr for PITR restore

**Blocking**: No

---

## References

- **Design Flaws**: [Flaw #17 - Data Tier Management Gaps](../design-flaws/resolved/17-data-tier-mgmt.md)
- **Related Decisions**:
  - DD-009: Data Retention & Pattern Evidence (tiered storage baseline)
  - DD-007: Pattern Validation Architecture (re-validation performance requirements)
  - DD-008: Agent Credibility System (graph corruption affects credibility)
- **Industry Patterns**:
  - CDN cache warming (Cloudflare, Akamai)
  - Database buffer pool management (PostgreSQL shared_buffers)
  - Neo4j backup/recovery: <https://neo4j.com/docs/operations-manual/current/backup-restore/>
- **PostgreSQL Materialized Views**: <https://www.postgresql.org/docs/current/sql-creatematerializedview.html>

---

## Status History

| Date       | Status   | Notes                                       |
| ---------- | -------- | ------------------------------------------- |
| 2025-11-18 | Proposed | Initial proposal based on Flaw #17 analysis |
| 2025-11-18 | Approved | Hybrid approach, <1hr detection SLA         |

---

## Notes

### Cost Estimate

**Access Tracking Storage**:

```text
Assumptions:
- 1000 stocks analyzed per year
- 100 files per stock (financial statements, filings, transcripts)
- 10 accesses per file per year average
- 1M accesses per year

PostgreSQL Storage:
  Raw log: 1M rows/year × 100 bytes = 100MB/year
  5-year retention: 500MB × $0.023/GB = $0.01/mo
  Materialized views: 50MB × $0.023/GB = $0.001/mo
  Total: ~$0.02/mo (negligible)
```

**Tier Promotion Costs**:

```text
Assumptions:
- 10% of Cold files promoted to Warm (high re-validation)
- 5% of Warm files promoted to Hot (active analysis)
- 100GB Cold → Warm: $0.001 → $0.010 = +$0.90/mo
- 50GB Warm → Hot: $0.010 → $0.023 = +$0.65/mo

Total Tier Promotion Cost: ~$1.55/mo
vs. All Hot Storage: Would be +$200/mo (200GB × $0.023)
Cost Increase: <1% of all-hot baseline
```

**Integrity Monitoring Costs**:

```text
Prometheus/Grafana: Open-source (self-hosted)
Compute for checks: <5min/day × $0.10/hr = $0.25/mo
Backup storage:
  Neo4j database: ~10GB
  Hourly incremental: 100MB/day × 30 days = 3GB
  Total: 13GB × $0.001/GB (Cold) = $0.013/mo

Total Monitoring Cost: ~$0.26/mo
```

**Total Additional Cost: ~$1.83/mo** (vs $5.29/mo tiered storage baseline = +35%)

### Future Considerations

- **Cost-Based Promotion**: Factor storage cost delta into promotion decision (not just access frequency)
- **Predictive Promotion**: ML model to predict access patterns (Phase 8 enhancement)
- **Tiered Backups**: Move old Neo4j backups to Cold tier (30+ days)
- **Graph Sharding**: If Neo4j >100GB, shard by time period (Phase 8 scalability)
- **Access Pattern Learning**: Identify seasonal patterns (e.g., earnings season spikes)
