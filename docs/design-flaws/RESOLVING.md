# Resolving Design Flaws

Guide for marking design flaws as resolved using `resolve_flaw.py`.

## Quick Start

```bash
# Resolved by design decision (auto-infers description from DD title)
python resolve_flaw.py 12 --dd DD-013

# Resolved by direct fix (manual description required)
python resolve_flaw.py 5 --desc "Added input validation"

# Override auto-inferred description
python resolve_flaw.py 12 --dd DD-013 --desc "Custom text"

# Skip confirmation prompt
python resolve_flaw.py 12 --dd DD-013 --yes

# Specify custom date
python resolve_flaw.py 12 --dd DD-013 --date 2025-11-15

# Partially-resolved flaw (already marked, just move and update refs)
python resolve_flaw.py 12 --dd DD-013  # Preserves existing data

# Force overwrite all existing resolution data
python resolve_flaw.py 12 --dd DD-013 --force
```

## Arguments

| Argument            | Required | Description                                          |
| ------------------- | -------- | ---------------------------------------------------- |
| `N`                 | Yes      | Flaw ID number                                       |
| `--dd DD-XXX`       | \*       | Design decision that resolves flaw                   |
| `--desc "text"`     | \*       | Resolution description                               |
| `--date YYYY-MM-DD` | No       | Resolution date (defaults to today)                  |
| `--yes`             | No       | Skip confirmation prompt                             |
| `--force`           | No       | Force overwrite existing resolution data             |
| `--force-template`  | No       | Force insert template even if section already exists |

\* Must provide either `--dd` or `--desc` (or both), unless flaw already has resolution data

## What Script Does Automatically

1. **Updates frontmatter** (smart preservation):

   - `status: active` → `status: resolved`
   - Adds `resolved: YYYY-MM-DD` (preserves existing unless `--date` or `--force`)
   - Adds `resolution: "text"` (preserves existing unless `--desc`/`--dd` or `--force`)

2. **Moves file**: `active/NN-name.md` → `resolved/NN-name.md`

3. **Updates path references**: All `design-flaws/active/NN-` links → `design-flaws/resolved/NN-` across entire repo

4. **Inserts resolution template**: Adds resolution section at top of markdown body (skips if already exists unless `--force-template`)

5. **Regenerates INDEX.md**: Runs `generate_index.py` automatically

### Smart Preservation

Script detects partially-resolved flaws and preserves existing data:

- If `status: resolved` already set → preserves, shows warning
- If `resolved:` date already set → preserves unless `--date` or `--force`
- If `resolution:` text already set → preserves unless `--desc`/`--dd` or `--force`
- If resolution section already in body → skips template unless `--force-template`

## Manual Steps Required

After running script, you must:

### 1. Fill in Resolution Content

Edit `resolved/NN-name.md`:

**Important**: Remove `[TODO: ...]` placeholders from template and replace with actual content.

**If resolved by DD:**

```markdown
## Resolution Summary

**Status**: RESOLVED ✅
**Resolution**: DD-013 (see design decision document)
**Reference**: [DD-013: Title](../../design-decisions/DD-013_TITLE.md)

### How DD-013 Resolves This Flaw

[TODO: Explain specific aspects of DD that address the flaw] ← REMOVE THIS LINE

Example (replace TODO with actual content like this):

- DD-013 introduces lifecycle states that prevent premature deletion
- Archive API enforces 90-day retention policy
- Automated migration handles transition from active to archived
```

**If direct fix:**

```markdown
## Resolution Summary

**Status**: RESOLVED ✅
**Resolution**: Direct implementation fix

### Implementation Details

[TODO: Describe what was implemented to resolve this flaw] ← REMOVE THIS LINE

Example (replace TODO with actual content like this):

- Added zod validation schema to form handler (src/forms/validate.ts:45)
- Prevents empty submissions
- Returns user-friendly error messages
```

### 2. Update DEPENDENCIES.md

Check if this flaw was blocking others:

```bash
# Search for this flaw in DEPENDENCIES.md
grep "#N" DEPENDENCIES.md
```

