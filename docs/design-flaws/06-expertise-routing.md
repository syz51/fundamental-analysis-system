# Flaw #6: Static Human Expertise Routing

**Status**: UNRESOLVED ⚠️
**Priority**: Low
**Impact**: Sub-optimal human expertise matching for complex decisions

---

## 6. Static Human Expertise Routing

### Problem Description

**Current State**: Four predefined human specialist roles with no dynamic assignment, credibility tracking, or learning from human expertise patterns.

From both v1.0 and v2.0:

```yaml
Expertise Routing:
  Technical Analyst:
    - Entry/exit timing
    - Chart patterns
    - Technical indicators

  Industry Specialist:
    - Business model assessment
    - Competitive dynamics
    - Industry trends

  Financial Expert:
    - Accounting review
    - Model validation
    - Ratio analysis

  Risk Manager:
    - Position sizing
    - Portfolio impact
    - Risk assessment
```

### Specific Issues

**No Dynamic Assignment**:

- System doesn't know which human expert to route decision to
- No matching of decision characteristics to expert strengths
- All decisions presumably go to same person or random assignment

**No Human Credibility Tracking**:

- Agents have credibility scores
- Humans don't
- System can't learn which humans are best at which decisions
- Can't weight human input by track record

**No Learning from Human Patterns**:

- Humans override AI recommendations
- Overrides are valuable signal about what AI misses
- System doesn't learn from pattern of overrides
- Human expertise not captured in memory

**Static Specialization**:

- Humans may develop new expertise over time
- Or lose expertise (role changes)
- System has no mechanism to update

### Real-World Scenario

```text
Decision Queue:

Decision 1: Tesla Valuation
  Characteristics:
    - Industry: Automotive + Tech
    - Complexity: High (multiple business lines)
    - Key Issues: Regulatory risk, technology moat
    - Uncertainty: High

  Current System: Route to... ? (undefined)

  Better System:
    - Human Expert Track Record:
      * Alex: EV industry specialist, 87% accuracy on tech valuations
      * Jordan: Traditional auto background, 62% accuracy on EV
      * Sam: General financial expert, 71% accuracy overall
    - Route to: Alex (best match)

Decision 2: Bank Balance Sheet Analysis
  Characteristics:
    - Industry: Financial Services
    - Complexity: Medium
    - Key Issues: Credit risk, interest rate sensitivity
    - Uncertainty: Medium

  Current System: Route to... ? (undefined)

  Better System:
    - Human Expert Track Record:
      * Alex: Tech background, 58% accuracy on financials
      * Jordan: No banking experience
      * Sam: Former bank analyst, 91% accuracy on banks
    - Route to: Sam (best match)
```

### Impact Assessment

| Issue                      | Consequence                           | Severity |
| -------------------------- | ------------------------------------- | -------- |
| Suboptimal expert matching | Wrong human reviews decision          | High     |
| Cannot learn from humans   | Human expertise not captured          | High     |
| No human accountability    | Can't identify which humans add value | Medium   |
| Static routing             | Doesn't adapt to expert development   | Medium   |
| Override patterns lost     | Valuable signals ignored              | High     |

### Recommended Solution

#### Human Expertise Profiling

```python
class HumanExpertiseProfile:
    """Track human expert capabilities and track record"""

    def __init__(self, expert_id, name):
        self.expert_id = expert_id
        self.name = name
        self.specializations = []
        self.decision_history = []
        self.accuracy_by_domain = {}
        self.override_patterns = []

    def add_decision(self, decision, outcome=None):
        """Record human decision for tracking"""

        self.decision_history.append({
            'decision_id': decision.id,
            'date': decision.date,
            'company': decision.company,
            'sector': decision.sector,
            'ai_recommendation': decision.ai_recommendation,
            'human_decision': decision.human_decision,
            'was_override': decision.ai_recommendation != decision.human_decision,
            'override_reason': decision.override_reason if decision.was_override else None,
            'outcome': outcome,
            'accuracy': self.calculate_accuracy(decision, outcome) if outcome else None
        })

    def calculate_domain_accuracy(self, domain, timeframe_months=12):
        """Calculate human's accuracy in specific domain"""

        recent_decisions = [
            d for d in self.decision_history
            if d['sector'] == domain
            and (now() - d['date']).days < timeframe_months * 30
            and d['outcome'] is not None
        ]

        if len(recent_decisions) < 3:
            return None  # Insufficient data

        accuracies = [d['accuracy'] for d in recent_decisions]

        return DomainAccuracy(
            domain=domain,
            accuracy=statistics.mean(accuracies),
            sample_size=len(recent_decisions),
            confidence='high' if len(recent_decisions) > 10 else 'medium'
        )

    def identify_expertise_areas(self):
        """Automatically identify human's strengths"""

        # Group decisions by domain
        by_domain = {}
        for decision in self.decision_history:
            domain = decision['sector']
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(decision)

        # Calculate accuracy per domain
        expertise_areas = []
        for domain, decisions in by_domain.items():
            accuracy = self.calculate_domain_accuracy(domain)

            if accuracy and accuracy.accuracy > 0.75 and accuracy.sample_size > 5:
                expertise_areas.append({
                    'domain': domain,
                    'accuracy': accuracy.accuracy,
                    'decisions_count': accuracy.sample_size,
                    'strength': 'high' if accuracy.accuracy > 0.85 else 'medium'
                })

        # Sort by accuracy
        expertise_areas.sort(key=lambda x: x['accuracy'], reverse=True)

        return expertise_areas

    def analyze_override_patterns(self):
        """Learn from when human overrides AI"""

        overrides = [d for d in self.decision_history if d['was_override']]

        # Group by override reason
        by_reason = {}
        for override in overrides:
            reason = override['override_reason']
            if reason not in by_reason:
                by_reason[reason] = []
            by_reason[reason].append(override)

        # Identify patterns
        patterns = []
        for reason, instances in by_reason.items():
            if len(instances) >= 3:
                # Calculate how often override was correct
                instances_with_outcome = [i for i in instances if i['outcome']]

                if len(instances_with_outcome) > 0:
                    correct_overrides = sum(
                        1 for i in instances_with_outcome
                        if i['accuracy'] > 0.7
                    )

                    override_accuracy = correct_overrides / len(instances_with_outcome)

                    patterns.append(OverridePattern(
                        reason=reason,
                        frequency=len(instances),
                        accuracy=override_accuracy,
                        example_decisions=[i['decision_id'] for i in instances[:3]]
                    ))

        return patterns
```

