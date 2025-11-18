# Agent Credibility System - Technical Specification

## Overview

This document provides the technical specification for the comprehensive agent credibility scoring system that addresses temporal decay, market regime adaptation, performance trend detection, and human override tracking.

**Related Design Decisions**:
- [DD-008: Comprehensive Agent Credibility System](../design-decisions/DD-008_AGENT_CREDIBILITY_SYSTEM.md)
- [DD-004: Agent Credibility Scoring](../../docs/design-flaws/resolved/04-credibility-scoring.md) (RESOLVED)

---

## Implementation Phases

The credibility system is implemented in two phases to balance rapid delivery with comprehensive functionality:

### Phase 2: Simple Credibility (Months 3-4)

**Components implemented**:
- ✅ **TimeWeightedCredibility** (Section 1 below)
- ✅ **Wilson confidence intervals** (integrated into TimeWeightedCredibility)

**Phase 2 configuration**:
```python
# Simple credibility calculation (Phase 2 only)
simple_credibility_config = {
    'decay_halflife_years': 2.0,           # Exponential temporal decay
    'min_sample_size': 15,                  # Minimum datapoints for auto-resolution
    'confidence_level': 0.95,               # Wilson score confidence level
    'regime_detection': False,              # No regime-specific scoring
    'trend_detection': False,               # No trend extrapolation
    'override_tracking': False,             # No override penalties
    'context_matching': False               # No multi-dimensional matching
}

# Phase 2 credibility formula
credibility_score = base_accuracy * temporal_weight

# Auto-resolution threshold (includes confidence intervals)
min_differential = max(0.25, wilson_CI_A + wilson_CI_B)
```

**Use case**: Enables debate auto-resolution (DD-003 Level 2) with statistically sound credibility differentials

**Limitations**:
- No market regime awareness (bull vs bear performance conflated)
- No trend detection (improving agents underestimated)
- No override tracking (blind spots undetected)
- No context matching (domain specialists not distinguished)

---

### Phase 4: Comprehensive Credibility (Months 7-8)

**Additional components implemented**:
- ✅ **MarketRegimeDetector** (Section 2 below)
- ✅ **AgentTrendAnalysis** (Section 3 below)
- ✅ **HumanOverrideTracking** (Section 4 below)
- ✅ **Context matching** (Section 5 below)
- ✅ **ComprehensiveCredibilitySystem** (Section 6 below - orchestrator)

**Phase 4 configuration**:
```python
# Comprehensive credibility calculation (Phase 4)
comprehensive_credibility_config = {
    'decay_halflife_years': 2.0,           # Exponential temporal decay
    'min_sample_size': 15,                  # Minimum datapoints for auto-resolution
    'confidence_level': 0.95,               # Wilson score confidence level
    'regime_detection': True,               # ✅ Regime-specific scoring (6 regimes)
    'regime_min_samples': 50,               # Min samples for regime-specific credibility
    'trend_detection': True,                # ✅ 52-week trend extrapolation
    'trend_min_r_squared': 0.3,             # Min R² for trend significance
    'override_tracking': True,              # ✅ Override rate penalties
    'override_thresholds': [0.20, 0.40],    # Penalty thresholds (15%, 30%)
    'context_matching': True,               # ✅ Multi-dimensional context
    'context_dimensions': 5                 # sector, metric_type, time_horizon, size, growth
}

# Phase 4 credibility formula (full DD-008 spec)
credibility_score = (
    base_accuracy *           # Context-matched historical accuracy
    temporal_weight *         # Exponential decay (2-year half-life)
    regime_adjustment *       # Current market regime performance
    trend_adjusted *          # Performance trajectory extrapolation
    override_penalty          # Human override rate penalty
)
```

**Backward compatibility**: Falls back to Phase 2 simple credibility if insufficient data for regime/trend/override/context components

---

## System Components

**Note**: Sections below describe the full Phase 4 implementation. For Phase 2, only Section 1 (TimeWeightedCredibility with confidence intervals) is implemented. Sections 2-6 are Phase 4 enhancements.

### 1. TimeWeightedCredibility

**Purpose**: Apply exponential temporal decay to agent performance data

**Class Definition**:

