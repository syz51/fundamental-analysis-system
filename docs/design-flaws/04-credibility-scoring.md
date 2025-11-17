# Flaw #4: Agent Credibility Scoring - No Temporal Decay

**Status**: UNRESOLVED ⚠️
**Priority**: Medium
**Impact**: Agent credibility scores don't adapt to changing market conditions

---

## 4. Agent Credibility Scoring - No Temporal Decay

### Problem Description

**Current State**: Agent accuracy tracked cumulatively with no adjustment for time, market regime changes, or recent performance trends.

From v2.0:

```python
def get_agent_track_record(self, agent_id, context):
    """Get agent's historical performance in similar contexts"""
    return self.graph_db.query("""
        MATCH (agent:Agent {id: $agent_id})-[:PERFORMED]->(a:Analysis)
        WHERE a.context SIMILAR TO $context
        RETURN
            COUNT(a) as total,
            AVG(a.accuracy) as avg_accuracy,
            COLLECT(a.lessons) as lessons
    """, agent_id=agent_id, context=context)
```

**Problem**: `AVG(a.accuracy)` treats 2020 performance same as 2025 performance.

### Specific Issues

**Market Regime Problem**:

```text
Financial Analyst Track Record:
  2019-2021 (Bull Market): 92% accuracy
    - Easy to predict: Growth continues, margins expand
    - 50 analyses, 46 accurate

  2022-2023 (Bear Market): 68% accuracy
    - Harder: Inflation, rate hikes, margin compression
    - 25 analyses, 17 accurate

  2024-2025 (Current): Unknown

Current Credibility Score: AVG(92%, 68%) = 80%

Problem: What if 2025 is high-rate environment like 2022?
  - Agent struggled in 2022 (68%)
  - Current 80% score overweights 2019-2021 performance
  - Should be closer to 68% for current regime
```

**Agent Improvement/Degradation Not Captured**:

```text
Strategy Analyst:
  2020: 65% accuracy (learning)
  2021: 72% accuracy (improving)
  2022: 81% accuracy (proficient)
  2023: 87% accuracy (expert)
  2024: 89% accuracy (mastery)

Current Score: AVG = 79%

Problem: Agent clearly improving but score doesn't reflect it
  - Latest performance is 89%
  - Should weight recent more heavily
  - 79% underestimates current capability
```

**Stale Performance Artifacts**:

```text
Valuation Agent:
  2018-2020: Used flawed DCF model (55% accuracy, 30 analyses)
  2021: Model upgraded
  2021-2025: Improved model (88% accuracy, 70 analyses)

Current Score: (30*0.55 + 70*0.88) / 100 = 77.1%

Problem: Old bad model drags down score forever
  - Current model is 88% accurate
  - 2018-2020 irrelevant to 2025 capability
  - Should phase out old performance
```

### Impact Assessment

| Issue                                  | Consequence                                       | Severity |
| -------------------------------------- | ------------------------------------------------- | -------- |
| Regime-dependent accuracy not captured | Over/under-weight agents in wrong conditions      | High     |
| Improvement trends ignored             | Improving agents undervalued                      | Medium   |
| Historical artifacts persist           | Past mistakes haunt forever                       | High     |
| Recency not valued                     | Recent track record should matter more            | High     |
| Human overrides unaccounted            | If humans frequently override agent, not captured | Medium   |

### Recommended Solution

#### Time-Weighted Credibility Score