#### Dynamic Expert Routing

```python
class DynamicExpertRouter:
    """Match decisions to best-qualified human expert"""

    def __init__(self):
        self.experts = []  # List of HumanExpertiseProfile

    def route_decision(self, decision):
        """Select best expert for this decision"""

        # Extract decision characteristics
        characteristics = self.extract_characteristics(decision)

        # Score each expert
        expert_scores = []
        for expert in self.experts:
            score = self.score_expert_match(expert, characteristics)
            expert_scores.append((expert, score))

        # Sort by score
        expert_scores.sort(key=lambda x: x[1].overall_score, reverse=True)

        # Return best match with explanation
        best_expert, best_score = expert_scores[0]

        return ExpertAssignment(
            expert=best_expert,
            decision=decision,
            match_score=best_score.overall_score,
            rationale=best_score.rationale,
            alternatives=expert_scores[1:3]  # Show next 2 options
        )

    def score_expert_match(self, expert, characteristics):
        """Calculate how well expert matches decision needs"""

        scores = {}

        # 1. Domain expertise match
        domain_accuracy = expert.calculate_domain_accuracy(
            characteristics.sector
        )
        scores['domain'] = domain_accuracy.accuracy if domain_accuracy else 0.5

        # 2. Complexity match (has expert handled similar complexity?)
        complexity_match = self.match_complexity(
            expert,
            characteristics.complexity
        )
        scores['complexity'] = complexity_match

        # 3. Similar decision history
        similar_decisions = self.find_similar_decisions(
            expert,
            characteristics
        )
        scores['similarity'] = similar_decisions.avg_accuracy if similar_decisions else 0.5

        # 4. Availability (is expert overloaded?)
        workload = self.get_expert_workload(expert)
        scores['availability'] = 1.0 - min(workload / 10, 0.5)  # Penalty if >10 pending

        # 5. Recency (has expert worked on this sector recently?)
        recency = self.check_recent_experience(
            expert,
            characteristics.sector,
            months=3
        )
        scores['recency'] = 1.0 if recency else 0.7

        # Weighted combination
        weights = {
            'domain': 0.35,
            'complexity': 0.20,
            'similarity': 0.25,
            'availability': 0.10,
            'recency': 0.10
        }

        overall_score = sum(
            scores[factor] * weights[factor]
            for factor in weights
        )

        return ExpertMatchScore(
            overall_score=overall_score,
            component_scores=scores,
            rationale=self.generate_rationale(expert, scores, characteristics)
        )

    def generate_rationale(self, expert, scores, characteristics):
        """Explain why this expert was selected"""

        reasons = []

        if scores['domain'] > 0.8:
            reasons.append(f"Strong track record in {characteristics.sector} ({scores['domain']:.0%} accuracy)")

        if scores['similarity'] > 0.75:
            reasons.append(f"Successfully handled similar decisions before")

        if scores['complexity'] > 0.8:
            reasons.append(f"Experienced with {characteristics.complexity} complexity analyses")

        if scores['availability'] > 0.9:
            reasons.append(f"Currently available (low workload)")

        return " | ".join(reasons)
```

#### Learning from Human Decisions

