---
flaw_id: 19
title: Partial Failure Handling Undefined
status: active
priority: high
phase: 2
effort_weeks: 4
impact: Undefined behavior when subset of agents fail
blocks: ["Multi-agent reliability"]
depends_on: ["Multi-agent workflows operational"]
domain: ["agents", "architecture"]
sub_issues:
  - id: G1
    severity: high
    title: Agent failure quorum undefined
  - id: G2
    severity: high
    title: Message protocol implementation missing
  - id: M6
    severity: medium
    title: Data contradiction resolution timeout missing
discovered: 2025-11-17
---

# Flaw #19: Partial Failure Handling Undefined

**Status**: 🔴 ACTIVE
**Priority**: High
**Impact**: Undefined behavior when subset of agents fail
**Phase**: Phase 2 (Months 3-4)

---

## Problem Description

No specification for handling partial agent failures in multi-agent workflows:

1. **G1**: No quorum requirements when subset of agents complete
2. **G2**: Message queue retry/ordering undefined
3. **M6**: Data contradiction resolution timeout missing

### Sub-Issue G1: No Agent Failure Quorum

**Files**: All multi-agent workflows lack partial failure specs

**Problem**: If 4 of 5 specialist agents complete, should analysis proceed or retry?

**Undefined Scenario**:
```text
Parallel Analysis Phase (5 agents):
  ✅ Business Research: SUCCESS
  ✅ Financial Analyst: SUCCESS
  ❌ Strategy Analyst: TIMEOUT (API failure)
  ⚠️  Valuation: PARTIAL (DCF only, no comparables)
  ✅ News Monitor: SUCCESS

Questions:
  1. Proceed to Debate phase?
  2. Retry Strategy Agent?
  3. Adjust confidence scores? By how much?
  4. Notify human? At what failure threshold?
  5. Valuation "partial" counts as success or failure?
```

**Missing Specifications**:
- Minimum quorum (3 of 5? 4 of 5?)
- Partial completion handling
- Confidence adjustment formulas
- Retry logic and backoff
- Human notification triggers

### Sub-Issue G2: Message Protocol Implementation

**Files**: `docs/architecture/07-collaboration-protocols.md:13-28`

**Problem**: Message JSON structure defined but no implementation details.

**Current State**: Structure shown but missing:
- Message queue technology (RabbitMQ? Redis? Kafka?)
- Message ordering guarantees
- Retry policy for failed deliveries
- Message TTL and expiration
- Dead letter queue handling
- Broadcast vs unicast implementation

### Sub-Issue M6: Contradiction Resolution Timeout

**Files**: `docs/operations/03-data-management.md:257-278`

**Problem**: Contradiction resolution process has human arbitration but no timeout/fallback.

**Current Contradiction Flow**:
```yaml
1. Detect contradiction
2. Evaluate evidence quality
3. Check agent track records
4. Human arbitration if unresolved  # NO TIMEOUT SPECIFIED
5. Update memory with resolution
```

**Missing**: Fallback if human unavailable (similar to debate resolution)

---

## Recommended Solution

### G1: Agent Failure Quorum System

```python
class PartialFailureHandler:
    """Handle partial agent failures in parallel workflows"""

    QUORUM_REQUIREMENTS = {
        'parallel_analysis': {
            'minimum_agents': 3,  # of 5 total
            'critical_agents': ['financial', 'business'],  # Must succeed
            'confidence_penalty': 0.10  # per missing agent
        },
        'debate_phase': {
            'minimum_agents': 2,  # of 3 participants
            'critical_agents': [],
            'confidence_penalty': 0.20
        }
    }

    def check_quorum(self, workflow, completed_agents, failed_agents):
        """Determine if quorum met"""

        req = self.QUORUM_REQUIREMENTS[workflow]

        # Check minimum count
        if len(completed_agents) < req['minimum_agents']:
            return QuorumResult(
                met=False,
                reason='insufficient_agents',
                action='retry_failed'
            )

        # Check critical agents
        critical_failed = [
            a for a in failed_agents
            if a.agent_type in req['critical_agents']
        ]

        if critical_failed:
            return QuorumResult(
                met=False,
                reason=f'critical_agent_failed: {critical_failed[0].agent_type}',
                action='retry_critical'
            )

        # Quorum met, adjust confidence
        confidence_penalty = len(failed_agents) * req['confidence_penalty']

        return QuorumResult(
            met=True,
            confidence_adjustment=-confidence_penalty,
            action='proceed_with_penalty',
            missing_agents=failed_agents
        )

    def handle_partial_completion(self, analysis, partial_results):
        """Handle agents that partially completed"""

        for result in partial_results:
            if result.status == 'partial':
                # Determine if partial sufficient
                completeness = self._assess_completeness(result)

                if completeness > 0.70:
                    # Treat as success with confidence penalty
                    result.status = 'success'
                    result.confidence *= 0.90
                else:
                    # Treat as failure, retry
                    result.status = 'failed'
                    self.retry_agent(result.agent_id, analysis)
```

### G2: Message Queue Specification

```python
# Recommended: RabbitMQ for reliability + ordering

class MessageQueueConfig:
    """Message queue implementation details"""

    QUEUE_TYPE = 'rabbitmq'

    EXCHANGES = {
        'agent_communication': {
            'type': 'topic',
            'durable': True
        }
    }

    QUEUES = {
        'agent_{agent_id}': {
            'durable': True,
            'max_length': 1000,
            'message_ttl': 3600000,  # 1 hour
            'dead_letter_exchange': 'dlx_agent_messages'
        }
    }

    RETRY_POLICY = {
        'max_retries': 3,
        'backoff': 'exponential',  # 1s, 2s, 4s
        'dead_letter_after': 3
    }

    ORDERING = {
        'guarantee': 'per_sender',  # Messages from Agent A arrive in order
        'priority_levels': ['critical', 'high', 'normal', 'low']
    }
```

### M6: Contradiction Resolution Fallback

```python
class ContradictionResolver:
    """Resolve data contradictions with timeout"""

    RESOLUTION_TIMEOUT_HOURS = 6

    def resolve_contradiction(self, contradiction):
        """Resolve with fallback"""

        # Try evidence-based resolution
        if evidence_resolves := self.evaluate_evidence(contradiction):
            return evidence_resolves

        # Try track-record-based resolution
        if track_record_resolves := self.check_agent_credibility(contradiction):
            return track_record_resolves

        # Escalate to human with timeout
        try:
            human_resolution = self.escalate_to_human(
                contradiction,
                timeout_hours=self.RESOLUTION_TIMEOUT_HOURS
            )
            return human_resolution

        except TimeoutError:
            # Fallback: Mark both as uncertain, use neither
            return ResolutionResult(
                resolution='provisional_uncertainty',
                action='mark_both_uncertain',
                confidence=0.50,
                requires_human_review=True
            )
```

---

## Implementation Plan

**Week 1**: G1 quorum system
**Week 2**: G1 retry logic & notifications
**Week 3**: G2 RabbitMQ setup & config
**Week 4**: M6 contradiction fallback

---

## Success Criteria

- ✅ G1: Zero blocked analyses from partial failures (100 tests)
- ✅ G1: Confidence penalties validated (±10% of expected)
- ✅ G2: Message delivery 99.9% success rate
- ✅ M6: Contradictions resolved <6hr (95th percentile)

---

## Dependencies

- **Blocks**: Production reliability, multi-agent workflows
- **Depends On**: Agent framework operational
- **Related**: Flaw #8 (Debate Resolution - RESOLVED), Data management
