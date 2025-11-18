# Memory Architecture

## Hybrid Memory Model

The system implements a four-tier hybrid memory architecture combining centralized knowledge with distributed agent-specific memories and execution state persistence:

```text
┌─────────────────────────────────────────────┐
│      Central Knowledge Graph (Neo4j)         │
│  Companies | Patterns | Decisions | Outcomes │
└─────────────────────────────────────────────┘
                    ▲ ▼ Sync
┌─────────────────────────────────────────────┐
│   Checkpoint Storage (PostgreSQL + Redis)    │
│   Agent State | Subtask Progress | Recovery  │
└─────────────────────────────────────────────┘
                    ▲ ▼ Save/Restore
┌──────────────┬──────────────┬───────────────┐
│   L2 Cache   │   L2 Cache   │   L2 Cache    │
│ Specialized  │ Specialized  │ Specialized   │
├──────────────┼──────────────┼───────────────┤
│  Financial   │   Strategy   │   Valuation   │
│    Agent     │    Agent     │     Agent     │
│ L1: Working  │ L1: Working  │  L1: Working  │
└──────────────┴──────────────┴───────────────┘
```

---

## Memory Hierarchy

### L1: Agent Working Memory (RAM)

- **Purpose**: Immediate context for current analysis
- **Contents**: Active calculations, current company data, debate context
- **Size**: ~100 items per agent
- **TTL**: 24h (active), 14d (paused, [DD-016](../design-decisions/DD-016_L1_MEMORY_DURABILITY.md))
- **Access Time**: <10ms

### L2: Agent Specialized Cache (Local Database)

- **Purpose**: Domain-specific patterns and frequently accessed data
- **Contents**:
  - Financial Agent: Ratio patterns, peer comparisons, accounting rules
  - Strategy Agent: Management patterns, capital allocation histories
  - Valuation Agent: Model templates, multiple histories, sector norms
- **Size**: ~10,000 items per agent
- **TTL**: Weeks (with refresh)
- **Access Time**: <100ms

### L3: Central Knowledge Graph (Graph Database)

- **Purpose**: Permanent institutional knowledge
- **Contents**: All analyses, decisions, outcomes, patterns, relationships
- **Size**: Unlimited
- **TTL**: Permanent
- **Access Time**: <1s

### Checkpoint Storage (Execution State Persistence)

- **Purpose**: Agent execution state for failure recovery and pause/resume
- **Contents**: Subtask progress, working memory snapshot (L1 dump), interim results, execution context, failure details
- **Storage**: Dual-tier
  - PostgreSQL (durable, permanent record)
  - Redis (fast recovery, 7-day TTL)
- **Trigger**: Save after each subtask completion
- **Access Time**: <5s (Redis), <30s (PostgreSQL fallback)
- **Retention**: Delete on analysis success, 30-day retention for failures

See [DD-011 Agent Checkpoint System](../design-decisions/DD-011_AGENT_CHECKPOINT_SYSTEM.md) for complete design.

### L1 Durability & Recovery

**Purpose**: Preserve agent working memory across multi-day pauses and failures without duplicate work.

L1 working memory (Redis) uses dual-layer snapshot system to survive pauses and crashes. Without durability, agents must re-fetch API data (wasting quota), re-parse documents (wasting time), and re-calculate interim results on resume.

**5-Component Architecture**:

1. **L1TTLManager**: Dynamic TTL management
   - Active analysis: 24h TTL (normal working memory)
   - Paused analysis: 14d TTL (extended for multi-day pauses)
   - Auto-restore to 24h on resume

2. **L1CacheSnapshotter**: Per-agent snapshots with hybrid triggers
   - **During analysis**: Piggyback on checkpoint events → Redis secondary only (fast ~100ms)
   - **On pause**: Force dual snapshot → Redis secondary + PostgreSQL (durability)
   - Type preservation: All Redis types (string, list, hash, set, zset) preserved

3. **L1CacheRestorer**: Restore from snapshot with type preservation
   - Restore performance: <5s (Redis secondary), <30s (PostgreSQL fallback)
   - Clears stale L1 keys before restore to avoid conflicts
   - Restores active 24h TTL on resume

4. **ConsistencyVerifier**: Hash-based validation on restore
   - SHA256 hash of sorted L1 keys + values
   - Detects partial restore failures, stale data, corruption
   - Fail-fast on mismatch

5. **DualRecoveryStrategy**: 3-tier fallback chain
   - Tier 1: L1 still exists (fastest, just restore TTL)
   - Tier 2: Redis secondary snapshot (fast <5s)
   - Tier 3: PostgreSQL checkpoint (durable <30s)

**Redis Data Structures**:

```
# Per-agent snapshot keys
fas:l1_snapshot:{agent_id} = <JSONB snapshot with type metadata>
fas:l1_snapshot_meta:{agent_id} = {timestamp, hash, checkpoint_id, key_count}

# Agent L1 working memory keys
L1:{agent_id}:working:* = <agent-specific working memory>
```

**PostgreSQL Schema Extension**:

```sql
-- Extends agent_checkpoints table from DD-011
ALTER TABLE agent_checkpoints ADD COLUMN l1_snapshot JSONB;
ALTER TABLE agent_checkpoints ADD COLUMN l1_snapshot_hash TEXT;
```

**Integration with Checkpoint & Pause Systems**:

- **DD-011 Checkpoint**: Hooks snapshot on checkpoint save (Redis secondary only during analysis)
- **DD-012 Pause**: Triggers TTL extension + full dual snapshot on pause, restore + verification on resume
- **AgentMemory**: Per-agent L1 key namespacing ensures isolation

**Performance Characteristics**:

- Snapshot overhead: ~100ms (Redis-to-Redis copy)
- Restore latency: <5s typical, <30s worst-case
- Storage overhead: ~100 KB per agent × 5 agents/stock × 200 stocks = 100 MB total
- Zero duplicate work on resume (API quota savings, time savings)

See [DD-016 L1 Memory Durability](../design-decisions/DD-016_L1_MEMORY_DURABILITY.md) for complete design, rollback strategy, and testing requirements.

---

## Knowledge Graph Schema

