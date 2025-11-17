# DD-008: Comprehensive Agent Credibility Scoring System

**Status**: Implemented
**Date**: 2025-11-17
**Decider(s)**: System Architecture Team
**Related Docs**:

- [Feedback Loops](../docs/learning/02-feedback-loops.md)
- [Memory System](../docs/architecture/02-memory-system.md)
- [Coordination Agents](../docs/architecture/05-agents-coordination.md)
- [Collaboration Protocols](../docs/architecture/07-collaboration-protocols.md)
- [Credibility System Implementation](../docs/implementation/05-credibility-system.md)

**Related Decisions**:

- [DD-003: Debate Deadlock Resolution](DD-003_DEBATE_DEADLOCK_RESOLUTION.md) - Uses credibility for auto-resolution
- [DD-006: Negative Feedback System](DD-006_NEGATIVE_FEEDBACK_SYSTEM.md) - Updates credibility via post-mortems

---

## Context

### The Problem

Agent credibility in v2.0 architecture used simple cumulative averaging of historical accuracy, treating all performance data equally regardless of when it occurred or under what market conditions.

**Current Implementation** (v2.0 baseline):

```python
def get_agent_track_record(self, agent_id, context):
    """Get agent's historical performance in similar contexts"""
    return self.graph_db.query("""
        MATCH (agent:Agent {id: $agent_id})-[:PERFORMED]->(a:Analysis)
        WHERE a.context SIMILAR TO $context
        RETURN
            COUNT(a) as total,
            AVG(a.accuracy) as avg_accuracy
    """)
```

**Critical Flaw**: `AVG(a.accuracy)` treats 2020 performance identically to 2025 performance, ignoring:

- **Temporal decay**: Recent performance should matter more
- **Market regime changes**: Agent accuracy varies by market conditions (bull/bear, rates, volatility)
- **Performance trends**: Agents improve or degrade over time
- **Human override patterns**: Frequent overrides indicate systematic blind spots
- **Context specificity**: Domain expertise in specific sectors/metrics not captured

### Impact on System Decisions

This flaw undermined critical system components:

1. **Debate Auto-Resolution** (DD-003): Facilitator uses credibility differential (>0.25 threshold) to resolve conflicts automatically. Stale credibility scores led to:

   - Wrong agent position selected (agent good in 2020 bull market, poor in 2023 bear market)
   - Credibility gaps artificially narrow/wide due to outdated data
   - Auto-resolution failures requiring unnecessary human escalation

2. **Agent Recommendation Weighting**: Final system recommendations weighted by credibility. Stale scores meant:

   - Improving agents undervalued (mastery-level agent treated as learning-level)
   - Degrading agents overweighted (expert-in-2019 treated as still expert)
   - Regime-dependent performance ignored (bull-market specialist overweighted in bear markets)

3. **Learning System Feedback** (DD-006): Post-mortem lessons applied based on agent credibility. Without accurate scores:
   - Wrong agents receive pattern adjustments
   - Correct agents penalized for stale mistakes
   - Learning velocity reduced

### Real-World Examples

**Example 1: Market Regime Blindness**

```text
Financial Analyst Track Record:
  2019-2021 (Bull Market, Low Rates): 92% accuracy (50 analyses)
  2022-2023 (Bear Market, High Rates): 68% accuracy (25 analyses)

Current Score: AVG(92%, 68%) = 80%

Problem: In 2025 high-rate environment similar to 2022:
  - Agent struggled in 2022 (68% accuracy)
  - Simple average (80%) overestimates capability by 12%
  - Debate auto-resolution selects wrong agent
  - Final recommendations overweight flawed analysis
```

**Example 2: Improvement Trajectory Ignored**

```text
Strategy Analyst Evolution:
  2020: 65% accuracy (learning phase)
  2021: 72% accuracy (improving)
  2022: 81% accuracy (proficient)
  2023: 87% accuracy (expert)
  2024: 89% accuracy (mastery)

Current Score: AVG(all) = 79%

Problem: Latest performance is 89% (mastery-level)
  - Simple average (79%) underestimates by 10%
  - Agent treated as "proficient" when actually "mastery"
  - Recommendations underweighted in debates
  - Opportunity cost: agent could handle more complex analyses
```

**Example 3: Historical Artifact Persistence**

```text
Valuation Agent Model Evolution:
  2018-2020: Flawed DCF model (55% accuracy, 30 analyses)
  2021: Model upgraded (architectural fix)
  2021-2025: Improved model (88% accuracy, 70 analyses)

Current Score: (30×0.55 + 70×0.88) / 100 = 77.1%

Problem: Current capability is 88% but score is 77.1%
  - 2018-2020 irrelevant to 2025 (different model architecture)
  - Permanently penalized for past mistakes despite fix
  - 11% underestimation persists indefinitely
```

### Why This Needs Resolution Now

Phase 4 (Optimization) focuses on refining learning systems and agent coordination. Accurate credibility scoring is foundational for:

- **Debate auto-resolution effectiveness** (DD-003): 70%+ of debates should auto-resolve, requires accurate credibility differentials
- **Post-mortem lesson application** (DD-006): Wrong agents receive lessons if credibility scores stale
- **Gate 6 pattern validation** (DD-001): Human review effort wasted if patterns recommended by low-credibility agents
- **Human override learning**: System can't learn from overrides without tracking override patterns

**Blocking dependencies**:

- Memory scalability (DD-005): Credibility recalculation must scale to 1000+ stocks
- Pattern validation (DD-007): Pattern approval requires agent credibility context
- Negative feedback (DD-006): Post-mortems update credibility based on outcomes

---

## Decision

**Implement comprehensive multi-factor credibility scoring system with temporal decay, market regime specificity, performance trend detection, human override tracking, and multi-dimensional context matching.**

The system calculates agent credibility as:

