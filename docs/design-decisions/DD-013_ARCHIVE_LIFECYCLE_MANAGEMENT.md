# DD-013: Pattern Archive Lifecycle Management

**Status**: Approved
**Date**: 2025-11-18
**Decider(s)**: System Architect
**Related Docs**:

- [Memory System](../architecture/02-memory-system.md)
- [Learning Systems](../learning/01-learning-systems.md)
- [Data Management](../operations/03-data-management.md)
- [DD-009: Data Retention & Pattern Evidence](DD-009_DATA_RETENTION_PATTERN_EVIDENCE.md)

**Related Decisions**: DD-005 (Memory Scalability), DD-007 (Pattern Validation), DD-009 (Data Retention)

---

## Context

### Problem Statement

DD-009 implements tiered storage and pattern-aware retention but has **two critical lifecycle gaps**:

**_Gap 1: Circular Deletion Dependency (Deprecated Patterns)_**

Pattern lifecycle includes "deprecated" status (docs/learning/01-learning-systems.md), but DD-009 retention logic only checks for "active patterns" (DD-009 L450). When pattern deprecated:

- Pattern-aware retention check: "Does file support any active patterns?" → NO
- Evidence becomes eligible for deletion immediately
- Post-mortem investigation blocked - evidence already deleted
- Cannot determine why pattern failed or if originally valid

**_Gap 2: No Archive Promotion Path_**

Memory system archives pattern details to cold storage (S3/data warehouse) as one-way flow (docs/architecture/02-memory-system.md L996-1000). Archives isolated from active queries:

- No query interface for cold storage (must retrieve full archive)
- No promotion triggers when patterns become relevant again
- No re-hydration procedures (S3 → L3 knowledge graph)
- Multi-year learning evolution blocked - can't leverage historical insights when market regimes change

### Concrete Examples

**Deprecated Pattern Evidence Loss**:

```text
2023: Pattern "SaaS margin expansion" validated
  - Active status, supporting evidence in Hot tier

2024: Pattern starts underperforming
  - Moved to "probationary" status
  - Evidence migrated to Warm tier

2025: Pattern deprecated after repeated failures
  - DD-009 check: "Active patterns using evidence? NO"
  - Evidence deleted from Cold tier
  - Post-mortem needed: WHY did pattern fail?
  - Evidence gone - investigation blocked
```

**Archive Promotion Need**:

```text
2020: Pattern "High interest rate bank profitability"
  - Active during 2015-2020
  - Archived when rates dropped to near-zero (2020-2021)

2024: Interest rates spike to 5%+
  - 2020-era pattern highly relevant again
  - Archive contains validated evidence + agent analysis
  - But: No mechanism to promote back to active graph
  - Agents rediscover pattern from scratch (wasted effort)
```

### Why Address Now

- **Post-Mortem System (DD-006)** requires deprecated pattern evidence for failure investigations
- **Pattern Re-validation** needs to determine if failures due to market regime changes or original flaws
- **Learning System Evolution** blocked - can't leverage multi-year pattern knowledge
- **Wasted Effort** - agents rediscover archived patterns during regime changes
- **Before Phase 3**: Must solve before pattern validation system launches

---

## Decision

**Implement pattern lifecycle extensions with deprecated retention windows and auto-promote archive system.**

Extends DD-009 with (1) pattern status-aware retention logic providing 18-month protected windows for deprecated patterns requiring Tier 2 archives, and (2) cached index + promotion engine enabling fast archive queries with auto-promotion on regime triggers subject to 48-hour human override.

---

## Options Considered

### Option 1: Extend Retention to All Deprecated Patterns

**Description**: Keep ALL deprecated pattern evidence permanently or very long term (5+ years)

**Pros**:

- Complete protection for post-mortems
- Simple rule - no complex logic
- Never lose investigation capability

**Cons**:

- High storage cost - most deprecated patterns never investigated
- 80%+ of deprecated patterns irrelevant within 2 years
- Doesn't scale - 1000 patterns/year × 5yr × 200MB = 1TB
- No differentiation between early-stage vs validated patterns

**Estimated Effort**: 3 days (update retention logic only)

---

### Option 2: Post-Mortem Archive on Demand

**Description**: No automatic retention - create archive only when human requests post-mortem

**Pros**:

- Minimal storage cost
- Only archive what's actually needed
- Human decides what's important

**Cons**:

- **Critical flaw**: Evidence already deleted when post-mortem requested
- Reactive not proactive - too late to archive
- Defeats purpose of investigation

**Estimated Effort**: 1 week (archive request interface)

---

### Option 3: Status-Aware Retention with Time Windows - **CHOSEN (Gap 1)**

**Description**: Extend DD-009 pattern-aware retention to check pattern status, retain deprecated patterns for fixed window (18 months), require archive sufficiency before deletion

**Pros**:

- Balances cost vs investigation window (most post-mortems within 12mo)
- Tier-specific logic - early-stage patterns need less retention
- Archive sufficiency check prevents premature deletion
- Predictable costs - 18mo window limits growth

**Cons**:

- More complex retention logic (status + age checks)
- Still possible to miss late post-mortems (>18mo)
- Requires Tier 2 archives for late-stage patterns (storage cost)

**Estimated Effort**: 1 week (retention logic + archive checks)

---

### Option 4: Manual Archive Retrieval Only

**Description**: Keep archives in cold storage, require manual S3 retrieval when needed (no promotion system)

**Pros**:

- Simple - no promotion infrastructure
- Low cost - archives stay cold
- Human control over what gets promoted

**Cons**:

- Slow response to regime changes (manual retrieval 1-2 days)
- Misses time-sensitive opportunities
- Archives not searchable/queryable
- High latency for post-mortems (3-10s S3 queries)

**Estimated Effort**: 0 (no new work)

---

### Option 5: Auto-Promote with Human Override - **CHOSEN (Gap 2)**

**Description**: Cached index for fast queries, auto-promote on regime triggers, alert human with 48hr override window

**Pros**:

- Fast regime response - pattern live immediately
- Searchable archives via cached index (<100ms)
- Human oversight - can reject false positives
- Time-sensitive opportunities captured
- Leverages historical knowledge automatically

**Cons**:

- Two systems to maintain (index + cold storage)
- Risk of false positive promotions (mitigated by override window)
- Cached index storage cost (5-10MB per 1000 patterns - negligible)

**Estimated Effort**: 2 weeks (index service + promotion engine + alert system)

---

## Rationale

### Why Status-Aware Retention (Option 3)

1. **Post-Mortem Window**: 18mo covers 90%+ of investigations (most within 12mo of deprecation)
2. **Cost Control**: 18mo retention vs 3yr saves 50% storage, vs permanent saves 90%
3. **Archive Sufficiency**: Prevents deletion if Tier 2 archive missing - forces proper archival before cleanup
4. **Tiered Protection**: Early-stage patterns (candidate/statistically_validated) need less protection - Tier 1 sufficient; late-stage patterns (human_approved/active) need full evidence - Tier 2 required
5. **DD-009 Extension**: Builds on existing pattern-aware retention - minimal code changes

### Why Auto-Promote with Override (Option 5)

1. **Speed vs Safety**: Auto-promote captures opportunities immediately, human override catches false positives within 48hr
2. **Cached Index**: 5-10MB index enables fast search, only retrieve full archive when promoting - 99% cost reduction vs keeping all active
3. **Regime Detection**: Interest rates, inflation regimes, industry cycles make old patterns relevant - system detects automatically
4. **Learning Evolution**: Multi-year knowledge accessible - agents learn from historical patterns without manual retrieval
5. **Human Efficiency**: Alerts notify only when action needed, not blocking workflow

### Why Not Other Options

- **Option 1** (Extend all): Storage cost too high, doesn't differentiate importance
- **Option 2** (On demand): Evidence already gone when requested - defeats purpose
- **Option 4** (Manual only): Too slow for regime changes, archives not searchable

---

## Consequences

### Positive Impacts

- **Post-Mortem Capability**: 18mo window provides evidence for failure investigations
- **Regime Adaptation**: Automatically leverages historical patterns when markets change
- **Learning Evolution**: Multi-year pattern knowledge accessible via cached index
- **Cost Effective**: 18mo window + selective Tier 2 vs permanent retention saves 70% storage
- **Human Oversight**: 48hr override prevents false positives while maintaining speed
- **Searchable Archives**: <100ms index queries vs 3-10s S3 retrieval

### Negative Impacts / Tradeoffs

