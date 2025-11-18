---
flaw_id: 12
title: Pattern Archive Lifecycle Gaps
status: resolved
priority: high
phase: 3-4
effort_weeks: 7
impact: Data loss risk for deprecated patterns, no archive promotion
blocks: ['Post-mortem investigation']
depends_on: ['DD-009 implemented', '#9 post-mortem system']
resolved_by: DD-013
resolved_date: 2025-11-18
domain: ['memory', 'data']
sub_issues:
  - id: C2
    severity: critical
    title: Circular dependency in deletion
  - id: A3
    severity: high
    title: No archive promotion path
discovered: 2025-11-17
---

# Flaw #12: Pattern Archive Lifecycle Gaps

**Status**: ✅ RESOLVED (DD-013)
**Resolved Date**: 2025-11-18
**Priority**: Critical
**Impact**: Data loss risk for deprecated pattern evidence, no archive re-promotion path
**Phase**: Phase 3-4 (Months 5-8)

---

## Problem Description

DD-009 implements pattern-aware retention and selective archiving, but has two critical gaps:

1. **Circular Dependency in Deletion Logic** (C2): Can't delete aging evidence if it supports active patterns, but what about deprecated patterns?
2. **No Archive Promotion Path** (A3): Archived memories can't be promoted back to active graph when needed

### Sub-Issue C2: Circular Deletion Dependency

**Files**:

- `docs/operations/03-data-management.md:446-455`
- `design-decisions/DD-009:203-225`

**Problem**: Pattern-aware retention prevents deleting files that support active patterns, but logic unclear for deprecated patterns, risking data loss or retention bloat.

**Current State**:

```yaml
# DD-009 L203-225
Before deleting aging evidence from Cold tier:
  1. Does file support any active patterns?
  2. Is file already archived?
  3. If yes to #1: Retain
     If yes to #2: Safe to delete (archived)
```

**Circular Dependency Scenario**:

```text
Year 1: Pattern "High R&D predicts growth" identified
  - Evidence: 15 filings supporting pattern
  - Pattern status: active
  - Files: Retained (support active pattern)

Year 3: Pattern validated and archived
  - Archive created (Tier 1: lightweight 5MB)
  - Original files (150MB) still in Hot/Warm storage
  - Pattern status: still active

Year 5: Pattern deprecated (no longer predictive in new regime)
  - Pattern status: deprecated (not active)
  - Original files now eligible for deletion?

  CHECK 1: Does file support active patterns?
    → NO (pattern deprecated)
    → Criterion says: OK to delete

  CHECK 2: Is file already archived?
    → YES (archived in Year 3)
    → Criterion says: Safe to delete

  ACTION: Delete 150MB original files

Year 6: Post-mortem investigation on WHY pattern failed
  - Need original filings to diagnose failure mode
  - Files deleted (only 5MB archive remains)
  - Archive insufficient for root cause analysis
  - INVESTIGATION BLOCKED

PROBLEM: Deleted evidence needed for failure investigation
```

**Missing Logic**:

- Deprecated pattern evidence retention rules
- Post-mortem evidence requirements for non-active patterns
- Archive sufficiency determination
- Retention period for deprecated patterns (how long?)

### Sub-Issue A3: No Archive Promotion Path

**Files**:

- `docs/architecture/02-memory-system.md:986-1008`
- `design-decisions/DD-009`

**Problem**: Memories archived to cold storage (S3, data warehouse) can't be promoted back to active graph when needed, limiting long-term learning.

**Current State**:

```yaml
# memory-system.md L1000-1001
3. Archive full detail to cold storage (S3, data warehouse)
4. Remove full detail from L3 graph
# One-way flow: Active graph → Archive (no reverse path)
```

**Scenarios Requiring Re-Promotion**:

**Scenario 1: Regime Change Reactivates Old Pattern**

