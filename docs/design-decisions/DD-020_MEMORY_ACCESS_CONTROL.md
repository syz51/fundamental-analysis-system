# DD-020: Memory System Access Control

**Status**: Approved
**Date**: 2025-11-18
**Decider(s)**: System Architect
**Related Docs**:

- [Memory System](../architecture/02-memory-system.md)
- [Data Management](../operations/03-data-management.md)
- [Agents - Support](../architecture/04-agents-support.md)

**Related Decisions**: DD-018 (Memory Failure Resilience), DD-019 (Data Tier Operations)

---

## Context

### Problem Statement

**Missing Access Control for Memory System**: While `data-management.md:516-541` defines role-based access control (RBAC) for data files (raw/processed), the memory system (L2 agent caches, L3 central knowledge graph) lacks access control specifications. This creates:

- **Data Integrity Risk**: Agents could corrupt central knowledge graph via unrestricted writes
- **Agent Isolation Missing**: No rules preventing agents from modifying each other's L2 caches
- **Pattern Lifecycle Undefined**: Unclear who can create/validate/deprecate/delete patterns
- **Credibility Score Vulnerability**: Learning Engine credibility updates uncontrolled
- **No Accountability**: Lack of audit trail prevents root cause analysis after incidents

### Concrete Examples

**Example 1: Rogue Agent Cache Corruption**

```text
Scenario: Financial Analyst agent has bug causing invalid ratio writes
Current State: Bug writes corrupt data to own L2 cache AND other agents' caches
Result: Business Research Agent retrieves corrupt ROE value, propagates error
Impact: QC Agent detects contradiction, triggers debate, delays pipeline
Expected: Agent isolation prevents cross-cache writes
```

**Example 2: Unauthorized Pattern Modification**

```text
Scenario: Strategy Analyst disputes pattern "High ROIC indicates durable moat"
Current State: Agent could directly modify pattern confidence_score in Neo4j
Result: Pattern degraded without validation, affects all future analyses
Impact: Pattern integrity compromised, learning system corrupted
Expected: Only Knowledge Base Agent + Learning Engine can modify patterns
```

**Example 3: Credibility Score Manipulation**

```text
Scenario: Agent attempts to boost own credibility after repeated failures
Current State: No enforcement preventing agent from writing to credibility_scores table
Result: Failed agent maintains high credibility, incorrect debate auto-resolution
Impact: Low-quality findings accepted, bad investment recommendations
Expected: Only Learning Engine authorized to update credibility scores
```

**Example 4: Pattern Pollution**

```text
Scenario: Business Research Agent proposes pattern during normal analysis
Current State: Unclear if agent can create Pattern nodes directly vs proposal queue
Result: Unvalidated pattern enters system (status=PROPOSED, no human review)
Impact: Future analyses reference unvalidated pattern, quality degradation
Expected: Agents propose patterns → Knowledge Base Agent validates → Human approves
```

### Why Address Now

- **Phase 3 Requirement**: Production deployment blocked without security controls
- **Data Integrity Critical**: Central knowledge graph is single source of truth
- **Regulatory Compliance**: Audit trail required for investment decision forensics
- **Before Scale**: Must solve before 200+ stocks when manual monitoring impossible
- **Blocks DD-007**: Pattern validation requires trustworthy pattern lifecycle controls
- **Blocks DD-008**: Agent credibility system vulnerable without write protection

---

## Decision

**Implement role-based access control (RBAC) for memory system with 5 roles, permission matrix for L1/L2/L3 access, and comprehensive audit logging for all memory writes.**

Primary approach uses permission-based API gateway layer enforcing read/write/delete rules per role and resource, supplemented by PostgreSQL audit log capturing all memory modifications with actor tracking, old/new values, and action reasoning.

---

## Options Considered

### Option 1: No Access Control (Status Quo)

**Description**: Trust all agents, no enforcement layer

**Pros**:

- Zero implementation cost
- No performance overhead
- Simple architecture

**Cons**:

- Data integrity risk (agent bugs cause corruption)
- No security against malicious agents
- No audit trail (can't debug incidents)
- Production non-compliant
- Pattern lifecycle uncontrolled

**Estimated Effort**: 0 weeks (no implementation)

---

### Option 2: API-Only Access (No Direct Neo4j)

**Description**: Agents access memory only via API, no direct database connections

**Pros**:

- Simpler than full RBAC (no permission matrix)
- Prevents direct database manipulation
- Easier to implement

**Cons**:

- No granular control (agent can still corrupt via API)
- Doesn't solve L2 cache isolation
- No audit logging
- Doesn't define pattern lifecycle permissions
- Incomplete solution

**Estimated Effort**: 1 week (API gateway only)

---

### Option 3: Coarse-Grained RBAC (2 Roles)

**Description**: Two roles only: "agent" (read-only L3) and "admin" (full access)

**Pros**:

- Simple permission matrix (2 roles vs 5)
- Prevents agent L3 writes
- Low implementation complexity

**Cons**:

- Doesn't distinguish Knowledge Base Agent from regular agents
- Learning Engine has no write path for credibility scores
- Debate Facilitator can't read cross-agent caches
- Over-privileged "admin" role (agents need some writes)
- Insufficient granularity

**Estimated Effort**: 2 weeks (permission checks + audit log)

---

### Option 4: Fine-Grained RBAC (5 Roles) - **CHOSEN**

**Description**: 5 roles with granular permissions: agent, knowledge_base_agent, debate_facilitator, learning_engine, human_admin

**Pros**:

- Precise permissions per role (principle of least privilege)
- Agent isolation (read_write_own for L1/L2, read_all for L3)
- Pattern lifecycle clear (Knowledge Base Agent validates, humans approve)
- Credibility protection (only Learning Engine writes)
- Debate Facilitator gets cross-cache read for mediation
- Comprehensive audit logging
- Production-ready security

**Cons**:

- More complex permission matrix (5 roles × 6 resources)
- Requires API authorization layer (5ms overhead per query)
- More testing surface area

**Estimated Effort**: 4 weeks (permission matrix + API layer + audit log + testing)

---

## Rationale

### Why Fine-Grained RBAC (5 Roles)

1. **Principle of Least Privilege**: Each role has exactly the permissions needed, no more
2. **Agent Isolation**: `read_write_own` for L1/L2 prevents cross-agent cache corruption
3. **Pattern Lifecycle Control**: Clear path: agent proposes → KB Agent validates → human approves
4. **Credibility Protection**: Only Learning Engine writes credibility_scores (prevents self-manipulation)
5. **Debate Mediation**: Facilitator `read_all` L2 caches enables cross-agent evidence review
6. **Industry Standard**: RBAC proven in databases (PostgreSQL roles), APIs (OAuth scopes), cloud (AWS IAM)

### Why API Authorization Layer

1. **Enforcement Point**: Single location to check permissions (vs scattered checks)
2. **Audit Integration**: Every API call logged with actor, resource, action
3. **Performance**: 5ms overhead acceptable (<10ms analysis latency budget)
4. **Future-Proof**: Supports additional roles (e.g., watchlist_manager) without refactoring
5. **Testable**: Permission checks isolated, 100% test coverage achievable

### Why PostgreSQL Audit Log

1. **Already in Stack**: System uses PostgreSQL for metadata, no new infrastructure
2. **Append-Only**: Immutable audit trail for forensics, regulatory compliance
3. **Structured Queries**: Fast incident investigation (filter by actor, resource, timerange)
4. **Retention**: 5-year retention aligns with investment decision audit requirements
5. **Industry Proven**: Database audit logs standard in financial systems

### Why 6 Resource Types

1. **L1 Working Memory**: Agent-specific, ephemeral, needs `read_write_own`
2. **L2 Agent Cache**: Agent-specific, persistent, needs isolation + Facilitator cross-read
3. **L3 Central Graph**: Shared, critical, needs fine-grained write control
4. **Pattern Nodes**: Lifecycle (propose/validate/approve/deprecate/delete), needs governance
5. **Credibility Scores**: High-integrity, only Learning Engine writes
6. **Audit Log**: Read-only for most, admin-only delete (retention compliance)

---

## Consequences

### Positive Impacts

- **Data Integrity**: Agent bugs can't corrupt central knowledge graph (read-only L3 for agents)
- **Agent Isolation**: Agents can't pollute each other's L2 caches (read_write_own enforcement)
- **Pattern Governance**: Clear lifecycle prevents unvalidated patterns (proposal queue)
- **Credibility Protection**: Self-manipulation impossible (Learning Engine-only writes)
- **Accountability**: Full audit trail enables root cause analysis (all writes logged)
- **Production Ready**: RBAC unblocks Phase 4 deployment (security compliance met)
- **Regulatory Compliance**: 5-year audit retention meets investment advisor requirements
- **Scalability**: Permission checks <5ms overhead, scales to 1000+ stocks

### Negative Impacts / Tradeoffs

- **Performance Overhead**: 5ms per query for permission checks (vs <1ms baseline)
- **Implementation Effort**: 4 weeks (vs 0 weeks status quo, 1 week API-only)
- **Operational Complexity**: 5 roles to manage (vs 0 roles status quo)
- **Testing Surface**: Permission matrix 5×6=30 test cases minimum
- **Audit Log Storage**: 10-20% PostgreSQL storage increase (access logs)
- **Migration Required**: Existing agents need role assignment before deployment

### Affected Components

**Services to Implement**:

- `MemoryAccessControl`: Permission matrix, check_permission() API
- `MemoryAuditLog`: Log all memory writes to PostgreSQL
- `AuthorizationGateway`: API layer enforcing RBAC before memory operations
- `RoleManager`: Assign/revoke roles for agents, humans
- `AuditLogQuery`: Query interface for incident investigation

**Data Pipeline**:

- Agent memory request → AuthorizationGateway.check_permission()
- If authorized → Execute memory operation → MemoryAuditLog.log_write()
- If denied → Log denial → Return 403 Forbidden

**Documentation**:

- `docs/architecture/02-memory-system.md`: Add §5 Access Control
- `docs/architecture/04-agents-support.md`: Clarify Knowledge Base Agent permissions
- `docs/operations/03-data-management.md`: Link memory RBAC to file RBAC (unified governance)

---

## Implementation Notes

### Permission Matrix

**5 Roles × 6 Resources**:

```python
class MemoryAccessControl:
    """Access control for memory system"""

    PERMISSIONS = {
        'agent': {
            'l1_working_memory': 'read_write_own',  # Own L1 only
            'l2_agent_cache': 'read_write_own',     # Own L2 only
            'l3_central_graph': 'read_all',         # Read-only L3
            'pattern_lifecycle': 'propose_only',     # Can propose patterns
            'credibility_scores': 'read_own',        # Own credibility only
            'audit_log': 'none'
        },
        'knowledge_base_agent': {
            'l1_working_memory': 'read_write_own',
            'l2_agent_cache': 'read_write_own',
            'l3_central_graph': 'read_write',        # Can write to L3
            'pattern_lifecycle': 'validate',         # Can advance pattern status
            'credibility_scores': 'read_all',
            'audit_log': 'read_all'
        },
        'debate_facilitator': {
            'l1_working_memory': 'read_write_own',
            'l2_agent_cache': 'read_all',            # Cross-agent view for mediation
            'l3_central_graph': 'read_all',
            'pattern_lifecycle': 'read_all',
            'credibility_scores': 'read_all',        # Needs for auto-resolution
            'audit_log': 'read_all'
        },
        'learning_engine': {
            'l1_working_memory': 'none',
            'l2_agent_cache': 'read_all',
            'l3_central_graph': 'read_write',
            'pattern_lifecycle': 'validate',         # Can advance pattern status
            'credibility_scores': 'read_write_all',  # Updates credibility
            'audit_log': 'read_all'
        },
        'human_admin': {
            'l1_working_memory': 'read_all',
            'l2_agent_cache': 'read_all',
            'l3_central_graph': 'read_write_delete',
            'pattern_lifecycle': 'full_control',
            'credibility_scores': 'read_write_all',
            'audit_log': 'read_write_delete'         # Retention management
        }
    }

    def check_permission(self, actor_role: str, resource_type: str,
                        action: str, resource_owner: str = None) -> bool:
        """Check if role can perform action on resource

        Args:
            actor_role: Role of actor attempting action
            resource_type: Type of resource (l1_working_memory, l2_agent_cache, etc)
            action: Action to perform (read, write, delete, propose, validate, etc)
            resource_owner: Owner of resource (for _own permissions)

        Returns:
            True if authorized, False otherwise
        """

        perms = self.PERMISSIONS.get(actor_role, {})
        resource_perm = perms.get(resource_type, 'none')

        if resource_perm == 'none':
            return False

        # Parse permission string
        if action == 'read':
            if 'read' in resource_perm:
                # Check if read_own vs read_all
                if resource_perm == 'read_own' and resource_owner != actor_role:
                    return False
                return True

        if action == 'write':
            if 'write' in resource_perm:
                # Check if write_own vs write_all
                if 'write_own' in resource_perm and resource_owner != actor_role:
                    return False
                return True

        if action == 'delete':
            return 'delete' in resource_perm

        # Pattern lifecycle actions
        if action in ['propose', 'validate', 'approve', 'deprecate']:
            return action in resource_perm or 'full_control' in resource_perm

        return False
```

### Audit Logging Architecture

**PostgreSQL Schema**:

```sql
-- Audit log (append-only, partitioned by month)
CREATE TABLE memory_access_audit (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_id VARCHAR(100) NOT NULL,        -- agent_id or human_id
    actor_role VARCHAR(50) NOT NULL,       -- 'agent', 'knowledge_base_agent', etc
    resource_type VARCHAR(50) NOT NULL,    -- 'l3_central_graph', 'pattern_lifecycle', etc
    resource_id VARCHAR(255) NOT NULL,     -- node_id, pattern_id, cache_key, etc
    action VARCHAR(50) NOT NULL,           -- 'read', 'write', 'delete', 'propose', etc
    authorized BOOLEAN NOT NULL,           -- True if allowed, False if denied
    old_value JSONB,                       -- Previous state (for writes)
    new_value JSONB,                       -- New state (for writes)
    action_reason TEXT,                    -- Why agent performed action
    request_context JSONB                  -- Additional context (IP, session, etc)
) PARTITION BY RANGE (timestamp);

-- Indexes for investigation queries
CREATE INDEX idx_audit_timestamp ON memory_access_audit(timestamp DESC);
CREATE INDEX idx_audit_actor ON memory_access_audit(actor_id, timestamp DESC);
CREATE INDEX idx_audit_resource ON memory_access_audit(resource_type, resource_id);
CREATE INDEX idx_audit_unauthorized ON memory_access_audit(authorized) WHERE authorized = false;

-- Retention: 5 years (regulatory compliance)
-- Monthly partitions with automated cleanup
```

**Audit Logging Implementation**:

```python
class MemoryAuditLog:
    """Audit trail for memory modifications"""

    def log_access(self, actor: Actor, resource: Resource, action: str,
                   authorized: bool, old_value=None, new_value=None):
        """Log all memory access attempts"""

        self.db.execute("""
            INSERT INTO memory_access_audit (
                actor_id, actor_role, resource_type, resource_id,
                action, authorized, old_value, new_value, action_reason
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [
            actor.id,
            actor.role,
            resource.type,
            resource.id,
            action,
            authorized,
            json.dumps(old_value) if old_value else None,
            json.dumps(new_value) if new_value else None,
            actor.action_reason
        ])

    def query_audit_log(self, filters: dict) -> List[AuditEntry]:
        """Query audit log for investigation

        Examples:
            # Find all unauthorized access attempts
            audit_log.query({'authorized': False})

            # Find all pattern modifications by specific agent
            audit_log.query({'actor_id': 'financial_analyst_1',
                           'resource_type': 'pattern_lifecycle'})

            # Find all credibility score changes in timerange
            audit_log.query({'resource_type': 'credibility_scores',
                           'timestamp_range': ('2025-11-01', '2025-11-18')})
        """

        query = "SELECT * FROM memory_access_audit WHERE 1=1"
        params = []

        if 'actor_id' in filters:
            query += " AND actor_id = %s"
            params.append(filters['actor_id'])

        if 'resource_type' in filters:
            query += " AND resource_type = %s"
            params.append(filters['resource_type'])

        if 'authorized' in filters:
            query += " AND authorized = %s"
            params.append(filters['authorized'])

        if 'timestamp_range' in filters:
            query += " AND timestamp BETWEEN %s AND %s"
            params.extend(filters['timestamp_range'])

        query += " ORDER BY timestamp DESC LIMIT 1000"

        return self.db.query(query, params)
```

### Authorization Gateway

**API Layer Integration**:

```python
class AuthorizationGateway:
    """API gateway enforcing RBAC for memory operations"""

    def __init__(self, access_control: MemoryAccessControl,
                 audit_log: MemoryAuditLog):
        self.access_control = access_control
        self.audit_log = audit_log

    def authorize_and_execute(self, actor: Actor, resource: Resource,
                             action: str, operation: Callable):
        """Check permission, log access, execute operation"""

        # Check permission
        authorized = self.access_control.check_permission(
            actor_role=actor.role,
            resource_type=resource.type,
            action=action,
            resource_owner=resource.owner
        )

        # Log access attempt
        self.audit_log.log_access(
            actor=actor,
            resource=resource,
            action=action,
            authorized=authorized
        )

        # Execute if authorized
        if not authorized:
            raise PermissionDenied(
                f"{actor.role} cannot {action} {resource.type}"
            )

        # Capture old value for writes
        old_value = resource.get_current_value() if action == 'write' else None

        # Execute operation
        result = operation()

        # Log write details
        if action in ['write', 'delete']:
            self.audit_log.log_access(
                actor=actor,
                resource=resource,
                action=action,
                authorized=True,
                old_value=old_value,
                new_value=result if action == 'write' else None
            )

        return result
```

### Pattern Lifecycle Permissions

**Pattern State Machine with RBAC**:

```python
class PatternLifecycle:
    """Pattern lifecycle with access control"""

    STATES = ['PROPOSED', 'VALIDATED', 'APPROVED', 'ACTIVE', 'DEPRECATED', 'ARCHIVED']

    TRANSITIONS = {
        'PROPOSED': {
            'validate': ['knowledge_base_agent', 'human_admin'],
            'reject': ['human_admin']
        },
        'VALIDATED': {
            'approve': ['human_admin'],
            'reject': ['human_admin']
        },
        'APPROVED': {
            'activate': ['knowledge_base_agent', 'human_admin']
        },
        'ACTIVE': {
            'deprecate': ['learning_engine', 'human_admin']
        },
        'DEPRECATED': {
            'archive': ['human_admin']
        }
    }

    def transition_pattern(self, pattern_id: str, new_status: str,
                          actor: Actor, reason: str):
        """Transition pattern status with permission check"""

        pattern = self.get_pattern(pattern_id)
        current_status = pattern.status

        # Check if transition is allowed
        if new_status not in self.TRANSITIONS.get(current_status, {}):
            raise InvalidTransition(
                f"Cannot transition from {current_status} to {new_status}"
            )

        # Check if actor role is authorized for this transition
        allowed_roles = self.TRANSITIONS[current_status].get(
            new_status.lower(), []
        )

        if actor.role not in allowed_roles:
            raise PermissionDenied(
                f"{actor.role} cannot transition pattern from "
                f"{current_status} to {new_status}"
            )

        # Execute transition via authorization gateway
        return self.gateway.authorize_and_execute(
            actor=actor,
            resource=Resource(type='pattern_lifecycle', id=pattern_id),
            action=new_status.lower(),
            operation=lambda: self.update_pattern_status(
                pattern_id, new_status, reason
            )
        )
```

### Agent Role Assignment

**Configuration**:

```yaml
# config/agent_roles.yaml
agents:
  screening_agent:
    role: agent
    permissions: [l1_write_own, l2_write_own, l3_read_all, pattern_propose]

  business_research_agent:
    role: agent
    permissions: [l1_write_own, l2_write_own, l3_read_all, pattern_propose]

  financial_analyst_agent:
    role: agent
    permissions: [l1_write_own, l2_write_own, l3_read_all, pattern_propose]

  strategy_analyst_agent:
    role: agent
    permissions: [l1_write_own, l2_write_own, l3_read_all, pattern_propose]

  valuation_agent:
    role: agent
    permissions: [l1_write_own, l2_write_own, l3_read_all, pattern_propose]

  knowledge_base_agent:
    role: knowledge_base_agent
    permissions:
      [
        l1_write_own,
        l2_write_own,
        l3_read_write,
        pattern_validate,
        credibility_read_all,
      ]

  debate_facilitator:
    role: debate_facilitator
    permissions: [l1_write_own, l2_read_all, l3_read_all, credibility_read_all]

  learning_engine:
    role: learning_engine
    permissions:
      [l2_read_all, l3_read_write, pattern_validate, credibility_read_write_all]

humans:
  analyst:
    role: human_admin
    permissions: [full_control]
```

### Integration Points

**Memory Write Flow**:

```python
# Before: Direct Neo4j write (no access control)
def store_pattern_old(agent_id, pattern_data):
    neo4j.run("CREATE (p:Pattern {data: $data})", data=pattern_data)

# After: Via authorization gateway
def store_pattern_new(agent_id, pattern_data):
    actor = Actor(id=agent_id, role='agent')
    resource = Resource(type='pattern_lifecycle', id='new_pattern')

    return gateway.authorize_and_execute(
        actor=actor,
        resource=resource,
        action='propose',
        operation=lambda: neo4j.run(
            "CREATE (p:Pattern {status: 'PROPOSED', data: $data})",
            data=pattern_data
        )
    )
```

**Cross-Agent Cache Access** (Debate Facilitator):

```python
# Debate Facilitator reading Financial Analyst's L2 cache
def get_agent_evidence(facilitator_id, target_agent_id, cache_key):
    actor = Actor(id=facilitator_id, role='debate_facilitator')
    resource = Resource(
        type='l2_agent_cache',
        id=cache_key,
        owner=target_agent_id
    )

    # Facilitator has read_all permission for L2, so this succeeds
    return gateway.authorize_and_execute(
        actor=actor,
        resource=resource,
        action='read',
        operation=lambda: redis.get(f"{target_agent_id}:l2:{cache_key}")
    )
```

### Testing Requirements

**Permission Matrix Test Coverage**:

```python
def test_agent_l3_write_denied():
    """Agents cannot write to L3 central graph"""
    actor = Actor(id='financial_analyst_1', role='agent')
    resource = Resource(type='l3_central_graph', id='pattern_123')

    authorized = access_control.check_permission(
        actor_role=actor.role,
        resource_type=resource.type,
        action='write'
    )

    assert authorized == False

def test_kb_agent_l3_write_allowed():
    """Knowledge Base Agent can write to L3"""
    actor = Actor(id='kb_agent_1', role='knowledge_base_agent')
    resource = Resource(type='l3_central_graph', id='pattern_123')

    authorized = access_control.check_permission(
        actor_role=actor.role,
        resource_type=resource.type,
        action='write'
    )

    assert authorized == True

def test_agent_cross_cache_read_denied():
    """Agents cannot read other agents' L2 caches"""
    actor = Actor(id='financial_analyst_1', role='agent')
    resource = Resource(
        type='l2_agent_cache',
        id='cache_key_123',
        owner='business_research_1'
    )

    authorized = access_control.check_permission(
        actor_role=actor.role,
        resource_type=resource.type,
        action='read',
        resource_owner=resource.owner
    )

    assert authorized == False

def test_facilitator_cross_cache_read_allowed():
    """Debate Facilitator can read all agents' L2 caches"""
    actor = Actor(id='debate_facilitator_1', role='debate_facilitator')
    resource = Resource(
        type='l2_agent_cache',
        id='cache_key_123',
        owner='financial_analyst_1'
    )

    authorized = access_control.check_permission(
        actor_role=actor.role,
        resource_type=resource.type,
        action='read',
        resource_owner=resource.owner
    )

    assert authorized == True

def test_learning_engine_credibility_write_allowed():
    """Learning Engine can write credibility scores"""
    actor = Actor(id='learning_engine_1', role='learning_engine')
    resource = Resource(type='credibility_scores', id='agent_123')

    authorized = access_control.check_permission(
        actor_role=actor.role,
        resource_type=resource.type,
        action='write'
    )

    assert authorized == True

def test_agent_credibility_write_denied():
    """Agents cannot write credibility scores"""
    actor = Actor(id='financial_analyst_1', role='agent')
    resource = Resource(type='credibility_scores', id='agent_123')

    authorized = access_control.check_permission(
        actor_role=actor.role,
        resource_type=resource.type,
        action='write'
    )

    assert authorized == False

def test_audit_log_captures_unauthorized_attempt():
    """Audit log records unauthorized access attempts"""
    actor = Actor(id='financial_analyst_1', role='agent')
    resource = Resource(type='l3_central_graph', id='pattern_123')

    with pytest.raises(PermissionDenied):
        gateway.authorize_and_execute(
            actor=actor,
            resource=resource,
            action='write',
            operation=lambda: None
        )

    # Verify audit log entry
    audit_entries = audit_log.query({
        'actor_id': 'financial_analyst_1',
        'resource_type': 'l3_central_graph',
        'authorized': False
    })

    assert len(audit_entries) > 0
    assert audit_entries[0].action == 'write'
```

### Performance Benchmarking

**Target**: <5ms overhead per query

```python
def benchmark_permission_check():
    """Measure permission check overhead"""

    actor = Actor(id='test_agent', role='agent')
    resource = Resource(type='l3_central_graph', id='pattern_123')

    times = []
    for _ in range(10000):
        start = time.perf_counter()
        access_control.check_permission(
            actor_role=actor.role,
            resource_type=resource.type,
            action='read'
        )
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    p50 = np.percentile(times, 50)
    p95 = np.percentile(times, 95)
    p99 = np.percentile(times, 99)

    assert p50 < 1.0  # p50 < 1ms
    assert p95 < 5.0  # p95 < 5ms
    assert p99 < 10.0  # p99 < 10ms
```

### Rollback Strategy

If RBAC causes issues:

1. **Feature Flag**: Disable authorization checks, keep audit logging
2. **Degraded Mode**: Log denials but allow (monitoring-only)
3. **Gradual Rollout**: Enable RBAC for L3 only first, then L2
4. **Full Rollback**: Remove authorization gateway, direct memory access

**Monitoring**:

- Track authorization denial rate (target: <1% denied)
- Monitor permission check latency (target: p95 <5ms)
- Alert on unauthorized access attempts (>10/hour)
- Dashboard for audit log queries

---

## Open Questions

None - all critical questions resolved during design:

1. ✅ Number of roles: 5 (agent, knowledge_base_agent, debate_facilitator, learning_engine, human_admin)
2. ✅ Permission granularity: Fine-grained (read_own vs read_all, write_own vs write_all)
3. ✅ Pattern lifecycle: 6 states (PROPOSED → VALIDATED → APPROVED → ACTIVE → DEPRECATED → ARCHIVED)
4. ✅ Audit retention: 5 years (regulatory compliance)
5. ✅ Performance budget: <5ms overhead per query
6. ✅ Enforcement point: API authorization gateway
7. ✅ Credibility write authority: Learning Engine only
8. ✅ Debate Facilitator cross-cache access: read_all for L2 caches

**Blocking**: No

---

## References

- **Design Flaws**: [Flaw #20 - Memory System Access Control Undefined](../design-flaws/active/20-access-control.md)
- **Related Decisions**:
  - DD-018: Memory Failure Resilience (backup/recovery but not access control)
  - DD-019: Data Tier Operations (graph integrity monitoring)
  - DD-007: Pattern Validation Architecture (pattern lifecycle requirements)
  - DD-008: Agent Credibility System (credibility score protection requirements)
- **Architecture**:
  - [Memory System](../architecture/02-memory-system.md) (L1/L2/L3 architecture)
  - [Agents - Support](../architecture/04-agents-support.md) (Knowledge Base Agent definition)
  - [Data Management](../operations/03-data-management.md) (file RBAC baseline)
- **Industry Patterns**:
  - PostgreSQL roles: <https://www.postgresql.org/docs/current/user-manag.html>
  - AWS IAM RBAC: <https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html>
  - OAuth scopes: <https://oauth.net/2/scope/>

---

## Status History

| Date       | Status   | Notes                                       |
| ---------- | -------- | ------------------------------------------- |
| 2025-11-18 | Proposed | Initial proposal based on Flaw #20 analysis |
| 2025-11-18 | Approved | Fine-grained RBAC (5 roles), <5ms overhead  |

---

## Notes

### Cost Estimate

**Audit Log Storage**:

```text
Assumptions:
- 13 agents × 100 memory operations/day = 1300 operations/day
- 475,000 operations/year
- 5-year retention = 2.4M records

PostgreSQL Storage:
  Row size: ~500 bytes (includes JSONB values)
  Total: 2.4M × 500 bytes = 1.2GB
  Cost: 1.2GB × $0.023/GB = $0.028/mo
  Negligible cost
```

**Performance Overhead**:

```text
Permission check: <1ms (in-memory dictionary lookup)
Audit log write: <4ms (async PostgreSQL insert)
Total: <5ms per operation

Analysis latency budget: 100ms
Overhead: 5ms / 100ms = 5%
Acceptable for production
```

**Implementation Effort**: 4 weeks

**Week 1**: Permission matrix definition, access control class, role configuration
**Week 2**: API authorization gateway, integration with memory layer
**Week 3**: Audit logging (PostgreSQL schema, logging service, query API)
**Week 4**: Testing (30+ test cases), performance benchmarking, documentation

**Dependencies**:

- Memory system operational (L1/L2/L3) - ✅ exists
- PostgreSQL database operational - ✅ exists
- Neo4j central graph operational - ✅ exists
- Agent role configuration - new requirement

### Future Considerations

- **Dynamic Permissions**: Time-based permissions (e.g., temporary admin access)
- **Fine-Grained Pattern Permissions**: Per-domain pattern access (financial patterns vs business patterns)
- **Audit Log Analytics**: ML-based anomaly detection on access patterns
- **Role Hierarchy**: Inherit permissions (e.g., human_admin inherits knowledge_base_agent)
- **API Rate Limiting**: Per-role rate limits to prevent abuse
- **Encryption**: Encrypt audit log old_value/new_value fields (sensitive data protection)
