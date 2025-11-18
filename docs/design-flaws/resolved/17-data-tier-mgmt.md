---
flaw_id: 17
title: Data Tier Management Gaps
status: resolved
priority: high
phase: 4
effort_weeks: 4
impact: Performance degradation, no corruption recovery
blocks:
- Production reliability
depends_on:
- DD-009 tiered storage
- Neo4j operational
domain:
- data
- memory
sub_issues:
- id: H3
  severity: high
  title: No storage tier migration rollback procedures
- id: G4
  severity: medium
  title: Knowledge graph corruption recovery missing
discovered: 2025-11-17
resolved: '2025-11-18'
resolution: 'DD-019: Data Tier Management Operations'
---
# Flaw #17: Data Tier Management Gaps

## Resolution Summary

**Status**: RESOLVED ✅
**Resolved Date**: 2025-11-18
**Resolution**: [DD-019: Data Tier Management Operations](../../design-decisions/DD-019_DATA_TIER_OPERATIONS.md)
**Phase**: Phase 4 (Months 7-8)

### How DD-019 Resolves This Flaw

DD-019 resolves both sub-issues identified in this flaw by implementing comprehensive operational procedures for DD-009's tiered storage system:

**H3: Storage Tier Migration Rollback** - RESOLVED
- **Access-Based Re-Promotion System**: PostgreSQL-based access tracking logs file accesses, enabling automatic re-promotion when usage patterns change
- **Re-Promotion Thresholds**: Warm→Hot (10+ accesses/week), Cold→Warm (3+ accesses/week)
- **Performance Recovery**: <24hr promotion time ensures frequently-accessed historical data returns to fast tiers
- **Manual Override**: Admin API allows tier pinning for critical files or testing scenarios
- **Cost Monitoring**: Tracks promotion costs to prevent budget overruns

**G4: Knowledge Graph Corruption Recovery** - RESOLVED
- **Hybrid Integrity Monitoring**: Three-tier approach (real-time alerts, hourly lightweight checks, daily comprehensive scans)
- **Detection SLA**: <1hr for critical corruption via hourly checks
- **Automated Repair**: Common issues (orphaned relationships, missing properties, index corruption) auto-fixed without human intervention
- **PITR Backups**: Hourly incremental + daily full backups with 30-day retention
- **Disaster Recovery**: Cross-region replication (primary) + separate provider backup (secondary) with <1hr RTO
- **Recovery Procedures**: Documented procedures for minor corruption, moderate corruption, and catastrophic failure scenarios

**Implementation Artifacts**:
- Updated `docs/operations/03-data-management.md`: Added Access-Based Tier Re-Promotion section
- Updated `docs/architecture/02-memory-system.md`: Added Graph Integrity Monitoring & Recovery section
- Updated `docs/implementation/02-tech-requirements.md`: Added Neo4j backup/recovery specs, integrity monitoring requirements, PostgreSQL access tracking schema

**Production Readiness**: Unblocks Phase 4 deployment with operational robustness for tiered storage and knowledge graph integrity

---

## Problem Description

DD-009 implements tiered storage but lacks operational procedures:

1. **H3**: No rollback when recently-migrated data needed urgently
2. **G4**: No knowledge graph corruption recovery

### Sub-Issue H3: No Storage Migration Rollback

**Files**: `docs/operations/03-data-management.md:363-406`, `design-decisions/DD-009`

**Problem**: Files auto-migrate Hot→Warm→Cold based on age, but no re-promotion if access patterns change.

**Performance Degradation Scenario**:
```text
Year 2.0: File in Hot storage (<10ms access)
Year 2.1: Auto-migrated Hot → Warm (age-based)
Year 2.2: Pattern re-validation needs file frequently

Expected: <10ms (analysis designed for Hot tier)
Actual: 100ms (Warm tier latency)
Result: Analysis timeouts (calibrated for Hot performance)
```

**Missing**:
- Access frequency tracking for rollback triggers
- Re-promotion algorithm (Warm→Hot, Cold→Warm)
- Cost implications of frequent rollbacks

**Solution**: Access-frequency-based re-promotion

### Sub-Issue G4: No Graph Corruption Recovery

**Files**: None (gap in all docs)

**Problem**: Central knowledge graph (Neo4j) single point of failure with no recovery procedures.

**Corruption Scenarios**:
1. Partial write failure during memory sync
2. Relationship inconsistency (orphaned edges)
3. Index corruption from crash
4. Schema migration failure