```yaml
Nodes:
  Company:
    - ticker: string
    - sector: string
    - analyzed_count: integer
    - last_analysis: datetime

  Analysis:
    - id: string
    - date: datetime
    - recommendation: enum
    - confidence: float
    - outcome: float

  Pattern:
    - name: string
    - category: string
    - success_rate: float
    - occurrence_count: integer
    - status: enum [candidate, statistically_validated, human_approved, active, rejected_holdout, rejected_blind, rejected_statistical, deprecated]
    - training_correlation: float
    - validation_correlation: float
    - test_correlation: float
    - blind_test_score: float
    - control_p_value: float
    - validation_sample_size: integer
    - validated_date: datetime
    - approved_date: datetime
    - last_performance_check: datetime
    - quarantined: boolean

  Decision:
    - id: string
    - type: string
    - agents_involved: array
    - outcome: enum

  Agent:
    - name: string
    - specialization: string
    - accuracy_scores: object
    - total_decisions: integer

  SourceCredibility:
    - source_name: string
    - source_type: string
    - base_accuracy: float
    - hierarchy_weight: float
    - temporal_decay_halflife: float
    - contradiction_count: integer
    - resolution_outcomes: object
    - last_updated: datetime

  DataContradiction:
    - id: string
    - data_point: string
    - source_a: string
    - source_b: string
    - value_a: float
    - value_b: float
    - resolution_level: enum [1_evidence, 2_credibility, 3_human, 4_fallback]
    - resolution_method: string
    - final_value: float
    - credibility_differential: float
    - timestamp: datetime
    - priority: enum [CRITICAL, HIGH, MEDIUM, LOW]
    - provisional: boolean
    - reviewed_at_gate3: boolean

Relationships:
  - Company -[HAS_ANALYSIS]-> Analysis
  - Analysis -[IDENTIFIED_PATTERN]-> Pattern
  - Analysis -[LED_TO]-> Decision
  - Decision -[HAS_OUTCOME]-> Outcome
  - Agent -[PERFORMED]-> Analysis
  - Agent -[MADE]-> Decision
  - Pattern -[SIMILAR_TO]-> Pattern
  - Company -[PEER_OF]-> Company
  - DataContradiction -[RESOLVED_BY_SOURCE]-> SourceCredibility
  - Analysis -[HAS_CONTRADICTION]-> DataContradiction
  - SourceCredibility -[PROVIDED_DATA_FOR]-> Analysis
```

### Pattern Validation Knowledge Graph Extensions

To support the 3-tier pattern validation system ([DD-007](../design-decisions/DD-007_PATTERN_VALIDATION_ARCHITECTURE.md)), the knowledge graph includes specialized nodes and relationships for tracking validation metadata:

```yaml
Additional Nodes for Pattern Validation:
  PatternValidation:
    - pattern_id: string
    - validation_type: enum [holdout, blind_test, control_group]
    - test_start_date: datetime
    - test_end_date: datetime
    - passed: boolean
    - test_correlation: float
    - sample_size: integer
    - p_value: float (for control group tests)
    - improvement_ratio: float (for blind tests)
    - failure_reason: string (if rejected)
    - test_metadata: object

  ShadowAnalysis:
    - id: string
    - pattern_id: string
    - analysis_id: string
    - with_pattern_prediction: float
    - without_pattern_prediction: float
    - actual_outcome: float
    - pattern_helped: boolean
    - timestamp: datetime

Additional Relationships for Pattern Validation:
  - Pattern -[HAS_VALIDATION]-> PatternValidation
  - Pattern -[TESTED_IN]-> ShadowAnalysis
  - PatternValidation -[BLOCKED_BY]-> PatternValidation (dependency chain)
  - Pattern -[REJECTED_AT_GATE6]-> Human (if human rejected)
  - Pattern -[APPROVED_AT_GATE6]-> Human (if human approved)
```

**Pattern Lifecycle Tracking**:

The system stores complete validation history including:

- All validation test results (holdout, blind, control)
- Shadow analysis outcomes for each pattern
- Gate 6 human review decisions and rationale
- Pattern performance degradation over time
- Rejection reasons for failed patterns

**Query Capabilities**:

```cypher
# Find patterns ready for Gate 6 review
MATCH (p:Pattern)
WHERE p.status = 'statistically_validated'
  AND NOT EXISTS((p)-[:APPROVED_AT_GATE6]->())
RETURN p.name, p.validation_correlation, p.control_p_value, p.validated_date
ORDER BY p.validated_date ASC

# Retrieve complete validation history for a pattern
MATCH (p:Pattern {name: 'Q4_retail_margin_compression'})-[:HAS_VALIDATION]->(v:PatternValidation)
RETURN p.status, v.validation_type, v.passed, v.test_correlation, v.failure_reason
ORDER BY v.test_start_date ASC

# Find patterns that failed blind testing
MATCH (p:Pattern)-[:HAS_VALIDATION]->(v:PatternValidation)
WHERE v.validation_type = 'blind_test'
  AND v.passed = false
RETURN p.name, v.improvement_ratio, v.failure_reason
ORDER BY v.test_end_date DESC

# Calculate validation pass rates by tier
MATCH (p:Pattern)-[:HAS_VALIDATION]->(v:PatternValidation)
WHERE v.test_end_date > datetime() - duration({months: 6})
RETURN v.validation_type,
       SUM(CASE WHEN v.passed THEN 1 ELSE 0 END) as passed_count,
       COUNT(*) as total_count,
       toFloat(SUM(CASE WHEN v.passed THEN 1 ELSE 0 END)) / COUNT(*) as pass_rate
GROUP BY v.validation_type

# Find active patterns showing performance degradation
MATCH (p:Pattern)
WHERE p.status = 'active'
  AND p.success_rate < p.training_correlation * 0.8
RETURN p.name, p.training_correlation, p.success_rate,
       (p.training_correlation - p.success_rate) as degradation
ORDER BY degradation DESC
LIMIT 10
```

**Pattern Quarantine Enforcement**:

The memory system enforces strict quarantine rules:

- Patterns with `status != 'active'` never returned to agent queries
- Separate storage partitions for validated vs unvalidated patterns
- Broadcast operations filtered to only include active patterns
- Audit trail for all pattern access attempts

