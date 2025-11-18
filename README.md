# Multi-Agent Fundamental Analysis System

Autonomous AI agent system for stock fundamental analysis. Mimics human analyst teams through collaborative intelligence, parallel processing, and human-in-the-loop oversight.

## Quick Start

```bash
# Install dependencies
uv sync

# Run system
python main.py
```

**Requirements**: Python 3.14+

## Architecture

**5-Layer System**:

- **Human Interface**: Dashboard, notifications, feedback, analytics
- **Memory & Learning**: Central knowledge graph, learning engine, patterns
- **Coordination**: Lead coordinator, debate facilitator, QC
- **Specialists**: Screening, business, financial, strategy, valuation (with memory)
- **Support**: Data collector, news monitor, knowledge base, report writer

**13 Specialized Agents** → Memory-enhanced pipeline → 6 human decision gates

## Analysis Pipeline

1. **Screening** (Days 1-2): Quantitative filters → Human Gate 1
2. **Parallel Analysis** (Days 3-7): Business/Financial/Strategy/News research
3. **Debate & Synthesis** (Days 8-9): Agent findings challenged → Human Gate 2
4. **Valuation** (Days 10-11): DCF, scenarios → Human Gate 3
5. **Documentation** (Day 12): Reports, watchlists → Human Gates 4 & 5

## Tech Stack

- **Backend**: Agent services, API layer
- **Frontend**: Dashboard, visualization
- **Orchestration**: Workflow management
- **Analysis**: Data processing, statistical analysis, time series forecasting
- **AI**: Agent framework, LLM integration

## Data Sources

- SEC EDGAR (10-K, 10-Q, 8-K)
- Financial providers (Koyfin, Bloomberg, Refinitiv)
- News feeds (Reuters, Bloomberg)
- Alternative data (web traffic, social sentiment)

## Project Structure

- `/docs` - Architecture and design documentation
- `/docs/design-decisions` - Architectural decision records
- `/examples` - Code samples (to be populated)

## Roadmap

- **Month 4**: MVP (10 stocks end-to-end)
- **Month 6**: Beta (50 stocks, 80% accuracy)
- **Month 8**: Production (200 stocks, <24hr turnaround)
- **Month 12**: Scale (1000+ stocks)

## Documentation

**[📚 Complete Documentation](docs/README.md)** - Full design documentation:

- **[Architecture](docs/architecture/)** - 5-layer system, 13 agents, memory system, collaboration protocols
- **[Operations](docs/operations/)** - 12-day analysis pipeline, 6 human gates, data management
- **[Learning](docs/learning/)** - Pattern recognition, feedback loops, performance metrics
- **[Implementation](docs/implementation/)** - Roadmap, tech stack, compliance, glossary
- **[Design Decisions](docs/design-decisions/)** - DD-XXX architectural decision records
- **[Design Flaws](docs/design-flaws/)** - Active issues tracking, resolved flaws
- **[Examples](examples/)** - Code samples (to be populated)

**Quick Links**: [System Overview](docs/architecture/01-system-overview.md) | [Roadmap](docs/implementation/01-roadmap.md) | [CLAUDE.md](CLAUDE.md)

## Key Features

- **Parallel Processing**: Multiple agents work simultaneously
- **Collaborative Intelligence**: Agents debate and validate findings
- **Human Augmentation**: Expert input at critical decision points
- **Transparency**: All reasoning auditable
- **Continuous Learning**: System improves through feedback loops

## Compliance

- SEC investment advisor regulations
- GDPR/CCPA data privacy
- Complete audit trails
- No material non-public info

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Disclaimer

Educational project demonstrating multi-agent systems architecture. Not financial advice. Not an investment service. For personal research and portfolio demonstration only.

---

**Status**: v2.0 Design | **Last Updated**: 2025-11-17