```python
credibility_score = (
    base_accuracy *           # Context-matched historical accuracy
    temporal_weight *         # Exponential decay (2-year half-life)
    regime_adjustment *       # Current market regime performance
    trend_adjusted *          # Performance trajectory extrapolation
    override_penalty          # Human override rate penalty
)
```

### Core Components

**1. Temporal Decay with Exponential Weighting**

Replace fixed time buckets with smooth exponential decay:

```python
weight = 0.5^(age_years / decay_halflife_years)

# Default: 2-year half-life
# Agent-specific tuning:
#   - News Monitor: 6 months (fast-changing domain)
#   - Financial Analyst: 3 years (stable domain)
#   - Strategy Analyst: 2 years (balanced)
```

**Benefits over time buckets**:

- Smooth continuous decay (no cliff effects at bucket boundaries)
- Mathematically principled (half-life has clear interpretation)
- Configurable per agent based on domain stability
- Recent data weighted heavily (3-month-old = 93% weight, 2-year-old = 50% weight)

**2. Market Regime-Specific Credibility**

Track agent performance separately for 6 market regimes:

```python
class MarketRegime(Enum):
    BULL_LOW_RATES = "bull_low_rates"       # S&P +10%+ YoY, Fed <3%, VIX <20
    BULL_HIGH_RATES = "bull_high_rates"     # S&P +10%+ YoY, Fed ≥3%
    BEAR_HIGH_RATES = "bear_high_rates"     # S&P negative YoY, Fed ≥3%, VIX >25
    BEAR_LOW_RATES = "bear_low_rates"       # S&P negative YoY, Fed <3%
    HIGH_VOLATILITY = "high_volatility"     # VIX >30 (regardless of returns)
    NORMAL = "normal"                       # Default classification

# Credibility calculation
if regime_sample_size >= 50:
    credibility = regime_accuracy * 0.70 + overall_accuracy * 0.30
else:
    credibility = regime_accuracy * 0.30 + overall_accuracy * 0.70
```

**Detection logic**: Daily market data monitoring (S&P 500 returns, Fed Funds Rate via FRED API, VIX)

**3. Performance Trend Detection**

Linear regression on 52-week rolling accuracy identifies improving/degrading agents:

```python
slope, intercept, r_value = linear_regression(timestamps, accuracy_scores)

trend_strength = r_value^2  # R-squared (0-1)
trend_direction = "improving" if slope > 0 else "degrading"

# If statistically significant (R² > 0.3)
if trend_strength > 0.3:
    extrapolated_6mo = current_accuracy + (slope * 0.5_years)
    credibility = current_accuracy * 0.70 + extrapolated_6mo * 0.30
```

**Captures agent evolution**: Improving agent (65%→89%) gets 90.8% credibility vs 79% simple average

**4. Human Override Rate Tracking**

Track when humans override agent recommendations to identify blind spots:

```python
override_rate = human_overrides / total_recommendations

# Credibility penalty
if override_rate > 0.40:      # Critical (>40%)
    penalty = 0.70  # 30% penalty
elif override_rate > 0.20:    # Concerning (20-40%)
    penalty = 0.85  # 15% penalty
else:                         # Acceptable (<20%)
    penalty = 1.00  # No penalty
```

**Root cause triggers**: Override rate >30% for 3 months, overrides clustered in specific context (e.g., 60% in tech sector)

**5. Multi-Dimensional Context Matching**

Calculate accuracy based on similarity across 6 dimensions:

```python
context_dimensions = [
    'sector',        # Technology, Healthcare, Retail, etc.
    'metric_type',   # Revenue, Margin, Cash Flow, Strategic
    'time_horizon',  # Near-term <1Y, Medium 1-3Y, Long-term >3Y
    'company_size',  # Mega-cap, Large-cap, Mid-cap, Small-cap
    'growth_stage'   # Mature, Growth, Turnaround, Startup
]

# Context similarity scoring
if context_match == 6/6:      # Exact match
    context_weight = 1.00     # Use context-specific accuracy
elif context_match >= 4/6:    # Strong match
    context_weight = 0.70     # 70% context, 30% overall
elif context_match >= 2/6:    # Weak match
    context_weight = 0.30     # 30% context, 70% overall
else:                         # No match
    context_weight = 0.00     # Use overall accuracy only
```

**6. Confidence Intervals**

Calculate statistical significance based on sample size:

```python
# Wilson score interval for binomial proportion (95% confidence)
confidence_interval = 1.96 * sqrt((credibility * (1-credibility)) / sample_size)

# Auto-resolution threshold includes confidence
min_differential = max(0.25, agent_A_CI + agent_B_CI)
```

**Prevents premature auto-resolution**: Small sample sizes (N<10) have wide confidence intervals, forcing human review

---

## Options Considered

### Option 1: Simple Time Buckets (Baseline - Rejected)

**Description**: Keep current approach but add fixed time-based weighting

```python
# Last 3 months: 50% weight
# 3-12 months: 30% weight
# 1-2 years: 15% weight
# 2+ years: 5% weight

credibility = (
    recent_3mo * 0.50 +
    months_3to12 * 0.30 +
    years_1to2 * 0.15 +
    years_2plus * 0.05
)
```

**Pros**:

- Simple to implement (2-3 days)
- Easy to explain to humans
- Minimal database schema changes
- Low computational cost

**Cons**:

- **Cliff effects**: 2.9-month-old prediction gets 50% weight, 3.1-month-old gets 30% (artificial discontinuity)
- **No regime awareness**: Bull vs bear market performance conflated
- **No trend detection**: Can't identify improving/degrading agents
- **No override tracking**: Blind spots undetected
- **Fixed weights**: Can't tune decay rate per agent/domain
- **Arbitrary boundaries**: Why 3 months? Why not 2 or 4?