### Debate-Specific Knowledge Graph Extensions

To support the tiered debate resolution system, the knowledge graph includes specialized nodes and relationships for tracking debate patterns and agent credibility:

```yaml
Additional Nodes for Debate Resolution:
  Debate:
    - id: string
    - topic: string
    - challenger_agent: string
    - challenged_agent: string
    - disputed_finding: string
    - challenge_basis: string
    - resolution_level: enum [1_agent, 2_facilitator, 3_human, 4_fallback, 5_gate_review]
    - resolution_method: enum [consensus, credibility_weighted, human_binding, conservative_default, override]
    - final_position: string
    - timestamp: datetime
    - priority: enum [critical_path, valuation, supporting]
    - provisional: boolean
    - override_window_closed: datetime

  DebateResolution:
    - id: string
    - debate_id: string
    - winning_position: string
    - winning_agent: string
    - credibility_differential: float
    - resolution_time_seconds: integer
    - human_override: boolean
    - override_rationale: string
    - downstream_impact: array
    - accuracy_tracked: boolean
    - outcome_correctness: float (populated later)

  AgentCredibility:
    - agent_id: string
    - domain: string (e.g., "tech_margins", "management_evaluation")
    - overall_score: float
    - sample_size: integer
    - recent_accuracy: float (last 10 decisions)
    - time_weighted_score: float
    - bias_corrections: object
    - last_updated: datetime
    # Temporal decay parameters
    - decay_halflife_years: float (default 2.0, configurable per agent)
    - last_decay_calculation: datetime
    # Market regime-specific credibility
    - regime_credibility: object
        BULL_LOW_RATES: {accuracy: float, sample_size: int}
        BULL_HIGH_RATES: {accuracy: float, sample_size: int}
        BEAR_HIGH_RATES: {accuracy: float, sample_size: int}
        BEAR_LOW_RATES: {accuracy: float, sample_size: int}
        HIGH_VOLATILITY: {accuracy: float, sample_size: int}
        NORMAL: {accuracy: float, sample_size: int}
    # Performance trend metrics
    - trend_slope: float (accuracy change per year, from linear regression)
    - trend_direction: enum [improving, stable, degrading]
    - trend_strength: float (R-squared, 0-1)
    - extrapolated_6mo: float (projected accuracy in 6 months)
    - trend_last_calculated: datetime
    # Human override tracking
    - override_rate: float (% of recommendations overridden)
    - override_rate_by_context: object (override rate by sector/metric/regime)
    - override_outcome_accuracy: float (% of overrides that were correct)
    - override_reasons: object (breakdown: missed_qualitative_factor, stale_data, flawed_logic, etc.)
    - override_credibility_penalty: float (multiplier 0.70-1.00 based on override rate)
    # Context-specific credibility tracking
    - context_dimensions: object
        sector: {dimension_value: {accuracy: float, sample_size: int}}
        metric_type: {dimension_value: {accuracy: float, sample_size: int}}
        time_horizon: {dimension_value: {accuracy: float, sample_size: int}}
        company_size: {dimension_value: {accuracy: float, sample_size: int}}
        growth_stage: {dimension_value: {accuracy: float, sample_size: int}}

Additional Relationships for Debate Resolution:
  - Debate -[RESOLVED_BY]-> Agent (facilitator or human)
  - Debate -[WINNING_POSITION]-> Agent
  - Debate -[HAS_RESOLUTION]-> DebateResolution
  - DebateResolution -[IMPACTED_ANALYSIS]-> Analysis
  - Agent -[HAS_CREDIBILITY_IN]-> Domain
  - Debate -[SIMILAR_TO]-> Debate (pattern matching)
  - Pattern -[SUPPORTS_POSITION]-> Debate (historical evidence)
  - Human -[OVERRODE]-> DebateResolution
```

**Debate Pattern Storage**:

The system stores complete debate histories including:

- Debate topics and agent positions
- Resolution methods and outcomes
- Credibility scores at time of debate
- Time to resolution at each level
- Provisional vs binding resolutions
- Human override patterns
- Accuracy of fallback resolutions (tracked post-outcome)

**Query Capabilities**:

```cypher
# Find similar past debates
MATCH (d1:Debate)-[:SIMILAR_TO]-(d2:Debate)
WHERE d1.topic CONTAINS "margin_sustainability"
  AND d2.resolution_level IN [3_human, 4_fallback]
RETURN d2, d2.final_position, d2.outcome_correctness
ORDER BY d2.timestamp DESC
LIMIT 5

# Retrieve agent credibility in specific domain
MATCH (a:Agent)-[r:HAS_CREDIBILITY_IN]->(domain)
WHERE a.name = "financial_analyst"
  AND domain.name = "retail_margins"
RETURN r.overall_score, r.sample_size, r.recent_accuracy

# Find debates where conservative default was applied
MATCH (d:Debate)-[:HAS_RESOLUTION]->(dr:DebateResolution)
WHERE d.resolution_level = '4_fallback'
  AND dr.human_override = true
RETURN d.topic, d.final_position, dr.override_rationale, dr.outcome_correctness

# Calculate facilitator auto-resolution success rate
MATCH (d:Debate)-[:HAS_RESOLUTION]->(dr:DebateResolution)
WHERE d.resolution_level = '2_facilitator'
  AND dr.accuracy_tracked = true
RETURN AVG(dr.outcome_correctness) as success_rate,
       COUNT(*) as total_auto_resolutions
```

**Agent Credibility Tracking**:

The system maintains sophisticated dynamic credibility scores for each agent using multi-factor temporal weighting, regime-specific performance, trend detection, and human override tracking.

**Comprehensive Credibility Calculation**:

```python
# Base accuracy calculation with multi-dimensional context matching
base_accuracy = (
    context_specific_accuracy * context_weight +
    overall_accuracy * (1 - context_weight)
)

# Temporal decay weighting (exponential with configurable half-life)
temporal_weight = 0.5^(age_years / decay_halflife_years)

# Market regime adjustment (if sufficient regime-specific data)
if regime_sample_size >= 50:
    regime_adjustment = regime_accuracy * 0.70 + overall_accuracy * 0.30
else:
    regime_adjustment = regime_accuracy * 0.30 + overall_accuracy * 0.70

# Performance trend extrapolation (if statistically significant R² > 0.3)
if trend_strength > 0.3:
    extrapolated = current_accuracy + (trend_slope * 0.5_years)
    trend_adjusted = current_accuracy * 0.70 + extrapolated * 0.30
else:
    trend_adjusted = current_accuracy

# Human override penalty (if override rate exceeds threshold)
if override_rate > 0.40:
    override_penalty = 0.70  # 30% penalty
elif override_rate > 0.20:
    override_penalty = 0.85  # 15% penalty
else:
    override_penalty = 1.00  # No penalty

# Final credibility score
credibility_score = (
    base_accuracy *
    temporal_weight *
    regime_adjustment *
    trend_adjusted *
    override_penalty
)
```

**Credibility Update Triggers**:

- **Immediate** (within 1 hour): Major errors, human override, challenge lost in debate
- **Daily**: Regime detection, new outcomes recorded
- **Weekly**: Trend analysis updated (52-week rolling regression)
- **Monthly**: Comprehensive review (all dimensions, pattern validation)
- **Quarterly**: Override rate analysis, blind spot investigation

**Credibility Requirements**:

- Minimum 15 data points for basic credibility (domain-level)
- Minimum 50 data points for regime-specific scoring
- Minimum 52 weeks of data for trend detection (statistically meaningful regression)
- Auto-resolution requires minimum 15 data points with credibility differential >0.25 (dynamic: `max(0.25, CI_A + CI_B)`)

**Bias Correction Storage**:

- Systematic over/under-estimation patterns
- Sector-specific biases
- Market regime dependencies
- Recommended adjustments for future analyses

**Similar Debate Precedent Retrieval**:

When a new debate initiates, the system retrieves relevant historical debates:

**Similarity Matching Criteria**:

1. **Topic similarity**: NLP-based semantic matching on debate topics
2. **Agent pairing**: Same agents involved in past debates
3. **Domain overlap**: Similar analytical domains (margins, growth, ROIC, etc.)
4. **Pattern involvement**: Same patterns cited as evidence
5. **Company characteristics**: Similar sector, size, maturity

**Precedent Presentation**:

```yaml
Historical Precedent Context:

Similar Debates (3 found):
  1. Topic: "Tech margin sustainability in competitive markets"
     Date: 2024-06-15
     Agents: Financial Analyst vs Strategy Analyst
     Resolution: Human arbitration → Financial Analyst position
     Outcome: Correct (margins held, accuracy: 0.92)
     Lesson: Financial analyst credibility higher in margin defense

  2. Topic: "Operating leverage assumptions"
     Date: 2024-08-22
     Agents: Financial Analyst vs Valuation Agent
     Resolution: Credibility-weighted → Valuation Agent (diff: 0.31)
     Outcome: Correct (accuracy: 0.88)

  3. Topic: "Gross margin expansion potential"
     Date: 2024-03-10
     Resolution: Conservative default (human unavailable)
     Outcome: Conservative position correct (accuracy: 1.0)
     Lesson: Conservative defaults effective for margin debates

Pattern Success Rates:
  - "Margin compression in competitive markets": 0.73 (12 occurrences)
  - "Operating leverage benefits": 0.68 (8 occurrences)

Agent Track Records in This Domain (retail margins):
  - Financial Analyst: 0.82 (15 decisions)
  - Strategy Analyst: 0.71 (12 decisions)
  - Credibility differential: 0.11 (below auto-resolution threshold)
```

This precedent context enables:

- Data-driven debate facilitation
- Informed credibility weighting
- Pattern-based argument validation
- Learning from past resolution effectiveness

### Post-Mortem Knowledge Graph Extensions

To support negative feedback mechanisms ([DD-006](../design-decisions/DD-006_NEGATIVE_FEEDBACK_SYSTEM.md)), the knowledge graph includes nodes and relationships for tracking failure investigations and lessons learned:

```yaml
Additional Nodes for Post-Mortem System:
  PostMortem:
    - id: string
    - decision_id: string
    - checkpoint: enum [30, 90, 180, 365]
    - deviation: float
    - trigger_date: datetime
    - status: enum [queued, in_review, completed, timeout]
    - priority: float (based on deviation severity)
    - completion_date: datetime

  FailureAnalysis:
    - id: string
    - postmortem_id: string
    - root_cause_category: enum [data_quality, model_assumptions, missing_factors, timing, regime_change, black_swan]
    - root_cause_details: string
    - foreseeability_rating: integer (1-5)
    - unexpected_changes: array
    - missing_factors: array
    - warning_signs: array

  HumanInsight:
    - id: string
    - postmortem_id: string
    - primary_reason: string
    - factors_missed: string
    - warning_signs_missed: string
    - future_actions: string
    - patterns_to_revise: array
    - foreseeability_rating: integer (1-5)
    - review_date: datetime

  SuccessValidation:
    - id: string
    - decision_id: string
    - thesis_score: float (thesis validation 0-1)
    - market_contribution: float
    - sector_contribution: float
    - stock_specific_contribution: float
    - skill_ratio: float
    - classification: enum [genuine_success, partial_success, lucky_success]

  Lesson:
    - id: string
    - source: enum [ai_analysis, human_insight, combined]
    - postmortem_id: string
    - category: string
    - insight: string
    - recommended_action: string
    - affected_domains: array
    - priority: enum [high, medium, low]
    - applied: boolean
    - applied_date: datetime
    - effectiveness_tracked: boolean

Additional Relationships for Post-Mortem System:
  - Decision -[HAS_POSTMORTEM]-> PostMortem
  - PostMortem -[HAS_ANALYSIS]-> FailureAnalysis
  - PostMortem -[HAS_INSIGHT]-> HumanInsight
  - PostMortem -[GENERATED_LESSON]-> Lesson
  - Decision -[HAS_SUCCESS_VALIDATION]-> SuccessValidation
  - Lesson -[AFFECTS_AGENT]-> Agent
  - Lesson -[AFFECTS_PATTERN]-> Pattern
  - Lesson -[ADDED_TO_CHECKLIST]-> Agent
  - Agent -[RECEIVED_LESSON]-> Lesson
  - Pattern -[REVISED_BY]-> Lesson (triggers Gate 6 review)
```