```python
class TimeWeightedCredibility:
    def __init__(self):
        self.recency_weight = 0.5  # 50% weight on last 6 months
        self.regime_weight = 0.3   # 30% weight on current regime
        self.historical_weight = 0.2  # 20% weight on all history

    def calculate_agent_credibility(self, agent, context):
        """Multi-factor credibility with temporal decay"""

        # 1. Recent performance (last 6 months)
        recent_accuracy = self.get_recent_accuracy(
            agent,
            months=6
        )

        # 2. Current regime performance
        current_regime = self.identify_market_regime()
        regime_accuracy = self.get_regime_accuracy(
            agent,
            regime=current_regime
        )

        # 3. Historical baseline (with decay)
        historical_accuracy = self.get_decayed_historical_accuracy(
            agent,
            decay_halflife_years=2
        )

        # 4. Context-specific accuracy
        context_accuracy = self.get_context_accuracy(
            agent,
            context=context
        )

        # Weighted combination
        credibility = (
            recent_accuracy * self.recency_weight +
            regime_accuracy * self.regime_weight +
            historical_accuracy * self.historical_weight
        )

        # Context adjustment
        if context_accuracy.sample_size > 5:
            credibility = credibility * 0.7 + context_accuracy.score * 0.3

        return CredibilityScore(
            overall=credibility,
            recent=recent_accuracy,
            regime=regime_accuracy,
            historical=historical_accuracy,
            context=context_accuracy,
            sample_sizes={
                'recent': recent_accuracy.count,
                'regime': regime_accuracy.count,
                'historical': historical_accuracy.count,
                'context': context_accuracy.count
            }
        )

    def get_decayed_historical_accuracy(self, agent, decay_halflife_years):
        """Apply exponential decay to historical performance"""

        analyses = self.kb.get_all_agent_analyses(agent.id)

        total_weighted_accuracy = 0
        total_weight = 0

        for analysis in analyses:
            age_years = (now() - analysis.date).days / 365

            # Exponential decay: weight = 0.5^(age/halflife)
            weight = 0.5 ** (age_years / decay_halflife_years)

            total_weighted_accuracy += analysis.accuracy * weight
            total_weight += weight

        return total_weighted_accuracy / total_weight if total_weight > 0 else 0.5

    def identify_market_regime(self):
        """Classify current market environment"""

        # Simple regime classification
        rates = self.get_current_rates()
        volatility = self.get_market_volatility()
        trend = self.get_market_trend(months=6)

        if rates.high() and volatility.high():
            return MarketRegime.BEAR_HIGH_RATES
        elif rates.low() and trend.up():
            return MarketRegime.BULL_LOW_RATES
        elif volatility.high():
            return MarketRegime.HIGH_VOLATILITY
        else:
            return MarketRegime.NORMAL

    def get_regime_accuracy(self, agent, regime):
        """Get agent's historical accuracy in similar regimes"""

        similar_periods = self.kb.find_similar_regimes(regime)

        regime_analyses = []
        for period in similar_periods:
            analyses = self.kb.get_agent_analyses(
                agent.id,
                start_date=period.start,
                end_date=period.end
            )
            regime_analyses.extend(analyses)

        if len(regime_analyses) < 3:
            # Not enough data - use overall average
            return self.get_overall_accuracy(agent)

        return AccuracyScore(
            score=statistics.mean([a.accuracy for a in regime_analyses]),
            count=len(regime_analyses),
            confidence='high' if len(regime_analyses) > 10 else 'medium'
        )
```

#### Trend Detection

```python
class AgentTrendAnalysis:
    """Detect if agent improving or degrading"""

    def analyze_performance_trend(self, agent, window_months=12):
        """Calculate performance trajectory"""

        analyses = self.kb.get_agent_analyses(
            agent.id,
            since=months_ago(window_months)
        )

        # Sort chronologically
        analyses.sort(key=lambda a: a.date)

        # Calculate rolling accuracy
        window_size = max(5, len(analyses) // 4)
        rolling_accuracy = []

        for i in range(len(analyses) - window_size):
            window = analyses[i:i+window_size]
            rolling_accuracy.append({
                'date': window[-1].date,
                'accuracy': statistics.mean([a.accuracy for a in window])
            })

        # Linear regression to detect trend
        if len(rolling_accuracy) > 3:
            dates_numeric = [(r['date'] - rolling_accuracy[0]['date']).days
                           for r in rolling_accuracy]
            accuracies = [r['accuracy'] for r in rolling_accuracy]

            slope, intercept = self.linear_regression(dates_numeric, accuracies)

            # Annualized trend
            days_per_year = 365
            annual_trend = slope * days_per_year

            return TrendAnalysis(
                slope=annual_trend,
                direction='improving' if annual_trend > 0.02 else
                         'degrading' if annual_trend < -0.02 else 'stable',
                confidence=self.calculate_trend_confidence(rolling_accuracy),
                current_accuracy=accuracies[-1],
                extrapolated_6mo=accuracies[-1] + (slope * 180)  # 6 months
            )
        else:
            return TrendAnalysis(
                slope=0,
                direction='insufficient_data',
                confidence='low'
            )

    def adjust_credibility_for_trend(self, base_credibility, trend):
        """Boost/penalize based on trajectory"""

        if trend.direction == 'improving' and trend.confidence == 'high':
            # Give credit for improvement - use extrapolated score
            return base_credibility * 0.7 + trend.extrapolated_6mo * 0.3

        elif trend.direction == 'degrading' and trend.confidence == 'high':
            # Penalize degradation
            return base_credibility * 0.9

        else:
            return base_credibility
```

