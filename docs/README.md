# Multi-Agent Fundamental Analysis System - Documentation

**Version 2.0** | **Last Updated:** 2025-11-18

Comprehensive design documentation for the autonomous AI-powered stock analysis system.

---

## Quick Navigation

### 🏗️ Architecture

Understand the system design, memory model, agents, and collaboration protocols.

- [01 - System Overview](architecture/01-system-overview.md) - Executive summary, objectives, 5-layer architecture
- [02 - Memory System](architecture/02-memory-system.md) - L1/L2/L3 hybrid model, knowledge graph, sync protocols
- [03 - Specialist Agents](architecture/03-agents-specialist.md) - 6 core analysis agents (screening, business, financial, strategy, valuation, macro)
- [04 - Support Agents](architecture/04-agents-support.md) - 4 infrastructure agents (data collector, news monitor, QC, knowledge base)
- [05 - Coordination Agents](architecture/05-agents-coordination.md) - Lead coordinator, debate facilitator
- [06 - Output Agents](architecture/06-agents-output.md) - Report writer, watchlist manager
- [07 - Collaboration Protocols](architecture/07-collaboration-protocols.md) - Inter-agent messaging, debate protocol, memory-enhanced communication

### ⚙️ Operations

How the system runs day-to-day analysis and integrates with humans.

- [01 - Analysis Pipeline](operations/01-analysis-pipeline.md) - 5-phase workflow, 12-day cycle, phase diagrams
- [02 - Human Integration](operations/02-human-integration.md) - 6 decision gates, engagement modes, dashboard design
- [03 - Data Management](operations/03-data-management.md) - Data sources, storage architecture, governance policies

### 🧠 Learning & Feedback

System learning, pattern discovery, and continuous improvement.

- [01 - Learning Systems](learning/01-learning-systems.md) - Outcome tracking, pattern discovery, validation processes
- [02 - Feedback Loops](learning/02-feedback-loops.md) - Agent self-improvement, human feedback integration
- [03 - Metrics](learning/03-metrics.md) - Memory system metrics, performance indicators

### 🚀 Implementation

Roadmap, technical requirements, and deployment considerations.

- [01 - Roadmap](implementation/01-roadmap.md) - 5 phases, key milestones
- [02 - Technical Requirements](implementation/02-tech-requirements.md) - Tech stack, infrastructure, compute/storage needs
- [03 - Risks & Compliance](implementation/03-risks-compliance.md) - Risk assessment, regulatory considerations
- [04 - Glossary](implementation/04-glossary.md) - Terms and definitions
- [05 - Credibility System](implementation/05-credibility-system.md) - Agent scoring for debates, temporal decay, regime adaptation

### 🔍 Design Decisions

Deep dives into specific complex architectural choices.

- [Index of All Decisions](design-decisions/INDEX.md) - All design decisions with status (21 approved)
- [Template](design-decisions/TEMPLATE.md) - Standard format for documenting new decisions

**Recent Decisions**:
- [DD-022: Macro Analyst Agent](design-decisions/DD-022_MACRO_ANALYST_AGENT.md) - Top-down macro analysis (Phase 2)
- [DD-026: Macro Reports Format & Delivery](design-decisions/DD-026_MACRO_REPORTS.md) - Report specifications
- [DD-021: Neo4j High Availability](design-decisions/DD-021_NEO4J_HA.md) - Production infrastructure

### ⚠️ Design Flaws

Known design issues and resolutions tracked in `design-flaws/`:

- [Index](design-flaws/INDEX.md) - All flaws by priority/domain/phase
- [Status](design-flaws/STATUS.md) - Current blocker tracking by phase
- [Navigation Guide](design-flaws/README.md) - How to use the design-flaws folder

---

## Code Examples

Practical implementation samples are in `/examples`:

- [Agent Implementations](../examples/agent-implementations/) - Sample agent code
- [Memory Operations](../examples/memory-operations/) - Memory system usage examples
- [Workflow Scripts](../examples/workflow-scripts/) - Pipeline orchestration
- [API Integrations](../examples/api-integrations/) - External data source connectors

---

## Documentation Architecture

```text
/docs
├── README.md (this file)         # Master navigation
├── /architecture                 # System design (7 docs)
├── /operations                   # Day-to-day workflows (3 docs)
├── /learning                     # Learning systems (3 docs)
├── /implementation               # Roadmap & tech specs (5 docs)
├── /design-decisions             # Design deep-dives
├── /design-flaws                 # Design issues & resolutions
└── /archive
    ├── /historical-design        # Previous design versions
    └── /design-flaws             # Archived design flaw docs

/examples                         # Code samples
```

---

## Reading Paths

**New to the project?** Start here:

1. [System Overview](architecture/01-system-overview.md) - Big picture
2. [Analysis Pipeline](operations/01-analysis-pipeline.md) - How it works
3. [Roadmap](implementation/01-roadmap.md) - Development timeline

**Implementing agents?** Read:

1. [Specialist Agents](architecture/03-agents-specialist.md) - Core analysis agents
2. [Support Agents](architecture/04-agents-support.md) - Infrastructure agents
3. [Collaboration Protocols](architecture/07-collaboration-protocols.md) - Inter-agent communication
4. [Credibility System](implementation/05-credibility-system.md) - Agent scoring for debates
5. [Examples](../examples/agent-implementations/) - Sample code

**Working on memory systems?** Read:

1. [Memory System](architecture/02-memory-system.md) - Architecture overview
2. [Credibility System](implementation/05-credibility-system.md) - Agent credibility storage
3. [Learning Systems](learning/01-learning-systems.md) - How memory improves over time
4. [Design Flaws Index](design-flaws/INDEX.md) - Known issues to address

**Planning integration?** Read:

1. [Human Integration](operations/02-human-integration.md) - Gate design
2. [Data Management](operations/03-data-management.md) - Data sources
3. [Technical Requirements](implementation/02-tech-requirements.md) - Infrastructure needs

---

## System Enhancements (Phase 2+)

The system integrates **top-down macro analysis** with bottom-up company research:

- **Macro Analyst Agent**: Analyzes market regimes, economic indicators, sector dynamics
- **Sector Favorability**: Guides screening priorities (avoid poor-timing sectors)
- **Discount Rate Calibration**: DCF models reflect interest rate environment
- See [DD-022](design-decisions/DD-022_MACRO_ANALYST_AGENT.md) for details

---

## Version History

- **v2.0** (2025-11-17) - Modular documentation restructure, added memory/learning systems
- **v1.0** (2025-11) - Initial comprehensive design document

See [/archive](archive/historical-design/) for previous versions.

---

## Contributing

When updating documentation:

1. Keep each file focused on single topic (200-600 lines)
2. Update cross-references if relationships change
3. Use design decision template for architectural choices
4. Add code samples to `/examples`, not inline in docs
5. Update this master index when adding new docs

---

**Questions or feedback?** See design-decisions/ for architectural discussions.
