# Memory Architecture

## Hybrid Memory Model

The system implements a three-tier hybrid memory architecture combining centralized knowledge with distributed agent-specific memories:

```text
┌─────────────────────────────────────────────┐
│      Central Knowledge Graph (Neo4j)         │
│  Companies | Patterns | Decisions | Outcomes │
└─────────────────────────────────────────────┘
                    ▲ ▼ Sync
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
- **TTL**: Hours
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

Relationships:
  - Company -[HAS_ANALYSIS]-> Analysis
  - Analysis -[IDENTIFIED_PATTERN]-> Pattern
  - Analysis -[LED_TO]-> Decision
  - Decision -[HAS_OUTCOME]-> Outcome
  - Agent -[PERFORMED]-> Analysis
  - Agent -[MADE]-> Decision
  - Pattern -[SIMILAR_TO]-> Pattern
  - Company -[PEER_OF]-> Company
```

---

## Memory Synchronization Protocol

**Note**: Code samples referenced here have been omitted from architecture docs. See `/examples/` directory for implementation examples.

### Event-Driven Priority Sync Architecture

The Memory Sync Manager uses an event-driven approach with three priority tiers to ensure timely synchronization while minimizing overhead.

**Sync Priority Levels**:

| Priority | Trigger Events | Latency | Use Cases |
|----------|---------------|---------|-----------|
| **Critical** | Debates, challenges, human gates | <2 seconds | Ensures consistency during high-stakes interactions |
| **High** | Important findings, alerts, confirmations | <10 seconds | Fast propagation of significant discoveries |
| **Normal** | Routine updates, batch operations | 5 minutes | Background sync for non-urgent updates |

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

---

## Related Documentation

- [System Overview](./01-system-overview.md) - High-level architecture
- [Specialist Agents](./03-agents-specialist.md) - Agents using memory systems
- [Knowledge Base Agent](./04-agents-support.md#knowledge-base-agent) - Memory management agent
- [Collaboration Protocols](./07-collaboration-protocols.md) - Memory-enhanced communication