```python
class TimeWeightedCredibility:
    """
    Calculates credibility with exponential temporal decay
    """

    def __init__(self, agent_id: str, decay_halflife_years: float = 2.0):
        self.agent_id = agent_id
        self.decay_halflife_years = decay_halflife_years

    def calculate_temporal_weight(self, age_years: float) -> float:
        """
        Calculate temporal weight using exponential decay

        Args:
            age_years: Age of prediction in years

        Returns:
            Weight between 0 and 1 (recent=1.0, old approaches 0)
        """
        return 0.5 ** (age_years / self.decay_halflife_years)

    def apply_weights(self, predictions: List[Prediction]) -> float:
        """
        Calculate weighted accuracy across all predictions

        Args:
            predictions: List of historical predictions with timestamps

        Returns:
            Time-weighted accuracy score (0-1)
        """
        weighted_sum = 0.0
        weight_sum = 0.0

        current_time = datetime.now()

        for pred in predictions:
            age_years = (current_time - pred.timestamp).days / 365.25
            weight = self.calculate_temporal_weight(age_years)

            weighted_sum += pred.accuracy * weight
            weight_sum += weight

        return weighted_sum / weight_sum if weight_sum > 0 else 0.0
```

**Configuration**:

- **Default half-life**: 2 years (recent performance 2x weight of 2-year-old data)
- **Agent-specific tuning**:
  - News Monitor: 6 months (fast-changing domain)
  - Financial Analyst: 3 years (stable domain)
  - Strategy Analyst: 2 years (balanced)
  - Valuation Agent: 2 years (balanced)

**Example Weights**:

| Age      | Weight |
| -------- | ------ |
| 3 months | 0.93   |
| 6 months | 0.87   |
| 1 year   | 0.71   |
| 2 years  | 0.50   |
| 4 years  | 0.25   |
| 8 years  | 0.06   |

---

### 2. MarketRegimeDetector

**Purpose**: Classify current market conditions and retrieve regime-specific agent performance

**Market Regime Taxonomy**:

```python
from enum import Enum

class MarketRegime(Enum):
    BULL_LOW_RATES = "bull_low_rates"       # S&P +10%+ YoY, Fed <3%, VIX <20
    BULL_HIGH_RATES = "bull_high_rates"     # S&P +10%+ YoY, Fed ≥3%
    BEAR_HIGH_RATES = "bear_high_rates"     # S&P negative YoY, Fed ≥3%, VIX >25
    BEAR_LOW_RATES = "bear_low_rates"       # S&P negative YoY, Fed <3%
    HIGH_VOLATILITY = "high_volatility"     # VIX >30 (regardless of returns)
    NORMAL = "normal"                       # Default classification
```

**Detection Logic**:

```python
class MarketRegimeDetector:
    """
    Detects current market regime based on market indicators
    """

    def __init__(self, market_data_source: MarketDataAPI):
        self.data_source = market_data_source

    def detect_current_regime(self) -> MarketRegime:
        """
        Classify current market regime

        Returns:
            MarketRegime enum value
        """
        # Fetch current market indicators
        sp500_ytd_return = self.data_source.get_sp500_ytd_return()
        fed_funds_rate = self.data_source.get_fed_funds_rate()
        vix = self.data_source.get_vix()

        # High volatility overrides other classifications
        if vix > 30:
            return MarketRegime.HIGH_VOLATILITY

        # Bull market classifications
        if sp500_ytd_return > 0.10:
            if fed_funds_rate >= 3.0:
                return MarketRegime.BULL_HIGH_RATES
            else:
                return MarketRegime.BULL_LOW_RATES

        # Bear market classifications
        if sp500_ytd_return < 0:
            if fed_funds_rate >= 3.0 and vix > 25:
                return MarketRegime.BEAR_HIGH_RATES
            else:
                return MarketRegime.BEAR_LOW_RATES

        # Default
        return MarketRegime.NORMAL

    def get_regime_specific_accuracy(
        self,
        agent_id: str,
        domain: str,
        regime: MarketRegime
    ) -> Tuple[float, int]:
        """
        Retrieve agent's accuracy in specific regime

        Returns:
            (accuracy, sample_size) tuple
        """
        # Query knowledge graph for regime-specific performance
        query = f"""
        MATCH (a:Agent)-[c:HAS_CREDIBILITY_IN]->(d:Domain)
        WHERE a.id = $agent_id AND d.name = $domain
        RETURN c.regime_credibility[$regime] as regime_data
        """

        result = self.data_source.query_graph(query, {
            'agent_id': agent_id,
            'domain': domain,
            'regime': regime.value
        })

        if result and result['regime_data']:
            return (
                result['regime_data']['accuracy'],
                result['regime_data']['sample_size']
            )
        else:
            return (0.0, 0)  # No data for this regime
```

**Data Sources**:

