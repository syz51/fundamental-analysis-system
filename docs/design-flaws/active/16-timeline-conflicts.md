---
flaw_id: 16
title: Timeline & Dependency Conflicts
status: active
priority: high
phase: 2
effort_weeks: 2
impact: Phase 2 blocked by Phase 4 dependency
blocks: ["Phase 2 implementation"]
depends_on: []
domain: ["architecture"]
sub_issues:
  - id: H1
    severity: high
    title: Credibility dependency circular
  - id: M8
    severity: medium
    title: Benchmarking sprints missing
discovered: 2025-11-17
---

# Flaw #16: Timeline & Dependency Conflicts

**Status**: 🔴 ACTIVE
**Priority**: High
**Impact**: Phase 2 blocked by Phase 4 dependency, underestimated timelines
**Phase**: Immediate (affects Phases 2-4)

---

## Problem Description

Roadmap has timeline conflicts and missing allocations:

1. **H1**: Phase 2 (Months 3-4) requires credibility system not built until Phase 4 (Months 7-8)
2. **M8**: Benchmarking phases missing from timeline despite DD-005 requirements

### Sub-Issue H1: Phase 2-4 Credibility Dependency

**Files**: `docs/implementation/01-roadmap.md:112-157`, `docs/design-flaws/PRIORITY.md:31-51`

**Problem**: Debate Resolution (Phase 2) needs comprehensive credibility scoring (Phase 4).

**Timeline Conflict**:
```yaml
# Phase 2 (Months 3-4)
- Implement memory-enhanced debate facilitator
  - Credibility-weighted auto-resolution (>0.25 threshold)
  # REQUIRES: Agent credibility scoring

# Phase 4 (Months 7-8)
- Flaw #4: Agent Credibility System (DD-008)
  - Exponential decay, regime-specific scores
  # IMPLEMENTED: Month 7-8

CONFLICT: Can't implement credibility-weighted resolution in Month 3
         without credibility system (Month 7)
```

**Solution**: Two-phase credibility implementation
- **Phase 2 (Simplified)**: Overall accuracy only, no regime/context specificity
- **Phase 4 (Comprehensive)**: Full DD-008 with decay, regime detection, multi-dimensional context

### Sub-Issue M8: Missing Benchmark Allocations

**Files**: `docs/implementation/01-roadmap.md:229-330`, `design-decisions/DD-005`

**Problem**: DD-005 requires benchmarking at each phase, but roadmap doesn't allocate time.

**Current State**:
```yaml
Phase 1: Foundation (Months 1-2) - NO BENCHMARK MILESTONE
Phase 2: Core (Months 3-4) - NO BENCHMARK MILESTONE
Phase 3: Advanced (Months 5-6) - "Benchmark baseline" mentioned L270 but no duration
Phase 4: Optimization (Months 7-8) - "Re-benchmark at production scale" L352
```

**Benchmarking Typically Requires**:
- 1 week data collection (run 50+ analyses)
- 1 week analysis & tuning
- Total: 2 weeks per phase

**Impact**: 8 weeks underestimation (2 weeks × 4 phases)

---

## Recommended Solution

### H1: Phased Credibility Implementation

**Phase 2 Simplified Credibility** (Week 3-4):
```python
class SimplifiedCredibility:
    """Lightweight credibility for Phase 2"""

    def get_credibility(self, agent_id):
        """Overall accuracy only"""

        outcomes = self.get_agent_outcomes(agent_id)

        correct = sum(1 for o in outcomes if o.correct)
        total = len(outcomes)

        if total < 5:
            return 0.50  # Default for new agents

        return CredibilityScore(
            overall=correct / total,
            sample_size=total,
            confidence_interval=self._wilson_ci(correct, total),
            version='simplified_v2_0'
        )
```

**Phase 4 Comprehensive Credibility** (Week 7-8):
```python
class ComprehensiveCredibility(SimplifiedCredibility):
    """Full DD-008 implementation"""

    def get_credibility(self, agent_id, context):
        """Regime-specific, contextual credibility"""

        # Inherit simplified for backward compatibility
        base = super().get_credibility(agent_id)

        # Add regime-specific scoring
        regime_score = self.get_regime_credibility(
            agent_id,
            context.market_regime
        )

        # Add multi-dimensional context matching
        context_score = self.get_contextual_credibility(
            agent_id,
            context
        )

        # Add temporal decay
        decayed_score = self.apply_temporal_decay(
            regime_score,
            half_life_years=2
        )

        return CredibilityScore(
            overall=base.overall,
            regime_specific=decayed_score,
            contextual=context_score,
            version='comprehensive_dd008'
        )
```

### M8: Add Benchmark Sprints

**Updated Roadmap**:
```yaml
Phase 1: Months 1-2
  - Week 1-7: Foundation implementation
  - Week 8: Benchmark Sprint 1 (data infra, screening)

Phase 2: Months 3-4
  - Week 9-15: Core agents implementation
  - Week 16: Benchmark Sprint 2 (debate resolution, memory sync)

Phase 3: Months 5-6
  - Week 17-23: Advanced features
  - Week 24: Benchmark Sprint 3 (pattern validation, scalability)

Phase 4: Months 7-8
  - Week 25-31: Optimization
  - Week 32: Benchmark Sprint 4 (production scale, 200+ stocks)
```

---

## Implementation Plan

**Immediate**: Restructure roadmap with phased credibility
**Week 1**: Implement simplified credibility for Phase 2
**Months 7-8**: Upgrade to comprehensive credibility (DD-008)
**All Phases**: Add 1-week benchmark sprints

---

## Success Criteria

- ✅ H1: Phase 2 debate resolution works with simplified credibility
- ✅ H1: Phase 4 upgrade maintains backward compatibility
- ✅ M8: Each phase ends with benchmark report
- ✅ M8: Benchmarks validate performance targets (DD-005)

---

## Dependencies

- **Blocks**: Phase 2 implementation (immediate blocker)
- **Depends On**: Debate resolution design (Flaw #8 - RESOLVED)
- **Related**: DD-008 (Credibility), DD-005 (Scalability), Roadmap
