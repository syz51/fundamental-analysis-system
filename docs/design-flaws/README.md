# Design Flaws

Documentation of design issues discovered during system architecture development, with resolutions and implementation tracking.

---

## Overview

This folder contains **24 documented design flaws** identified through comprehensive architecture reviews. Each flaw is tracked with priority, dependencies, resolution status, and implementation details.

**Current Stats** (as of 2025-11-18):

- **Active**: 0 flaws (all resolved or deferred)
- **Resolved**: 24 flaws (through design decisions DD-001 through DD-021)
- **Deferred**: 3 flaws (moved to future/ for consideration in later phases)
- **Minor Issues**: 6 low-priority clarifications

---

## Structure

```text
docs/design-flaws/
├── INDEX.md                # Central navigation (start here!)
├── STATUS.md               # Phase-by-phase blocker tracking
├── README.md               # This file - how to navigate
├── RESOLVING.md            # Guide for resolving flaws (using script)
├── generate_index.py       # Auto-generates INDEX.md
├── resolve_flaw.py         # Auto-resolve script (moves, updates refs)
├── MINOR-ISSUES.md         # Low-priority clarifications
│
├── active/                 # Active flaws (0 files - all resolved!)
│   └── NN-flaw-name.md
│
├── future/                 # Deferred flaws (3 files)
│   └── NN-flaw-name.md
│
└── resolved/               # Resolved flaws (24 files)
    └── NN-flaw-name.md

docs/archive/design-flaws/  # Deprecated files (moved 2025-11-18)
├── 00-SUMMARY.md           # → see INDEX.md
├── PRIORITY.md             # → see INDEX.md, STATUS.md
├── DEPENDENCIES.md         # → see INDEX.md, STATUS.md
└── ROADMAP.md              # → see STATUS.md, implementation/01-roadmap.md
```

### File Naming Convention

- **Active flaws**: `active/NN-short-name.md`
- **Resolved flaws**: `resolved/NN-short-name.md`
- **Deferred flaws**: `future/NN-short-name.md`
- **Numbering**: Flaws numbered #1-26 in discovery order (some gaps for deferred flaws)

---

## How to Navigate

### Start Here: What's Your Goal?

**I want to...**

| Goal                            | Go To                                                                         |
| ------------------------------- | ----------------------------------------------------------------------------- |
| See all flaws at a glance       | [INDEX.md](INDEX.md) - Quick stats & priority view                            |
| Track phase blockers            | [STATUS.md](STATUS.md) - Phase-by-phase blocker tracking                      |
| Plan implementation timeline    | [STATUS.md](STATUS.md) or [01-roadmap.md](../implementation/01-roadmap.md)    |
| Find flaws in a specific domain | [INDEX.md § Domain View](INDEX.md#-domain-view) (memory/learning/agents/etc.) |
| Find flaws in a specific phase  | [INDEX.md § Quick Filters](INDEX.md#-quick-filters) or [STATUS.md](STATUS.md) |
| Find quick wins (<3 weeks)      | [INDEX.md § By Effort](INDEX.md#by-effort)                                    |
| Understand flaw frontmatter     | [Frontmatter Schema](#frontmatter-schema) below                               |
| Add a new flaw                  | [Maintenance § Adding Flaws](#adding-a-new-flaw) below                        |
| Resolve a flaw                  | [RESOLVING.md](RESOLVING.md) - Automated script guide                         |

### Navigation by View

**Priority View** → [INDEX.md](INDEX.md)

- All 24 flaws resolved or deferred to future/
- 3 flaws deferred to future phases
- See INDEX.md for complete historical priority breakdown

**Timeline View** → [STATUS.md](STATUS.md) or [implementation/01-roadmap.md](../implementation/01-roadmap.md)

- All phases complete or deferred
- STATUS.md tracks phase-by-phase blocker resolution
- implementation/01-roadmap.md for overall project timeline

**Domain View** → [INDEX.md § Domain View](INDEX.md#-domain-view)

- Memory System
- Learning System
- Agent System
- Data System
- Human Gates
- Architecture

See INDEX.md for complete domain breakdown and flaw counts.

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
flaw_id: 13 # Integer: Flaw number (1-26)
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
| `flaw_id`       | int        | ✅       | Unique flaw number (1-26)                                     |
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
   - Update [STATUS.md](STATUS.md) if it affects phase blockers

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

6. **Update dependencies**: Check [STATUS.md](STATUS.md)

### Changing Flaw Priority

1. **Update frontmatter** in flaw file:

   ```yaml
   priority: critical # changed from high
   ```

2. **Regenerate INDEX.md**:

   ```bash
   python generate_index.py
   ```

3. **Update [STATUS.md](STATUS.md)** if phase changed

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

- [STATUS.md](STATUS.md) - phase blocker tracking
- This [README.md](README.md) - navigation guide

---

## Migration Notes

**Old Structure** (pre-2025-11-18):

- `PRIORITY.md` - 594 lines, combined priority/dependencies/roadmap
- `00-SUMMARY.md` - outdated summary table
- Active flaws in root, no frontmatter

**New Structure** (post-2025-11-18):

- [INDEX.md](INDEX.md) - Priority & domain views (~250 lines)
- [STATUS.md](STATUS.md) - Phase blocker tracking (~140 lines)
- All flaws have YAML frontmatter
- Active flaws in `active/` (now 0), resolved in `resolved/` (24 files), deferred in `future/` (3 files)
- Old files moved to `../archive/design-flaws/` (centralized archive)
- DEPENDENCIES.md & ROADMAP.md archived (info in STATUS.md & implementation/01-roadmap.md)

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

**Questions?** Check [INDEX.md](INDEX.md) for quick navigation or [STATUS.md](STATUS.md) for phase blocker tracking.

**Last Updated**: 2025-11-18