**Post-Mortem Workflow Storage**:

The system stores complete failure investigation histories:

- Deviation triggers and queue management
- AI-driven root cause categorization
- Human review responses with structured insights
- Success validation (luck vs skill decomposition)
- Lessons extracted from both AI and human analysis
- Lesson application tracking (which agents/patterns affected)
- Effectiveness measurement of lessons over time

**Query Capabilities**:

```cypher
# Find post-mortems pending human review
MATCH (pm:PostMortem)
WHERE pm.status = 'in_review'
  AND pm.trigger_date < datetime() - duration({hours: 24})
RETURN pm.decision_id, pm.deviation, pm.trigger_date, pm.priority
ORDER BY pm.priority DESC
LIMIT 5

# Retrieve complete post-mortem for a decision
MATCH (d:Decision)-[:HAS_POSTMORTEM]->(pm:PostMortem)
WHERE d.id = $decision_id
OPTIONAL MATCH (pm)-[:HAS_ANALYSIS]->(fa:FailureAnalysis)
OPTIONAL MATCH (pm)-[:HAS_INSIGHT]->(hi:HumanInsight)
OPTIONAL MATCH (pm)-[:GENERATED_LESSON]->(l:Lesson)
RETURN pm, fa, hi, COLLECT(l) as lessons

# Find lessons learned from specific failure category
MATCH (pm:PostMortem)-[:HAS_ANALYSIS]->(fa:FailureAnalysis)
WHERE fa.root_cause_category = 'missing_factors'
MATCH (pm)-[:GENERATED_LESSON]->(l:Lesson)
WHERE l.applied = true
RETURN l.insight, l.recommended_action, l.affected_domains, l.applied_date
ORDER BY l.applied_date DESC
LIMIT 10

# Calculate success validation statistics
MATCH (sv:SuccessValidation)
WHERE sv.classification = 'lucky_success'
RETURN COUNT(*) as lucky_count,
       AVG(sv.skill_ratio) as avg_skill_ratio,
       AVG(sv.market_contribution) as avg_market_contribution

# Find patterns pending revision from post-mortem lessons
MATCH (l:Lesson)-[:AFFECTS_PATTERN]->(p:Pattern)
WHERE l.applied = false
  AND p.status = 'active'
RETURN p.name, COLLECT(l.insight) as revision_reasons,
       COUNT(l) as lesson_count
ORDER BY lesson_count DESC

# Track lesson effectiveness
MATCH (l:Lesson)-[:AFFECTS_AGENT]->(a:Agent)
WHERE l.effectiveness_tracked = true
  AND l.applied_date > datetime() - duration({months: 6})
MATCH (a)-[:MADE]->(d:Decision)
WHERE d.date > l.applied_date
RETURN l.insight, AVG(d.accuracy) as post_lesson_accuracy,
       COUNT(d) as decisions_since_lesson
```

**NegativeFeedbackManager Component**:

Orchestrates post-mortem workflow and integrates with existing systems:

**Integration Points**:

- **OutcomeTracker**: Triggers post-mortems when checkpoint deviation >30%
- **Central Knowledge Graph**: Stores post-mortem reports, lessons, validation data
- **Learning Engine**: Applies lessons to patterns (queued for Gate 6 validation)
- **Human Interface**: Post-mortem review dashboard with structured questions
- **All Specialist Agents**: Receive lesson updates (checklists, bias corrections)
- **Gate 6**: Validates pattern revisions proposed by post-mortem lessons

**Queue Management**:

- Max 5 concurrent post-mortems in human review
- Priority queue by deviation severity (largest deviations first)
- Timeout tracking (48hr SLA for human review)
- Overflow queue for pending investigations

**Lesson Broadcasting**:

When post-mortem completed, lessons propagated via:

1. Agent checklist updates (new items to consider)
2. Pattern revision proposals (flagged for Gate 6 review)
3. Screening filter updates (if applicable)
4. Bias correction storage (systematic over/under-estimation)
5. Lesson library indexing (searchable by category/agent/pattern)

### Pattern Evidence Archive Knowledge Graph Extensions

To support data retention and pattern validation over time ([DD-009](../design-decisions/DD-009_DATA_RETENTION_PATTERN_EVIDENCE.md)), the knowledge graph includes nodes and relationships for tracking pattern evidence archives:

```yaml
Pattern Node Extensions for Evidence Archiving:
  Pattern:
    # Evidence tracking
    evidence_refs: array<string>        # File paths to supporting evidence
    archive_tier: integer               # 0 (none), 1 (lightweight), 2 (full)
    archive_refs: array<string>         # Archive directory paths
    is_critical: boolean                # Meets 2-of-4 criteria for full archive
    critical_score: integer             # 0-4 based on criteria met

    # Critical pattern criteria
    used_in_investment_decision: boolean
    confidence_score: float
    impact_score: float                 # >0.5 = influenced >$50K or >10% allocation
    validation_count: integer           # ≥3 = proven track record

    # Archive metadata
    tier1_created_date: datetime        # When lightweight archive created
    tier2_created_date: datetime        # When full archive created (if applicable)
    archive_size_mb: float              # Total archive size

Additional Nodes for Evidence Management:
  ArchiveDirectory:
    - pattern_id: string
    - tier: integer (1 or 2)
    - path: string
    - created_date: datetime
    - size_mb: float
    - retention_expiry: datetime
    - content_types: array (metadata, processed_summary, analysis_snapshot, full_processed, agent_analysis, validation_history)

  DataFile:
    - file_path: string
    - storage_tier: enum [hot, warm, cold]
    - created_date: datetime
    - tier_migration_date: datetime
    - size_mb: float
    - supports_pattern_count: integer  # How many active patterns reference this file
    - retention_expiry: datetime       # When eligible for deletion
    - in_archive: boolean              # Whether archived for pattern preservation

Additional Relationships for Evidence Archives:
  - Pattern -[SUPPORTED_BY_FILE]-> DataFile
  - Pattern -[HAS_ARCHIVE {tier: 1|2}]-> ArchiveDirectory
  - ArchiveDirectory -[CONTAINS_FILE]-> DataFile (archived copies)
  - DataFile -[MIGRATED_TO_TIER {from: tier, to: tier, date: datetime}]-> DataFile
```

