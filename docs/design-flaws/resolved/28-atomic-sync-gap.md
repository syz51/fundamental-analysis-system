---
flaw_id: 28
title: Atomic Gap in Sync-Snapshot
status: resolved
priority: high
phase: 2
effort_weeks: 1
impact: Data inconsistency during debates
blocks: []
depends_on: []
domain: ['memory', 'architecture']
discovered: 2025-11-19
resolved: 2025-11-19
resolution: 'Atomic Sync-Lock Protocol'
---

# Flaw #28: Atomic Gap in Sync-Snapshot Protocol

| Attribute    | Details                                                                         |
| :----------- | :------------------------------------------------------------------------------ |
| **Status**   | **Resolved**                                                                    |
| **Phase**    | Phase 2 (Core Agents)                                                           |
| **Priority** | High                                                                            |
| **Effort**   | Medium (1 week)                                                                 |
| **Impact**   | Data inconsistency during debates; "Hallucinated" disagreements between agents. |

## Problem Description

The "Pre-Debate Memory Synchronization" protocol (in `docs/architecture/07-collaboration-protocols.md`) specifies:

1. **Force sync all participants** (<2 seconds)
2. **Create memory snapshot**
3. **Load historical context**

**The Gap:**
There is no locking or atomic guarantee between Step 1 (Sync) and Step 2 (Snapshot).

- **Agent A** pushes its state (Sync).
- **Agent A** continues executing (e.g., updates a variable based on a new incoming price).
- **System** takes Snapshot of Central Graph (which contains Agent A's _pushed_ state).
- **Debate Starts**: Agent A references its _local_ working memory (New State), while the Debate Coordinator references the _Snapshot_ (Old State).

**Result:**
Agent A might argue "Price is $100" (Local Memory), while the Debate context says "Price is $99" (Snapshot). This causes "hallucinated" conflicts where agents and the coordinator are out of sync, potentially leading to debate deadlocks or invalid resolutions.

## Resolution

### 1. Implementation of "Atomic Sync-Lock Protocol"

Updated `docs/architecture/07-collaboration-protocols.md` to include a locking mechanism:

```python
# 1. Acquire Sync Lock (Pause writes)
# 2. Force Sync (Flush to central)
# 3. Create Snapshot (Frozen state)
# 4. Release Lock
```

This ensures that the Snapshot captures the exact state of the agents at the moment of synchronization, with no possibility of drift.

## Action Items

- [x] Define `SyncLock` interface in `docs/architecture/02-memory-system.md`. (Note: Included in Protocol logic directly)
- [x] Update `docs/architecture/07-collaboration-protocols.md` to include the locking step.
