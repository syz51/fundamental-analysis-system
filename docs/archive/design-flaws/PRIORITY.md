# Design Flaws - Priority & Implementation Order

> **⚠️ This file has been deprecated and split into multiple focused documents**
>
> The content from this 594-line file has been reorganized for better maintainability:
>
> - **[INDEX.md](INDEX.md)** - Priority views (critical/high/medium/low), domain navigator, quick filters
> - **[DEPENDENCIES.md](DEPENDENCIES.md)** - Dependency graph, dependency matrix, blocking analysis
> - **[ROADMAP.md](ROADMAP.md)** - Phase-by-phase timeline, milestones, next steps
> - **[README.md](README.md)** - How to navigate the design-flaws folder

---

## Quick Migration Guide

**If you were looking for...**

| Old Section | New Location |
|-------------|--------------|
| Implementation Order | [ROADMAP.md](ROADMAP.md) |
| Critical Path | [DEPENDENCIES.md § Critical Path](DEPENDENCIES.md#critical-path) |
| Dependency Matrix | [DEPENDENCIES.md § Dependency Matrix](DEPENDENCIES.md#dependency-matrix) |
| Risk Assessment | [DEPENDENCIES.md § Risk Assessment](DEPENDENCIES.md#risk-assessment) |
| Next Steps | [ROADMAP.md § Next Steps](ROADMAP.md#next-steps) |
| Priority by flaw | [INDEX.md](INDEX.md) - sortable by priority/phase/domain |
| Blocking analysis | [DEPENDENCIES.md § Blocking Analysis](DEPENDENCIES.md#blocking-analysis) |

---

## What's New in the Restructure

### Better Organization

- **INDEX.md**: Priority-focused view with collapsible sections
- **DEPENDENCIES.md**: Dependency relationships and blocking analysis
- **ROADMAP.md**: Timeline-focused view with phase breakdown

### Programmatic Access

All 21 flaw files now have **YAML frontmatter** with structured metadata:

```yaml
---
flaw_id: 13
title: Learning System Validation Gaps
status: active
priority: critical
phase: 3
effort_weeks: 6
impact: Auto-approval without validation
blocks: ["Auto-approval deployment"]
depends_on: ["Gate 6 operational", "DD-007 pattern validation"]
domain: ["learning"]
---
```

### Auto-Generation

Run `python generate_index.py` to regenerate INDEX.md from frontmatter.

### Scalability

- Collapsible sections handle 50+ flaws
- Multiple navigation paths (priority/phase/domain/dependency)
- Domain grouping shows related flaws together

---

## Quick Stats (as of 2025-11-18)

- **Total**: 21 flaws + 6 minor issues
- **Active**: 11 (3 critical, 6 high, 1 medium, 1 deferred)
- **Resolved**: 10
- **Critical Blockers**: 3 (#13, #15, #21)
- **Phase 2 Blockers**: 3 (#14, #16, #19)

---

**Please use the new navigation files listed above for current information.**

For questions on how to navigate the restructured folder, see [README.md](README.md).