**Estimated Effort**: Low (3-5 days)

**Rejection Rationale**: Cliff effects at bucket boundaries create gaming opportunities. Agent with 2.9-month track record gets 50% weight, 3.1-month gets 30% despite negligible actual difference. Fails to address regime-specific performance or improvement trajectories.

---

### Option 2: Recency-Only Exponential Decay (Partial Solution - Rejected)

**Description**: Implement exponential temporal decay but skip regime/trend/override tracking

```python
weight = 0.5^(age_years / 2.0)  # 2-year half-life
credibility = weighted_average(accuracy, weights)
```

**Pros**:

- Smooth decay curve (no cliff effects)
- Mathematically principled (half-life concept)
- Relatively simple (1 week implementation)
- Tunable decay rate per agent

**Cons**:

- **No regime awareness**: Financial Analyst with 92% in bull market, 68% in bear market gets blended score inappropriate for current regime
- **No trend detection**: Strategy Analyst improving from 65%→89% underestimated at ~79% average
- **No override tracking**: Can't identify agents with systematic blind spots
- **Incomplete solution**: Addresses temporal decay but ignores other critical factors
- **Still misleading**: Recent average may not reflect current regime capability

**Estimated Effort**: Medium (1 week)

**Rejection Rationale**: Solves temporal decay but fails to address market regime dependency (critical for financial analysis accuracy). Missing 50%+ of the credibility problem. Strategy Analyst improving 65%→89% still underestimated because trend not captured.

---

### Option 3: Comprehensive Multi-Factor System (Selected)

**Description**: Full implementation with temporal decay, regime specificity, trend detection, override tracking, and context matching

```python
credibility = (
    base_accuracy *           # Context-matched
    temporal_weight *         # Exponential decay (2yr half-life)
    regime_adjustment *       # Current regime performance
    trend_adjusted *          # Performance trajectory
    override_penalty          # Override rate penalty
)
```

**Pros**:

- **Regime-adaptive**: Bull-market specialist not overweighted in bear markets
- **Trend-aware**: Improving agents (65%→89%) get extrapolated credibility (90.8%)
- **Blind spot detection**: Override tracking (>40% rate = 30% penalty) catches systematic issues
- **Context-specific**: Tech margin expert gets higher weight for tech margin questions
- **Statistically rigorous**: Confidence intervals prevent premature auto-resolution
- **Future-proof**: Captures agent evolution, adapts to regime shifts
- **Accurate auto-resolution**: Credibility differentials reflect true current capability
- **Validates via backtesting**: Can verify with 2020-2023 historical data

**Cons**:

- **Implementation complexity**: 5 components (temporal, regime, trend, override, context) vs simple average
- **Computational cost**: Trend detection requires 52-week regression, regime detection requires daily market data
- **Data requirements**: Need 50+ decisions for regime-specific credibility, 52 weeks for trend detection
- **Database schema changes**: 30+ new fields in AgentCredibility node
- **Recalculation overhead**: Daily regime detection, weekly trend analysis, monthly comprehensive review
- **Explanation complexity**: Harder to explain multi-factor formula to humans vs simple average
- **Tuning required**: Decay half-life, regime thresholds, trend significance (R²>0.3), override penalties

**Estimated Effort**: High (2 weeks implementation + 1 week testing/validation)

**Selected**: Despite complexity, this is the only option that comprehensively addresses all identified credibility scoring flaws. Regime awareness, trend detection, and override tracking are critical for accurate agent weighting in debates and recommendations.

---

### Option 4: Machine Learning Credibility Predictor (Rejected - Overkill)

**Description**: Train ML model to predict agent future accuracy based on features (historical performance, market conditions, agent characteristics, context)

```python
# Features: agent_history, current_regime, sector, metric_type, volatility, etc.
# Target: agent_accuracy_next_6_months

model = GradientBoostingRegressor()
model.fit(features, target_accuracy)

credibility = model.predict(current_features)
```

**Pros**:

- **Potentially most accurate**: ML can capture non-linear relationships
- **Discovers hidden patterns**: May find regime/context interactions not manually specified
- **Adaptive**: Automatically adjusts as market evolves
- **No manual tuning**: Learns optimal weights from data

**Cons**:

- **Massive overkill**: Requires 1000+ training samples (need years of operational data)
- **Explainability loss**: Black-box predictions hard to justify to humans at Gate 4
- **Overfitting risk**: With limited data, may learn spurious correlations
- **Model drift**: Requires retraining, monitoring, validation infrastructure
- **Development time**: 4-6 weeks for proper ML pipeline (training, validation, deployment, monitoring)
- **Computational cost**: 10-100x more expensive than formula-based approach
- **Dependencies**: Requires ML infrastructure, feature engineering, model versioning
- **Premature optimization**: Formula-based approach likely sufficient for Phase 4

**Estimated Effort**: Very High (4-6 weeks)

**Rejection Rationale**: Insufficient data for reliable ML training (need 1000+ agent-decision-outcome triplets). Explainability critical for human arbitration at Gate 4 - humans need to understand why agent A has higher credibility than agent B. Formula-based approach provides transparency while capturing 90%+ of credibility variance.

---

## Rationale

### Why Option 3 (Comprehensive Multi-Factor) Was Selected

**1. Addresses All Identified Failure Modes**

Each component solves a specific real-world problem:

- **Temporal decay**: Solves "2018 DCF model mistakes haunt forever" (Valuation Agent 55%→88% now 88%)
- **Regime specificity**: Solves "92% bull market analyst gets 80% in bear market" (Financial Analyst now regime-matched)
- **Trend detection**: Solves "65%→89% improvement ignored" (Strategy Analyst now 90.8% extrapolated)
- **Override tracking**: Solves "45% override rate undetected" (Valuation Agent penalty triggers investigation)
- **Context matching**: Solves "generalist vs specialist not distinguished" (tech margin expert weighted higher for tech margins)