If found:

- Remove from "Blocks" column of dependency table
- Update "Currently Blocked" count
- Recalculate critical path if needed

### 3. Update ROADMAP.md

Update phase progress:

```markdown
# Before

**Phase 2**: 3 of 8 complete

# After (if this was Phase 2 flaw)

**Phase 2**: 4 of 8 complete
```

Remove from active flaw lists, add note if affects critical path.

### 4. Review Changes

Before committing:

```bash
# View what changed
git status
git diff

# Check specific files
cat resolved/NN-name.md  # Verify resolution template inserted
cat INDEX.md  # Verify flaw moved to resolved section
```

## Validation Checklist

Before running script:

- [ ] Flaw exists in `active/` directory
- [ ] If using `--dd`, design decision file exists in `docs/design-decisions/`
- [ ] If using `--desc`, description accurately describes resolution
- [ ] No other active flaws depend on this flaw (check DEPENDENCIES.md)

After running script:

- [ ] File moved from `active/` to `resolved/`
- [ ] Frontmatter updated correctly (status, resolved, resolution)
- [ ] Resolution template inserted in markdown body
- [ ] All path references updated (check files listed in output)
- [ ] INDEX.md regenerated successfully
- [ ] DEPENDENCIES.md updated
- [ ] ROADMAP.md updated
- [ ] Resolution content filled in (not just template)
- [ ] TODO placeholders removed from resolution section

## Common Issues

### "Flaw not found in active/"

**Cause**: Flaw already resolved or wrong ID

**Fix**:

```bash
ls active/  # Check what's in active
ls resolved/  # Check if already resolved
```

### "Design decision DD-XXX not found"

**Cause**: DD file doesn't exist or wrong ID

**Fix**:

```bash
ls docs/design-decisions/  # Check available DDs
# Create DD first if needed
```

### "Must provide either --dd or --desc"

**Cause**: Forgot both arguments

**Fix**: Add at least one:

```bash
python resolve_flaw.py 12 --dd DD-013  # OR
python resolve_flaw.py 12 --desc "Fixed via validation"
```

### References not updated

**Cause**: Script uses exact filename match

**Fix**: Manually search and update:

```bash
grep -r "design-flaws/active/12-" docs/
# Update manually if script missed any
```

### INDEX.md regeneration failed

**Cause**: Python dependencies missing or syntax error in flaw files

**Fix**:

```bash
cd docs/design-flaws
python generate_index.py  # Run manually to see error
```

### Partially-resolved flaw (already marked in frontmatter)

**Cause**: Flaw frontmatter already has `status: resolved` but file not moved

**Behavior**: Script preserves existing data, shows warning

**Example**:

```bash
$ python resolve_flaw.py 12 --dd DD-013

⚠️  WARNING: Flaw already partially resolved

Existing values:
  - Status: resolved
  - Resolved date: 2025-11-17
  - Resolution: DD-013: Archive lifecycle

These values will be preserved unless explicitly overridden
Use --force to overwrite all existing values

Changes to be made:
  - Move: active/12-archive-lifecycle.md → resolved/12-archive-lifecycle.md
  - Status: resolved (already resolved, preserving)
  - Resolution: DD-013: Archive lifecycle (preserving)
  - Resolved date: 2025-11-17 (preserving)
```

**Fix**: Just proceed - script will move file and update references while preserving data

**Override**: Use `--force` to overwrite existing values or `--desc`/`--date` to override specific fields

## Examples

### Example 1: DD Resolution