- **Late Post-Mortems**: Investigations >18mo after deprecation may lack evidence (acceptable - rare)
- **Index Maintenance**: Cached index requires sync with cold storage (additional complexity)
- **Override Burden**: Humans receive alerts for regime promotions (mitigated by 48hr window - can batch review)
- **False Promotions**: Regime triggers may fire incorrectly (mitigated by override + 6mo cooldown before re-deprecation)
- **Storage Coordination**: Track deprecated patterns across tiers + archives + index

### Affected Components

**Services to Implement**:

- `TieredStorageManager` (EXTEND): Add deprecated status checks, 18mo retention logic
- `PatternAwareRetention` (EXTEND): Check archive tier before deletion eligibility
- `ArchiveIndexService` (NEW): Maintain cached pattern metadata in Redis/ElasticSearch
- `ArchiveQueryService` (NEW): S3 interface for full archive retrieval
- `PromotionEngine` (NEW): Regime trigger evaluation, auto-promote logic, confidence scoring
- `PromotionAlertService` (NEW): Human notifications, override handling, audit trail
- `PatternLifecycleManager` (EXTEND): Add retention metadata, promotion history tracking

**Data Pipeline**:

- Deprecated pattern triggers 18mo retention window start
- Archive sufficiency check blocks deletion if Tier 2 missing (late-stage patterns)
- Regime change detection triggers promotion evaluation
- Auto-promote updates L3 graph, alerts human
- Human override demotes pattern back to archive, logs decision

**Documentation**:

- `docs/design-decisions/DD-013_ARCHIVE_LIFECYCLE_MANAGEMENT.md` (this doc)
- `docs/design-decisions/DD-009_DATA_RETENTION_PATTERN_EVIDENCE.md` (add DD-013 reference)
- `docs/learning/01-learning-systems.md` (promotion examples, override procedures)
- `docs/design-flaws/resolved/12-archive-lifecycle.md` (status → resolved_by DD-013)

---

## Implementation Notes

### Extended Retention Logic (Gap 1 Solution)

**Pattern-Aware Retention Update** (extends DD-009 L446-453):

```yaml
Before deleting files from Cold tier:
  1. Query knowledge graph: Does file support any patterns? (any status)
  2. For each pattern found:
     a. If status = "active" → RETAIN (existing DD-009 logic)
     b. If status = "deprecated":
        - Check deprecation_date
        - If deprecation_date < 18 months ago → RETAIN
        - If deprecation_date >= 18 months ago → Check archive sufficiency
     c. Archive Sufficiency Check:
        - If pattern reached "human_approved" or "active" or "probationary" status:
          - Require: archive_tier == 2 (Tier 2 full archive)
          - If Tier 2 exists → SAFE TO DELETE
          - If Tier 2 missing → RETAIN + ALERT (archive gap)
        - If pattern only reached "candidate" or "statistically_validated":
          - Require: archive_tier >= 1 (Tier 1 lightweight sufficient)
          - If Tier 1/2 exists → SAFE TO DELETE
          - If no archive → RETAIN + ALERT
  3. Post-Mortem Lock:
     - If pattern flagged "under_investigation" → RETAIN (regardless of age)
  4. If all checks pass → Eligible for deletion
```

**Example Scenarios**:

```text
Scenario A: Early-stage deprecated pattern
  - Pattern: "candidate" → deprecated 6mo ago
  - Archive tier: 1 (lightweight)
  - Retention check: 6mo < 18mo → RETAIN
  - At 18mo: Tier 1 exists → SAFE TO DELETE

Scenario B: Late-stage deprecated pattern
  - Pattern: "active" → "probationary" → deprecated 12mo ago
  - Archive tier: 1 (lightweight only - GAP!)
  - Retention check: 12mo < 18mo → RETAIN
  - At 18mo: Tier 2 required but missing → RETAIN + ALERT
  - Human creates Tier 2 archive → Then safe to delete

Scenario C: Pattern under post-mortem
  - Pattern: deprecated 20mo ago (>18mo)
  - Archive tier: 2 (full)
  - Investigation flag: under_investigation = true
  - Retention check: Investigation active → RETAIN (override time window)
```

### Archive Index System (Gap 2 Solution)

**Cached Index Schema** (Redis/ElasticSearch):