**2. Critical for Debate Auto-Resolution (DD-003)**

Debate Facilitator auto-resolves when credibility differential >0.25. Stale scores cause:

```text
Example: Tech margin sustainability debate
  Financial Analyst: 82% recent (tech margins), 75% overall → stale: 75%
  Strategy Analyst: 71% recent (tech margins), 78% overall → stale: 78%

Stale differential: |75% - 78%| = 3% → escalates to human (incorrect)
Accurate differential: |82% - 71%| = 11% → still escalates (correct, but closer)

With regime + context:
  Financial Analyst: 82% tech margins, 85% in current regime → 83.5%
  Strategy Analyst: 71% tech margins, 68% in current regime → 69.5%

Accurate differential: |83.5% - 69.5%| = 14% → still escalates
BUT if Financial Analyst has improving trend (78%→85%):
  Extrapolated: 85% * 0.7 + 87% * 0.3 = 86.1%

Final differential: |86.1% - 69.5%| = 16.6% → still escalates

With larger gap (real scenario):
  Financial Analyst: 88% (regime + trend adjusted)
  Strategy Analyst: 65% (regime + trend adjusted)
  Differential: 23% → close to auto-resolution threshold

Comprehensive credibility enables accurate auto-resolution decisions.
```

**3. Enables Learning System Feedback (DD-006)**

Post-mortem lessons applied based on agent credibility. Example:

```text
Decision fails (30%+ deviation at 180-day checkpoint)
Post-mortem identifies: "Tech margin compression underestimated"

Which agent receives lesson?
  Option A: Financial Analyst (margin expert, 88% current credibility)
  Option B: Strategy Analyst (generalist, 71% current credibility)

Stale scores might show:
  Financial Analyst: 75% (dragged down by 2018-2020 old model)
  Strategy Analyst: 78% (benefiting from lucky 2019-2021 bull market)

Wrong lesson assignment: Strategy Analyst receives margin lesson despite lower true capability

Accurate scores:
  Financial Analyst: 88% (regime + trend adjusted, recent model performance)
  Strategy Analyst: 71% (regime + trend adjusted, current capability)

Correct lesson assignment: Financial Analyst receives lesson (higher credibility in margins)
```

**4. Tradeoffs Deemed Acceptable**

**Complexity vs Accuracy**: Multi-factor formula is complex, but failure modes are severe:

- Wrong debate auto-resolution → bad investment decision → financial loss
- Wrong lesson assignment → slower learning → compounding inaccuracy
- Regime blindness → systematic overconfidence in wrong conditions

**Computational Cost vs Performance**: Recalculation overhead managed via:

- Incremental updates (not full recalculation each time)
- Cached regime-specific scores (invalidate only on new data)
- Batch processing (daily regime, weekly trend, monthly comprehensive)
- Target: <200ms credibility retrieval (acceptable for debate resolution)

**Data Requirements vs Fallbacks**:

- Regime-specific: Need 50+ decisions → fallback to overall if insufficient
- Trend detection: Need 52 weeks → fallback to current if insufficient
- Context matching: Need 10+ similar → fallback to overall if insufficient

**5. Alignment with System Principles**

- **Human-in-the-loop**: Confidence intervals ensure premature auto-resolution avoided
- **Transparency**: Formula-based (not black-box ML) explainable to humans at Gate 4
- **Learning systems**: Captures agent evolution over time (trend detection)
- **Adaptive intelligence**: Regime-specific performance adapts to market conditions
- **Rigorous validation**: Backtestable on 2020-2023 historical data

**6. Risks Deemed Manageable**

**Risk: Insufficient data for regime-specific credibility**

- Mitigation: Fallback to overall credibility when sample_size < 50
- Acceptance: 70%+ of agents will have sufficient data by Phase 4

**Risk: Regime detection inaccuracy**

- Mitigation: Use established metrics (S&P, Fed Funds, VIX) with clear thresholds
- Acceptance: Even imperfect regime classification (80% accurate) improves over no regime awareness

**Risk: Trend detection noise (R² < 0.3)**

- Mitigation: Only apply trend adjustment if statistically significant (R² > 0.3)
- Acceptance: ~40% of agents will have significant trends, others use current accuracy

**Risk: Override tracking gaming (agents learn to match human bias)**

- Mitigation: Track override outcome accuracy (was human right?), investigate clustered overrides
- Acceptance: Post-mortem validation (DD-006) catches systematic gaming

---

## Consequences

### Positive Impacts

**1. Accurate Debate Auto-Resolution**

- **Before**: 50-60% of debates auto-resolved (stale credibility → narrow/misleading differentials)
- **After**: 70-80% of debates auto-resolved (accurate credibility → clear differentials when warranted)
- **Benefit**: Reduced human arbitration workload (Gate 4), faster analysis pipeline

**2. Improved Agent Recommendation Weighting**

- **Before**: Improving agents (65%→89%) underweighted at 79% simple average
- **After**: Improving agents extrapolated to 90.8% (trend-adjusted credibility)
- **Benefit**: Better final recommendations, higher system accuracy

**3. Regime-Adaptive Performance**

- **Before**: Bull-market specialist (92% in 2019-2021) overweighted in 2023 bear market (actual 68%)
- **After**: Regime-specific credibility (68% in bear market) appropriately weights agent
- **Benefit**: Reduced systematic errors in regime transitions (2022 inflation shock, 2023 rate hikes)

**4. Blind Spot Detection**

- **Before**: Valuation Agent with 45% override rate undetected, continues making same mistakes
- **After**: Override tracking (45% → 30% penalty) triggers investigation, root cause analysis
- **Benefit**: Faster identification of systematic agent weaknesses, targeted improvements

**5. Learning System Effectiveness**

