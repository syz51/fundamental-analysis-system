---
flaw_id: 19
title: Partial Failure Handling Undefined
status: active
priority: high
phase: 2
effort_weeks: 4
impact: Undefined behavior when subset of agents fail
blocks: ['Multi-agent reliability']
depends_on: ['Multi-agent workflows operational']
domain: ['agents', 'architecture']
sub_issues:
  - id: G1
    severity: high
    title: Agent failure quorum undefined
    status: pending
  - id: G2
    severity: high
    title: Message protocol implementation missing
    status: resolved
    resolution: Tech-agnostic message queue spec defined (see tech-requirements.md)
  - id: M6
    severity: medium
    title: Data contradiction resolution timeout missing
    status: pending
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

**Design Decision**: Reject quorum-based approach. For investment decisions, incomplete analysis is unacceptable.

### G1: Checkpoint-Based Hard Stop (Replaces Quorum System)

**Principle**: Any agent failure triggers human-alerted pause. All required agents must complete.

```python
class AgentFailureHandler:
    """Handle agent failures with checkpoint-based resumption"""

    def on_agent_failure(self, agent_failure_event):
        """Hard stop on any agent failure - no partial proceed"""

        # 1. Save checkpoint (Flaw #22)
        checkpoint = self.checkpointer.save_checkpoint(
            agent=agent_failure_event.agent,
            subtask_completed=agent_failure_event.last_completed_subtask,
            progress_pct=agent_failure_event.progress_pct,
            failure_reason=agent_failure_event.error
        )

        # 2. Pause analysis for this stock (Flaw #23)
        pause_record = self.pause_manager.pause_analysis(
            stock_ticker=agent_failure_event.stock_ticker,
            reason='agent_failure',
            failed_agent=agent_failure_event.agent_type
        )

        # 3. Alert human (Flaw #24)
        alert = self.alert_manager.send_agent_failure_alert(
            stock_ticker=agent_failure_event.stock_ticker,
            agent_type=agent_failure_event.agent_type,
            error=agent_failure_event.error,
            checkpoint_progress=checkpoint.progress_pct,
            phase=pause_record.phase,
            day=pause_record.day
        )

        logger.critical(
            f"Analysis PAUSED: {agent_failure_event.stock_ticker} - "
            f"{agent_failure_event.agent_type} failed at {checkpoint.progress_pct}%"
        )

        # 4. Wait for human resolution (NO auto-proceed, NO timeout)
        # Human must explicitly:
        #   - Resolve root cause (infrastructure/API/data issue)
        #   - Click "Resume Analysis" button
        #   - OR click "Cancel Analysis" button

        return {
            'action': 'hard_stop',
            'checkpoint_id': checkpoint.id,
            'pause_id': pause_record.id,
            'alert_id': alert.id,
            'awaiting_human': True
        }

    def on_human_resolution(self, stock_ticker, resolution_action):
        """Human resolved issue - resume from checkpoint"""

        if resolution_action == 'resume':
            # Resume from checkpoint (Flaw #22 + #23)
            resume_plan = self.pause_manager.resume_analysis(stock_ticker)

            logger.info(f"Analysis RESUMED: {stock_ticker} - {resume_plan.summary()}")

            return resume_plan

        elif resolution_action == 'cancel':
            # Human decided to cancel analysis
            self.analysis_manager.cancel_analysis(
                stock_ticker=stock_ticker,
                reason='human_cancelled_after_failure'
            )

            logger.info(f"Analysis CANCELLED: {stock_ticker} by human decision")

            return {'action': 'cancelled'}

    def handle_partial_completion(self, analysis, partial_results):
        """Reject partial completions - all agents must finish"""

        # NO 70% threshold - this is removed
        # Partial completion = failure, not success with penalty

        for result in partial_results:
            if result.status == 'partial':
                # Treat as failure - save checkpoint and pause
                self.on_agent_failure(
                    AgentFailureEvent(
                        agent=result.agent,
                        stock_ticker=analysis.stock_ticker,
                        error='Partial completion - insufficient for analysis',
                        progress_pct=result.completeness * 100,
                        last_completed_subtask=result.last_subtask
                    )
                )

        # Analysis does NOT proceed with partial results
        return {'action': 'paused', 'reason': 'partial_completion_rejected'}
```

**Key Changes from Original Proposal**:

- ❌ **REMOVED**: Quorum requirements (minimum 3 of 5 agents)
- ❌ **REMOVED**: Critical agent designation (all agents now critical)
- ❌ **REMOVED**: Confidence penalties for missing agents
- ❌ **REMOVED**: "Proceed with penalty" logic
- ❌ **REMOVED**: 70% partial completion threshold
- ✅ **ADDED**: Hard stop on ANY agent failure
- ✅ **ADDED**: Human alert with AGENT_FAILURE priority
- ✅ **ADDED**: Checkpoint-based resumption (no duplicate work)
- ✅ **ADDED**: No timeout - always wait for human

**Rationale**: For fundamental investment analysis, incomplete data can lead to incorrect decisions. Better to pause and complete properly than proceed with partial information and arbitrary confidence penalties.

### G2: Message Queue Specification

**Technology-Agnostic Requirements**:

```yaml
Message Queue Requirements:

  Reliability:
    - Delivery guarantee: At-least-once semantics
    - Persistent storage: Survive system restarts
    - Dead letter queue: Handle failed message deliveries
    - Durability: Messages persisted to disk

  Ordering:
    - Per-sender ordering: Messages from Agent A arrive in order
    - Priority levels: 4 tiers (critical, high, normal, low)
    - No global ordering required across all agents

  Performance:
    - Latency: <100ms (95th percentile)
    - Queue depth limit: 1000 messages per agent
    - Message TTL: 1 hour (prevent stale messages)
    - Throughput: Support 5-10 concurrent agents

  Retry Policy:
    - Max retries: 3 attempts
    - Backoff strategy: Exponential (1s, 2s, 4s)
    - Dead letter handling: After 3 failed retries

  Topology:
    - Topic-based routing: agent_communication topic
    - Per-agent queues: Isolated message streams
    - Broadcast capability: System-wide announcements
    - Unicast: Direct agent-to-agent messages

Technology Options: [RabbitMQ, Apache Kafka, Redis Streams]
Decision: TBD - Phase 2 implementation
Selection Criteria: Reliability, operational complexity, existing infrastructure
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

**Prerequisites**: Resolve Flaws #22, #23, #24 first (checkpoint/pause/alert infrastructure)

**Week 1**: G1 hard stop integration, checkpoint triggers on failure
**Week 2**: G1 human alert integration, resume from checkpoint testing
**Week 3**: G2 RabbitMQ setup & config
**Week 4**: M6 contradiction fallback

---

## Success Criteria

- ✅ G1: Zero incomplete analyses proceed (100% hard stop on any failure)
- ✅ G1: Human alerted <30s on agent failure (SMS/push/email)
- ✅ G1: Resume from checkpoint preserves completed work (no duplicate work in 100 tests)
- ✅ G2: Message delivery 99.9% success rate
- ✅ M6: Contradictions resolved <6hr (95th percentile)

---

## Dependencies

- **Blocks**: Production reliability, multi-agent workflows
- **Depends On**:
  - Flaw #22 (agent checkpoints) - REQUIRED for G1
  - Flaw #23 (workflow pause/resume) - REQUIRED for G1
  - Flaw #24 (agent failure alerts) - REQUIRED for G1
  - Agent framework operational
- **Related**: Flaw #8 (Debate Resolution - RESOLVED), Data management