**Missing**:
- Corruption detection (integrity checks)
- Automated repair procedures
- Rollback to last known good state
- Disaster recovery SLA

**Solution**: Daily integrity checks, automated repair, PITR backups

---

## Recommended Solution

### H3: Access-Based Re-Promotion

```python
class TierMigrationWithRollback:
    """Storage tier management with access-based re-promotion"""

    ACCESS_THRESHOLD_HOT = 10  # accesses per week
    ACCESS_THRESHOLD_WARM = 3  # accesses per week

    def check_reprom otion_needed(self):
        """Daily job to identify candidates for re-promotion"""

        # Find Warm files with high access
        warm_files = self.get_files_in_tier('warm')

        for file_id in warm_files:
            access_count = self.count_accesses(file_id, days=7)

            if access_count >= self.ACCESS_THRESHOLD_HOT:
                self.promote_tier(file_id, from_tier='warm', to_tier='hot')

        # Find Cold files with moderate access
        cold_files = self.get_files_in_tier('cold')

        for file_id in cold_files:
            access_count = self.count_accesses(file_id, days=7)

            if access_count >= self.ACCESS_THRESHOLD_WARM:
                self.promote_tier(file_id, from_tier='cold', to_tier='warm')

    def promote_tier(self, file_id, from_tier, to_tier):
        """Promote file to faster tier"""

        # Calculate cost impact
        cost_impact = self.calculate_promotion_cost(
            file_id, from_tier, to_tier
        )

        # Copy to new tier
        self.copy_file(file_id, to_tier)

        # Update metadata
        self.update_tier_metadata(file_id, to_tier)

        # Keep in old tier for 7 days (safety)
        self.schedule_deletion(file_id, from_tier, days=7)

        return PromotionResult(
            file_id=file_id,
            from_tier=from_tier,
            to_tier=to_tier,
            cost_delta_monthly=cost_impact,
            latency_improvement=self.tier_latency(from_tier) - self.tier_latency(to_tier)
        )
```

### G4: Graph Corruption Recovery

```python
class GraphIntegrityMonitor:
    """Neo4j integrity checks and recovery"""

    def daily_integrity_check(self):
        """Run integrity constraints"""

        checks = [
            self.check_orphaned_relationships(),
            self.check_missing_required_properties(),
            self.check_pattern_evidence_links(),
            self.check_agent_credibility_scores(),
            self.check_index_consistency()
        ]

        issues = [c for c in checks if not c.passed]

        if issues:
            self.trigger_repair(issues)

        return IntegrityReport(
            total_checks=len(checks),
            passed=len([c for c in checks if c.passed]),
            issues=issues
        )

    def check_orphaned_relationships(self):
        """Find relationships with missing nodes"""

        query = """
        MATCH ()-[r]->()
        WHERE NOT exists((startNode(r))) OR NOT exists((endNode(r)))
        RETURN count(r) as orphaned
        """

        result = self.neo4j.run(query)
        orphaned_count = result.single()['orphaned']

        return IntegrityCheck(
            name='orphaned_relationships',
            passed=orphaned_count == 0,
            issue_count=orphaned_count
        )

    def trigger_repair(self, issues):
        """Automated repair for common issues"""

        for issue in issues:
            if issue.name == 'orphaned_relationships':
                self.repair_orphaned_relationships()

            elif issue.name == 'missing_properties':
                self.repair_missing_properties()

            elif issue.name == 'index_corruption':
                self.rebuild_indices()

    def backup_and_restore(self):
        """Point-in-time recovery from backup"""

        # Daily backup schedule
        self.neo4j.backup(
            backup_dir=f'/backups/neo4j_{date.today()}',
            incremental=True
        )

        # Keep 30 days of backups
        self.purge_old_backups(keep_days=30)
```

---

## Implementation Plan

**Week 1**: H3 access tracking infrastructure
**Week 2**: H3 re-promotion algorithm
**Week 3**: G4 integrity check suite
**Week 4**: G4 automated repair & backup

---

## Success Criteria

- ✅ H3: Files promoted within 24hr of access spike
- ✅ H3: Promotion cost <$50/month (estimated 100 promotions)
- ✅ G4: Corruption detected within 24hr
- ✅ G4: PITR backup recovery <1hr

---

## Dependencies

- **Blocks**: Production reliability (Phase 4)
- **Depends On**: DD-009 tiered storage operational, Neo4j deployed
- **Related**: Flaw #5 (Data Retention - RESOLVED), DD-009