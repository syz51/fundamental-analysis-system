---
flaw_id: 27
title: Sync Priority Inversion
status: resolved
priority: critical
phase: 3
effort_weeks: 1
impact: System blindness to critical state changes
blocks: []
depends_on: []
domain: ['memory', 'architecture']
discovered: 2025-11-19
resolved: 2025-11-19
resolution: '4-tier priority sync with reserved capacity'
---

# Flaw #27: Memory Sync Priority Inversion & Saturation

| Attribute    | Details                                                                                     |
| :----------- | :------------------------------------------------------------------------------------------ |
| **Status**   | **Resolved**                                                                                |
| **Phase**    | Phase 3 (Memory System)                                                                     |
| **Priority** | Critical                                                                                    |
| **Effort**   | Medium (1 week)                                                                             |
| **Impact**   | System blindness to critical state changes (e.g., Market Crash) during high-load scenarios. |

## Problem Description

The `SyncBackpressureManager` (defined in `docs/architecture/02-memory-system.md`) implements a priority-based eviction policy to handle queue saturation. The policy states: "Critical sync + full queue: evict lowest priority".

**The logic flaw:**
The system assumes there will always be a "lowest priority" item (Normal/High) to evict. However, during a system-wide stress event (e.g., Flash Crash), the following sequence can occur:

1. **Macro Agent** detects "Regime Change" (Crash) → triggers **Critical** Sync (Broadcast).
2. **Screening Agents** detect price anomalies → trigger **Critical** Syncs (Debates).
3. **Alert Manager** detects failures → triggers **Critical** Syncs (Alerts).

If the queue is flooded with Type 2 and Type 3 "Critical" syncs, the queue becomes 100% full of "Critical" items. When the "Regime Change" (Type 1) sync arrives:

- It enters the queue (if there's space).
- OR, if the queue is full of Critical items, the eviction logic is undefined or might drop the _oldest_ Critical item.

**Scenario:**
If the "Regime Change" alert (the most important signal) is dropped or delayed behind 50 "Debate" syncs, the agents will continue to debate and analyze stocks using **stale regime data** (e.g., "Bull Market" logic) during a crash. This leads to catastrophic "Buy" recommendations during a plummeting market.

## Resolution

### 1. Introduced "System-Critical" Priority Tier

Expanded the priority levels to 4 tiers in `docs/architecture/02-memory-system.md`:

- **System-Critical (Tier 0):** Regime changes, Global stops, Panic buttons. _Never dropped. Can evict "Critical"._
- **Critical (Tier 1):** Debates, Human Gates.
- **High (Tier 2):** Important findings.
- **Normal (Tier 3):** Routine syncs.

### 2. Reserved Queue Capacity

Enforced reserved slots for higher priorities in `SyncBackpressureManager`:

- Max Queue Depth: 100
- Reserved for Tier 0: 10 slots (Tier 1-3 cannot fill these)
- Reserved for Tier 1: 20 slots (Tier 2-3 cannot fill these)

### 3. Protocol Update

Updated `docs/architecture/07-collaboration-protocols.md` to assign "Regime Change" and "Major Fed Announcement" to the **System-Critical** priority tier.

## Action Items

- [x] Update `docs/architecture/02-memory-system.md` with 4-tier priority logic.
- [x] Update `SyncBackpressureManager` code specification to include reserved capacity logic.
- [x] Update `docs/architecture/07-collaboration-protocols.md` to assign "Regime Change" to Tier 0.
