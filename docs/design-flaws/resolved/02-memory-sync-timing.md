---
flaw_id: 2
title: Memory Sync Timing Incompatible with Debate Protocol
status: resolved
priority: critical
phase: 1
effort_weeks: 2
impact: Required for reliable inter-agent communication
blocks: ['#7', '#8']
depends_on: []
domain: ['memory']
resolved: 2025-11-17
resolution: DD-002 Event-Driven Memory Synchronization
---

# Flaw #2: Memory Sync Timing Incompatible with Debate Protocol

**Status**: RESOLVED ✅
**Priority**: Critical
**Resolution**: Event-driven memory sync architecture implemented
**Reference**: [DD-002: Event-Driven Memory Synchronization](../../design-decisions/DD-002_EVENT_DRIVEN_MEMORY_SYNC.md)

---

## Problem Description

**Current State**: Memory synchronization operates on fixed 5-minute intervals, but debate protocol requires sub-hour responses with potentially stale data.

From v2.0:

```python
class MemorySyncManager:
    def __init__(self):
        self.sync_interval = 300  # 5 minutes
```

From debate protocol:

```json
{
  "escalation_timer": 3600, // 1 hour
  "response_requirements": {
    "acknowledge": "15 minutes",
    "evidence": "1 hour"
  }
}
```

## Specific Issues

**Race Condition Scenario**:

```text
T=0:00  Agent A (Financial) finds "capex spike anomaly" → stores in local cache
T=0:05  Regular sync would happen, but A is busy analyzing
T=0:08  Agent B (Strategy) challenges A on related "ROI projection"
T=0:09  Agent A queries central KB for supporting evidence
T=0:09  Central KB doesn't have A's capex finding (not synced yet)
T=0:10  Agent A responds without full context
T=0:12  Regular sync happens - A's finding now in central KB (too late)
T=0:15  Debate proceeds with incomplete information
```

**Result**: Debate quality degraded due to memory synchronization lag.

## Impact Assessment

| Issue                        | Frequency | Impact   | Consequence                                           |
| ---------------------------- | --------- | -------- | ----------------------------------------------------- |
| Stale evidence in debates    | High      | Medium   | Sub-optimal debate resolutions                        |
| Contradictory positions      | Medium    | High     | Agents contradict themselves due to cache incoherence |
| Missing critical findings    | Low       | Critical | Important discoveries not available when needed       |
| Human sees inconsistent data | Medium    | High     | Trust in system degraded                              |

## Recommended Solution

### Event-Driven Priority Sync

```python
class EnhancedMemorySyncManager:
    def __init__(self):
        self.regular_sync_interval = 300  # 5 minutes (low priority)
        self.priority_sync_timeout = 10  # 10 seconds (high priority)
        self.critical_sync_timeout = 2  # 2 seconds (critical)

    async def sync_agent_memory(self, agent, priority='normal'):
        """Enhanced sync with priority levels"""
        if priority == 'critical':
            # Immediate sync for challenges, human gates
            await self.force_immediate_sync(agent)
        elif priority == 'high':
            # Fast sync for important findings
            await self.priority_sync(agent, timeout=self.priority_sync_timeout)
        else:
            # Regular interval-based sync
            await self.scheduled_sync(agent)

    async def force_immediate_sync(self, agent):
        """Critical sync - blocks until complete"""
        # Push all local insights to central immediately
        local_insights = agent.get_all_local_insights()
        await self.central_kb.bulk_add(local_insights, priority='critical')

        # Pull all relevant updates immediately
        updates = await self.central_kb.get_all_updates_for_agent(
            agent.specialization,
            priority='critical'
        )
        agent.update_local_cache(updates, force=True)

        # Notify agent sync complete
        agent.memory_state = 'synchronized'

    async def handle_debate_initiated(self, challenge):
        """Triggered when debate/challenge starts"""
        # Force sync for both challenger and challenged
        await self.force_immediate_sync(challenge.challenger)
        await self.force_immediate_sync(challenge.challenged)

        # Sync all agents in same analysis stream
        related_agents = self.get_related_agents(challenge.context)
        for agent in related_agents:
            await self.priority_sync(agent)

    async def handle_human_gate_approaching(self, gate):
        """Triggered 30 minutes before human gate"""
        # Ensure all agents synced before human reviews
        all_agents = self.get_all_active_agents(gate.analysis_id)
        sync_tasks = [
            self.force_immediate_sync(agent)
            for agent in all_agents
        ]
        await asyncio.gather(*sync_tasks)

        # Verify consistency
        self.verify_memory_consistency(gate.analysis_id)
```

### Message-Triggered Sync

```python
class MessageBasedSync:
    PRIORITY_TRIGGERS = {
        'challenge': 'critical',
        'finding_with_precedent': 'high',
        'alert': 'critical',
        'human_request': 'critical',
        'confirmation': 'high',
        'request': 'normal'
    }

    async def handle_message(self, message):
        """Trigger appropriate sync based on message type"""
        priority = self.PRIORITY_TRIGGERS.get(
            message.message_type,
            'normal'
        )

        if priority in ['critical', 'high']:
            # Sync sender and recipient before processing
            await self.sync_manager.sync_agent_memory(
                message.from_agent,
                priority=priority
            )
            await self.sync_manager.sync_agent_memory(
                message.to_agent,
                priority=priority
            )

        # Process message with synchronized state
        await self.process_message(message)
```

### Debate-Specific Sync Protocol

```python
class DebateSyncProtocol:
    async def initialize_debate(self, debate_topic, participants):
        """Ensure all participants have consistent view"""

        # 1. Force sync all participants
        sync_tasks = [
            self.sync_manager.force_immediate_sync(agent)
            for agent in participants
        ]
        await asyncio.gather(*sync_tasks)

        # 2. Create debate snapshot
        debate_memory_snapshot = await self.create_memory_snapshot(
            participants=participants,
            topic=debate_topic
        )

        # 3. Lock memory state for debate duration
        self.lock_memory_state(debate_memory_snapshot)

        # 4. All agents work from same snapshot
        for agent in participants:
            agent.set_debate_context(debate_memory_snapshot)

        return debate_memory_snapshot

    async def create_memory_snapshot(self, participants, topic):
        """Create point-in-time view of relevant memories"""
        return MemorySnapshot(
            timestamp=now(),
            participants=participants,
            relevant_patterns=self.kb.get_patterns_for_topic(topic),
            relevant_histories=self.kb.get_histories_for_topic(topic),
            agent_states={
                agent.id: agent.get_memory_state()
                for agent in participants
            }
        )
```

## Performance Impact

| Sync Type            | Frequency | Latency  | Overhead |
| -------------------- | --------- | -------- | -------- |
| Regular (5min)       | Low       | N/A      | Minimal  |
| Priority (10s)       | Medium    | 10-50ms  | Low      |
| Critical (immediate) | Low       | 50-200ms | Medium   |

**Mitigation**: Critical syncs are rare (debates, human gates) - acceptable overhead.

---

**Related Documentation**:

- [DD-002: Event-Driven Memory Synchronization](../../design-decisions/DD-002_EVENT_DRIVEN_MEMORY_SYNC.md)
- [Memory System](../architecture/02-memory-system.md)
- [Collaboration Protocols](../architecture/07-collaboration-protocols.md)