**Archive Creation Workflow**:

The system automatically creates archives based on pattern lifecycle:

**Tier 1 Archive** (Lightweight, 1-5MB):

- **Trigger**: Pattern passes first validation (DD-007)
- **Contents**:
  - `metadata.json`: Pattern definition, confidence, validation results
  - `processed_summary.json`: Key metrics, ratios (1-5MB)
  - `analysis_snapshot.json`: Agent findings, evidence references
- **Retention**: 7 years
- **Purpose**: Safety net if evidence ages out before investment decision

**Tier 2 Archive** (Full, 50-200MB):

- **Trigger**: Pattern used in investment decision OR becomes critical (2-of-4 criteria)
- **Contents**:
  - All Tier 1 content
  - Full processed data: financial statements, ratios, peer comparisons
  - Complete agent analysis: findings, confidence, debates
  - Validation history: all re-validation results
- **Retention**: 10 years
- **Purpose**: Deep post-mortems, regulatory compliance, agent training

**Critical Pattern Scoring** (2-of-4 criteria triggers Tier 2):

```yaml
Critical Criteria:
  1. used_in_investment_decision: true (auto-qualifies)
  2. confidence_score: >0.7 (statistical strength)
  3. impact_score: >0.5 (>$50K position or >10% allocation)
  4. validation_count: ≥3 (proven track record)

Scoring Examples:
  - Investment decision + High confidence → Score 2 → Tier 2
  - High confidence + Multiple validations → Score 2 → Tier 2
  - Medium confidence + Low validations → Score 0 → No archive
```

**Query Capabilities**:

```cypher
# Find patterns eligible for Tier 2 archive promotion
MATCH (p:Pattern)
WHERE p.archive_tier = 1
  AND (
    p.used_in_investment_decision = true OR
    (p.confidence_score > 0.7 AND p.validation_count >= 3) OR
    (p.confidence_score > 0.7 AND p.impact_score > 0.5) OR
    (p.validation_count >= 3 AND p.impact_score > 0.5)
  )
RETURN p.name, p.confidence_score, p.validation_count, p.impact_score
ORDER BY p.tier1_created_date ASC

# Find data files eligible for deletion (no pattern dependencies)
MATCH (f:DataFile)
WHERE f.storage_tier = 'cold'
  AND f.supports_pattern_count = 0
  AND f.in_archive = false
  AND f.created_date < datetime() - duration({years: 7})
RETURN f.file_path, f.size_mb, f.created_date
ORDER BY f.size_mb DESC

# Check if file supports active patterns before deletion
MATCH (f:DataFile)<-[:SUPPORTED_BY_FILE]-(p:Pattern)
WHERE f.file_path = $file_path
  AND p.status = 'active'
RETURN COUNT(p) as active_pattern_count

# Find patterns with evidence at risk of deletion
MATCH (p:Pattern)-[:SUPPORTED_BY_FILE]->(f:DataFile)
WHERE p.status = 'active'
  AND p.archive_tier = 0
  AND f.retention_expiry < datetime() + duration({months: 6})
RETURN p.name, p.confidence_score, f.file_path, f.retention_expiry
ORDER BY f.retention_expiry ASC

# Calculate archive storage costs by tier
MATCH (ad:ArchiveDirectory)
RETURN ad.tier,
       COUNT(*) as archive_count,
       SUM(ad.size_mb) as total_size_mb,
       AVG(ad.size_mb) as avg_size_mb
GROUP BY ad.tier

# Find patterns missing archives despite meeting criteria
MATCH (p:Pattern)
WHERE p.archive_tier = 0
  AND p.used_in_investment_decision = true
RETURN p.name, p.confidence_score, p.validation_count, p.tier1_created_date
ORDER BY p.tier1_created_date ASC
```

**Storage Architecture**:

```text
/data/memory/pattern_archives/
├── {pattern_id}/
│   ├── tier1/
│   │   ├── metadata.json
│   │   ├── processed_summary.json
│   │   └── analysis_snapshot.json
│   ├── tier2/ (if critical)
│   │   ├── all_tier1_content/
│   │   ├── processed_data/
│   │   │   ├── financial_statements/
│   │   │   ├── ratios/
│   │   │   └── peer_comparisons/
│   │   ├── agent_analysis/
│   │   └── validation_history/
│   └── archive_metadata.json
└── index.json (pattern_id → archive_tier mapping)
```

**Integration with Tiered Storage**:

The archive system works in conjunction with tiered data storage:

1. **Hot Tier** (0-2yr): Active analysis, $0.023/GB/mo, <10ms access
2. **Warm Tier** (2-5yr): Recent history, $0.010/GB/mo, <100ms access
3. **Cold Tier** (5-10yr): Historical data, $0.001/GB/mo, <3s access

**Pattern-Aware Retention**:

- Before migrating Cold → Delete, check `supports_pattern_count`
- If any active patterns reference file, retain in Cold tier
- If file archived for pattern, safe to delete from tiered storage
- Estimated cost: ~$5/mo for 750GB tiered + $0.22/mo for archives

### Data Contradiction Resolution Knowledge Graph Extensions

To support data source contradiction resolution with timeout and fallback ([DD-010](../design-decisions/DD-010_DATA_CONTRADICTION_RESOLUTION.md)), the knowledge graph includes nodes and relationships for tracking source credibility and contradiction resolution history.

**Key Nodes** (already added to base schema above):

- **SourceCredibility**: Tracks reliability of data sources (SEC, Bloomberg, Reuters, etc.) with 3-component credibility formula
- **DataContradiction**: Records contradiction events, resolution methods, and outcomes

**Source Credibility 3-Component Formula**:

```python
# Component 1: Base accuracy (historical contradiction outcomes)
base_accuracy = correct_resolutions / total_contradictions_involving_source

# Component 2: Source type hierarchy (hard-coded trust levels)
hierarchy_weights = {
    "SEC_EDGAR": 1.00,
    "Bloomberg": 0.95,
    "Refinitiv": 0.90,
    "Reuters": 0.90,
    "Company_IR": 0.85,
    "News": 0.70
}

# Component 3: Temporal decay (4.5-year half-life exponential weighting)
temporal_weight = 0.5 ** (age_years / 4.5)

# Final source credibility score
credibility_score = (
    base_accuracy * 0.40 +
    hierarchy_weights[source_type] * 0.40 +
    temporal_weight * 0.20
)
```

**Contradiction Resolution Workflow Storage**:

The system stores complete contradiction resolution histories including:

- Data point discrepancies (metric name, conflicting values, sources)
- 4-level escalation path (evidence quality → credibility auto-resolution → human arbitration → fallback)
- Resolution outcomes and methods
- Provisional resolutions pending Gate 3 review
- Human override patterns for critical data

**Query Capabilities**:

```cypher
# Retrieve source credibility for data provider
MATCH (sc:SourceCredibility)
WHERE sc.source_name = "Bloomberg"
RETURN sc.base_accuracy, sc.hierarchy_weight, sc.contradiction_count

# Find provisional contradictions pending Gate 3 review
MATCH (dc:DataContradiction)
WHERE dc.provisional = true
  AND dc.reviewed_at_gate3 = false
  AND dc.priority = 'CRITICAL'
RETURN dc.data_point, dc.source_a, dc.source_b, dc.final_value
ORDER BY dc.timestamp ASC

# Calculate source credibility win rate
MATCH (sc:SourceCredibility)<-[:RESOLVED_BY_SOURCE]-(dc:DataContradiction)
WHERE sc.source_name = $source_name
RETURN sc.source_name,
       COUNT(dc) as total_contradictions,
       sc.base_accuracy as win_rate

# Find contradictions that required human arbitration
MATCH (dc:DataContradiction)
WHERE dc.resolution_level = '3_human'
  AND dc.timestamp > datetime() - duration({months: 6})
RETURN dc.data_point, dc.source_a, dc.source_b, dc.credibility_differential
ORDER BY dc.timestamp DESC
```

**Gate 3 Integration**:

During Gate 3 (Assumption Validation), human reviews all provisional contradiction resolutions:

- Display: Data point, conflicting sources, credibility scores, fallback value used
- Actions: Confirm fallback / Override with new value / Mark uncertain / Request investigation
- Impact: Show valuation sensitivity to contradiction resolution
- Blocking: CRITICAL contradictions (revenue, margins) block analysis if unresolved

**Cross-References**:

- See [DD-010](../design-decisions/DD-010_DATA_CONTRADICTION_RESOLUTION.md) for complete design rationale
- See [Data Management](../operations/03-data-management.md) for operational procedures
- See [Human Integration](../operations/02-human-integration.md) for Gate 3 UI specifications

---

## Memory Synchronization Protocol

**Note**: Code samples referenced here have been omitted from architecture docs. See `/examples/` directory for implementation examples.

### Event-Driven Priority Sync Architecture

The Memory Sync Manager uses an event-driven approach with three priority tiers to ensure timely synchronization while minimizing overhead.

**Sync Priority Levels**:

| Priority     | Trigger Events                            | Latency     | Use Cases                                           |
| ------------ | ----------------------------------------- | ----------- | --------------------------------------------------- |
| **Critical** | Debates, challenges, human gates          | <2 seconds  | Ensures consistency during high-stakes interactions |
| **High**     | Important findings, alerts, confirmations | <10 seconds | Fast propagation of significant discoveries         |
| **Normal**   | Routine updates, batch operations         | 5 minutes   | Background sync for non-urgent updates              |

### Synchronization Process

**Push Operations** (Local → Central):

- Critical: Immediate push when debate initiated or human gate approaching
- High: Fast push for important discoveries (importance > 0.7)
- Normal: Scheduled push every 5 minutes for routine updates

**Pull Operations** (Central → Local):

- Critical: Force immediate pull before debates/challenges
- High: Fast pull when relevant high-priority updates available
- Normal: Periodic pull of cross-domain insights

**Event-Triggered Sync**:

The system automatically triggers critical sync when:

- **Debate/Challenge Initiated**: Both challenger and challenged agents force-synced
- **Human Gate Approaching**: All agents synced 30 minutes before gate
- **Alert Messages**: Sending and receiving agents high-priority synced
- **Finding with Precedent**: High-priority sync to ensure historical context available

### Memory Snapshot for Debates

During debates, the system creates a point-in-time memory snapshot:

1. **Force sync all participants** - ensures consistent starting state
2. **Create locked snapshot** - prevents mid-debate inconsistencies
3. **All agents reference snapshot** - uniform view of evidence
4. **Sync after resolution** - propagate debate outcomes

### Relevance Determination

The system determines which agents need immediate notification based on:

- Agent specialization overlap
- Current active analyses
- Historical usage patterns
- Insight importance and urgency
- Message type and priority