#### Human Override Tracking

```python
class HumanOverrideTracking:
    """Track when humans override agent recommendations"""

    def track_human_override(self, decision):
        """Record when human changes agent recommendation"""

        for agent_recommendation in decision.agent_recommendations:
            if decision.final_decision != agent_recommendation.decision:
                # Human overrode this agent
                override = HumanOverride(
                    agent_id=agent_recommendation.agent_id,
                    agent_recommendation=agent_recommendation.decision,
                    human_decision=decision.final_decision,
                    reason=decision.override_reason,
                    context=decision.context,
                    date=decision.date
                )

                self.kb.store_override(override)

    def calculate_override_rate(self, agent, context=None):
        """How often are this agent's recommendations changed?"""

        overrides = self.kb.get_agent_overrides(
            agent.id,
            context=context,
            since=months_ago(12)
        )

        total_decisions = self.kb.count_agent_decisions(
            agent.id,
            context=context,
            since=months_ago(12)
        )

        override_rate = len(overrides) / total_decisions if total_decisions > 0 else 0

        # Categorize reasons
        reason_breakdown = {}
        for override in overrides:
            reason = override.reason
            reason_breakdown[reason] = reason_breakdown.get(reason, 0) + 1

        return OverrideAnalysis(
            override_rate=override_rate,
            total_overrides=len(overrides),
            total_decisions=total_decisions,
            reason_breakdown=reason_breakdown,
            most_common_reason=max(reason_breakdown, key=reason_breakdown.get)
                              if reason_breakdown else None
        )

    def adjust_credibility_for_overrides(self, base_credibility, override_analysis):
        """Reduce credibility if frequently overridden"""

        # High override rate is a red flag
        if override_analysis.override_rate > 0.4:  # >40% overridden
            penalty = (override_analysis.override_rate - 0.4) * 0.5
            return base_credibility * (1 - penalty)
        else:
            return base_credibility
```

#### Complete Credibility System

```python
class ComprehensiveCredibilitySystem:
    """Combine all credibility factors"""

    def get_agent_credibility(self, agent, context, current_decision):
        """Calculate final credibility score"""

        # Base time-weighted score
        base_score = self.time_weighted_credibility.calculate_agent_credibility(
            agent,
            context
        )

        # Trend adjustment
        trend = self.trend_analysis.analyze_performance_trend(agent)
        trend_adjusted = self.trend_analysis.adjust_credibility_for_trend(
            base_score.overall,
            trend
        )

        # Override adjustment
        override_analysis = self.override_tracking.calculate_override_rate(
            agent,
            context
        )
        override_adjusted = self.override_tracking.adjust_credibility_for_overrides(
            trend_adjusted,
            override_analysis
        )

        # Confidence interval based on sample size
        confidence_interval = self.calculate_confidence_interval(
            override_adjusted,
            base_score.sample_sizes
        )

        return FinalCredibilityScore(
            score=override_adjusted,
            confidence_interval=confidence_interval,
            components={
                'recent': base_score.recent,
                'regime': base_score.regime,
                'historical': base_score.historical,
                'trend': trend.direction,
                'override_rate': override_analysis.override_rate
            },
            recommendation_weight=self.calculate_recommendation_weight(
                override_adjusted,
                confidence_interval
            )
        )

    def calculate_recommendation_weight(self, credibility, confidence_interval):
        """How much should we trust this agent's recommendation?"""

        # Reduce weight if high uncertainty
        uncertainty_penalty = (confidence_interval.upper - confidence_interval.lower) / 2

        # Weight between 0.1 (minimum trust) and 1.0 (full trust)
        weight = max(0.1, credibility - uncertainty_penalty)

        return weight
```

### Implementation Timeline

1. **Phase 1** (Month 1): Implement time-weighted scoring
2. **Phase 2** (Month 2): Add regime detection and regime-specific accuracy
3. **Phase 3** (Month 3): Implement trend detection
4. **Phase 4** (Month 4): Add human override tracking
5. **Phase 5** (Month 5): Full integration and backtesting

---
