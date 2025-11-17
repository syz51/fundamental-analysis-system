# Flaw #13: Learning System Validation Gaps

**Status**: 🔴 ACTIVE
**Priority**: Critical
**Impact**: Auto-approval without validation, blind testing contamination
**Phase**: Phase 3 (Months 5-6)

---

## Problem Description

Gate 6 learning validation system (DD-004) has two critical gaps:

1. **C3**: Auto-approval 95% accuracy target but no validation mechanism before deployment
2. **H4**: Blind testing contamination risk through logs/cache/debugging

### Sub-Issue C3: Auto-Approval No Validation

**Files**: `docs/operations/02-human-integration.md:373-382`, `design-decisions/DD-004:119-149`

**Problem**: DD-004 specifies auto-approval at >95% accuracy in production, but no method to validate this before enabling.

**Current State**:
```yaml
Auto-Approval Rules (Production Phase):
  - Credibility Changes: Auto-approve if delta <0.05 AND sample_size ≥20
  - Lessons Learned: Auto-approve if confirmations ≥5 AND confidence ≥0.9
  - Patterns: NEVER auto-approved

Target: >95% accuracy
```

**Missing**:
- Validation methodology before enabling auto-approval
- Monitoring for accuracy degradation after enabled
- Rollback triggers if accuracy falls below 95%
- Sample size requirements for validation phase

**Risk**: Auto-approve incorrect learnings, degrading decision quality system-wide

### Sub-Issue H4: Blind Testing Contamination

**Files**: `docs/learning/01-learning-systems.md:246-278`, `design-decisions/DD-007`

**Problem**: Blind testing requires agents unaware of pattern, but shadow analysis could leak through logs/debugging/cache.

**Contamination Vectors**:
```text
1. Shared logging systems
   - Analysis A (with pattern) logs "Using pattern X"
   - Analysis B (without pattern) sees logs
   - Agent learns pattern exists indirectly

2. Agent L2 cache contamination
   - Agent performs Analysis A with pattern → cached
   - Same agent performs Analysis B without pattern
   - Cache may contain pattern-influenced results

3. Knowledge graph queries
   - Pattern stored in L3 graph during Analysis A
   - Analysis B queries similar cases
   - Graph traversal surfaces pattern indirectly

4. Debugging output visibility
   - Dev mode logs expose pattern details
   - Agents in blind test have access to debug logs
```

**Missing**:
- Pattern quarantine enforcement
- Log filtering during blind tests
- Cache isolation mechanisms
- Contamination detection

---

## Recommended Solution

### C3: Auto-Approval Validation Framework

```python
class AutoApprovalValidator:
    """Validate auto-approval accuracy before enabling"""

    SHADOW_MODE_DURATION_DAYS = 90
    MIN_DECISIONS_FOR_VALIDATION = 100

    def run_shadow_mode(self):
        """Run auto-approval in shadow mode (no actual auto-approval)"""

        shadow_decisions = []

        for gate_6_submission in self.monitor_gate_6():
            # Compute what auto-approval system WOULD decide
            auto_decision = self.compute_auto_approval_decision(
                gate_6_submission
            )

            # But still send to human
            human_decision = self.send_to_human(gate_6_submission)

            # Compare decisions
            shadow_decisions.append(ShadowDecision(
                submission=gate_6_submission,
                auto_decision=auto_decision,
                human_decision=human_decision,
                agreed=auto_decision == human_decision
            ))

        return shadow_decisions

    def validate_accuracy(self, shadow_decisions):
        """Check if accuracy meets 95% threshold"""

        if len(shadow_decisions) < self.MIN_DECISIONS_FOR_VALIDATION:
            return ValidationResult(
                ready=False,
                reason=f"Need {self.MIN_DECISIONS_FOR_VALIDATION} decisions"
            )

        accuracy = sum(d.agreed for d in shadow_decisions) / len(shadow_decisions)

        # Calculate confidence interval
        ci = self._wilson_confidence_interval(
            successes=sum(d.agreed for d in shadow_decisions),
            total=len(shadow_decisions)
        )

        return ValidationResult(
            ready=accuracy > 0.95 and ci.lower > 0.93,
            accuracy=accuracy,
            confidence_interval=ci,
            sample_size=len(shadow_decisions)
        )
```

### H4: Blind Testing Quarantine System

```python
class BlindTestingQuarantine:
    """Isolate pattern from agents during blind testing"""

    def start_blind_test(self, pattern_id):
        """Quarantine pattern for blind testing"""

        # 1. Mark pattern as quarantined
        self.set_pattern_status(pattern_id, 'quarantine_blind_test')

        # 2. Remove from agent L2 caches
        self.flush_pattern_from_caches(pattern_id)

        # 3. Set up log filtering
        self.enable_log_filter(pattern_id)

        # 4. Create isolated agent instances
        blind_test_agents = self.create_isolated_agents(
            exclude_patterns=[pattern_id]
        )

        return BlindTestSession(
            pattern_id=pattern_id,
            agents=blind_test_agents,
            log_filter_active=True,
            cache_isolated=True
        )

    def enable_log_filter(self, pattern_id):
        """Filter logs to prevent pattern leakage"""

        self.log_filters[pattern_id] = LogFilter(
            pattern_id=pattern_id,
            redact_keywords=[
                f"pattern_{pattern_id}",
                self.get_pattern_name(pattern_id),
                # Add pattern-specific keywords
            ],
            drop_events_mentioning=True
        )
```

---

## Implementation Plan

**Week 1-2**: C3 shadow mode framework
**Week 3**: C3 validation metrics & rollback
**Week 4-5**: H4 quarantine system
**Week 6**: Integration testing

---

## Success Criteria

- ✅ C3: Shadow mode runs 90 days with >100 decisions
- ✅ C3: Auto-approval accuracy validated >95% before enabling
- ✅ C3: Rollback triggered if accuracy drops <93%
- ✅ H4: Zero contamination detected in 20 blind tests
- ✅ H4: Cache isolation verified (no cross-test leakage)

---

## Dependencies

- **Blocks**: Gate 6 auto-approval (DD-004), Pattern validation (DD-007)
- **Depends On**: Gate 6 operational, blind testing framework
- **Related**: Flaw #3 (Pattern Validation - RESOLVED), DD-004, DD-007