- **Before**: Post-mortem lessons assigned based on stale credibility (wrong agent receives lesson)
- **After**: Lessons assigned to highest-credibility agent in relevant context
- **Benefit**: Faster system learning, compounding accuracy improvements

**6. Context-Specific Expertise Recognition**

- **Before**: Generalist (75% overall) weighted equally to specialist (88% in tech margins) for tech margin question
- **After**: Specialist gets higher weight (context match 5/6 dimensions → 86% vs generalist 76%)
- **Benefit**: Domain expertise properly valued, more accurate niche analyses

**7. Enables Future Optimizations**

- Agent responsibility expansion (improving agents handle more complex tasks)
- Dynamic gate routing (high-credibility agents get expedited review)
- Confidence-weighted voting (credibility × confidence for ensemble decisions)

### Negative Impacts / Tradeoffs

**1. Implementation Complexity**

- **Impact**: 5 components (temporal, regime, trend, override, context) vs simple average
- **Effort**: 2 weeks implementation + 1 week testing/validation (vs 3 days for time buckets)
- **Maintenance**: Ongoing tuning (half-life, regime thresholds, trend significance)
- **Mitigation**: Comprehensive test suite, validation against historical data, clear documentation

**2. Computational Overhead**

- **Recalculation costs**:
  - Daily: Regime detection (market data fetching, classification logic)
  - Weekly: Trend analysis (52-week linear regression per agent)
  - Monthly: Comprehensive review (all dimensions, all agents)
- **Storage costs**: 30+ new fields per AgentCredibility node (regime_credibility, trend metrics, override tracking)
- **Query latency**: Credibility retrieval <200ms target (vs <50ms for simple AVG)
- **Mitigation**: Incremental updates, cached scores, batch processing, performance benchmarking

**3. Data Requirements**

- **Regime-specific**: Need 50+ decisions per regime (6 regimes = 300+ total decisions for full coverage)
- **Trend detection**: Need 52 weeks of operational data
- **Context matching**: Need 10+ decisions per context dimension combination
- **Impact**: New agents (months 1-6) have limited regime/trend data → fallback to overall credibility
- **Mitigation**: Graceful degradation (fallback to overall if insufficient data), ramp-up period expected

**4. Explanation Complexity**

- **Before**: "Agent A has 78% accuracy, Agent B has 71%, differential 7% → escalate to human"
- **After**: "Agent A: 82% base × 0.93 temporal × 0.85 regime × 1.02 trend × 1.00 override = 65.8%, Agent B: 71% base × 0.87 temporal × 0.78 regime × 0.95 trend × 0.85 override = 41.2%, differential 24.6% → auto-resolve to A"
- **Impact**: Humans at Gate 4 may struggle to validate credibility calculations
- **Mitigation**: Provide breakdown in UI (show each component), highlight dominant factors, compare to simple average

**5. Tuning Parameter Sensitivity**

- **Decay half-life**: 2 years (default) vs 6 months (News Monitor) vs 3 years (Financial Analyst) - wrong choice distorts credibility
- **Regime thresholds**: S&P +10% (bull), Fed 3% (high rates), VIX 30 (high vol) - arbitrary boundaries create edge cases
- **Trend significance**: R² > 0.3 - too low (noise), too high (miss real trends)
- **Override penalties**: 20%/40% thresholds, 15%/30% penalties - wrong calibration over/under-penalizes
- **Mitigation**: Backtesting on 2020-2023 data, sensitivity analysis, A/B testing in production

**6. Potential Gaming Vectors**

