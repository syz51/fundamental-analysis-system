# Flaw #20: Memory System Access Control Undefined

**Status**: 🔴 ACTIVE
**Priority**: Medium
**Impact**: Data integrity risk from unrestricted memory modifications
**Phase**: Phase 3 (Months 5-6)

---

## Problem Description

**Files**: `docs/operations/03-data-management.md:516-541` (role-based access for data), memory system docs

**Problem**: Data-management.md specifies role-based access control for data files, but memory system (L2 caches, L3 graph) access control undefined.

**Current State**:
```yaml
# data-management.md L516-541 - Data file access control:
Roles:
  - Admins: Full access
  - Agents: Read source data, write processed
  - Analysts: Read-only all

# Memory system access - UNDEFINED:
  - Can agents read each other's L2 caches?
  - Can agents write to L3 graph directly?
  - Who can deprecate patterns?
  - Who can modify agent credibility scores?
  - Audit trail for memory modifications?
```

---

## Missing Specifications

### 1. Agent L2 Cache Access

**Questions**:
- Can Financial Analyst read Business Analyst's L2 cache?
- Cross-agent cache pollution risk?
- Cache poisoning prevention?

### 2. L3 Central Graph Write Access

**Questions**:
- Can agents write directly to Neo4j or only through API?
- Who can create/delete Pattern nodes?
- Who can modify credibility scores?
- Who can archive/deprecate patterns?

### 3. Pattern Lifecycle Permissions

**Questions**:
- Pattern creation: Any agent or only Knowledge Base Agent?
- Pattern validation: Human-only or automated?
- Pattern deprecation: Who decides?
- Pattern deletion: Never? Or admin-only?

### 4. Audit Trail

**Questions**:
- Log all memory writes?
- Track pattern modification history?
- Credibility score change audit?

---

## Recommended Solution

```python
class MemoryAccessControl:
    """Access control for memory system"""

    PERMISSIONS = {
        'agent': {
            'l1_working_memory': 'read_write_own',  # Own L1 only
            'l2_agent_cache': 'read_write_own',     # Own L2 only
            'l3_central_graph': 'read_all',         # Read-only L3
            'pattern_propose': True,                 # Can propose patterns
            'pattern_modify': False,                 # Cannot modify patterns
            'credibility_read': 'read_own',          # Own credibility only
            'credibility_write': False
        },
        'knowledge_base_agent': {
            'l1_working_memory': 'read_write_own',
            'l2_agent_cache': 'read_own',
            'l3_central_graph': 'read_write',        # Can write to L3
            'pattern_propose': True,
            'pattern_modify': True,                  # Can advance pattern status
            'credibility_read': 'read_all',
            'credibility_write': False
        },
        'debate_facilitator': {
            'l1_working_memory': 'read_write_own',
            'l2_agent_cache': 'read_all',            # Needs cross-agent view
            'l3_central_graph': 'read_all',
            'pattern_propose': False,
            'pattern_modify': False,
            'credibility_read': 'read_all',          # Needs for auto-resolution
            'credibility_write': False
        },
        'learning_engine': {
            'l1_working_memory': 'none',
            'l2_agent_cache': 'read_all',
            'l3_central_graph': 'read_write',
            'pattern_propose': True,
            'pattern_modify': True,
            'credibility_read': 'read_all',
            'credibility_write': True,               # Updates credibility
        },
        'human_admin': {
            'l1_working_memory': 'read_all',
            'l2_agent_cache': 'read_all',
            'l3_central_graph': 'read_write_delete',
            'pattern_propose': True,
            'pattern_modify': True,
            'credibility_read': 'read_all',
            'credibility_write': True,
        }
    }

    def check_permission(self, role, resource, action):
        """Check if role can perform action on resource"""

        perms = self.PERMISSIONS.get(role, {})
        resource_perm = perms.get(resource, 'none')

        if resource_perm == 'none':
            return False

        # Parse permission string
        if action == 'read' and 'read' in resource_perm:
            return True

        if action == 'write' and 'write' in resource_perm:
            return True

        if action == 'delete' and 'delete' in resource_perm:
            return True

        return False

class MemoryAuditLog:
    """Audit trail for memory modifications"""

    def log_memory_write(self, actor, resource, action, data):
        """Log all memory writes"""

        self.write_audit_log({
            'timestamp': datetime.now(),
            'actor': actor.id,
            'actor_role': actor.role,
            'resource_type': resource.type,
            'resource_id': resource.id,
            'action': action,  # create/update/delete
            'old_value': resource.get_current_value(),
            'new_value': data,
            'reason': actor.action_reason
        })
```

---

## Implementation Plan

**Week 1**: Define permission matrix
**Week 2**: Implement access control layer
**Week 3**: Add audit logging
**Week 4**: Integration testing

---

## Success Criteria

- ✅ Permission matrix enforced (100% test coverage)
- ✅ Audit log captures all L3 writes
- ✅ Zero unauthorized memory modifications (security testing)
- ✅ Performance impact <5ms per query (access check overhead)

---

## Dependencies

- **Blocks**: Production security compliance
- **Depends On**: Memory system operational (L1/L2/L3)
- **Related**: Data governance (data-management.md), Learning systems
