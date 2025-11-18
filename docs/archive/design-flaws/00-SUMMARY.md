# Design Flaws Summary

> **⚠️ This file has been deprecated**
>
> The design-flaws folder has been restructured for better scalability.
>
> **New Navigation:**
>
> - **[INDEX.md](INDEX.md)** - Quick reference with priority/domain/phase views
> - **[DEPENDENCIES.md](DEPENDENCIES.md)** - Dependency graph and blocking analysis
> - **[ROADMAP.md](ROADMAP.md)** - Phase timeline and milestones
> - **[README.md](README.md)** - How to navigate this folder

---

## Quick Stats (as of 2025-11-18)

- **Total**: 21 flaws + 6 minor issues
- **Active**: 11 (3 critical, 6 high, 1 medium, 1 deferred)
- **Resolved**: 10
- **Deferred**: 1

---

## Where to Find What You Need

| If you want to...                             | Go to                                                                    |
| --------------------------------------------- | ------------------------------------------------------------------------ |
| See all flaws at a glance                     | [INDEX.md](INDEX.md)                                                     |
| Find critical blockers                        | [INDEX.md § Critical Flaws](INDEX.md#-critical-active-flaws-3)           |
| Understand dependencies                       | [DEPENDENCIES.md](DEPENDENCIES.md)                                       |
| Plan implementation timeline                  | [ROADMAP.md](ROADMAP.md)                                                 |
| Find flaws by domain (memory/learning/agents) | [INDEX.md § Domain View](INDEX.md#-domain-view)                          |
| See what's blocking a feature                 | [DEPENDENCIES.md § Blocking Analysis](DEPENDENCIES.md#blocking-analysis) |

---

## Why the Change?

**Old structure** (this file):

- Single 112-line file with all flaws
- Became outdated (showed 10 flaws, actually 21)
- Hard to maintain, no programmatic access

**New structure**:

- Multiple focused files (INDEX, DEPENDENCIES, ROADMAP, README)
- YAML frontmatter in each flaw file (programmatically queryable)
- Auto-generated INDEX.md via `python generate_index.py`
- Scalable to 50+ flaws with collapsible sections

---

**Please use [INDEX.md](INDEX.md) for current flaw information.**
