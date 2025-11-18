# Design Flaws

Documentation of design issues discovered during system architecture development, with resolutions and implementation tracking.

---

## Overview

This folder contains **21 documented design flaws** identified through comprehensive architecture reviews. Each flaw is tracked with priority, dependencies, resolution status, and implementation details.

**Current Stats** (as of 2025-11-18):

- **Active**: 10 flaws (3 critical, 5 high, 1 medium, 1 deferred)
- **Resolved**: 11 flaws (through design decisions DD-001 through DD-012)
- **Deferred**: 1 flaw (subset of another flaw)
- **Minor Issues**: 6 low-priority clarifications

---

## Structure

```text
docs/design-flaws/
├── INDEX.md                # Central navigation (start here!)
├── DEPENDENCIES.md         # Dependency graph & critical path
├── ROADMAP.md              # Phase timeline
├── README.md               # This file - how to navigate
├── RESOLVING.md            # Guide for resolving flaws (using script)
├── generate_index.py       # Auto-generates INDEX.md
├── resolve_flaw.py         # Auto-resolve script (moves, updates refs)
├── MINOR-ISSUES.md         # Low-priority clarifications
│
├── active/                 # Active flaws (10 files)
│   └── NN-flaw-name.md
│
└── resolved/               # Resolved flaws (11 files)
    └── NN-flaw-name.md

docs/archive/design-flaws/  # Deprecated files (moved 2025-11-18)
├── 00-SUMMARY.md           # → see INDEX.md
└── PRIORITY.md             # → see INDEX.md, DEPENDENCIES.md, ROADMAP.md
```

### File Naming Convention

- **Active flaws**: `active/NN-short-name.md`
- **Resolved flaws**: `resolved/NN-short-name.md`
- **Numbering**: Flaws numbered #1-21 in discovery order

---

## How to Navigate

### Start Here: What's Your Goal?

**I want to...**

