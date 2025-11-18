#!/usr/bin/env python3
"""
Generate INDEX.md from flaw frontmatter.

Usage:
    python generate_index.py

Parses YAML frontmatter from all flaw files and generates INDEX.md with:
- Quick stats
- Priority tables (critical/high/medium/low)
- Resolved flaws by phase
- Domain view
- Quick filters (phase/effort/dependencies)
"""

import re
from pathlib import Path
from collections import defaultdict
import yaml

DESIGN_FLAWS_DIR = Path(__file__).parent


def parse_frontmatter(filepath):
    """Extract YAML frontmatter from a markdown file."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract YAML frontmatter
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if match:
        try:
            metadata = yaml.safe_load(match.group(1))
            metadata["filepath"] = filepath
            return metadata
        except yaml.YAMLError as e:
            print(f"Warning: Could not parse frontmatter in {filepath}: {e}")
            return None
    return None


def get_all_flaws():
    """Get metadata for all flaw files."""
    flaws = []

    # Active flaws (active/ directory)
    active_dir = DESIGN_FLAWS_DIR / "active"
    if active_dir.exists():
        for filepath in active_dir.glob("*.md"):
            metadata = parse_frontmatter(filepath)
            if metadata:
                flaws.append(metadata)

    # Resolved flaws (resolved/ directory)
    resolved_dir = DESIGN_FLAWS_DIR / "resolved"
    if resolved_dir.exists():
        for filepath in resolved_dir.glob("*.md"):
            metadata = parse_frontmatter(filepath)
            if metadata:
                flaws.append(metadata)

    # Future flaws (future/ directory)
    future_dir = DESIGN_FLAWS_DIR / "future"
    if future_dir.exists():
        for filepath in future_dir.glob("*.md"):
            metadata = parse_frontmatter(filepath)
            if metadata:
                flaws.append(metadata)

    return sorted(flaws, key=lambda f: f["flaw_id"])


def categorize_flaws(flaws):
    """Categorize flaws by status and priority."""
    active = [f for f in flaws if f["status"] == "active"]
    resolved = [f for f in flaws if f["status"] == "resolved"]
    future = [f for f in flaws if f["status"] == "future"]

    # Further categorize active by priority
    critical = [f for f in active if f["priority"] == "critical"]
    high = [f for f in active if f["priority"] == "high"]
    medium = [f for f in active if f["priority"] == "medium"]
    low = [f for f in active if f["priority"] == "low"]

    return {
        "active": active,
        "resolved": resolved,
        "future": future,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
    }


def get_relative_path(filepath):
    """Get relative path from design-flaws dir."""
    try:
        return Path(filepath).relative_to(DESIGN_FLAWS_DIR)
    except ValueError:
        return Path(filepath).name


def format_effort(weeks):
    """Format effort in weeks."""
    return f"{weeks}w"


def format_dependencies(deps):
    """Format dependencies list."""
    if not deps:
        return "-"
    return ", ".join(deps)


def generate_index(flaws):
    """Generate INDEX.md content."""
    cats = categorize_flaws(flaws)

    content = []
    content.append("# Design Flaws Index")
    content.append("")
    content.append("## At a Glance")
    content.append("")
    content.append(f"- **Total**: {len(flaws)} flaws + 6 minor issues")
    content.append(
        f"- **Active**: {len(cats['active'])} ({len(cats['critical'])} critical, {len(cats['high'])} high, {len(cats['medium'])} medium, {len(cats['low'])} low)"
    )
    content.append(f"- **Resolved**: {len(cats['resolved'])}")
    content.append(f"- **Future**: {len(cats['future'])}")
    content.append("")
    content.append("---")
    content.append("")

    # Critical flaws
    content.append("## 🚨 Critical Active Flaws (%d)" % len(cats["critical"]))
    content.append("")
    content.append("Blocks MVP or production deployment:")
    content.append("")
    content.append("| # | Flaw | Impact | Phase | Effort | Dependencies |")
    content.append("|---|------|--------|-------|--------|--------------|")
    for f in cats["critical"]:
        path = get_relative_path(f["filepath"])
        deps = format_dependencies(f.get("depends_on", []))
        content.append(
            f"| [{f['flaw_id']}]({path}) | {f['title']} | {f['impact']} | {f['phase']} | {format_effort(f['effort_weeks'])} | {deps} |"
        )
    content.append("")
    content.append("---")
    content.append("")

    # High priority
    content.append("## High Priority Active Flaws (%d)" % len(cats["high"]))
    content.append("")
    content.append("<details>")
    content.append("<summary><b>Should fix before MVP</b></summary>")
    content.append("")
    content.append("| # | Flaw | Impact | Phase | Effort | Dependencies |")
    content.append("|---|------|--------|-------|--------|--------------|")
    for f in cats["high"]:
        path = get_relative_path(f["filepath"])
        deps = format_dependencies(f.get("depends_on", []))
        content.append(
            f"| [{f['flaw_id']}]({path}) | {f['title']} | {f['impact']} | {f['phase']} | {format_effort(f['effort_weeks'])} | {deps} |"
        )
    content.append("")
    content.append("</details>")
    content.append("")
    content.append("---")
    content.append("")

    # Medium priority
    content.append("## Medium Priority (%d)" % len(cats["medium"]))
    content.append("")
    content.append("<details>")
    content.append("<summary><b>Post-MVP improvements</b></summary>")
    content.append("")
    content.append("| # | Flaw | Impact | Phase | Effort |")
    content.append("|---|------|--------|-------|--------|")
    for f in cats["medium"]:
        path = get_relative_path(f["filepath"])
        content.append(
            f"| [{f['flaw_id']}]({path}) | {f['title']} | {f['impact']} | {f['phase']} | {format_effort(f['effort_weeks'])} |"
        )
    content.append("")
    content.append("</details>")
    content.append("")
    content.append("---")
    content.append("")

    # Low Priority
    content.append("## Low Priority (%d)" % len(cats["low"]))
    content.append("")
    content.append("<details>")
    content.append("<summary><b>Future optimization</b></summary>")
    content.append("")
    content.append("| # | Flaw | Impact | Phase | Effort |")
    content.append("|---|------|--------|-------|--------|")
    for f in cats["low"]:
        path = get_relative_path(f["filepath"])
        content.append(
            f"| [{f['flaw_id']}]({path}) | {f['title']} | {f['impact']} | {f['phase']} | {format_effort(f['effort_weeks'])} |"
        )
    content.append("")
    content.append("</details>")
    content.append("")
    content.append("---")
    content.append("")

    # Future Flaws (stats only)
    content.append("## 🔮 Future Flaws (%d)" % len(cats["future"]))
    content.append("")
    content.append("Potential improvements tracked for future consideration:")
    content.append("")
    for f in cats["future"]:
        path = get_relative_path(f["filepath"])
        content.append(f"- [#{f['flaw_id']}]({path}) - {f['title']}")
    content.append("")
    content.append("---")
    content.append("")

    # Resolved by phase
    resolved_by_phase = defaultdict(list)
    for f in cats["resolved"]:
        phase = f["phase"]
        resolved_by_phase[phase].append(f)

    content.append("## ✅ Resolved Flaws by Phase (%d)" % len(cats["resolved"]))
    content.append("")
    phase_names = {
        1: "Foundation & Basic Memory",
        2: "Core Agents with Memory",
        3: "Advanced Memory Features",
        4: "Optimization & Learning",
        5: "Continuous Evolution",
    }

    for phase in sorted(
        resolved_by_phase.keys(), key=lambda p: (int(str(p).split("-")[0]), str(p))
    ):
        flaws_in_phase = resolved_by_phase[phase]
        phase_name = phase_names.get(phase, f"Phase {phase}")

        content.append("<details>")
        content.append(
            f"<summary><b>Phase {phase}: {phase_name} ({len(flaws_in_phase)} resolved)</b></summary>"
        )
        content.append("")
        content.append("| # | Flaw | Resolution | Completed |")
        content.append("|---|------|-----------|-----------|")
        for f in flaws_in_phase:
            path = get_relative_path(f["filepath"])
            resolution = f.get("resolution", "N/A")
            resolved_date = f.get("resolved", "N/A")
            content.append(
                f"| [{f['flaw_id']}]({path}) | {f['title']} | {resolution} | {resolved_date} |"
            )
        content.append("")
        content.append("</details>")
        content.append("")

    content.append("---")
    content.append("")

    # Domain view
    content.append("## 🏷️ Domain View")
    content.append("")
    content.append("Navigate by system component:")
    content.append("")

    # Collect flaws by domain
    flaws_by_domain = defaultdict(list)
    for f in flaws:
        domains = f.get("domain", [])
        if isinstance(domains, str):
            domains = [domains]
        for domain in domains:
            flaws_by_domain[domain].append(f)

    domain_names = {
        "memory": "Memory System",
        "learning": "Learning System",
        "agents": "Agent System",
        "data": "Data System",
        "human-gates": "Human Gates",
        "architecture": "Architecture",
    }

    for domain_key in [
        "memory",
        "learning",
        "agents",
        "data",
        "human-gates",
        "architecture",
    ]:
        if domain_key not in flaws_by_domain:
            continue

        domain_flaws = flaws_by_domain[domain_key]
        active_in_domain = [f for f in domain_flaws if f["status"] == "active"]
        resolved_in_domain = [f for f in domain_flaws if f["status"] == "resolved"]

        domain_name = domain_names.get(domain_key, domain_key.capitalize())
        content.append("<details>")
        content.append(
            f"<summary><b>{domain_name} ({len(domain_flaws)} flaws: {len(active_in_domain)} active, {len(resolved_in_domain)} resolved)</b></summary>"
        )
        content.append("")

        if active_in_domain:
            content.append("**Active:**")
            for f in sorted(active_in_domain, key=lambda x: x["flaw_id"]):
                path = get_relative_path(f["filepath"])
                priority_map = {"critical": "C", "high": "H", "medium": "M", "low": "L"}
                priority = priority_map.get(f["priority"], "?")
                content.append(
                    f"- [#{f['flaw_id']}]({path}) - {f['title']} ({priority}, Phase {f['phase']})"
                )
            content.append("")

        if resolved_in_domain:
            content.append("**Resolved:**")
            for f in sorted(resolved_in_domain, key=lambda x: x["flaw_id"]):
                path = get_relative_path(f["filepath"])
                content.append(f"- [#{f['flaw_id']}]({path})✅ - {f['title']}")
            content.append("")

        content.append("</details>")
        content.append("")

    content.append("---")
    content.append("")

    # Quick filters
    content.append("## 📊 Quick Filters")
    content.append("")

    # By phase
    content.append("### By Phase")
    content.append("")
    active_by_phase = defaultdict(list)
    for f in cats["active"]:
        phase = f["phase"]
        active_by_phase[phase].append(f)

    for phase in sorted(
        active_by_phase.keys(), key=lambda p: (int(str(p).split("-")[0]), str(p))
    ):
        flaws_in_phase = active_by_phase[phase]
        desc = phase_names.get(phase, f"Phase {phase}")
        content.append(f"**Phase {phase} ({desc}):** {len(flaws_in_phase)} active")
        for f in flaws_in_phase:
            path = get_relative_path(f["filepath"])
            priority_map = {"critical": "C", "high": "H", "medium": "M", "low": "L"}
            priority = priority_map.get(f["priority"], "?")
            content.append(
                f"- [{f['flaw_id']}]({path}) {f['title']} ({priority}, {format_effort(f['effort_weeks'])})"
            )
        content.append("")

    # By effort
    content.append("### By Effort")
    content.append("")
    quick_wins = [f for f in cats["active"] if f["effort_weeks"] < 3]
    medium_effort = [f for f in cats["active"] if 3 <= f["effort_weeks"] <= 5]
    large_effort = [f for f in cats["active"] if f["effort_weeks"] > 5]

    content.append(f"**Quick wins (<3 weeks):** {len(quick_wins)} flaws")
    for f in quick_wins:
        path = get_relative_path(f["filepath"])
        content.append(
            f"- [{f['flaw_id']}]({path}) - {format_effort(f['effort_weeks'])}"
        )
    content.append("")

    content.append(f"**Medium (3-5 weeks):** {len(medium_effort)} flaws")
    for f in medium_effort:
        path = get_relative_path(f["filepath"])
        content.append(
            f"- [{f['flaw_id']}]({path}) - {format_effort(f['effort_weeks'])}"
        )
    content.append("")

    content.append(f"**Large (>5 weeks):** {len(large_effort)} flaws")
    for f in large_effort:
        path = get_relative_path(f["filepath"])
        content.append(
            f"- [{f['flaw_id']}]({path}) - {format_effort(f['effort_weeks'])}"
        )
    content.append("")

    # By dependencies
    content.append("### By Dependencies")
    content.append("")
    unblocked = [f for f in cats["active"] if not f.get("depends_on")]
    one_dep = [f for f in cats["active"] if len(f.get("depends_on", [])) == 1]
    multi_dep = [f for f in cats["active"] if len(f.get("depends_on", [])) >= 2]

    content.append(f"**Unblocked (ready to start):** {len(unblocked)} flaws")
    for f in unblocked:
        path = get_relative_path(f["filepath"])
        content.append(f"- [{f['flaw_id']}]({path}) - No dependencies")
    content.append("")

    content.append(f"**Waiting on 1 dependency:** {len(one_dep)} flaws")
    for f in one_dep:
        path = get_relative_path(f["filepath"])
        deps = ", ".join(f.get("depends_on", []))
        content.append(f"- [{f['flaw_id']}]({path}) - {deps}")
    content.append("")

    content.append(f"**Waiting on 2+ dependencies:** {len(multi_dep)} flaws")
    for f in multi_dep:
        path = get_relative_path(f["filepath"])
        deps = ", ".join(f.get("depends_on", []))
        content.append(f"- [{f['flaw_id']}]({path}) - {deps}")
    content.append("")

    content.append("---")
    content.append("")

    # Footer
    content.append("## 🔗 Related Documentation")
    content.append("")
    content.append("- [README.md](README.md) - How to navigate and use this folder")
    content.append("- [STATUS.md](STATUS.md) - Current status and progress tracking")
    content.append("- [RESOLVING.md](RESOLVING.md) - Resolution workflow and guidelines")
    content.append("- [Minor Issues](resolved/MINOR-ISSUES.md) - 6 low-priority clarifications (all resolved 2025-11-18)")
    content.append(
        "- [Design Decisions](../design-decisions/) - DD-XXX resolution documents"
    )
    content.append("- [Implementation Roadmap](../implementation/01-roadmap.md) - Phase timeline")
    content.append("")
    content.append("---")
    content.append("")
    content.append(
        "**Last Updated**: Auto-generated from frontmatter (run `python generate_index.py` to refresh)"
    )

    return "\n".join(content)


def main():
    """Main entry point."""
    print("Parsing flaw files...")
    flaws = get_all_flaws()
    print(f"Found {len(flaws)} flaws")

    print("Generating INDEX.md...")
    content = generate_index(flaws)

    output_path = DESIGN_FLAWS_DIR / "INDEX.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Generated {output_path}")
    print(f"   - {len([f for f in flaws if f['status'] == 'active'])} active flaws")
    print(f"   - {len([f for f in flaws if f['status'] == 'resolved'])} resolved flaws")
    print(f"   - {len([f for f in flaws if f['status'] == 'future'])} future flaws")


if __name__ == "__main__":
    main()