```python
class HumanDecisionLearning:
    """Capture and learn from human decision patterns"""

    def capture_human_decision(self, decision, expert):
        """Record decision with rich context for learning"""

        # Record in expert profile
        expert.add_decision(decision)

        # If override, extract lessons
        if decision.ai_recommendation != decision.human_decision:
            self.extract_override_lessons(decision, expert)

    def extract_override_lessons(self, decision, expert):
        """Learn from why human disagreed with AI"""

        override_analysis = {
            'decision_id': decision.id,
            'expert_id': expert.expert_id,
            'ai_recommendation': decision.ai_recommendation,
            'human_decision': decision.human_decision,
            'override_reason': decision.override_reason,
            'context': decision.context,

            # What did AI miss?
            'ai_blind_spots': self.identify_ai_blind_spots(decision),

            # What did human see that AI didn't?
            'human_insights': decision.human_reasoning,

            # Which agent was overridden most?
            'overridden_agents': self.identify_overridden_agents(decision),
        }

        # Store for pattern analysis
        self.kb.store_human_override(override_analysis)

        # Check if this reveals systematic AI weakness
        if self.is_systematic_pattern(override_analysis):
            self.flag_for_ai_improvement(override_analysis)

    def identify_systematic_ai_weaknesses(self):
        """Find recurring patterns in human overrides"""

        all_overrides = self.kb.get_all_human_overrides()

        # Group by reason
        by_reason = {}
        for override in all_overrides:
            reason = override['override_reason']
            if reason not in by_reason:
                by_reason[reason] = []
            by_reason[reason].append(override)

        # Identify frequent patterns
        systematic_weaknesses = []
        for reason, instances in by_reason.items():
            if len(instances) >= 5:  # Occurred 5+ times
                weakness = SystematicWeakness(
                    reason=reason,
                    frequency=len(instances),
                    affected_sectors=list(set(i['context']['sector'] for i in instances)),
                    affected_agents=self.most_common_agents(instances),
                    recommendation=self.generate_improvement_recommendation(reason, instances)
                )
                systematic_weaknesses.append(weakness)

        return systematic_weaknesses

    def generate_improvement_recommendation(self, reason, instances):
        """Suggest how to fix systematic AI weakness"""

        # Analyze what agents consistently miss
        common_factors = self.identify_common_factors(instances)

        if 'qualitative_factors' in common_factors:
            return "Train agents to consider qualitative factors like management credibility, competitive dynamics"

        elif 'macro_context' in common_factors:
            return "Improve macro context integration - humans catching macro shifts agents miss"

        elif 'risk_assessment' in common_factors:
            return "Enhance risk modeling - humans identifying tail risks agents underweight"

        else:
            return f"Review agent logic for: {', '.join(common_factors)}"
```

#### Human Expertise Dashboard

```python
class HumanExpertiseDashboard:
    """Provide transparency into human expert performance"""

    def generate_expert_report(self, expert):
        """Create comprehensive expert performance report"""

        report = {
            'expert_name': expert.name,
            'total_decisions': len(expert.decision_history),
            'time_period': self.get_time_period(expert.decision_history),

            # Overall performance
            'overall_accuracy': self.calculate_overall_accuracy(expert),

            # Domain breakdown
            'expertise_areas': expert.identify_expertise_areas(),

            # Override analysis
            'override_stats': {
                'total_overrides': sum(1 for d in expert.decision_history if d['was_override']),
                'override_rate': sum(1 for d in expert.decision_history if d['was_override']) / len(expert.decision_history),
                'override_accuracy': self.calculate_override_accuracy(expert),
                'top_override_reasons': expert.analyze_override_patterns()
            },

            # Trends
            'performance_trend': self.analyze_trend(expert),

            # Comparison to AI
            'vs_ai_baseline': self.compare_to_ai(expert),

            # Value add
            'unique_contributions': self.identify_unique_value(expert)
        }

        return report

    def compare_to_ai(self, expert):
        """Show where human adds value beyond AI"""

        # Find decisions where human and AI agreed
        agreements = [d for d in expert.decision_history if not d['was_override']]

        # Find decisions where human overrode
        overrides = [d for d in expert.decision_history if d['was_override']]

        if len(overrides) == 0:
            return "Expert agrees with AI 100% of time"

        # Calculate outcome differential
        override_outcomes = [d for d in overrides if d['outcome']]

        if len(override_outcomes) > 0:
            human_was_right = sum(
                1 for d in override_outcomes
                if d['accuracy'] > 0.7
            ) / len(override_outcomes)

            return {
                'override_rate': len(overrides) / len(expert.decision_history),
                'override_success_rate': human_was_right,
                'value_add': 'High' if human_was_right > 0.6 else 'Medium' if human_was_right > 0.4 else 'Low'
            }
```

### Implementation Plan

1. **Phase 1** (Month 1):

   - Implement HumanExpertiseProfile
   - Start tracking human decisions
   - Build expertise database

2. **Phase 2** (Month 2):

   - Implement DynamicExpertRouter
   - Begin routing decisions to best-matched experts
   - Collect routing effectiveness data

3. **Phase 3** (Month 3):

   - Add override pattern analysis
   - Identify systematic AI weaknesses
   - Generate improvement recommendations

4. **Phase 4** (Month 4):
   - Build expertise dashboard
   - Provide transparency reports
   - Continuous refinement

---