- **Regime classification gaming**: Agent "optimizes" for bull market if knows regime detection logic
- **Trend gaming**: Agent improves accuracy short-term to boost extrapolated credibility
- **Override gaming**: Agent learns human biases, matches them to reduce override rate
- **Mitigation**:
  - Post-mortem outcome validation (DD-006) catches gaming long-term
  - Regime detection uses external market data (can't be gamed by individual agent)
  - Trend requires 52 weeks (hard to game sustainably)
  - Override outcome tracking (was human right?) detects bias-matching

### Affected Components

**Database Schema** (Memory System - DD-005):

- `AgentCredibility` node: +30 fields (regime_credibility, trend metrics, override tracking, decay parameters, context dimensions)
- Storage increase: ~2KB per agent per domain (~20 domains × 13 agents = 520KB total)

**Agent Systems**:

- **Debate Facilitator** (Coordination): Uses comprehensive credibility for auto-resolution logic
- **All Specialist Agents**: Credibility scores updated based on outcomes, overrides, regime changes
- **Learning Engine**: Applies lessons based on credibility-weighted agent selection

**Human Interface**:

- **Gate 4 Dashboard**: Display credibility breakdown (temporal, regime, trend, override components)
- **Debate Review UI**: Show credibility differential with confidence intervals
- **Override Tracking Dashboard**: Show override rates, reasons, outcome accuracy per agent

**Documentation**:

- ✅ `docs/learning/02-feedback-loops.md`: Time-weighted scoring section replaced with comprehensive approach
- ✅ `docs/architecture/02-memory-system.md`: AgentCredibility schema extended
- ✅ `docs/architecture/05-agents-coordination.md`: Debate credibility logic updated
- ✅ `docs/architecture/07-collaboration-protocols.md`: Credibility formula updated
- ✅ `docs/implementation/05-credibility-system.md`: Technical specification created (NEW)

**Code Changes** (Implementation Phase):

- `TimeWeightedCredibility` class: Exponential decay calculation
- `MarketRegimeDetector` class: Regime classification (S&P, Fed, VIX)
- `AgentTrendAnalysis` class: 52-week linear regression, extrapolation
- `HumanOverrideTracking` class: Override rate calculation, penalty determination
- `ComprehensiveCredibilitySystem` class: Orchestrator, final score calculation
- Integration with Debate Facilitator auto-resolution logic
- Integration with Memory System (knowledge graph updates)

---

## Implementation Notes

### Critical Constraints

**1. Performance Target**: <200ms credibility retrieval

- Cached scores (invalidate on new data only)
- Incremental updates (not full recalculation)
- Batch processing (daily regime, weekly trend, monthly comprehensive)

**2. Data Requirements**: Graceful degradation when insufficient data

- Regime-specific: Need 50+ decisions → fallback to overall if <50
- Trend detection: Need 52 weeks → fallback to current if <52
- Context matching: Need 10+ similar → fallback to overall if <10

**3. Backwards Compatibility**: Support agents with <6 months operational history

- Use overall accuracy if insufficient regime/trend data
- Confidence intervals widen for small sample sizes (N<10)
- Auto-resolution threshold increases (0.25 + CI_A + CI_B)

### Integration Points

**1. Debate Facilitator** (Level 2 Auto-Resolution):

```python
def should_auto_resolve(agent_A, agent_B, context):
    cred_A = credibility_system.calculate(agent_A.id, context.domain, context)
    cred_B = credibility_system.calculate(agent_B.id, context.domain, context)

    differential = abs(cred_A.score - cred_B.score)
    min_required = max(0.25, cred_A.confidence_interval + cred_B.confidence_interval)

    if differential > min_required:
        winner = agent_A if cred_A.score > cred_B.score else agent_B
        return (True, winner, cred_A, cred_B)
    else:
        return (False, None, cred_A, cred_B)  # Escalate to human
```

**2. Memory System** (Knowledge Graph Storage):

```cypher
MATCH (a:Agent {id: $agent_id})-[c:HAS_CREDIBILITY_IN]->(d:Domain {name: $domain})
SET c.overall_score = $overall_score,
    c.time_weighted_score = $temporal_weight,
    c.decay_halflife_years = $decay_halflife,
    c.regime_credibility = $regime_credibility,
    c.trend_slope = $trend_slope,
    c.trend_direction = $trend_direction,
    c.trend_strength = $trend_strength,
    c.override_rate = $override_rate,
    c.override_credibility_penalty = $override_penalty,
    c.context_dimensions = $context_dimensions,
    c.last_updated = datetime()
```

**3. Post-Mortem System** (DD-006 - Lesson Assignment):

```python
def assign_lesson(lesson, affected_domain):
    # Find highest-credibility agent in affected domain
    agents = get_agents_for_domain(affected_domain)
    credibilities = [(agent, calculate_credibility(agent, affected_domain))
                     for agent in agents]

    # Sort by credibility (descending)
    credibilities.sort(key=lambda x: x[1].score, reverse=True)

    # Assign to top agent (if credibility >70% and sample_size >20)
    top_agent, top_cred = credibilities[0]
    if top_cred.score > 0.70 and top_cred.sample_size > 20:
        apply_lesson(top_agent, lesson)
```

**4. Human Override Tracking** (Gates 4 & 5):

```python
def record_human_decision(agent_recommendation, human_decision, rationale):
    override = (agent_recommendation != human_decision)

    if override:
        store_override(
            agent_id=agent_recommendation.agent_id,
            agent_decision=agent_recommendation.decision,
            human_decision=human_decision,
            reason=rationale.category,  # missed_qualitative_factor, stale_data, flawed_logic
            context=agent_recommendation.context,
            timestamp=now()
        )

        # Update override metrics (used in next credibility calculation)
        update_override_rate(agent_recommendation.agent_id)
```

### Testing Requirements

**1. Historical Backtesting** (2020-2023 data)

Validate comprehensive credibility vs simple average:

```python
# For each historical decision (N=500+ decisions, 2020-2023)
for decision in historical_decisions:
    # Calculate credibility as-of decision date
    cred_simple = calculate_simple_average(agent, decision.date)
    cred_comprehensive = calculate_comprehensive(agent, decision.context, decision.date)

    # Measure prediction accuracy (6-month forward)
    actual_6mo_accuracy = get_actual_accuracy(agent, decision.date + 6_months)

    error_simple = abs(cred_simple - actual_6mo_accuracy)
    error_comprehensive = abs(cred_comprehensive.score - actual_6mo_accuracy)

# Target: comprehensive error < 0.70 × simple error (30% improvement)
assert mean(error_comprehensive) < 0.70 * mean(error_simple)
```

**2. Regime Transition Validation**

Test regime-specific credibility during 2020-2023 regime shifts:

```python
regime_transitions = [
    ('2020-Q1', 'HIGH_VOLATILITY'),      # COVID crash
    ('2020-Q2', 'BULL_LOW_RATES'),       # Recovery + stimulus
    ('2021-Q1', 'BULL_LOW_RATES'),       # Continued growth
    ('2022-Q1', 'BEAR_HIGH_RATES'),      # Inflation + rate hikes
    ('2023-Q1', 'NORMAL'),               # Stabilization
]

for transition_date, new_regime in regime_transitions:
    agents = get_all_agents()

    for agent in agents:
        # Credibility using simple average
        cred_simple = calculate_simple_average(agent, transition_date)

        # Credibility using regime-specific
        cred_regime = calculate_regime_specific(agent, new_regime, transition_date)

        # Measure accuracy in new regime (next 6 months)
        actual_accuracy = get_accuracy_in_regime(agent, new_regime, transition_date, 6_months)

        # Regime-specific should be closer to actual
        assert abs(cred_regime - actual_accuracy) < abs(cred_simple - actual_accuracy)
```

**3. Trend Detection Validation**

Identify improving agents (2020-2023):

```python
improving_agents = [
    ('strategy_analyst', [0.65, 0.72, 0.81, 0.87, 0.89]),  # 65%→89% improvement
    ('valuation_agent', [0.55, 0.72, 0.84, 0.88, 0.88]),   # 55%→88% improvement (after model upgrade)
]

for agent_id, accuracy_trajectory in improving_agents:
    # Calculate trend-adjusted credibility
    trend_metrics = analyze_trend(agent_id, accuracy_trajectory)

    assert trend_metrics['direction'] == 'improving'
    assert trend_metrics['strength'] > 0.5  # Strong trend
    assert trend_metrics['extrapolated_6mo'] > accuracy_trajectory[-1]  # Extrapolation > current
```

**4. Override Tracking Validation**

Identify agents with high override rates:

```python
high_override_agents = [
    ('valuation_agent', 0.45, 0.82),  # 45% override rate, 82% of overrides correct
]

for agent_id, override_rate, override_accuracy in high_override_agents:
    override_metrics = calculate_override_metrics(agent_id)

    assert override_metrics['override_rate'] > 0.40  # Critical threshold
    assert override_metrics['override_outcome_accuracy'] > 0.75  # Humans adding value

    penalty = calculate_override_penalty(override_rate)
    assert penalty == 0.70  # 30% penalty for >40% override rate
```

**5. Auto-Resolution Accuracy**

Measure auto-resolution correctness vs human decisions:

```python
# For debates that auto-resolved (credibility differential >0.25)
auto_resolved_debates = get_debates_auto_resolved(2020, 2023)

for debate in auto_resolved_debates:
    # Get auto-resolution winner
    auto_winner = debate.auto_resolution_winner

    # Get eventual human validation (if any)
    human_winner = debate.eventual_human_validation

    # Measure agreement
    agreement = (auto_winner == human_winner)

# Target: >85% agreement (auto-resolution matches human judgment)
assert sum(agreement) / len(auto_resolved_debates) > 0.85
```

### Rollback Strategy

**Phase 1: Parallel Calculation** (Week 1-2)

- Calculate both simple and comprehensive credibility
- Store both in database (separate fields)
- Use simple credibility for decisions (production)
- Log comprehensive credibility (shadow mode)
- Compare distributions, identify outliers

**Phase 2: A/B Testing** (Week 3-4)

- 50% of debates use comprehensive credibility
- 50% of debates use simple credibility
- Measure auto-resolution accuracy, human override rates
- Validate comprehensive performs better

**Phase 3: Full Rollout** (Week 5)

- 100% of debates use comprehensive credibility
- Monitor for regressions (auto-resolution accuracy, override rates)
- Keep simple credibility calculation for 30 days (rollback option)

**Rollback Trigger**: If comprehensive credibility shows:

- Auto-resolution accuracy <80% (vs >85% target)
- Human override rate >25% (vs <20% target)
- Credibility calculation latency >500ms (vs <200ms target)

**Rollback Procedure**:

1. Switch all debates back to simple credibility (1-line config change)
2. Investigate root cause (regime detection? trend detection? override tracking?)
3. Fix in shadow mode, re-validate with backtesting
4. Re-attempt rollout after validation

---

**Estimated Implementation Effort**: 2-3 weeks

**Breakdown**:

- Week 1: Implement core classes (TimeWeightedCredibility, MarketRegimeDetector, AgentTrendAnalysis, HumanOverrideTracking, ComprehensiveCredibilitySystem)
- Week 2: Database schema updates, integration with Debate Facilitator, Memory System, Post-Mortem System
- Week 3: Testing (backtesting, regime validation, trend validation, override validation, auto-resolution accuracy), documentation updates

**Dependencies**:

**Must Be Completed First**:

- [DD-005: Memory Scalability Optimization](DD-005_MEMORY_SCALABILITY_OPTIMIZATION.md) - Credibility recalculation must scale to 1000+ stocks
- [DD-006: Negative Feedback System](DD-006_NEGATIVE_FEEDBACK_SYSTEM.md) - Post-mortems update credibility based on outcomes
- [DD-003: Debate Deadlock Resolution](DD-003_DEBATE_DEADLOCK_RESOLUTION.md) - Auto-resolution logic uses credibility

**External Systems/APIs Required**:

- **FRED API** (Federal Reserve Economic Data): Fed Funds Rate (FEDFUNDS series)
- **S&P 500 data**: YoY returns (FRED `SP500` series or market data provider)
- **VIX data**: Volatility index (CBOE API or market data provider)
- **Market data provider**: Daily market indicators (alternative to FRED for lower latency)

---

## Open Questions

**1. Regime taxonomy completeness?**

Current 6 regimes (BULL_LOW_RATES, BULL_HIGH_RATES, BEAR_HIGH_RATES, BEAR_LOW_RATES, HIGH_VOLATILITY, NORMAL) - sufficient coverage?

**Missing regimes**:

- STAGFLATION (high inflation + low growth) - rare but distinct (1970s)
- DELEVERAGING (post-crisis balance sheet recession) - 2008-2009
- PANDEMIC (unique dynamics) - 2020

**Options**:

- A) Keep 6 regimes (simpler, sufficient coverage for 80%+ of market history)
- B) Expand to 9-10 regimes (better coverage, but needs more data per regime - 50+ decisions × 10 regimes = 500+ decisions required)