```yaml
Pattern Archive Index:
  pattern_id: string (UUID)
  pattern_name: string
  pattern_type: string (margin_expansion, debt_reduction, etc)
  status: string (deprecated, archived)
  deprecation_date: timestamp
  archive_tier: int (1 or 2)
  archive_location: string (S3 path)

  # Searchable metadata
  regime_tags: array<string> (high_interest_rate, low_inflation, etc)
  industry_tags: array<string> (SaaS, manufacturing, etc)
  key_metrics: object
    confidence_score: float
    validation_count: int
    historical_accuracy: float

  # Promotion tracking
  last_accessed: timestamp
  access_count_30d: int
  promotion_eligible: boolean
  promotion_history: array<object>
    - promoted_at: timestamp
    - demoted_at: timestamp (if overridden)
    - trigger: string
    - human_decision: string (null | "approved" | "rejected")

Index Updates:
  - Pattern archived → Add to index
  - Pattern accessed → Increment access_count_30d, update last_accessed
  - Promotion → Add to promotion_history
  - Monthly job → Reset access_count_30d, recalc promotion_eligible
```

**Index Size Estimate**:

```text
Per pattern index entry: ~5KB (metadata + tags + history)
1000 patterns/year × 10yr archive × 5KB = 50MB total
Redis cost: ~$0.01/mo (negligible)
```

**Query Interface**:

```yaml
Archive Search API:
  - search_by_regime(regime_tags: array) → pattern_ids
  - search_by_industry(industry_tags: array) → pattern_ids
  - search_by_metrics(confidence_min: float, accuracy_min: float) → pattern_ids
  - get_promotion_candidates(access_threshold: int) → pattern_ids
  - get_pattern_metadata(pattern_id: string) → full_index_entry

Query Performance:
  - Index queries: <100ms (Redis/ElasticSearch)
  - Full archive retrieval (if promoting): 3-5s (S3 GET)
  - Metadata-only queries: No S3 access needed (99% of queries)
```

### Promotion Engine Architecture

**Promotion Triggers**:

```yaml
Trigger Types:
  1. Regime Change Detection:
    - Interest rate shift >2% in 6mo → Query patterns tagged "high_interest_rate"
    - Inflation spike >1% in quarter → Query patterns tagged "inflation_regime"
    - Industry cycle shift → Query patterns by industry_tags
    - Confidence threshold: 0.6+ (historical accuracy)

  2. Access Frequency:
    - Pattern accessed 3+ times in 30 days
    - Multiple agents requesting same archived pattern
    - Suggests current relevance

  3. Post-Mortem Request:
    - Human explicitly requests pattern for investigation
    - Immediate promotion (no trigger evaluation)

  4. Re-Validation Request:
    - Pattern validation system requests historical pattern for comparison
    - Auto-promote for validation, demote after completion

Trigger Evaluation Logic:
  - Check trigger conditions (regime change, access frequency, etc)
  - Query index for matching patterns
  - Filter by confidence threshold (0.6+ for regime, no threshold for access frequency)
  - Score promotion candidates (0.0-1.0)
  - Auto-promote if score >0.7
  - Alert human with context
```

**Auto-Promotion Workflow**:

```text
1. Trigger fires (e.g., interest rate spike detected)
2. PromotionEngine queries index: search_by_regime(["high_interest_rate"])
3. Returns 5 matching patterns with confidence >0.6
4. For each pattern:
   a. Retrieve full archive from S3 (3-5s)
   b. Validate archive integrity
   c. Re-hydrate to L3 knowledge graph
   d. Add staleness metadata (archived_date, promotion_trigger, confidence_at_archive)
   e. Update status: "deprecated" → "active_from_archive"
5. Alert human:
   - "5 patterns promoted: Interest rate regime change detected"
   - Context: Trigger reason, pattern summaries, confidence scores
   - Action: Review in next 48hr, override if false positive
6. 48hr window:
   - Human reviews → Approves (no action) or Rejects (demotes pattern)
   - If rejected: Pattern demoted, trigger disabled for 6mo cooldown
   - If approved or timeout: Promotion permanent
```

**Re-Hydration Pipeline**:

```yaml
Archive → Active Graph Restoration:
  1. Retrieve from S3:
     - Pattern definition, validation history
     - Supporting evidence references
     - Agent analysis, debate logs (Tier 2 only)

  2. Validate Integrity:
     - Check archive version compatibility
     - Verify evidence references (warn if aged out)
     - Validate metrics schema

  3. Restore to L3 Graph:
     - Create pattern node with archived data
     - Add staleness metadata:
       - archived_at: timestamp
       - promoted_at: timestamp
       - promotion_trigger: string
       - staleness_warning: boolean (evidence >7yr old)
     - Restore relationships (if evidence still exists)

  4. Mark as Probationary:
     - Status: "active_from_archive" (not full "active")
     - Requires re-validation on new data before investment decisions
     - Probationary period: 3-6mo or 2 successful validations

  5. Update Index:
     - promotion_history: Add entry
     - last_accessed: Update timestamp
```