**Note**: For message queue reliability, ordering, performance specifications, and technology selection, see [Technical Requirements](../implementation/02-tech-requirements.md#message-queue).

---

## Scalability & Performance Optimization

The system implements comprehensive optimization strategies to maintain performance targets (<500ms memory retrieval) at production scale (1000+ stocks, 15K+ analyses). See [DD-005](../design-decisions/DD-005_MEMORY_SCALABILITY_OPTIMIZATION.md) for complete design rationale.

### Performance Targets

| Metric             | Target                               | Implementation Phase |
| ------------------ | ------------------------------------ | -------------------- |
| Memory retrieval   | <200ms (cached), <500ms (uncached)   | Phase 3-4            |
| Cache hit rate     | >80%                                 | Phase 3-4            |
| Graph size         | <50K active nodes                    | Phase 4-5            |
| Memory utilization | >85% of decisions use historical ctx | Phase 2-5            |

### Tiered Cache Architecture

**Extended 3-Tier Cache** (beyond agent L1/L2):

```text
┌─────────────────────────────────────────────────┐
│  System-Wide L1 Cache (Hot, <10ms)              │
│  Recent/frequent queries, 1hr TTL, 500MB         │
│  Tech: Fast in-memory cache (Redis/equivalent)   │
└─────────────────────────────────────────────────┘
                    ▲ ▼
┌─────────────────────────────────────────────────┐
│  Agent L2 Cache (Warm, <50ms)                   │
│  Specialized patterns per agent, LRU eviction    │
│  Tech: Local in-process memory                   │
└─────────────────────────────────────────────────┘
                    ▲ ▼
┌─────────────────────────────────────────────────┐
│  Central L3 Storage (Cold, <500ms)              │
│  Full knowledge graph, persistent                │
│  Tech: Graph database or equivalent              │
└─────────────────────────────────────────────────┘
```

**Cache Warming Strategy**:

- Before analysis starts, predictively preload:
  - Similar analyses for target company
  - Sector patterns and peer comparisons
  - Company history and precedents
- Reduces runtime cache misses from ~50% to <20%

**Cache Invalidation**:

- L1: Time-based (1hr TTL)
- L2: LRU eviction when capacity exceeded
- L3: Always fresh (source of truth)

### Query Optimization & Indexing

**Pre-Computed Similarity Index**:

- Offline batch process computes pairwise analysis similarities
- Stores top-K similar analyses per company (e.g., top 10)
- Nightly/weekly rebuild based on new analyses
- **Performance gain**: 2-5s graph traversal → <50ms index lookup

**Materialized Views**:

- Top patterns by sector
- Agent credibility scores (incrementally updated)
- Peer comparison matrices

**Index Rebuild Pipeline**:

- Incremental updates throughout day (new analyses added to index)
- Full rebuild weekly (recalculate all similarities, prune stale)
- Background batch process, minimal runtime impact

### Query Budget Enforcement

**Hard 500ms Timeout**:

- All memory queries wrapped with timeout enforcement
- Prevents runaway queries from blocking analysis pipeline

**Fallback Strategies** (when timeout exceeded):

- Return approximate result (e.g., top-5 instead of top-10 similar analyses)
- Return cached result marked with timestamp (slightly stale but fast)
- Sample-based results (50% sample of pattern matches)

**Monitoring**:

- Track timeout frequency by query type
- Alert if >5% queries timeout (indicates optimization needed)
- Log slow queries for investigation

### Incremental Credibility Updates

**Agent Credibility Optimization**:

Current approach (L3 queries scan all history):

```cypher
# Full historical scan on each query - O(n) with decision count
MATCH (a:Agent)-[:MADE]->(d:Decision)
WHERE a.id = $agent_id
RETURN avg(d.accuracy)
```

Optimized approach (cached + incremental):

```text
# Cache current score, update incrementally with new decisions
new_score = (current_score * count * decay + new_accuracy) / (count * decay + 1)
```

**Performance gain**: 800ms full scan → <10ms incremental update

### Memory Pruning Strategy

**Pruning Criteria** (must meet 2+ to archive):

- Age >2 years
- Access frequency <3 (rarely queried)
- Relevance score <0.3
- Superseded by better/newer memory

**Archival Process**:

1. Summarize: Extract key findings, outcomes, lessons learned
2. Store lightweight summary in active graph (keeps context)
3. Archive full detail to cold storage (S3, data warehouse, or equivalent)
4. Remove full detail from L3 graph

**Archive Promotion** ([DD-013](../../design-decisions/DD-013_ARCHIVE_LIFECYCLE_MANAGEMENT.md)):

Archived patterns can be promoted back to active graph when needed:

- **Triggers**: Regime change detection, high access frequency (3+ hits/30d), post-mortem requests
- **Cached Index**: Redis/ElasticSearch index enables <100ms queries without S3 retrieval
- **Auto-Promote**: Pattern re-hydrated immediately on trigger, human notified for 48hr override window
- **Re-Hydration**: S3 → validation → L3 graph restoration with staleness metadata
- **Probationary Status**: Promoted patterns require re-validation before investment use

This enables multi-year learning evolution - system leverages historical patterns when market regimes change rather than re-learning from scratch.

**Graph Size Management**:

- Target: <50K active nodes in L3 graph
- Monthly pruning review
- Ensures query performance remains consistent as system scales

### Parallel Query Execution

**Concurrent Memory Fetches**:

- Each analysis requires multiple memory queries (similar analyses, patterns, history, precedents)
- Execute all queries in parallel vs sequential
- Fail gracefully if individual query fails (don't block entire analysis)

**Performance gain**:

- Sequential: 5 queries × 200ms = 1,000ms
- Parallel: max(5 queries) = 200ms (5× faster)

### Benchmarking Requirements

Performance validation at each scale milestone:

| Phase     | Scale      | Analyses | Patterns | Benchmark Focus                      |
| --------- | ---------- | -------- | -------- | ------------------------------------ |
| Phase 1-2 | MVP        | 100      | 100      | Baseline, identify first bottlenecks |
| Phase 3   | Beta       | 150-500  | 500-1K   | Validate cache effectiveness         |
| Phase 4   | Production | 600-2K   | 1K-3K    | Stress test optimizations            |
| Phase 5   | Scale      | 3K-15K   | 3K-5K    | Confirm targets at full scale        |

**Key Metrics**:

- Graph query latency (variable-length path traversal)
- Pattern matching time (linear search across all patterns)
- Credibility calculation time (incremental vs full scan)
- Cache hit rate (target >80%)
- End-to-end memory overhead per analysis (target <200ms)

---

## Related Documentation

- [System Overview](./01-system-overview.md) - High-level architecture
- [Specialist Agents](./03-agents-specialist.md) - Agents using memory systems
- [Knowledge Base Agent](./04-agents-support.md#knowledge-base-agent) - Memory management agent
- [Collaboration Protocols](./07-collaboration-protocols.md) - Memory-enhanced communication
- [Technical Requirements](../implementation/02-tech-requirements.md#message-queue) - Message queue specifications for memory synchronization
- [DD-002: Event-Driven Memory Sync](../design-decisions/DD-002_EVENT_DRIVEN_MEMORY_SYNC.md) - Priority-based sync design
- [DD-005: Memory Scalability Optimization](../design-decisions/DD-005_MEMORY_SCALABILITY_OPTIMIZATION.md) - Performance optimization design