**Recommendation**: Start with 6 regimes (Option A), add specialized regimes if insufficient (e.g., if NORMAL regime has high variance, split into sub-regimes)

**2. Override reason taxonomy?**

Current categorization: `missed_qualitative_factor`, `stale_data`, `flawed_logic`

**Missing categories**:

- `incomplete_analysis` (agent didn't consider all relevant factors)
- `overconfidence` (agent overweighted weak evidence)
- `wrong_assumptions` (DCF assumptions unrealistic)
- `timing_error` (right direction, wrong timeframe)

**Options**:

- A) Keep 3 broad categories (simpler, easier for humans to categorize at Gate 4)
- B) Expand to 7-8 categories (better root cause tracking, but humans may struggle to categorize)

**Recommendation**: Start with 3 broad categories (Option A), refine based on 6-month override pattern analysis

**3. Trend detection sensitivity (R² threshold)?**

Current: R² > 0.3 for trend extrapolation

**Too low** (R² = 0.2): Noisy trends applied, extrapolation unreliable
**Too high** (R² = 0.5): Miss real but moderate trends, underestimate improving agents

**Options**:

- A) Fixed threshold (R² > 0.3) - simpler, consistent
- B) Dynamic threshold based on sample size (R² > 0.3 for N=52, R² > 0.2 for N=104) - adapts to data quality
- C) A/B test thresholds (0.2, 0.3, 0.4) on historical data, select best

