# DD-009: Data Retention & Pattern Evidence Architecture

**Status**: Approved
**Date**: 2025-11-17
**Decider(s)**: System Architect
**Related Docs**:

- [Memory System](../architecture/02-memory-system.md)
- [Data Management](../operations/03-data-management.md)
- [Learning Systems](../learning/01-learning-systems.md)
- [Pattern Validation](DD-007_PATTERN_VALIDATION_ARCHITECTURE.md)
  **Related Decisions**: DD-005 (Memory Scalability), DD-006 (Negative Feedback), DD-007 (Pattern Validation), DD-013 (Archive Lifecycle - extends this decision)

---

## Context

### Problem Statement

**Data Retention Conflict**: Patterns stored permanently in central knowledge graph, but supporting evidence (SEC filings, financial statements) deleted after 3-5 years. This creates:

- **Pattern Orphaning**: Cannot re-validate patterns when supporting evidence deleted
- **Broken Audit Trails**: Investment decisions lack supporting documentation for compliance
- **Failed Post-Mortems**: Cannot investigate pattern failures without original data
- **Learning System Degradation**: Historical knowledge lost, can't train agents on why patterns existed

### Concrete Example

```text
2020: Analyze Company XYZ
  - Pattern discovered: "SaaS margin expansion in growth phase"
  - Based on XYZ + 4 companies (2015-2020 data)

2025: Pattern starts failing
  - Need to investigate why pattern broke
  - Original 2015-2020 data deleted (beyond 5yr retention)
  - Cannot verify if pattern was originally valid
  - Cannot determine what changed
```

### Why Address Now

- **Pattern Validation (DD-007)** requires evidence for re-testing on hold-out data
- **Post-Mortem System (DD-006)** needs historical data for failure investigation
- **Agent Credibility (DD-008)** tracks accuracy by comparing predictions to evidence
- **Regulatory Risk**: Cannot justify historical investment decisions when evidence deleted
- **Before Production**: Must solve before Phase 4 when first retention expirations occur

---

## Decision

**Implement tiered storage with two-tier pattern archive system and multi-criteria critical pattern identification.**

Primary approach uses graduated storage tiers (Hot→Warm→Cold) with pattern-aware retention logic, supplemented by selective archiving of critical pattern evidence. Archives use lightweight (metadata + processed summaries) and full (complete processed data) tiers based on pattern importance.

---

## Options Considered

### Option 1: Pattern Archive

**Description**: Archive complete evidence when pattern created, retain 15+ years

**Pros**:

- Complete evidence preservation for all patterns
- Simple implementation (copy files on pattern creation)
- Guaranteed re-validation capability
- Strong audit trail for compliance

**Cons**:

- High storage costs (duplicate all evidence for every pattern)
- 80-90% of patterns never used in decisions (wasted archival)
- 15 years may be excessive (most patterns obsolete sooner)
- Scales poorly (1000 stocks/year × 50MB × 15yr = 750GB+)

**Estimated Effort**: 1 week (archive manager service)

---

### Option 2: Evidence Summarization

**Description**: Create permanent summaries before data deletion

**Pros**:

- Low storage cost (summaries vs full files)
- Preserves key insights even when evidence deleted
- Flexible summary format (can include pattern-specific excerpts)

**Cons**:

- Lossy compression (original evidence still lost)
- Cannot fully re-validate patterns from summaries
- Complex summarization logic (what to include?)
- May miss critical details in summary

**Estimated Effort**: 2 weeks (summarization engine, format design)

---

### Option 3: Tiered Storage

**Description**: Migrate aging data to cheaper storage tiers instead of deleting

**Pros**:

- Very low cost (Cold storage $0.001/GB/mo vs $0.023 Hot)
- Complete evidence preserved (non-lossy)
- Transparent to system (same files, different storage class)
- Scales well (750GB historical = $8/mo)

**Cons**:

- Slower access times for old data (Cold tier: ~3s vs 10ms)
- Requires cloud storage infrastructure
- Still need retention policy (can't keep forever)

**Estimated Effort**: 1 week (tiered migration service)

---

### Option 4: Hybrid (Tiered + Selective Archive) - **CHOSEN**

**Description**: Combine tiered storage (primary) with selective archiving (critical patterns only)

**Pros**:

- Cost-effective (tiered storage handles most data)
- Critical patterns fully protected (archive processed data)
- Scalable (only 10-20% of patterns archived)
- Flexible retention periods (7yr standard, 10yr critical)
- Non-lossy for important patterns

**Cons**:

- Two systems to maintain (tiered storage + archive manager)
- Need criteria for "critical" pattern (multi-factor scoring)
- Two-tier archive adds complexity

**Estimated Effort**: 2 weeks (tiered storage + archive manager + scoring)

---

## Rationale

### Why Hybrid Approach

1. **Cost vs. Coverage**: Tiered storage cheap enough to keep all data accessible 7-10yr, selective archive adds protection for critical patterns
2. **Regulatory Compliance**: 7yr retention meets SEC requirements, 10yr for investment decisions provides extra safety
3. **Scalability**: Archive only 10-20% of patterns (those actually used in decisions) vs 100%
4. **Learning System Needs**: DD-007 pattern validation requires evidence; selective archive ensures high-impact patterns always re-validatable
5. **Post-Mortem Capability**: DD-006 failure investigation needs deep dives on critical patterns; full archive enables this

### Why 7-10 Year Retention (Not 15)

- **7 years**: Standard regulatory compliance (SEC, audit trail requirements)
- **10 years**: Full business cycle coverage, multiple re-validation opportunities
- **Not 15**: Most patterns obsolete by then due to market/industry evolution
- **Cold storage economics**: $0.001/GB/mo makes 10yr vs 15yr cost difference negligible (~$3/mo)

### Why Processed Data + Metadata (Not Full Raw)

- **70% storage savings**: Processed financial statements ~15MB vs raw SEC filing ~50MB
- **Sufficient for re-validation**: Processed data contains normalized metrics, ratios needed for testing
- **Metadata enables tracing**: References to raw files still in Cold tier (7-10yr) or can request from SEC
- **Full raw only for critical**: If pattern super-critical AND evidence aged out, can optionally archive raw

---

## Consequences

### Positive Impacts

- **Pattern Validation Enabled**: DD-007 re-validation works for 7-10yr window
- **Post-Mortem Capability**: DD-006 failure investigation has evidence for critical patterns
- **Regulatory Compliance**: 7yr+ audit trail, investment decisions fully documented
- **Cost-Effective**: ~$8.65/mo for 750GB Cold + 50GB archives (vs $172.50 all Hot storage)
- **Learning System Integrity**: Agents can study historical patterns, understand why decisions made
- **Scalable**: Selective archiving (10-20% patterns) vs 100%

### Negative Impacts / Tradeoffs

- **Access Latency**: Cold tier ~3s retrieval vs 10ms Hot (acceptable for historical analysis)
- **Two Systems**: Tiered storage + archive manager (increased complexity)
- **Pattern Scoring Logic**: Multi-criteria "critical" determination requires ongoing calibration
- **Storage Coordination**: Must track files across tiers and archives (metadata management)
- **Partial Coverage**: Non-critical patterns lose evidence after 7yr (acceptable tradeoff)

### Affected Components

**Services to Implement**:

- `TieredStorageManager`: Migrate files Hot→Warm→Cold based on age
- `PatternAwareRetention`: Check pattern dependencies before Cold→Delete
- `PatternArchiveManager`: Create Tier 1/2 archives based on scoring
- `CriticalPatternScorer`: Multi-criteria evaluation for archive decisions

**Data Pipeline**:

- Pattern creation triggers Tier 1 lightweight archive (after first validation)
- Investment decision triggers Tier 2 full archive
- Data aging pipeline checks pattern dependencies before deletion
- Migration service moves files through tiers on schedule

**Documentation**:

- `docs/architecture/02-memory-system.md`: Pattern archive schema
- `docs/operations/03-data-management.md`: Retention policies
- `docs/learning/01-learning-systems.md`: Evidence requirements
- `docs/implementation/01-roadmap.md`: Phase 4 tasks

---

## Implementation Notes

### Tiered Storage Architecture

```yaml
Storage Tiers:
  Hot:
    retention: 0-2 years
    cost_per_gb_month: $0.023
    access_time: 10ms
    use_case: Active analysis

  Warm:
    retention: 2-5 years
    cost_per_gb_month: $0.010
    access_time: 100ms
    use_case: Recent re-validation

  Cold:
    retention: 5-10 years
    cost_per_gb_month: $0.001
    access_time: 3000ms
    use_case: Historical investigation, pattern re-validation

Migration Rules:
  - Age 0-2yr: Keep in Hot
  - Age 2-5yr: Migrate to Warm
  - Age 5-10yr: Migrate to Cold (if supports active patterns) OR Delete (if no dependencies)
  - Age 10yr+: Delete (unless critical pattern archive exists)
```

### Two-Tier Pattern Archive System

**Tier 1: Lightweight Archive** (Created at first validation pass)

```yaml
Trigger: Pattern validated successfully (not at creation)
Content:
  - metadata.json: Pattern definition, confidence, validation results
  - processed_summary.json: Key metrics, ratios, peer comparisons (1-5MB)
  - analysis_snapshot.json: Agent findings, evidence references
Size: 1-5MB per pattern
Retention: 7 years
Purpose: Safety net if evidence ages out before decision
```

**Tier 2: Full Archive** (Created at investment decision)

```yaml
Trigger: Pattern used in investment decision OR becomes critical (2-of-4 criteria)
Content:
  - All Tier 1 content
  - Full processed data: Financial statements, ratios, peer data (50-200MB)
  - Agent analysis: Complete findings, confidence tracking, debate logs
  - Validation history: All re-validation results, degradation tracking
Size: 50-200MB per pattern
Retention: 10 years
Purpose: Deep post-mortems, regulatory compliance, agent training
```

### Critical Pattern Multi-Criteria Scoring

**2-of-4 Criteria** (any 2 triggers Tier 2 full archive):

```yaml
Critical Pattern Criteria:
  1. used_in_investment_decision: true
     Weight: HIGHEST (any investment decision auto-qualifies)

  2. confidence_score: >0.7
     Rationale: Statistical strength, low false positive risk

  3. impact_score: >0.5
     Definition: Influenced >$50K position OR >10% portfolio allocation
     Rationale: Material financial impact

  4. validation_count: >=3
     Rationale: Proven track record, not lucky coincidence

Scoring Logic:
  - Score = sum(criteria_met)
  - Score >= 2: Create Tier 2 archive
  - Score == 1: Keep Tier 1 only
  - Score == 0: No archive (rely on tiered storage)
```

**Example Scoring**:

```text
Pattern A: Investment decision (✓) + Confidence 0.8 (✓) → Score 2 → Tier 2 Archive
Pattern B: Confidence 0.9 (✓) + Validations 5 (✓) → Score 2 → Tier 2 Archive
Pattern C: Confidence 0.6 (✗) + Validations 2 (✗) → Score 0 → No Archive
```

**Estimated Archive Rate**: 10-20% of patterns (manageable storage)

### Storage Structure

```text
/data
├── /raw (Tiered: Hot → Warm → Cold → Delete)
│   ├── /sec_filings
│   ├── /transcripts
│   ├── /market_data
│   └── /news_articles
│
├── /processed (Tiered: Hot → Warm → Cold → Delete)
│   ├── /financial_statements
│   ├── /ratios
│   ├── /sentiment_scores
│   └── /peer_comparisons
│
├── /memory
│   ├── /pattern_archives/
│   │   ├── /{pattern_id}/
│   │   │   ├── tier1/
│   │   │   │   ├── metadata.json
│   │   │   │   ├── processed_summary.json
│   │   │   │   └── analysis_snapshot.json
│   │   │   ├── tier2/  (if critical)
│   │   │   │   ├── all_tier1_content/
│   │   │   │   ├── processed_data/
│   │   │   │   │   ├── financial_statements/
│   │   │   │   │   ├── ratios/
│   │   │   │   │   └── peer_comparisons/
│   │   │   │   ├── agent_analysis/
│   │   │   │   └── validation_history/
│   │   │   └── archive_metadata.json
│   │   └── /index.json  (pattern_id → archive_tier mapping)
│   └── /knowledge_graph (Permanent)
```

### Knowledge Graph Schema Extensions

```yaml
Pattern Node Extensions:
  evidence_refs: array<string> # File paths to supporting evidence
  archive_tier: int # 0 (none), 1 (lightweight), 2 (full)
  archive_refs: array<string> # Archive file paths
  is_critical: boolean # 2-of-4 criteria met
  critical_score: int # 0-4 based on criteria

  # Critical criteria tracking
  used_in_investment_decision: boolean
  confidence_score: float
  impact_score: float
  validation_count: int

New Relationships:
  - Pattern -[SUPPORTED_BY_FILE]-> RawDataFile
  - Pattern -[HAS_ARCHIVE {tier: 1|2}]-> ArchiveDirectory
```

### Integration Points

**Pattern Creation Flow**:

1. Specialist agent discovers pattern
2. Pattern stored in knowledge graph (no archive yet)
3. Pattern enters validation queue

**Pattern Validation Flow**:

1. Pattern validated successfully (DD-007)
2. **Trigger Tier 1 Archive**: Archive manager creates lightweight archive
3. Update pattern node: `archive_tier=1`, `archive_refs=[...]`

**Investment Decision Flow**:

1. Pattern used in investment recommendation
2. **Trigger Tier 2 Archive**: Archive manager promotes to full archive
3. Update pattern node: `is_critical=true`, `used_in_investment_decision=true`, `archive_tier=2`

**Data Aging Flow**:

1. Scheduled job checks files eligible for tier migration/deletion
2. **Pattern-Aware Check**: Query knowledge graph for patterns referencing file
3. If active patterns exist: Keep in Cold tier (7-10yr)
4. If no patterns: Safe to delete
5. Before deletion: Check if file in any pattern archive (if yes, safe to delete)

### Testing Requirements

- **Tier Migration**: Verify Hot→Warm→Cold transitions at correct age thresholds
- **Archive Creation**: Test Tier 1 created at validation, Tier 2 at decision
- **Critical Scoring**: Test 2-of-4 criteria combinations, edge cases
- **Pattern-Aware Retention**: Verify files with pattern dependencies not deleted prematurely
- **Cost Tracking**: Monitor storage costs by tier, archive size distributions
- **Access Latency**: Test Cold tier retrieval acceptable for post-mortems (<5s)

### Rollback Strategy

If tiered storage causes issues:

1. Migrate all Cold tier back to Warm (higher cost, faster access)
2. If archive system fails: Extend base retention to 10yr (temporary)
3. If critical scoring over-archives: Raise threshold to 3-of-4 criteria
4. Full rollback: Return to original 3-5yr retention (lose pattern validation capability)

**Estimated Implementation Effort**: 2 weeks

**Dependencies**:

- Pattern storage system operational (DD-005)
- Pattern validation framework (DD-007)
- Cloud storage infrastructure (AWS S3/Glacier or GCP Standard/Archive)
- Knowledge graph query optimization for file→pattern lookups

---

## Open Questions

None - all critical questions resolved during design:

1. ✅ Approach: Tiered + Selective Archive (hybrid)
2. ✅ Retention period: 7yr standard, 10yr critical
3. ✅ Archive content: Processed + metadata (not full raw)
4. ✅ Critical threshold: 2-of-4 multi-criteria
5. ✅ Archive timing: Tier 1 at validation, Tier 2 at decision

**Blocking**: No

---

## References

- **Design Flaws**: [Flaw #5 - Data Retention Policy Conflict](../design-flaws/resolved/05-data-retention.md)
- **Related Decisions**:
  - DD-005: Memory Scalability Optimization (archive storage strategy)
  - DD-006: Negative Feedback System (mentions "Pattern evidence retained for re-validation")
  - DD-007: Pattern Validation Architecture (requires evidence for re-testing)
  - DD-008: Agent Credibility System (tracks accuracy vs original evidence)
- **Cloud Storage Pricing**:
  - AWS S3 Standard: $0.023/GB/mo
  - AWS S3 Infrequent Access: $0.010/GB/mo
  - AWS Glacier: $0.001/GB/mo
- **Regulatory**: SEC 17 CFR 240.17a-4 (7-year record retention for investment advisors)

---

## Status History

| Date       | Status   | Notes                                      |
| ---------- | -------- | ------------------------------------------ |
| 2025-11-17 | Proposed | Initial proposal based on Flaw #5 analysis |
| 2025-11-17 | Approved | Multi-criteria approach, 7-10yr retention  |

---

## Notes

### Cost Estimate

```text
Assumptions:
- 1000 stocks analyzed per year
- 50MB raw data + 15MB processed per analysis
- 50GB raw/year, 15GB processed/year

Tiered Storage (7yr retention, pattern-dependent):
  Year 0-2 (Hot):    100GB raw + 30GB processed = 130GB × $0.023 = $2.99/mo
  Year 2-5 (Warm):   150GB raw + 45GB processed = 195GB × $0.010 = $1.95/mo
  Year 5-7 (Cold):   100GB raw + 30GB processed = 130GB × $0.001 = $0.13/mo
  Subtotal: $5.07/mo

Pattern Archives (10yr retention, 10-20% of patterns):
  Tier 1 (80% of patterns): 800 patterns/yr × 3MB × 7yr = 16.8GB × $0.001 = $0.02/mo
  Tier 2 (20% of patterns): 200 patterns/yr × 100MB × 10yr = 200GB × $0.001 = $0.20/mo
  Subtotal: $0.22/mo

Total Storage Cost: ~$5.29/mo
vs. All Hot Storage: 1000GB × $0.023 = $23/mo
Savings: 77% cost reduction

Cost per pattern with full evidence trail: $0.005/mo
vs. losing pattern validation capability: Priceless
```

### Future Considerations

- **Pattern Decay**: Archived patterns with low validation scores could be demoted (Tier 2 → Tier 1)
- **Evidence Reconstruction**: If critical pattern needs evidence beyond 10yr, could request from SEC EDGAR (public filings)
- **Summarization Supplement**: Could add summarization layer as tertiary backup (DD-009-v2 enhancement)
- **Selective Raw Archiving**: Super-critical patterns (>$1M decisions) could archive full raw files (opt-in)

**Note**: DD-013 (Archive Lifecycle Management) extends this decision to address deprecated pattern retention and archive promotion capabilities.