```bash
$ python resolve_flaw.py 12 --dd DD-013

============================================================
Resolving Flaw #12: Archive Lifecycle Management
============================================================

Changes to be made:
  - Move: active/12-archive-lifecycle.md → resolved/12-archive-lifecycle.md
  - Status: active → resolved
  - Resolution: DD-013: Archive Lifecycle Management
  - Resolved date: 2025-11-18

  Path references to update (3 files):
    - docs/design-decisions/DD-013.md (2 references)
    - docs/architecture/01-system-overview.md (1 reference)

  Will regenerate: INDEX.md

Manual steps required after:
  - Fill in resolution content in resolved/12-archive-lifecycle.md
  - Update DEPENDENCIES.md
  - Update ROADMAP.md

============================================================
Proceed? [y/N] y

✅ Moved 12-archive-lifecycle.md to resolved/
✅ Updated 2 file(s) with new path

Regenerating INDEX.md...
✅ INDEX.md regenerated

============================================================
✅ Flaw #12 marked as resolved
============================================================

Next steps:
  1. Edit resolved/12-archive-lifecycle.md to add resolution details
  2. Update DEPENDENCIES.md
  3. Update ROADMAP.md
  4. Review and commit changes
```

### Example 2: Partially-Resolved Flaw

Flaw already marked in frontmatter but not moved:

```bash
$ python resolve_flaw.py 12 --dd DD-013

============================================================
Resolving Flaw #12: Archive Lifecycle Management
============================================================

⚠️  WARNING: Flaw already partially resolved

Existing values:
  - Status: resolved
  - Resolved date: 2025-11-17
  - Resolution: DD-013: Archive lifecycle

These values will be preserved unless explicitly overridden
Use --force to overwrite all existing values

Changes to be made:
  - Move: active/12-archive-lifecycle.md → resolved/12-archive-lifecycle.md
  - Status: resolved (already resolved, preserving)
  - Resolution: DD-013: Archive lifecycle (preserving)
  - Resolved date: 2025-11-17 (preserving)

  Path references to update (2 files):
    - docs/design-decisions/DD-013.md (1 reference)

  Will regenerate: INDEX.md

  Note: Resolution section already exists, skipping template insertion
        Use --force-template to override

Manual steps required after:
  - Fill in resolution content in resolved/12-archive-lifecycle.md
  - Update DEPENDENCIES.md
  - Update ROADMAP.md

============================================================
Proceed? [y/N] y

✅ Moved 12-archive-lifecycle.md to resolved/
✅ Updated 1 file(s) with new path

Regenerating INDEX.md...
✅ INDEX.md regenerated

============================================================
✅ Flaw #12 marked as resolved
============================================================
```

### Example 3: Direct Fix

```bash
$ python resolve_flaw.py 5 --desc "Added zod validation to form inputs" --yes

============================================================
Resolving Flaw #5: Missing Input Validation
============================================================

Changes to be made:
  - Move: active/05-input-validation.md → resolved/05-input-validation.md
  - Status: active → resolved
  - Resolution: Added zod validation to form inputs
  - Resolved date: 2025-11-18

  No path references found to update

  Will regenerate: INDEX.md

Manual steps required after:
  - Fill in resolution content in resolved/05-input-validation.md
  - Update DEPENDENCIES.md
  - Update ROADMAP.md

✅ Moved 05-input-validation.md to resolved/
✅ INDEX.md regenerated

============================================================
✅ Flaw #5 marked as resolved
============================================================

Next steps:
  1. Edit resolved/05-input-validation.md to add resolution details
  2. Update DEPENDENCIES.md
  3. Update ROADMAP.md
  4. Review and commit changes
```

## Workflow Summary

```text
1. Resolve flaw (implement DD or direct fix)
   ↓
2. Run script: python resolve_flaw.py N --dd DD-XXX [--yes]
   ↓
3. Fill in resolution content in resolved/NN-name.md
   ↓
4. Update DEPENDENCIES.md (remove blocks)
   ↓
5. Update ROADMAP.md (phase progress)
   ↓
6. Review changes: git diff
   ↓
7. Commit: git add . && git commit -m "Resolve flaw #N via DD-XXX"
```

## See Also

- [INDEX.md](INDEX.md) - View all active/resolved flaws
- [DEPENDENCIES.md](DEPENDENCIES.md) - Dependency graph
- [ROADMAP.md](ROADMAP.md) - Phase timeline
- [README.md](README.md) - Design flaws overview
- [generate_index.py](generate_index.py) - Index generation script