```text
Year 1-3: Pattern "Debt-funded buybacks boost EPS" active (low rate regime)
Year 3: Archived as "stable, well-validated pattern"
Year 4-7: High rate regime begins, pattern deprecated, archived
Year 8: Rates drop again, old low-rate patterns become relevant

NEED: Re-promote archived pattern to active graph
  - Query old patterns by regime
  - Re-validate with new data
  - Reactivate if still predictive

CURRENT STATE: Pattern in S3 archive, not queryable by graph algorithms
  - Can't find similar regime patterns
  - Can't leverage historical learnings
  - Forced to re-learn from scratch
```

**Scenario 2: Post-Mortem Investigation**

```text
Year 5: Major sector failure (tech growth stocks underperform)
Year 6: Post-mortem investigating pattern failures

NEED: Access archived patterns from 3-5 years ago
  - Compare current vs historical pattern performance
  - Identify what changed in recent patterns
  - Root cause analysis requires old pattern details

CURRENT STATE: Archives not integrated with graph queries
  - Manual S3 retrieval required
  - No automated precedent lookup
  - Investigation slowed by data access friction
```

**Scenario 3: Pattern Re-Validation**

```text
Year 4: Pattern archived after meeting validation criteria
Year 6: Blind testing framework enhanced (better holdout methodology)

NEED: Re-validate old patterns with improved methodology
  - Bulk re-validation of archived patterns
  - Promote validated patterns back to active
  - Deprecate patterns that fail new validation

CURRENT STATE: No batch re-validation interface
  - Archives isolated from validation pipeline
  - Can't retroactively improve quality
```

**Missing Components**:

- Archive query interface (SQL/S3 Select for structured queries)
- Promotion triggers (access frequency spike, regime change)
- Re-hydration procedure (S3 → L3 graph)
- Latency impact assessment (if archive accessed frequently)
- Cost implications (S3 retrieval fees)

---

## Impact Assessment

| Sub-Issue | Severity | Risk                                | Consequence           |
| --------- | -------- | ----------------------------------- | --------------------- |
| C2        | CRITICAL | Data loss for post-mortem evidence  | Can't investigate why |
| A3        | MEDIUM   | Limits long-term learning from past | Re-learn vs leverage  |

**Aggregate Impact**:

- C2: Evidence deletion blocks root cause analysis (critical for Flaw #9 - Negative Feedback)
- A3: Archived knowledge inaccessible limits multi-year learning evolution
- Combined: Pattern lifecycle incomplete, can't learn from long-term history

---

## Recommended Solution

### C2: Deprecated Pattern Retention Rules

#### Extended Retention Logic

```python
class PatternAwareRetention:
    """Enhanced retention logic for deprecated patterns"""

    DEPRECATED_RETENTION_YEARS = 3  # Keep evidence 3yr after deprecation

    def can_delete_file(self, file_id):
        """Determine if aging file can be deleted"""

        # Check 1: Does file support any patterns?
        patterns = self.get_patterns_supported_by(file_id)

        if not patterns:
            return True  # No patterns, safe to delete

        # Check 2: All patterns active?
        active_patterns = [p for p in patterns if p.status == 'active']
        if active_patterns:
            return False  # Active patterns require evidence

        # Check 3: Any patterns recently deprecated?
        deprecated_patterns = [p for p in patterns if p.status == 'deprecated']
        for pattern in deprecated_patterns:
            years_since_deprecation = (
                datetime.now() - pattern.deprecated_date
            ).days / 365

            if years_since_deprecation < self.DEPRECATED_RETENTION_YEARS:
                return False  # Keep for post-mortem investigation

        # Check 4: Is file archived with sufficient detail?
        if self.is_archived(file_id):
            archive_tier = self.get_archive_tier(file_id)

            # Tier 2 archives have full detail
            if archive_tier == 2:
                return True  # Safe to delete, full archive exists

            # Tier 1 archives may be insufficient for post-mortem
            if any(p.post_mortem_triggered for p in deprecated_patterns):
                return False  # Keep original for active post-mortem

        # Default: retain if unclear
        return False

    def get_retention_status(self, file_id):
        """Explain retention decision"""
        patterns = self.get_patterns_supported_by(file_id)

        status = RetentionStatus(file_id=file_id)

        for pattern in patterns:
            if pattern.status == 'active':
                status.add_reason(
                    f"Supports active pattern {pattern.id}",
                    priority='high',
                    retention_years='indefinite'
                )
            elif pattern.status == 'deprecated':
                years_left = self.DEPRECATED_RETENTION_YEARS - (
                    datetime.now() - pattern.deprecated_date
                ).days / 365

                if years_left > 0:
                    status.add_reason(
                        f"Supports deprecated pattern {pattern.id}",
                        priority='medium',
                        retention_years=years_left,
                        reason='post_mortem_investigation'
                    )

        return status
```

#### Archive Sufficiency Assessment

```python
class ArchiveSufficiency:
    """Determine if archive sufficient for future needs"""

    def assess_sufficiency(self, file_id, archive_tier):
        """Check if archive adequate for post-mortem"""

        file_type = self.get_file_type(file_id)

        # Tier 2 always sufficient (full detail)
        if archive_tier == 2:
            return SufficiencyResult(
                sufficient=True,
                confidence='high'
            )

        # Tier 1 sufficiency depends on file type
        if archive_tier == 1:
            if file_type == '10-K':
                # Tier 1 has key metrics, ratios, flags
                # May be insufficient for forensic investigation
                return SufficiencyResult(
                    sufficient=False,
                    confidence='medium',
                    reason='10-K requires full text for forensic analysis'
                )

            elif file_type == 'earnings_transcript':
                # Tier 1 has sentiment, topics, key quotes
                # May be sufficient for pattern re-validation
                return SufficiencyResult(
                    sufficient=True,
                    confidence='medium',
                    reason='Key excerpts captured in Tier 1'
                )

        return SufficiencyResult(
            sufficient=False,
            confidence='low',
            reason='Unknown file type or archive tier'
        )
```

### A3: Archive Promotion System

#### Archive Query Interface

```python
class ArchiveQueryInterface:
    """Query archived patterns without full re-hydration"""

    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.archive_bucket = 'pattern-archives'

    def query_archived_patterns(self, filters):
        """Query archives using S3 Select (Parquet)"""

        # Build SQL query for S3 Select
        sql = self._build_query(filters)

        # Query without downloading full archives
        response = self.s3_client.select_object_content(
            Bucket=self.archive_bucket,
            Key=f'patterns/{filters.year_range}.parquet',
            ExpressionType='SQL',
            Expression=sql,
            InputSerialization={'Parquet': {}},
            OutputSerialization={'JSON': {}}
        )

        # Parse results
        results = []
        for event in response['Payload']:
            if 'Records' in event:
                results.extend(json.loads(event['Records']['Payload']))

        return ArchivedPatternResults(
            patterns=results,
            count=len(results),
            query_time=response['Stats']['BytesScanned']
        )

    def _build_query(self, filters):
        """Build SQL for S3 Select"""
        conditions = []

        if filters.regime:
            conditions.append(f"market_regime = '{filters.regime}'")

        if filters.confidence_min:
            conditions.append(f"confidence >= {filters.confidence_min}")

        if filters.sector:
            conditions.append(f"sector = '{filters.sector}'")

        where_clause = ' AND '.join(conditions) if conditions else '1=1'

        return f"""
            SELECT pattern_id, pattern_type, confidence, occurrences,
                   market_regime, sector, validation_date
            FROM S3Object
            WHERE {where_clause}
            LIMIT 100
        """
```

#### Promotion Decision Logic

```python
class ArchivePromotion:
    """Decide when to promote archived patterns back to active graph"""

    ACCESS_FREQUENCY_THRESHOLD = 5  # Accesses in 7 days
    PROMOTION_COOLDOWN_DAYS = 90  # Don't demote for 90 days after promotion

    def should_promote(self, pattern_id):
        """Determine if pattern should be promoted from archive"""

        access_history = self.get_access_history(
            pattern_id,
            days=7
        )

        # Trigger 1: High access frequency
        if len(access_history) >= self.ACCESS_FREQUENCY_THRESHOLD:
            return PromotionDecision(
                promote=True,
                reason='high_access_frequency',
                priority='high',
                access_count=len(access_history)
            )

        # Trigger 2: Regime change reactivates pattern
        current_regime = self.get_current_market_regime()
        pattern_regime = self.get_pattern_regime(pattern_id)

        if current_regime == pattern_regime:
            # Pattern designed for current regime
            last_active_date = self.get_last_active_date(pattern_id)
            months_inactive = (datetime.now() - last_active_date).days / 30

            if months_inactive > 12:
                return PromotionDecision(
                    promote=True,
                    reason='regime_reactivation',
                    priority='medium',
                    regime=current_regime
                )

        # Trigger 3: Bulk re-validation requested
        if self.is_revalidation_pending(pattern_id):
            return PromotionDecision(
                promote=True,
                reason='revalidation_requested',
                priority='low',
                temporary=True  # Demote after revalidation
            )

        return PromotionDecision(promote=False)

    def promote_pattern(self, pattern_id):
        """Promote archived pattern to active graph"""

        # Step 1: Retrieve from S3
        archive_data = self.retrieve_from_s3(pattern_id)

        # Step 2: Re-hydrate to L3 graph
        self.hydrate_to_graph(archive_data)

        # Step 3: Set promotion metadata
        self.set_metadata(pattern_id, {
            'promoted_at': datetime.now(),
            'promotion_reason': self.should_promote(pattern_id).reason,
            'cooldown_until': datetime.now() + timedelta(
                days=self.PROMOTION_COOLDOWN_DAYS
            )
        })

        # Step 4: Update memory caches
        self.invalidate_cache(pattern_id)

        return PromotionResult(
            pattern_id=pattern_id,
            status='promoted',
            in_l3_graph=True
        )
```

#### Re-Hydration Procedure

```python
class PatternRehydration:
    """Re-hydrate archived patterns into active graph"""

    def rehydrate(self, pattern_id):
        """Full re-hydration from archive to L3 graph"""

        # Retrieve archive
        archive = self.s3_client.get_object(
            Bucket='pattern-archives',
            Key=f'patterns/{pattern_id}.json'
        )
        pattern_data = json.load(archive['Body'])

        # Reconstruct graph nodes
        pattern_node = self._create_pattern_node(pattern_data)
        evidence_nodes = self._create_evidence_nodes(pattern_data['evidence'])

        # Restore relationships
        relationships = self._create_relationships(
            pattern_node,
            evidence_nodes,
            pattern_data['relationships']
        )

        # Insert into Neo4j
        with self.neo4j_session() as session:
            session.write_transaction(
                self._insert_pattern_tx,
                pattern_node,
                evidence_nodes,
                relationships
            )

        # Update indices
        self._update_indices(pattern_id)

        return RehydrationResult(
            pattern_id=pattern_id,
            nodes_created=1 + len(evidence_nodes),
            relationships_created=len(relationships),
            latency_ms=(datetime.now() - start).total_seconds() * 1000
        )

    def _create_pattern_node(self, data):
        """Reconstruct Pattern node from archive"""
        return Node(
            'Pattern',
            id=data['id'],
            pattern_type=data['type'],
            confidence=data['confidence'],
            validation_date=data['validation_date'],
            status='promoted',  # Mark as promoted
            archived_date=data['archived_date'],
            promoted_date=datetime.now()
        )
```

---

## Implementation Plan

### Phase 1 (Week 1-2): C2 - Deprecated Pattern Retention

- [ ] Extend `PatternAwareRetention` with deprecated logic
- [ ] Add 3-year retention window after deprecation
- [ ] Implement `ArchiveSufficiency` assessment
- [ ] Update DD-009 with extended retention rules
- [ ] Add retention status explanation API

### Phase 2 (Week 3-4): A3 - Archive Query Interface

- [ ] Implement S3 Select queries for Parquet archives
- [ ] Build `ArchiveQueryInterface` class
- [ ] Add query filters (regime, confidence, sector)
- [ ] Test query performance (<500ms for 1000 patterns)
- [ ] Document archive query API

### Phase 3 (Week 5-6): A3 - Promotion System

- [ ] Implement `ArchivePromotion` decision logic
- [ ] Add access frequency tracking
- [ ] Build regime change detection triggers
- [ ] Implement `PatternRehydration` procedures
- [ ] Add cooldown period enforcement

### Phase 4 (Week 7): Testing & Integration

- [ ] Test C2 retention with deprecated patterns (10 scenarios)
- [ ] Test A3 promotion with regime changes
- [ ] Benchmark re-hydration latency (<3s for single pattern)
- [ ] Integration test with post-mortem system (Flaw #9)
- [ ] Cost analysis (S3 retrieval fees)

---

## Success Criteria

### C2: Deprecated Pattern Retention

- ✅ Zero evidence loss for patterns under post-mortem investigation
- ✅ Deprecated pattern evidence retained 3yr minimum
- ✅ Archive sufficiency correctly assessed (validated on 50 patterns)
- ✅ Retention status explainable (API response <100ms)

### A3: Archive Promotion

- ✅ Archive queries complete <500ms (1000 pattern scan)
- ✅ Promotion triggered within 24hr of regime change
- ✅ Re-hydration completes <3s per pattern
- ✅ Promoted patterns integrated with active graph (queryable immediately)
- ✅ S3 retrieval costs <$10/month (estimated 50 promotions/month)

---

## Dependencies

- **Blocks**: Post-mortem investigation (Flaw #9), Long-term learning evolution
- **Depends On**: DD-009 pattern archiving implemented, Neo4j graph operational
- **Related Flaws**: #5 (Data Retention - RESOLVED), #9 (Negative Feedback - RESOLVED)
- **Related DDs**: DD-009 (requires updates)

---

## Resolution (DD-013)

This flaw was resolved by [DD-013: Archive Lifecycle Management](../../design-decisions/DD-013_ARCHIVE_LIFECYCLE_MANAGEMENT.md) on 2025-11-18.

### How DD-013 Resolves Sub-Issue C2 (Circular Deletion Dependency)

DD-013 extends DD-009's pattern-aware retention with status-aware logic for deprecated patterns:

**Solution Implemented**:

- **18-month retention window** for deprecated patterns post-deprecation
- **Tiered archive requirements**:
  - Early-stage deprecated (candidate/statistically_validated): Tier 1 sufficient
  - Late-stage deprecated (human_approved/active/probationary): Tier 2 required
- **Archive sufficiency check** blocks deletion if required tier missing
- **Post-mortem lock** prevents deletion when pattern under investigation

**Key Difference from Original Proposal**:

- Original: 3-year retention window
- **Implemented**: 18-month window (cost optimization, covers 90%+ post-mortems)

### How DD-013 Resolves Sub-Issue A3 (No Archive Promotion Path)

DD-013 implements auto-promotion system with cached index and human oversight:

**Solution Implemented**:

- **Cached archive index** (Redis/ElasticSearch) for <100ms queries without S3 access
- **Promotion triggers**: Regime change detection, access frequency (3+ hits/30d), post-mortem needs
- **Auto-promote with 48hr human override**: Patterns promoted immediately, human can reject within window
- **Re-hydration pipeline**: S3 → validation → L3 graph restoration with staleness metadata
- **Probationary period**: Promoted patterns require re-validation before investment use
- **Cooldown logic**: 6-month observation period prevents promotion/demotion thrashing

**Key Difference from Original Proposal**:

- Original: High access frequency threshold (5 accesses/7d), 90-day cooldown
- **Implemented**: Lower threshold (3 accesses/30d), 6-month cooldown, human override system

### Implementation Status

- **Design**: Complete (DD-013 approved 2025-11-18)
- **Implementation**: Pending (Phase 3-4 per roadmap)
- **Dependencies**: DD-009 pattern archiving, regime detection service, Redis/ElasticSearch infrastructure

---

## Related Documentation

- [DD-013: Archive Lifecycle Management](../../design-decisions/DD-013_ARCHIVE_LIFECYCLE_MANAGEMENT.md) - **Resolution**
- [DD-009: Data Retention & Pattern Evidence](../../design-decisions/DD-009_DATA_RETENTION_PATTERN_EVIDENCE.md)
- [Memory System](../../architecture/02-memory-system.md)
- [Data Management](../../operations/03-data-management.md)
- [Learning Systems](../../learning/01-learning-systems.md)
