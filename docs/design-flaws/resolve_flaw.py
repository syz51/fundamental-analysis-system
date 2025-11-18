#!/usr/bin/env python3
"""
Mark a design flaw as resolved.

Usage:
    python resolve_flaw.py N [--dd DD-XXX] [--desc "text"] [--date YYYY-MM-DD] [--yes]

Examples:
    # Resolved by design decision (auto-infer description from DD title)
    python resolve_flaw.py 12 --dd DD-013

    # Resolved by direct fix (provide description)
    python resolve_flaw.py 5 --desc "Added input validation to form handler"

    # Override auto-inferred description
    python resolve_flaw.py 12 --dd DD-013 --desc "Custom description"

Operations:
    1. Updates frontmatter (status, resolved date, resolution text)
    2. Moves file from active/ to resolved/
    3. Updates all path references across docs
    4. Inserts resolution section template
    5. Regenerates INDEX.md

Manual steps required after:
    - Fill in resolution content in the markdown body
    - Update DEPENDENCIES.md
    - Update ROADMAP.md
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import date, datetime
import yaml
import subprocess


DESIGN_FLAWS_DIR = Path(__file__).parent
DOCS_DIR = DESIGN_FLAWS_DIR.parent
REPO_ROOT = DOCS_DIR.parent


def parse_frontmatter(filepath):
    """Extract YAML frontmatter from markdown file."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
    if match:
        try:
            metadata = yaml.safe_load(match.group(1))
            body = match.group(2)
            return metadata, body
        except yaml.YAMLError as e:
            print(f"Error parsing frontmatter in {filepath}: {e}")
            sys.exit(1)
    else:
        print(f"Error: No frontmatter found in {filepath}")
        sys.exit(1)


