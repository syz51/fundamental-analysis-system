# Coordination Agents

## Overview

Coordination agents orchestrate the overall workflow and manage collaborative processes. They ensure smooth execution across all agents, facilitate structured debates, and manage the human interface for critical decision gates.

The two coordination agents are:

1. Lead Analyst Coordinator - Overall workflow orchestration
2. Debate Facilitator Agent - Collaborative analysis and conflict resolution

---

## 1. Lead Analyst Coordinator

### Purpose

Orchestrate overall workflow

### Responsibilities

- Manage task assignments across all agents
- Resolve conflicts between agents
- Make go/no-go decisions at checkpoints
- Ensure timeline adherence
- Escalate to humans when needed
- Prioritize work based on deadlines and dependencies

### Coordination Functions

**Workflow Orchestration**:

- Schedule and sequence agent tasks
- Manage dependencies between analysis phases
- Track progress against timelines
- Optimize parallel execution

**Resource Allocation**:

- Distribute work across agents
- Balance load and priorities
- Allocate computational resources
- Manage queue and backlog

**Bottleneck Management**:

- Identify workflow slowdowns
- Resolve resource constraints
- Escalate blocking issues
- Rebalance workloads

**Communication Facilitation**:

- Route messages between agents
- Coordinate multi-agent tasks
- Manage information flow
- Ensure critical findings propagate

**Human Gate Preparation**:

- Package information for human review
- Prepare decision materials
- Send notifications and reminders
- Track human response times

---

## 2. Debate Facilitator Agent

### Purpose

Structure collaborative analysis and manage knowledge conflicts

### Responsibilities

- Organize discussion rounds
- Present opposing viewpoints
- Document consensus and dissent
- Force position defense with evidence
- Highlight uncertainties
- Ensure all perspectives considered

### Debate Protocol

**Setup Phase**:

- Set debate topics and participants
- Establish evidence standards
- Load relevant historical context
- Set time limits and rules

**Execution Phase**:

- Manage challenge-response cycles
- Track argument strength and credibility
- Enforce evidence requirements
- Maintain structured dialogue

**Resolution Phase**:

- Synthesize final positions
- Document areas of agreement/disagreement
- Escalate unresolved conflicts
- Update knowledge base with outcomes

### Debate Mechanics

**Challenge Structure**:

- Challenger and challenged agents identified
- Disputed finding clearly stated
- Challenge basis with evidence
- Required response and evidence type
- Escalation timer (typically 1 hour)

**Response Requirements**:

1. Acknowledge within 15 minutes
2. Provide evidence within 1 hour
3. Escalate to human if unresolved
4. Document resolution

**Credibility Weighting**:

- Weight arguments by agent track record
- Consider historical accuracy in similar contexts
- Apply domain expertise relevance
- Factor in evidence quality

### Memory-Enhanced Facilitation

The Debate Facilitator leverages the memory system to:

- Pre-load relevant historical debates
- Surface precedents for similar disagreements
- Weight agent positions by track record
- Identify patterns in past resolutions
- Learn optimal debate structures

**Historical Context Integration**:

- Similar past debates and outcomes
- Pattern success rates supporting each position
- Agent credibility in specific contexts
- Cautionary examples from memory

---

## Related Documentation

- [System Overview](./01-system-overview.md) - Overall architecture
- [Memory System](./02-memory-system.md) - Historical context for coordination
- [Specialist Agents](./03-agents-specialist.md) - Agents being coordinated
- [Support Agents](./04-agents-support.md) - Infrastructure support
- [Collaboration Protocols](./07-collaboration-protocols.md) - Communication standards