| Goal                            | Go To                                                                           |
| ------------------------------- | ------------------------------------------------------------------------------- |
| See all flaws at a glance       | [INDEX.md](INDEX.md) - Quick stats & priority view                              |
| Find critical blockers          | [INDEX.md § Critical Flaws](INDEX.md#-critical-active-flaws-3)                  |
| Understand dependencies         | [DEPENDENCIES.md](DEPENDENCIES.md) - Dependency graph & matrix                  |
| Plan implementation timeline    | [ROADMAP.md](ROADMAP.md) - Phase-by-phase breakdown                             |
| Find flaws in a specific domain | [INDEX.md § Domain View](INDEX.md#-domain-view) (memory/learning/agents/etc.)   |
| Find flaws in a specific phase  | [INDEX.md § Quick Filters](INDEX.md#-quick-filters) or [ROADMAP.md](ROADMAP.md) |
| See what's blocking a feature   | [DEPENDENCIES.md § Blocking Analysis](DEPENDENCIES.md#blocking-analysis)        |
| Find quick wins (<3 weeks)      | [INDEX.md § By Effort](INDEX.md#by-effort)                                      |
| Understand flaw frontmatter     | [Frontmatter Schema](#frontmatter-schema) below                                 |
| Add a new flaw                  | [Maintenance § Adding Flaws](#adding-a-new-flaw) below                          |
| Resolve a flaw                  | [RESOLVING.md](RESOLVING.md) - Automated script guide                           |

### Navigation by View

**Priority View** → [INDEX.md](INDEX.md)

- Critical (3 flaws) - blocks MVP/production
- High (6 flaws) - should fix before MVP
- Medium (1 flaw) - post-MVP
- Low/Deferred (2 flaws) - future optimization

**Timeline View** → [ROADMAP.md](ROADMAP.md)

- Phase 1 (Complete) - 2 flaws resolved
- Phase 2 (3 active blockers) - Must resolve before Phase 3
- Phase 3 (4 active) - Quality & learning
- Phase 4 (2 active) - Production readiness
- Phase 5 (2 deferred) - Optional refinements

**Domain View** → [INDEX.md § Domain View](INDEX.md#-domain-view)

- Memory System (6 flaws)
- Learning System (6 flaws)
- Agent System (5 flaws)
- Data System (3 flaws)
- Human Gates (4 flaws)
- Architecture (4 flaws)

**Dependency View** → [DEPENDENCIES.md](DEPENDENCIES.md)

- Critical path visualization
- Dependency matrix
- Blocking analysis
- Parallel workstreams

---

## For LLM Agents

### Programmatic Queries

Each flaw file has **YAML frontmatter** with structured metadata. You can parse this to:

1. **Filter by criteria**:

   ```python
   # Find all critical active flaws
   for flaw in glob("*.md"):
       metadata = parse_yaml_frontmatter(flaw)
       if metadata['status'] == 'active' and metadata['priority'] == 'critical':
           print(f"#{metadata['flaw_id']}: {metadata['title']}")
   ```

2. **Build dependency graphs**:

   ```python
   # Build dependency graph from frontmatter
   graph = nx.DiGraph()
   for flaw in all_flaws:
       metadata = parse_yaml_frontmatter(flaw)
       for dep in metadata.get('depends_on', []):
           graph.add_edge(dep, f"#{metadata['flaw_id']}")
   ```

3. **Calculate effort**:

   ```python
   # Sum total effort for active flaws
   total_weeks = sum(
       parse_yaml_frontmatter(f)['effort_weeks']
       for f in active_flaws
   )
   ```

### Quick Parsing Example

```python
import yaml
import re

def parse_flaw_file(filepath):
    """Extract frontmatter from a design flaw file."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Extract YAML frontmatter
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if match:
        metadata = yaml.safe_load(match.group(1))
        return metadata
    return None

# Example usage
metadata = parse_flaw_file('13-validation-gaps.md')
print(f"Flaw #{metadata['flaw_id']}: {metadata['title']}")
print(f"Status: {metadata['status']}, Priority: {metadata['priority']}")
print(f"Blocks: {metadata['blocks']}")
```

### Common Queries

**Find unblocked flaws** (ready to implement):

```python
[f for f in active_flaws
 if not f.frontmatter['depends_on'] or all_resolved(f.frontmatter['depends_on'])]
```

**Find flaws in a domain**:

```python
[f for f in all_flaws if 'memory' in f.frontmatter['domain']]
```

**Find critical path**:

```python
# Flaws with no dependents can be parallelized
[f for f in active_flaws if not f.frontmatter['blocks']]
```

---

## Frontmatter Schema

Every flaw file (`*.md`) has YAML frontmatter with the following fields:

```yaml
---
flaw_id: 13 # Integer: Flaw number (1-21)
title: 'Short descriptive title'
status: active # Enum: active | resolved | deferred
priority: critical # Enum: critical | high | medium | low
phase: 3 # Integer or range: 1, 2, 3, 4, 5, or "2-3", "3-4"
effort_weeks: 6 # Integer: Estimated effort in weeks
impact: 'Brief impact description'
blocks: ['Feature X', '#Y'] # List: What this flaw blocks (empty list [] if none)
depends_on: ['#Z', 'DD-00X'] # List: Prerequisites (empty list [] if none)
domain: ['learning', 'memory'] # List: System domains (see below)
sub_issues: # Optional: Sub-problems within this flaw
  - id: C3
    severity: critical # Enum: critical | high | medium | low
    title: 'Sub-issue description'
related_flaws: ['#6'] # Optional: Related but non-blocking flaws
discovered: 2025-11-17 # Date: When flaw was identified
resolved: 2025-11-17 # Date: When resolved (resolved status only)
resolution: 'DD-007 Pattern Validation' # String: Resolution method (resolved only)
---
```

### Field Descriptions

| Field           | Type       | Required | Description                                                   |
| --------------- | ---------- | -------- | ------------------------------------------------------------- |
| `flaw_id`       | int        | ✅       | Unique flaw number (1-21)                                     |
| `title`         | string     | ✅       | Short descriptive title                                       |
| `status`        | enum       | ✅       | `active`, `resolved`, or `deferred`                           |
| `priority`      | enum       | ✅       | `critical`, `high`, `medium`, or `low`                        |
| `phase`         | int/string | ✅       | Target phase: `1`, `2`, `3`, `4`, `5`, or ranges like `"2-3"` |
| `effort_weeks`  | int        | ✅       | Estimated effort in weeks                                     |
| `impact`        | string     | ✅       | Brief description of impact if unfixed                        |
| `blocks`        | list       | ✅       | What this flaw blocks (can be empty `[]`)                     |
| `depends_on`    | list       | ✅       | Prerequisites (can be empty `[]`)                             |
| `domain`        | list       | ✅       | System domains (see Domain Types below)                       |
| `sub_issues`    | list       | ⚠️       | Optional: Sub-problems with id/severity/title                 |
| `related_flaws` | list       | ❌       | Optional: Related flaws (non-blocking)                        |
| `discovered`    | date       | ✅       | Discovery date (YYYY-MM-DD)                                   |
| `resolved`      | date       | ⚠️       | Resolution date (resolved flaws only)                         |
| `resolution`    | string     | ⚠️       | Resolution method (resolved flaws only)                       |

### Domain Types

Valid domain values (can be multiple per flaw):

- `memory` - Memory system (L1/L2/L3 cache, knowledge graph)
- `learning` - Learning systems (patterns, feedback, validation)
- `agents` - Agent system (credibility, communication, coordination)
- `data` - Data management (retention, tiers, quality)
- `human-gates` - Human decision gates (routing, expertise, parameters)
- `architecture` - System architecture (scalability, protocols, design)

---

## Maintenance

### Adding a New Flaw

1. **Determine flaw number**: Next sequential number (currently 22)

2. **Create file**: `docs/design-flaws/active/22-short-name.md`

3. **Add frontmatter**:

   ```yaml
   ---
   flaw_id: 22
   title: Your Flaw Title
   status: active
   priority: high # critical/high/medium/low
   phase: 2 # or "2-3" for ranges
   effort_weeks: 4
   impact: Brief description of impact
   blocks: ['Feature X', '#Y'] # or []
   depends_on: ['#Z', 'DD-00X'] # or []
   domain: ['memory', 'agents']
   discovered: 2025-11-18
   ---
   ```

4. **Write content**:

   ```markdown
   # Flaw #22: Your Flaw Title

   **Status**: 🔴 ACTIVE
   **Priority**: High
   **Impact**: Brief impact description
   **Phase**: Phase 2 (Months 3-4)

   ---

   ## Problem Description

   [Detailed description...]

   ## Recommended Solution

   [Proposed fix...]

   ## Implementation Plan

   [Steps to resolve...]
   ```

5. **Regenerate INDEX.md**:

   ```bash
   python generate_index.py
   ```

6. **Update docs**:
   - Add to [DEPENDENCIES.md](DEPENDENCIES.md) if it blocks/depends on other flaws
   - Add to [ROADMAP.md](ROADMAP.md) in appropriate phase

### Resolving a Flaw

**Recommended**: Use automated script (handles frontmatter, file move, reference updates, INDEX regeneration)

```bash
# Resolved by design decision
python resolve_flaw.py 22 --dd DD-013

# Resolved by direct fix
python resolve_flaw.py 22 --desc "Added input validation"
```

See [RESOLVING.md](RESOLVING.md) for complete guide, examples, and troubleshooting.

**Manual process** (if needed):

1. **Update frontmatter**:

   ```yaml
   status: resolved
   resolved: 2025-11-20
   resolution: DD-010 Your Solution Name
   ```

2. **Move file**: `mv active/22-flaw-name.md resolved/22-flaw-name.md`

3. **Update content**: Add resolution summary at top

4. **Update all path references**: Find/replace `design-flaws/active/22-` → `design-flaws/resolved/22-` across repo

5. **Regenerate INDEX.md**: `python generate_index.py`

6. **Update dependencies**: Check [DEPENDENCIES.md](DEPENDENCIES.md) and [ROADMAP.md](ROADMAP.md)

### Changing Flaw Priority

1. **Update frontmatter** in flaw file:

   ```yaml
   priority: critical # changed from high
   ```

2. **Regenerate INDEX.md**:

   ```bash
   python generate_index.py
   ```

3. **Update [ROADMAP.md](ROADMAP.md)** if phase changed

### Regenerating INDEX.md

The `generate_index.py` script parses all flaw frontmatter and regenerates INDEX.md:

```bash
# From repo root
python docs/design-flaws/generate_index.py

# Or make it automatic
# Add to .git/hooks/pre-commit:
python docs/design-flaws/generate_index.py && git add docs/design-flaws/INDEX.md
```

**What gets auto-generated:**

- At a Glance stats
- Priority tables (critical/high/medium/low)
- Resolved flaws by phase
- Domain view groupings
- Quick filters (phase/effort/dependencies)

**What's manual:**

- [DEPENDENCIES.md](DEPENDENCIES.md) - dependency graph visualization
- [ROADMAP.md](ROADMAP.md) - phase descriptions and milestones
- This [README.md](README.md) - navigation guide

---

## Migration Notes

**Old Structure** (pre-2025-11-18):

- `PRIORITY.md` - 594 lines, combined priority/dependencies/roadmap
- `00-SUMMARY.md` - outdated summary table
- Active flaws in root, no frontmatter

**New Structure** (post-2025-11-18):

- [INDEX.md](INDEX.md) - Priority & domain views (~250 lines)
- [DEPENDENCIES.md](DEPENDENCIES.md) - Dependency graph & blocking analysis (~150 lines)
- [ROADMAP.md](ROADMAP.md) - Phase timeline (~150 lines)
- All flaws have YAML frontmatter
- Active flaws in `active/`, resolved in `resolved/`
- Old files moved to `../archive/design-flaws/` (centralized archive)

**Benefits:**

- Scalable to 50+ flaws (collapsible sections)
- Programmatically queryable (frontmatter)
- Multiple navigation views (priority/timeline/domain/dependency)
- Single source of truth (frontmatter → INDEX.md via script)

---

## Related Documentation

- [../architecture/](../architecture/) - System architecture docs
- [../learning/](../learning/) - Learning systems specs
- [../operations/](../operations/) - Operational procedures
- [../design-decisions/](../design-decisions/) - Resolution documents (DD-XXX)
- [../implementation/01-roadmap.md](../implementation/01-roadmap.md) - Overall project timeline

---

**Questions?** Check [INDEX.md](INDEX.md) for quick navigation or [DEPENDENCIES.md](DEPENDENCIES.md) for dependency relationships.

**Last Updated**: 2025-11-18