def write_markdown(filepath, frontmatter, body):
    """Write frontmatter and body to markdown file."""
    frontmatter_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    content = f"---\n{frontmatter_yaml}---\n{body}"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def get_dd_info(dd_id):
    """Get title and filename from design decision document.

    Returns:
        tuple: (title, filename) or raises SystemExit if not found
    """
    dd_files = list((DOCS_DIR / "design-decisions").glob(f"{dd_id}*.md"))
    if not dd_files:
        print(f"Error: Design decision {dd_id} not found in docs/design-decisions/")
        sys.exit(1)

    # Warn if multiple matches found
    if len(dd_files) > 1:
        print(f"Warning: Multiple DD files found for {dd_id}:")
        for f in dd_files:
            print(f"  - {f.name}")
        print(f"Using: {dd_files[0].name}")

    dd_file = dd_files[0]
    dd_filename = dd_file.name

    # Try to get title from frontmatter first
    with open(dd_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if has frontmatter
    if content.startswith("---\n"):
        metadata, _ = parse_frontmatter(dd_file)
        title = metadata.get("title", dd_id)
        return title, dd_filename

    # Otherwise extract from first H1 heading
    match = re.search(r"^# (.+)$", content, re.MULTILINE)
    if match:
        # Extract title, removing the "DD-XXX: " prefix if present
        title = match.group(1)
        if title.startswith(f"{dd_id}:"):
            title = title[len(dd_id) + 1 :].strip()
        return title, dd_filename

    return dd_id, dd_filename


def find_references(flaw_filename):
    """Find all references to this flaw across the repo."""
    references = []

    # Search for path references
    pattern = f"design-flaws/active/{flaw_filename}"

    # Search in all markdown files
    for md_file in REPO_ROOT.glob("**/*.md"):
        if md_file.is_file() and ".git" not in str(md_file):
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
                if pattern in content:
                    count = content.count(pattern)
                    references.append((md_file, count))

    return references


def update_references(flaw_filename):
    """Update all references from active/ to resolved/."""
    old_pattern = f"design-flaws/active/{flaw_filename}"
    new_pattern = f"design-flaws/resolved/{flaw_filename}"

    updated_files = []

    for md_file in REPO_ROOT.glob("**/*.md"):
        if md_file.is_file() and ".git" not in str(md_file):
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

            if old_pattern in content:
                new_content = content.replace(old_pattern, new_pattern)
                with open(md_file, "w", encoding="utf-8") as f:
                    f.write(new_content)
                updated_files.append(md_file)

    return updated_files


def create_resolution_template(dd_id=None, dd_filename=None):
    """Create resolution section template based on whether DD is provided."""
    if dd_id:
        # Use actual filename if provided, otherwise construct reference
        if dd_filename:
            dd_ref = f"[{dd_id}](../../design-decisions/{dd_filename})"
        else:
            dd_ref = f"[{dd_id}](../../design-decisions/)"

        return f"""
## Resolution Summary

**Status**: RESOLVED ✅
**Resolution**: {dd_id} (see design decision document)
**Reference**: {dd_ref}

### How {dd_id} Resolves This Flaw

[TODO: Explain how the design decision addresses this flaw]

---

"""
    else:
        return """
## Resolution Summary

**Status**: RESOLVED ✅
**Resolution**: Direct implementation fix

### Implementation Details

[TODO: Describe what was implemented to resolve this flaw]

---

"""


def main():
    parser = argparse.ArgumentParser(description="Mark a design flaw as resolved")
    parser.add_argument("flaw_id", type=int, help="Flaw ID number")
    parser.add_argument("--dd", help="Design decision ID (e.g., DD-013)")
    parser.add_argument("--desc", help="Resolution description")
    parser.add_argument(
        "--date", help="Resolution date (YYYY-MM-DD, defaults to today)"
    )
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    parser.add_argument(
        "--force", action="store_true", help="Force overwrite existing resolution data"
    )
    parser.add_argument(
        "--force-template",
        action="store_true",
        help="Force insert template even if resolution section exists",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.dd and not args.desc:
        print("Error: Must provide either --dd or --desc")
        sys.exit(1)

    # Validate date format if provided
    if args.date:
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print("Error: Invalid date format. Use YYYY-MM-DD (e.g., 2025-11-18)")
            sys.exit(1)

    # Find flaw file in active/
    active_dir = DESIGN_FLAWS_DIR / "active"
    flaw_files = list(active_dir.glob(f"{args.flaw_id:02d}-*.md"))

    if not flaw_files:
        print(f"Error: Flaw #{args.flaw_id} not found in active/")
        sys.exit(1)

    flaw_file = flaw_files[0]
    flaw_filename = flaw_file.name

    # Parse current frontmatter
    frontmatter, body = parse_frontmatter(flaw_file)
    flaw_title = frontmatter.get("title", f"Flaw #{args.flaw_id}")

    # Check if already partially or fully resolved
    already_resolved = frontmatter.get("status") == "resolved"
    has_resolved_date = "resolved" in frontmatter and frontmatter.get("resolved")
    has_resolution_text = "resolution" in frontmatter and frontmatter.get("resolution")
    has_resolution_section = "## Resolution Summary" in body

    # Detect conflicts
    has_conflicts = already_resolved or has_resolved_date or has_resolution_text

    # Get DD info if provided (for resolution text and template link)
    dd_title = None
    dd_filename = None
    if args.dd:
        dd_title, dd_filename = get_dd_info(args.dd)

    # Determine resolution text (preserve existing unless overridden or force)
    if has_resolution_text and not (args.desc or args.dd) and not args.force:
        # Preserve existing resolution text
        resolution_text = frontmatter.get("resolution")
    elif args.desc:
        resolution_text = args.desc
        if args.dd and args.dd not in args.desc:
            resolution_text = f"{args.dd}: {args.desc}"
    elif args.dd:
        resolution_text = f"{args.dd}: {dd_title}"
    else:
        print("Error: Unable to determine resolution text")
        sys.exit(1)

    # Determine resolved date (preserve existing unless overridden or force)
    if has_resolved_date and not args.date and not args.force:
        resolved_date = frontmatter.get("resolved")
    elif args.date:
        resolved_date = args.date
    else:
        resolved_date = date.today().isoformat()

    # Find all references
    references = find_references(flaw_filename)

    # Display what will change
    print(f"\n{'=' * 60}")
    print(f"Resolving Flaw #{args.flaw_id}: {flaw_title}")
    print(f"{'=' * 60}")

    # Show warnings if conflicts detected
    if has_conflicts and not args.force:
        print("\n⚠️  WARNING: Flaw already partially resolved")
        print("\nExisting values:")
        if already_resolved:
            print(f"  - Status: {frontmatter.get('status')}")
        if has_resolved_date:
            print(f"  - Resolved date: {frontmatter.get('resolved')}")
        if has_resolution_text:
            print(f"  - Resolution: {frontmatter.get('resolution')}")
        if has_resolution_section:
            print("  - Body: Contains resolution section")
        print("\nThese values will be preserved unless explicitly overridden")
        print("Use --force to overwrite all existing values")
        print()

    print("\nChanges to be made:")
    print(f"  - Move: active/{flaw_filename} → resolved/{flaw_filename}")

    # Show what's changing vs preserved
    current_status = frontmatter.get("status", "unknown")
    if current_status == "resolved":
        print(f"  - Status: {current_status} (already resolved, preserving)")
    else:
        print(f"  - Status: {current_status} → resolved")

    current_resolution = frontmatter.get("resolution")
    if has_resolution_text and not args.force and not (args.desc or args.dd):
        print(f"  - Resolution: {current_resolution} (preserving)")
    else:
        if current_resolution:
            print(f"  - Resolution: {current_resolution} → {resolution_text}")
        else:
            print(f"  - Resolution: {resolution_text}")

    current_date = frontmatter.get("resolved")
    if has_resolved_date and not args.force and not args.date:
        print(f"  - Resolved date: {current_date} (preserving)")
    else:
        if current_date:
            print(f"  - Resolved date: {current_date} → {resolved_date}")
        else:
            print(f"  - Resolved date: {resolved_date}")

    if references:
        print(f"\n  Path references to update ({len(references)} files):")
        for ref_file, count in references:
            rel_path = ref_file.relative_to(REPO_ROOT)
            print(f"    - {rel_path} ({count} reference{'s' if count > 1 else ''})")
    else:
        print("\n  No path references found to update")

    print("\n  Will regenerate: INDEX.md")
    print("\nManual steps required after:")
    print(f"  - Fill in resolution content in resolved/{flaw_filename}")
    print("  - Update DEPENDENCIES.md")
    print("  - Update ROADMAP.md")

    # Confirmation
    if not args.yes:
        print(f"\n{'=' * 60}")
        response = input("Proceed? [y/N] ")
        if response.lower() not in ["y", "yes"]:
            print("Aborted")
            sys.exit(0)

    # Update frontmatter
    frontmatter["status"] = "resolved"
    frontmatter["resolved"] = resolved_date
    frontmatter["resolution"] = resolution_text

    # Insert resolution template only if not already present (or force)
    if has_resolution_section and not args.force_template:
        # Skip template insertion, keep existing body
        new_body = body
        print(
            "\n  Note: Resolution section already exists, skipping template insertion"
        )
        print("        Use --force-template to override")
    else:
        # Insert resolution template at top of body
        resolution_template = create_resolution_template(args.dd, dd_filename)

        # Remove existing "# Flaw #N: Title" if present and add it after template
        body_lines = body.strip().split("\n")
        if body_lines and body_lines[0].startswith("# Flaw #"):
            title_line = body_lines[0]
            rest_of_body = "\n".join(body_lines[1:]).lstrip()
            new_body = f"{title_line}\n{resolution_template}\n{rest_of_body}"
        else:
            new_body = f"{resolution_template}\n{body.strip()}"

        if has_resolution_section and args.force_template:
            print("\n  Note: Forcing template insertion despite existing section")

    # Write updated file to active/ first
    write_markdown(flaw_file, frontmatter, new_body)

    # Move to resolved/
    resolved_dir = DESIGN_FLAWS_DIR / "resolved"
    resolved_dir.mkdir(exist_ok=True)
    new_path = resolved_dir / flaw_filename

    flaw_file.rename(new_path)
    print(f"\n✅ Moved {flaw_filename} to resolved/")

    # Update references
    if references:
        updated = update_references(flaw_filename)
        print(f"✅ Updated {len(updated)} file(s) with new path")

    # Regenerate INDEX.md
    print("\nRegenerating INDEX.md...")
    try:
        subprocess.run(
            ["python", "generate_index.py"],
            cwd=DESIGN_FLAWS_DIR,
            check=True,
            capture_output=True,
        )
        print("✅ INDEX.md regenerated")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to regenerate INDEX.md: {e}")
        print("Run 'python generate_index.py' manually")

    print(f"\n{'=' * 60}")
    print(f"✅ Flaw #{args.flaw_id} marked as resolved")
    print(f"{'=' * 60}")
    print("\nNext steps:")
    print(f"  1. Edit resolved/{flaw_filename} to add resolution details")
    print("  2. Update DEPENDENCIES.md")
    print("  3. Update ROADMAP.md")
    print("  4. Review and commit changes")


if __name__ == "__main__":
    main()