- **S&P 500 returns**: FRED API (`SP500` series)
- **Fed Funds Rate**: FRED API (`FEDFUNDS` series)
- **VIX**: CBOE API or market data provider
- **Update frequency**: Daily (cached for 24 hours)

**Regime-Specific Credibility Calculation**:

```python
def calculate_regime_adjusted_credibility(
    overall_accuracy: float,
    regime_accuracy: float,
    regime_sample_size: int
) -> float:
    """
    Blend regime-specific accuracy with overall accuracy

    Args:
        overall_accuracy: Agent's overall accuracy in domain
        regime_accuracy: Agent's accuracy in current regime
        regime_sample_size: Number of decisions in this regime

    Returns:
        Regime-adjusted credibility score
    """
    # If sufficient regime-specific data (50+ decisions)
    if regime_sample_size >= 50:
        return regime_accuracy * 0.70 + overall_accuracy * 0.30

    # If insufficient regime data (<50 decisions)
    else:
        return regime_accuracy * 0.30 + overall_accuracy * 0.70
```

---

### 3. AgentTrendAnalysis

**Purpose**: Detect performance trends and extrapolate future capability

**Class Definition**:

```python
import numpy as np
from scipy.stats import linregress

class AgentTrendAnalysis:
    """
    Analyzes agent performance trends using linear regression
    """

    def __init__(self, agent_id: str, domain: str):
        self.agent_id = agent_id
        self.domain = domain

    def calculate_trend(
        self,
        accuracy_history: List[Tuple[datetime, float]]
    ) -> Dict[str, float]:
        """
        Calculate performance trend via linear regression

        Args:
            accuracy_history: List of (timestamp, accuracy) tuples
            Must have at least 52 weeks of weekly data

        Returns:
            Dict with trend metrics:
                - slope: Accuracy change per year
                - direction: 'improving', 'stable', or 'degrading'
                - strength: R-squared (0-1)
                - extrapolated_6mo: Projected accuracy in 6 months
        """
        if len(accuracy_history) < 52:
            return {
                'slope': 0.0,
                'direction': 'stable',
                'strength': 0.0,
                'extrapolated_6mo': accuracy_history[-1][1] if accuracy_history else 0.0
            }

        # Convert timestamps to years from start
        start_time = accuracy_history[0][0]
        x = np.array([
            (ts - start_time).days / 365.25
            for ts, _ in accuracy_history
        ])
        y = np.array([acc for _, acc in accuracy_history])

        # Linear regression
        slope, intercept, r_value, p_value, std_err = linregress(x, y)

        # Calculate current and extrapolated accuracy
        current_time = x[-1]
        current_accuracy = y[-1]
        future_time = current_time + 0.5  # 6 months forward
        extrapolated = intercept + slope * future_time

        # Cap at realistic bounds
        extrapolated = max(0.0, min(0.95, extrapolated))

        # Determine direction
        if slope > 0.05:  # >5% per year improvement
            direction = 'improving'
        elif slope < -0.05:  # >5% per year degradation
            direction = 'degrading'
        else:
            direction = 'stable'

        return {
            'slope': slope,
            'direction': direction,
            'strength': r_value ** 2,  # R-squared
            'extrapolated_6mo': extrapolated
        }

    def apply_trend_adjustment(
        self,
        current_accuracy: float,
        trend_metrics: Dict[str, float]
    ) -> float:
        """
        Adjust credibility based on performance trend

        Args:
            current_accuracy: Current accuracy score
            trend_metrics: Output from calculate_trend()

        Returns:
            Trend-adjusted credibility
        """
        # Only apply if trend is statistically significant
        if trend_metrics['strength'] < 0.3:  # R² < 0.3
            return current_accuracy

        # Blend current with extrapolated (30% extrapolation weight)
        adjusted = (
            current_accuracy * 0.70 +
            trend_metrics['extrapolated_6mo'] * 0.30
        )

        return adjusted
```

**Requirements**:

- Minimum 52 weeks of weekly accuracy measurements
- Statistical significance threshold: R² > 0.3
- Extrapolation limited to 6 months forward
- Capped at 95% maximum accuracy (realistic upper bound)

**Trend Monitoring**:

- Flagged for review if `trend_strength > 0.5`
- Improving agents: Consider expanding responsibilities
- Degrading agents: Investigate root cause (model drift, domain shift)

---

### 4. HumanOverrideTracking

**Purpose**: Track when humans override agents to identify systematic blind spots

**Class Definition**:

```python
from collections import defaultdict

class HumanOverrideTracking:
    """
    Tracks human overrides and calculates credibility penalties
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def calculate_override_metrics(
        self,
        recommendations: List[Recommendation]
    ) -> Dict[str, Any]:
        """
        Calculate override rate and breakdown

        Args:
            recommendations: List of agent recommendations with override data

        Returns:
            Dict with override metrics:
                - override_rate: Overall % overridden
                - override_outcome_accuracy: % of overrides that were correct
                - override_reasons: Breakdown by reason category
                - override_by_context: Breakdown by sector/metric/regime
        """
        total = len(recommendations)
        overridden = [r for r in recommendations if r.human_override]
        override_count = len(overridden)

        # Overall override rate
        override_rate = override_count / total if total > 0 else 0.0

        # Override outcome accuracy (was human right to override?)
        override_correct = sum(
            1 for r in overridden
            if r.override_outcome == 'correct'
        )
        override_outcome_accuracy = (
            override_correct / override_count
            if override_count > 0 else 0.0
        )

        # Breakdown by reason
        reason_counts = defaultdict(int)
        for r in overridden:
            reason_counts[r.override_reason] += 1

        override_reasons = {
            reason: count / override_count
            for reason, count in reason_counts.items()
        } if override_count > 0 else {}

        # Breakdown by context
        context_override_rates = self._calculate_context_rates(
            recommendations
        )

        return {
            'override_rate': override_rate,
            'override_outcome_accuracy': override_outcome_accuracy,
            'override_reasons': override_reasons,
            'override_by_context': context_override_rates
        }

    def _calculate_context_rates(
        self,
        recommendations: List[Recommendation]
    ) -> Dict[str, Dict[str, float]]:
        """Calculate override rate by sector, metric, regime"""
        context_totals = defaultdict(lambda: defaultdict(int))
        context_overrides = defaultdict(lambda: defaultdict(int))

        for r in recommendations:
            # Track by sector
            context_totals['sector'][r.sector] += 1
            if r.human_override:
                context_overrides['sector'][r.sector] += 1

            # Track by metric type
            context_totals['metric'][r.metric_type] += 1
            if r.human_override:
                context_overrides['metric'][r.metric_type] += 1

            # Track by regime
            context_totals['regime'][r.regime] += 1
            if r.human_override:
                context_overrides['regime'][r.regime] += 1

        # Calculate rates
        context_rates = {}
        for context_type in ['sector', 'metric', 'regime']:
            context_rates[context_type] = {
                key: (
                    context_overrides[context_type][key] /
                    context_totals[context_type][key]
                )
                for key in context_totals[context_type]
            }

        return context_rates

    def calculate_credibility_penalty(
        self,
        override_rate: float
    ) -> float:
        """
        Calculate credibility multiplier based on override rate

        Args:
            override_rate: % of recommendations overridden (0-1)

        Returns:
            Credibility multiplier (0.70-1.00)
        """
        # Acceptable: <20% override rate
        if override_rate < 0.20:
            return 1.00  # No penalty

        # Concerning: 20-40% override rate
        elif override_rate < 0.40:
            return 0.85  # 15% penalty

        # Critical: >40% override rate
        else:
            return 0.70  # 30% penalty
```

**Root Cause Analysis Triggers**:

- Override rate >30% for 3 consecutive months
- Overrides clustered in specific context (e.g., 60% override rate in tech sector)
- Human override accuracy >75% (humans consistently adding value)

**Integration with Gates**:

- Gate 4: Human arbitration records override decisions
- Gate 5: Final decision captures override outcomes
- Post-mortem: Validates whether override was correct

---

### 5. ComprehensiveCredibilitySystem

**Purpose**: Orchestrate all credibility components into final score

**Class Definition**:

```python
class ComprehensiveCredibilitySystem:
    """
    Main orchestrator for comprehensive credibility scoring
    """

    def __init__(self):
        self.temporal_scorer = TimeWeightedCredibility
        self.regime_detector = MarketRegimeDetector
        self.trend_analyzer = AgentTrendAnalysis
        self.override_tracker = HumanOverrideTracking

    def calculate_credibility(
        self,
        agent_id: str,
        domain: str,
        context: AnalysisContext
    ) -> CredibilityScore:
        """
        Calculate comprehensive credibility score

        Args:
            agent_id: Agent identifier
            domain: Domain/specialization
            context: Current analysis context (sector, metric, regime, etc.)

        Returns:
            CredibilityScore object with final score and breakdown
        """
        # 1. Get agent's historical predictions
        predictions = self._fetch_predictions(agent_id, domain)

        # 2. Calculate base accuracy with context matching
        base_accuracy = self._calculate_context_matched_accuracy(
            predictions, context
        )

        # 3. Apply temporal decay
        temporal_weight = self.temporal_scorer(
            agent_id
        ).apply_weights(predictions)

        # 4. Get regime-specific adjustment
        current_regime = self.regime_detector.detect_current_regime()
        regime_accuracy, regime_sample_size = (
            self.regime_detector.get_regime_specific_accuracy(
                agent_id, domain, current_regime
            )
        )
        regime_adjustment = calculate_regime_adjusted_credibility(
            base_accuracy, regime_accuracy, regime_sample_size
        )

        # 5. Calculate performance trend
        accuracy_history = self._fetch_accuracy_history(agent_id, domain)
        trend_metrics = self.trend_analyzer(
            agent_id, domain
        ).calculate_trend(accuracy_history)
        trend_adjusted = self.trend_analyzer.apply_trend_adjustment(
            base_accuracy, trend_metrics
        )

        # 6. Apply human override penalty
        recommendations = self._fetch_recommendations(agent_id, domain)
        override_metrics = self.override_tracker(
            agent_id
        ).calculate_override_metrics(recommendations)
        override_penalty = self.override_tracker.calculate_credibility_penalty(
            override_metrics['override_rate']
        )

        # 7. Calculate confidence interval
        sample_size = len(predictions)
        confidence_interval = self._calculate_confidence_interval(
            base_accuracy, sample_size
        )

        # 8. Final credibility score
        final_credibility = (
            base_accuracy *
            temporal_weight *
            regime_adjustment *
            trend_adjusted *
            override_penalty
        )

        return CredibilityScore(
            score=final_credibility,
            confidence_interval=confidence_interval,
            breakdown={
                'base_accuracy': base_accuracy,
                'temporal_weight': temporal_weight,
                'regime_adjustment': regime_adjustment,
                'trend_adjusted': trend_adjusted,
                'override_penalty': override_penalty,
                'sample_size': sample_size
            },
            context_match=context,
            regime=current_regime,
            trend_metrics=trend_metrics,
            override_metrics=override_metrics
        )

    def _calculate_context_matched_accuracy(
        self,
        predictions: List[Prediction],
        context: AnalysisContext
    ) -> float:
        """
        Calculate accuracy with multi-dimensional context matching

        Context dimensions: sector, metric_type, time_horizon,
                           company_size, growth_stage
        """
        # Count dimension matches
        context_specific = []
        for pred in predictions:
            match_score = 0
            if pred.sector == context.sector:
                match_score += 1
            if pred.metric_type == context.metric_type:
                match_score += 1
            if pred.time_horizon == context.time_horizon:
                match_score += 1
            if pred.company_size == context.company_size:
                match_score += 1
            if pred.growth_stage == context.growth_stage:
                match_score += 1

            # Store with match quality
            context_specific.append((pred, match_score))

        # Calculate overall and context-specific accuracy
        overall_accuracy = np.mean([p.accuracy for p in predictions])

        # Get predictions with high context match (4-6 dimensions)
        high_match = [
            p for p, score in context_specific
            if score >= 4
        ]

        if len(high_match) >= 10:  # Sufficient context-specific data
            context_accuracy = np.mean([p.accuracy for p in high_match])
            context_weight = 0.70
        elif len(high_match) >= 3:  # Some context data
            context_accuracy = np.mean([p.accuracy for p in high_match])
            context_weight = 0.30
        else:  # No context match
            context_accuracy = overall_accuracy
            context_weight = 0.0

        # Blend context-specific with overall
        return (
            context_accuracy * context_weight +
            overall_accuracy * (1 - context_weight)
        )

    def _calculate_confidence_interval(
        self,
        credibility: float,
        sample_size: int
    ) -> float:
        """
        Calculate 95% confidence interval for credibility score

        Uses Wilson score interval for binomial proportion
        """
        if sample_size < 5:
            return 0.5  # Very wide interval for small samples

        # 95% confidence (z = 1.96)
        z = 1.96

        interval = z * np.sqrt(
            (credibility * (1 - credibility)) / sample_size
        )

        return interval
```

---

## Integration Points

### Debate Facilitator Integration

**Auto-Resolution Logic**:

```python
def should_auto_resolve(
    agent_A_credibility: CredibilityScore,
    agent_B_credibility: CredibilityScore
) -> Tuple[bool, str]:
    """
    Determine if debate can be auto-resolved based on credibility

    Returns:
        (should_resolve, winning_agent_id)
    """
    # Calculate differential
    differential = abs(
        agent_A_credibility.score - agent_B_credibility.score
    )

    # Ensure differential exceeds confidence intervals
    min_required = max(
        0.25,
        agent_A_credibility.confidence_interval +
        agent_B_credibility.confidence_interval
    )

    if differential > min_required:
        # Auto-resolve to higher credibility agent
        winner = (
            'agent_A' if agent_A_credibility.score > agent_B_credibility.score
            else 'agent_B'
        )
        return (True, winner)
    else:
        # Escalate to human
        return (False, None)
```

### Memory System Integration

**Storage in Knowledge Graph**:

```cypher
# Update agent credibility node with comprehensive data
MATCH (a:Agent {id: $agent_id})-[c:HAS_CREDIBILITY_IN]->(d:Domain {name: $domain})
SET c.overall_score = $overall_score,
    c.time_weighted_score = $temporal_weight,
    c.decay_halflife_years = $decay_halflife,
    c.last_decay_calculation = datetime(),
    c.regime_credibility = $regime_credibility,
    c.trend_slope = $trend_slope,
    c.trend_direction = $trend_direction,
    c.trend_strength = $trend_strength,
    c.extrapolated_6mo = $extrapolated_6mo,
    c.trend_last_calculated = datetime(),
    c.override_rate = $override_rate,
    c.override_outcome_accuracy = $override_outcome_accuracy,
    c.override_reasons = $override_reasons,
    c.override_credibility_penalty = $override_penalty,
    c.context_dimensions = $context_dimensions,
    c.last_updated = datetime()
```

### Recalculation Triggers

**Trigger Schedule**:

| Trigger Type             | Frequency     | Priority | Actions                                        |
| ------------------------ | ------------- | -------- | ---------------------------------------------- |
| Major error              | Immediate     | Critical | Recalculate all scores, update debates         |
| Human override           | Within 1 hour | High     | Update override metrics, apply penalty         |
| Challenge lost in debate | Within 1 hour | High     | Update credibility, track debate outcome       |
| New outcome recorded     | Daily batch   | Normal   | Incremental update, regime classification      |
| Regime detection         | Daily         | Normal   | Detect regime, update regime-specific scores   |
| Trend analysis           | Weekly        | Normal   | 52-week rolling regression, extrapolate        |
| Comprehensive review     | Monthly       | Normal   | Full recalculation, all dimensions, validation |
| Override rate analysis   | Quarterly     | Normal   | Blind spot investigation, root cause analysis  |

---

## Testing & Validation

### Historical Backtesting Requirements

**Test Data**:

- 2020-2023 historical data (includes regime transitions)
- Multiple agents with varying performance patterns
- Minimum 100 predictions per agent
- Cover all market regimes

**Validation Metrics**:

1. **Temporal Decay Validation**:

   - Verify recent performance weighted more heavily
   - Confirm smooth decay curve (no cliff effects)
   - Test half-life tuning across agent types

2. **Regime Detection Accuracy**:

   - Classify historical periods correctly
   - Verify regime transitions captured accurately
   - Test regime-specific credibility improves predictions

3. **Trend Detection Effectiveness**:

   - Identify improving/degrading agents correctly
   - Validate extrapolation accuracy (6-month forward)
   - Confirm statistical significance thresholds

4. **Override Tracking Impact**:

   - Verify high override rate reduces credibility
   - Test root cause analysis triggers
   - Validate penalty calibration

5. **Debate Resolution Improvement**:
   - Compare auto-resolution accuracy with/without comprehensive credibility
   - Measure reduction in human arbitration required
   - Track provisional decision override rates

**Success Criteria**:

- Credibility scores correlate >0.70 with actual future accuracy
- Auto-resolution accuracy >85% (vs human decisions)
- Override penalty correctly identifies blind spots (>75% correlation)
- Regime-specific scoring improves accuracy prediction by >10%

---

## Related Documentation

- [Feedback Loops](../learning/02-feedback-loops.md) - Time-weighted scoring implementation
- [Memory System](../architecture/02-memory-system.md) - AgentCredibility schema
- [Coordination Agents](../architecture/05-agents-coordination.md) - Debate credibility logic
- [Collaboration Protocols](../architecture/07-collaboration-protocols.md) - Credibility weighting
- [DD-004: Agent Credibility Scoring](../../docs/design-flaws/resolved/04-credibility-scoring.md) - Original flaw specification (RESOLVED)
