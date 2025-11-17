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

Structure collaborative analysis, manage knowledge conflicts, and provide fallback resolution when human arbitration unavailable

### Responsibilities

- Organize discussion rounds
- Present opposing viewpoints
- Document consensus and dissent
- Force position defense with evidence
- Highlight uncertainties
- Ensure all perspectives considered
- **Apply credibility-weighted auto-resolution when appropriate**
- **Manage provisional resolutions and override tracking**
- **Route debates based on priority and expert workload**

### Debate Protocol

**Setup Phase**:

- Set debate topics and participants
- Establish evidence standards
- Load relevant historical context
- Set time limits and rules
- Assign priority classification (critical-path, valuation, supporting)
- Check expert queue status (max 3 concurrent per expert)

**Execution Phase**:

- Manage challenge-response cycles
- Track argument strength and credibility
- Enforce evidence requirements
- Maintain structured dialogue
- Apply tiered escalation (see Level 2 below)

**Resolution Phase**:

- Synthesize final positions
- Document areas of agreement/disagreement
- Escalate unresolved conflicts (with fallback mechanisms)
- Update knowledge base with outcomes
- Track provisional decisions for gate review

### Debate Mechanics

**Challenge Structure**:

- Challenger and challenged agents identified
- Disputed finding clearly stated
- Challenge basis with evidence
- Required response and evidence type
- Escalation timer (typically 1 hour)
- Priority classification

**Response Requirements**:

1. Acknowledge within 15 minutes
2. Provide evidence within 1 hour
3. Apply credibility-weighted auto-resolution if applicable (Level 2)
4. Escalate to human if unresolved (Level 3)
5. Apply fallback resolution if human unavailable (Level 4)
6. Document resolution

**Credibility Weighting**:

- Weight arguments by agent track record
- Consider historical accuracy in similar contexts
- Apply domain expertise relevance
- Factor in evidence quality
- Calculate credibility differential for auto-resolution

### Fallback Resolution Authority (Level 2 & Level 4)

The Debate Facilitator has authority to resolve debates automatically when human arbitration is unavailable or when credibility gap is sufficient.

#### Level 2: Credibility-Weighted Auto-Resolution

**Trigger Conditions**:

- Agents fail to reach consensus after 1 hour
- Both agents have sufficient historical data (minimum 5 data points)
- Credibility differential >0.25

**Process**:

1. Calculate agent credibility scores in relevant context:

   - Historical accuracy on similar patterns
   - Domain expertise relevance
   - Recent performance trajectory
   - Evidence quality in current debate

2. Compute credibility differential:

   ```text
   differential = abs(agent_A_credibility - agent_B_credibility)
   ```

3. If differential >0.25:

   - Auto-resolve to higher credibility agent's position
   - Mark as "facilitator-resolved" (binding, not provisional)
   - Document reasoning and credibility scores
   - Notify both agents of resolution

4. If differential <0.25:
   - Escalate to Level 3 (human arbitration)
   - Include credibility analysis in escalation package

**Requirements for Auto-Resolution**:

- Minimum 5 historical data points per agent in similar context
- Clear credibility differential (>0.25)
- No critical-path blocking status (those escalate to human)
- Both agents provided evidence in good faith

#### Level 4: Fallback Conservative Default

**Trigger Conditions**:

- Human arbitration (Level 3) timeout (6 hours)
- OR expert queue full (>3 concurrent debates)
- OR expert explicitly unavailable

**Process**:

1. **Identify Conservative Position**:

   - Compare positions on risk spectrum
   - Select most cautious interpretation:
     - Lowest price target
     - Highest risk assessment
     - Most conservative assumptions
     - Most skeptical view
   - Use decision tree if positions not directly comparable

2. **Apply Provisional Resolution**:

   - Mark debate as "provisional - conservative default"
   - Document rationale for conservative choice
   - Set override window: Until next gate
   - Add to gate review queue

3. **Enable Pipeline Continuation**:

   - Downstream agents receive provisional resolution
   - Analyses proceed with conservative assumption
   - Flag dependent calculations for potential revision

4. **Track for Review**:
   - Add to "provisional decisions" list
   - Display at next human gate with context
   - Enable override with downstream impact check
   - Learn from eventual human decision

### Workload-Aware Debate Routing

**Queue Management**:

- Monitor expert workload (current debates in progress)
- Enforce limits: Max 3 concurrent debates per expert
- Display load indicator in dashboard (e.g., "2/3 debates")

**Routing Logic by Priority**:

1. **Critical-Path Blocking** (highest priority):

   - If queue <3: Immediate routing to expert
   - If queue full (3/3): Force auto-resolution via credibility OR apply conservative default
   - Never defer critical-path debates

2. **Valuation Impact** (medium priority):

   - If queue <3: Add to queue in arrival order
   - If queue full: Apply credibility auto-resolution if possible, else defer to next gate

3. **Supporting Analysis** (lowest priority):
   - If queue <3: Add to queue
   - If queue full: Defer to next gate for review
   - OR auto-resolve via credibility if applicable

**Overflow Handling**:

- When expert queue full (3/3) and new debate arrives:
  1. Check if credibility-weighted auto-resolution applicable
  2. If yes, resolve automatically (doesn't enter queue)
  3. If no, check priority:
     - Critical-path: Apply conservative default (Level 4)
     - Valuation/Supporting: Defer to next gate

### Provisional Decision Tracking

**Tracking Mechanism**:

- Maintain list of all provisional resolutions
- For each provisional decision, track:
  - Debate ID and topic
  - Conservative position applied
  - Alternative positions considered
  - Rationale for conservative choice
  - Override window deadline (next gate)
  - Downstream dependencies

**Gate Review Integration**:

- At each subsequent gate, display:
  - Count: "X provisional decisions require review"
  - Summary of each provisional debate
  - Agent positions and credibility scores
  - Facilitator's conservative default rationale

**Human Actions at Review**:

1. **Confirm**: Accept conservative default → becomes final resolution
2. **Override**: Select different position → check downstream impact
3. **Request Re-debate**: Trigger new debate with additional context

**Override Impact Analysis**:

- If human overrides provisional decision:
  1. Identify analyses that used provisional assumption
  2. Flag for potential revision
  3. Re-run critical calculations if needed
  4. Update confidence scores
  5. Propagate changes through dependency chain

### Memory-Enhanced Facilitation

The Debate Facilitator leverages the memory system to:

- Pre-load relevant historical debates
- Surface precedents for similar disagreements
- Weight agent positions by track record
- Identify patterns in past resolutions
- Learn optimal debate structures
- **Retrieve credibility scores for auto-resolution**
- **Track fallback accuracy over time**
- **Learn which positions tend to be more accurate**

**Historical Context Integration**:

- Similar past debates and outcomes
- Pattern success rates supporting each position
- Agent credibility in specific contexts
- Cautionary examples from memory
- **Fallback resolution accuracy tracking**
- **Human override patterns for calibration**

---

## Related Documentation

- [System Overview](./01-system-overview.md) - Overall architecture
- [Memory System](./02-memory-system.md) - Historical context for coordination
- [Specialist Agents](./03-agents-specialist.md) - Agents being coordinated
- [Support Agents](./04-agents-support.md) - Infrastructure support
- [Collaboration Protocols](./07-collaboration-protocols.md) - Communication standards
