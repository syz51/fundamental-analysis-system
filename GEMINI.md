# Fundamental Analysis System

## Project Overview
This project is a **Multi-Agent Fundamental Analysis System** designed to autonomously perform comprehensive stock investment research. It mimics a team of human analysts using collaborative intelligence, parallel processing, and human-in-the-loop oversight.

**Current Status:** Design Phase (v2.0). The repository primarily contains architectural specifications and design documents. Implementation is planned for future phases.

### Core Architecture
The system is built on a 5-layer architecture:
1.  **Human Interface:** Dashboard and decision gates.
2.  **Memory & Learning:** Central knowledge graph and learning engine.
3.  **Coordination:** Orchestration and conflict resolution.
4.  **Specialists:** Domain-specific agents (Screening, Business, Financial, Strategy, Valuation).
5.  **Support:** Data collection and monitoring.

## Directory Structure

*   **`docs/`**: The core of the current project. Contains all design and architectural documentation.
    *   `architecture/`: System overview, memory systems, agent roles, and protocols.
    *   `operations/`: Analysis pipeline, human integration, and data management.
    *   `learning/`: Feedback loops and metrics.
    *   `implementation/`: Roadmaps and requirements.
    *   `design-decisions/`: Records of architectural decisions (ADRs).
    *   `design-flaws/`: Tracking of known issues and resolutions.
*   **`examples/`**: Placeholder for future code samples.
*   **`plans/`**: Strategic planning documents.
*   **`main.py`**: Entry point (currently a placeholder).
*   **`pyproject.toml`**: Python project configuration and dependencies.

## Development & Usage

### Prerequisites
*   **Python:** 3.14+
*   **Package Manager:** `uv` (suggested by `uv.lock`)

### Building and Running
Since the project is in the design phase, "running" it currently serves to verify the environment.

1.  **Install Dependencies:**
    ```bash
    uv sync
    ```

2.  **Run Placeholder:**
    ```bash
    python main.py
    ```

### conventions
*   **Documentation First:** All architectural changes must be documented in `docs/` before implementation.
*   **Design Decisions:** Use the template in `docs/design-decisions/TEMPLATE.md` for new architectural choices.
*   **Agent Protocol:** Strict adherence to the defined message protocols and gate systems described in `docs/architecture/`.

## Key Documentation Points
*   **System Overview:** `docs/architecture/01-system-overview.md`
*   **Roadmap:** `docs/implementation/01-roadmap.md`
*   **Agent Roles:** `docs/architecture/03-agents-specialist.md` & `04-agents-support.md`
