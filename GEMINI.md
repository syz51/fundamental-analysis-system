# Fundamental Analysis System

## Project Overview

This project is a **Multi-Agent Fundamental Analysis System** designed to autonomously perform comprehensive stock investment research. It mimics a team of human analysts using collaborative intelligence, parallel processing, and human-in-the-loop oversight.

**Current Status:** **Design Phase (v2.0).** The repository primarily contains architectural specifications and design documents. Implementation has not started. The current design focus is on the Macro Analyst agent and preparing the roadmap for Phase 1 implementation.

### Core Architecture

The system is built on a 5-layer architecture:

1. **Human Interface:** Dashboard and decision gates (6 gates total).
2. **Memory & Learning:** Central knowledge graph (Neo4j) and learning engine.
3. **Coordination:** Orchestration, conflict resolution, and debate facilitation.
4. **Specialists:** Domain-specific agents (Screening, Business, Financial, Strategy, Valuation, Macro).
5. **Support:** Data collection, news monitoring, and reporting.

## Directory Structure

- **`docs/`**: The core of the current project. Contains all design and architectural documentation.
  - `architecture/`: System overview, memory systems, agent roles, and protocols.
  - `operations/`: Analysis pipeline, human integration, and data management.
  - `learning/`: Feedback loops, metrics, and validation.
  - `implementation/`: Roadmaps, requirements, and risks.
  - `design-decisions/`: Records of architectural decisions (ADRs DD-001 to DD-026).
  - `design-flaws/`: Tracking of active and resolved system flaws.
  - `archive/`: Historical design documents and superseded specs.
- **`plans/`**: Active implementation plans and remaining work items (e.g., Macro Analyst integration).
- **`examples/`**: Placeholder for code samples.
- **`main.py`**: Entry point (currently a placeholder).
- **`pyproject.toml`**: Python project configuration and dependencies.

## Development & Usage

### Prerequisites

- **Python:** 3.14+
- **Package Manager:** `uv` (suggested by `uv.lock`)

### Building and Running

Since the project is in the design phase, "running" it currently serves to verify the environment.

1. **Install Dependencies:**

   ```bash
   uv sync
   ```

2. **Run Placeholder:**

   ```bash
   python main.py
   ```

### Conventions

- **Documentation First:** All architectural changes must be documented in `docs/` before implementation.
- **Design Decisions:** Use the template in `docs/design-decisions/TEMPLATE.md` for new architectural choices.
- **Agent Protocol:** Strict adherence to the defined message protocols and gate systems described in `docs/architecture/`.

## Key Documentation Points

- **System Overview:** `docs/architecture/01-system-overview.md`
- **Roadmap:** `docs/implementation/01-roadmap.md`
- **Current Focus (Macro):** `docs/design-decisions/DD-022_MACRO_ANALYST_AGENT.md` & `plans/macro-analyst-integration-remaining-work.md`
- **Agent Roles:** `docs/architecture/03-agents-specialist.md` & `04-agents-support.md`