**Recommendation**: Option C (A/B test on 2020-2023 data), likely settle on R² > 0.3 (Option A)

**Blocking**: No - reasonable default (R² > 0.3) available, can refine later

---

## References

**Internal Documentation**:

- [Flaw #4: Agent Credibility Scoring](../docs/design-flaws/resolved/04-credibility-scoring.md) - Original flaw specification
- [Feedback Loops](../docs/learning/02-feedback-loops.md) - Time-weighted scoring implementation
- [Memory System](../docs/architecture/02-memory-system.md) - AgentCredibility schema
- [Coordination Agents](../docs/architecture/05-agents-coordination.md) - Debate credibility logic
- [Collaboration Protocols](../docs/architecture/07-collaboration-protocols.md) - Credibility weighting
- [Credibility System Implementation](../docs/implementation/05-credibility-system.md) - Technical specification
- [DD-003: Debate Deadlock Resolution](DD-003_DEBATE_DEADLOCK_RESOLUTION.md) - Auto-resolution logic
- [DD-005: Memory Scalability Optimization](DD-005_MEMORY_SCALABILITY_OPTIMIZATION.md) - Performance constraints
- [DD-006: Negative Feedback System](DD-006_NEGATIVE_FEEDBACK_SYSTEM.md) - Post-mortem credibility updates

**External Research**:

- **Temporal Weighting**: _Exponential Decay Models in Forecasting_ - Justifies half-life approach over time buckets
- **Regime Detection**: NBER Business Cycle Dating - Established methodology for regime classification
- **Performance Trend Analysis**: _Rolling Regression in Financial Time Series_ - 52-week window justification
- **Confidence Intervals**: Wilson Score Interval for binomial proportions - Statistical rigor for small samples
- **Market Data Sources**:
  - FRED API Documentation (Federal Reserve Economic Data)
  - CBOE VIX Methodology White Paper
  - S&P 500 Index Methodology

**Similar Decisions in Other Systems**:

- **Kaggle Competitions**: Exponential decay for participant rankings (time-weighted performance)
- **Elo Rating System**: Dynamic ratings with K-factor (equivalent to learning rate, similar to trend adjustment)
- **Credit Scoring**: FICO uses temporal decay (recent credit behavior weighted more heavily)
- **Recommendation Systems**: Netflix uses regime-specific accuracy (comedy vs drama predictions tracked separately)

---

## Status History

| Date       | Status      | Notes                                                      |
| ---------- | ----------- | ---------------------------------------------------------- |
| 2025-11-17 | Proposed    | Initial proposal created based on Flaw #4 analysis         |
| 2025-11-17 | Approved    | Approved based on comprehensive design review              |
| 2025-11-17 | Implemented | Documentation updates completed across 5 architecture docs |

**Next Steps**:

1. Code implementation (Week 1-2): Core classes, database schema updates
2. Integration (Week 2-3): Debate Facilitator, Memory System, Post-Mortem System
3. Testing & Validation (Week 3): Backtesting 2020-2023, regime validation, trend validation
4. Production Rollout (Week 4): A/B testing → Full rollout

---

## Notes

**Design Philosophy**: This decision prioritizes **accuracy over simplicity**. While a simple time-bucket approach (Option 1) would be easier to implement and explain, the consequences of inaccurate credibility scores are severe:

- Wrong debate auto-resolution → bad investment decisions → financial loss
- Wrong lesson assignment → slower learning → compounding inaccuracy
- Regime blindness → systematic overconfidence in wrong conditions

The comprehensive multi-factor approach (Option 3) addresses all identified failure modes at the cost of implementation complexity. This tradeoff is acceptable because:

1. **Credibility is foundational**: Used in debates (DD-003), learning (DD-006), pattern validation (DD-001), human gates (all gates)
2. **Failures are costly**: Bad investment decisions due to wrong agent weighting have direct financial impact
3. **Complexity is manageable**: Formula-based (not black-box ML), explainable, backtestable
4. **Future-proof**: Captures agent evolution, adapts to regime shifts, enables advanced optimizations

**Future Enhancements** (Post-Phase 4):

- **Ensemble credibility**: Combine multiple agents' credibility for final recommendation (credibility-weighted voting)
- **Dynamic responsibility allocation**: Improving agents (90%+ credibility) handle more complex analyses
- **Credibility-based gate routing**: High-credibility agents get expedited Gate 3/5 review
- **Meta-learning**: Learn optimal decay half-life, regime thresholds, trend significance from data
- **Confidence intervals in UI**: Visualize credibility with error bars at Gate 4 for human review

**Lessons Learned from Similar Systems**:

- **Kaggle**: Exponential decay prevents "resting on laurels" (one good submission shouldn't dominate forever)
- **Elo ratings**: Dynamic ratings capture player improvement over time (chess ratings increase with skill)
- **Credit scoring**: Recent behavior (last 6 months) matters more than 5-year-old bankruptcy
- **Netflix**: Comedy recommendations use comedy-specific accuracy, not overall accuracy

This decision applies these proven principles to agent credibility scoring.