**Cooldown Logic**:

```yaml
Re-Deprecation Protection:
  - Promoted pattern observed for 6 months minimum
  - Cannot re-deprecate until 2+ validation failures
  - Prevents promotion/demotion thrashing
  - If human overrides promotion → 6mo trigger cooldown (won't re-promote same pattern)
```

### Human Alert System

**Alert Format**:

```yaml
Promotion Alert:
  alert_type: 'pattern_promotion'
  trigger: 'regime_change_interest_rate'
  promoted_count: 5
  patterns:
    - pattern_id: 'uuid-1234'
      pattern_name: 'Bank profitability in high-rate environment'
      confidence_score: 0.82
      historical_accuracy: 0.75
      last_used: '2020-03-15'
      reason: 'Interest rates increased 2.5% in 6mo (trigger threshold: 2%)'
    - [4 more patterns...]

  action_required: 'Review and override if needed (48hr window)'
  deadline: '2025-11-20 14:30 UTC'
  override_url: '/patterns/promotion/batch-12345/override'

Alert Delivery:
  - In-app notification (dashboard)
  - Email digest (batched daily if <10 patterns, immediate if >10)
  - Slack/Teams integration (optional)

Override Interface:
  - Batch review: Approve all, Reject all, Individual selection
  - Rejection reason required (false_regime_signal, pattern_obsolete, other)
  - Override logged to audit trail
```

**Override Handling**:

```text
Human Override Actions:
  1. Approve Promotion:
     - No action needed (default after 48hr)
     - Pattern stays active, promotion permanent

  2. Reject Promotion (Individual):
     - Pattern demoted back to archive
     - Trigger cooldown: 6mo for this pattern + trigger combo
     - Reason logged for learning

  3. Reject Promotion (Trigger Type):
     - All patterns from this trigger batch demoted
     - Trigger sensitivity adjustment (e.g., raise interest rate threshold from 2% to 3%)
     - System learns to reduce false positives
```

### Integration Points

**Pattern Deprecation Flow**:

```text
1. Pattern moved to "deprecated" status
2. PatternLifecycleManager:
   a. Set deprecation_date = now()
   b. Check max_status_reached (candidate/validated/approved/active)
   c. Verify archive tier matches requirement
   d. If Tier 2 required but missing → Create Tier 2 archive
   e. Start 18mo retention window
3. Update archive index: status = "deprecated"
4. TieredStorageManager: Flag supporting evidence for 18mo retention
```

**Regime Change Detection Flow**:

```text
1. External signal (interest rate API, macro indicator service)
2. RegimeDetector evaluates thresholds
3. If regime shift detected:
   a. PromotionEngine.trigger("regime_change_interest_rate")
   b. Query index for matching patterns
   c. Score and filter promotion candidates
   d. Auto-promote eligible patterns (score >0.7)
   e. Alert human with batch summary
4. Human reviews within 48hr, overrides if needed
```

**Post-Mortem Investigation Flow**:

```text
1. Human requests post-mortem on deprecated pattern
2. Check pattern status:
   a. If <18mo since deprecation → Evidence should exist
   b. If >18mo → Check archive tier
3. If evidence missing:
   a. If Tier 2 archive exists → Retrieve from S3
   b. If no archive → Investigate why (archive gap alert)
4. Flag pattern: under_investigation = true
5. Retention override: RETAIN evidence regardless of age
6. Post-mortem completes → Clear investigation flag
```

### Testing Requirements

**Retention Logic Tests**:

- Verify deprecated patterns retained for 18mo
- Test archive sufficiency checks (Tier 1 vs Tier 2 requirements)
- Validate post-mortem lock prevents premature deletion
- Test edge case: Pattern deprecated → archived → re-promoted → deprecated again

**Index Sync Tests**:

- Archive creation triggers index entry
- Pattern promotion updates index
- Access tracking increments correctly
- Monthly reset of access_count_30d

**Promotion Engine Tests**:

- Regime triggers fire correctly (threshold testing)
- Access frequency promotion (3+ hits/30d)
- Confidence filtering (0.6+ threshold)
- Auto-promote workflow end-to-end
- Human override flow (approve/reject)
- Cooldown logic (6mo re-deprecation protection)

**Re-Hydration Tests**:

- Archive retrieval from S3 (3-5s latency)
- Integrity validation (version compatibility)
- L3 graph restoration (node + relationships)
- Staleness metadata added correctly
- Probationary status set

### Rollback Strategy

**If retention logic causes issues**:

1. Disable deprecated retention → Revert to DD-009 active-only checks (temporary)
2. Extend 18mo window to 24mo if post-mortems missing evidence
3. Force Tier 2 archives for all deprecated patterns (higher cost, full protection)

**If promotion system causes issues**:

1. Disable auto-promote → Require manual promotion approval (slower, safer)
2. Increase trigger thresholds (reduce false positives)
3. Disable specific trigger types (e.g., only access frequency, not regime)
4. Full rollback: Archive queries only, no promotion (Option 4)

**Estimated Implementation Effort**: 2 weeks

- Week 1: Extended retention logic + archive sufficiency checks + testing
- Week 2: Cached index + promotion engine + alert system + integration testing

**Dependencies**:

- DD-009 implemented (tiered storage + pattern archives)
- Pattern lifecycle state machine operational
- Regime detection service (interest rates, macro indicators)
- Redis/ElasticSearch infrastructure for cached index
- S3/cloud storage for cold archives

---

## Open Questions

None - all decisions finalized:

1. ✅ Retention period: 18 months for deprecated patterns
2. ✅ Archive sufficiency: Tier 2 for late-stage, Tier 1 for early-stage
3. ✅ Promotion strategy: Auto-promote with 48hr human override
4. ✅ Index system: Cached index (Redis/ElasticSearch) for fast queries

**Blocking**: No

---

## References

- **Design Flaws**: [Flaw #12 - Pattern Archive Lifecycle Gaps](../design-flaws/resolved/12-archive-lifecycle.md)
- **Related Decisions**:
  - DD-005: Memory Scalability Optimization (archive storage strategy)
  - DD-007: Pattern Validation Architecture (pattern lifecycle states)
  - DD-009: Data Retention & Pattern Evidence (extends this decision)
- **Pattern Lifecycle**: docs/learning/01-learning-systems.md L27-37 (candidate → deprecated states)
- **Memory System**: docs/architecture/02-memory-system.md L996-1000 (archival process)

---

## Status History

| Date       | Status   | Notes                                            |
| ---------- | -------- | ------------------------------------------------ |
| 2025-11-18 | Proposed | Initial proposal based on Flaw #12 analysis      |
| 2025-11-18 | Approved | 18mo retention, auto-promote with human override |

---

## Notes

### Cost Estimate

```text
Deprecated Pattern Retention (18mo window):
  Assumptions:
    - 1000 patterns/year, 20% reach deprecation
    - Average 6mo before deprecation
    - 200 deprecated patterns × 200MB evidence = 40GB

  18mo Retention Cost:
    - Extended retention: 40GB × 18mo effective × $0.001 (Cold) = $0.72/mo
    - Tier 2 archives (20% late-stage): 40 patterns × 100MB × 10yr × $0.001 = $0.40/mo
    - Subtotal: $1.12/mo

Cached Index Cost:
  - 10 years of patterns: 10,000 patterns × 5KB = 50MB
  - Redis: 50MB × $0.0002/MB/mo = $0.01/mo (negligible)

Total Additional Cost vs DD-009: ~$1.13/mo
Total System Cost (DD-009 + DD-013): ~$6.42/mo

Cost per deprecated pattern with full investigation capability: $0.056/mo
vs. losing post-mortem capability: Priceless
```

### Future Considerations

- **Regime Trigger Calibration**: Adjust thresholds based on false positive rates (e.g., interest rate 2% → 2.5% if too sensitive)
- **Archive Compression**: Tier 2 archives could use compression for older patterns (50% storage savings)
- **Multi-Regime Patterns**: Patterns matching multiple regime tags - prioritize for promotion
- **Auto-Demotion**: After 12mo active-from-archive with no validations → Auto-demote back to archive
- **Pattern Summarization**: Add lightweight summaries to index for preview without S3 retrieval (DD-009 Option 2 hybrid)
