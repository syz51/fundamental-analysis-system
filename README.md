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

```text
/data
├── /raw                    # Source data (SEC filings, transcripts, market data, news)
├── /processed              # Cleaned/transformed (financial statements, ratios, sentiment)
├── /models                 # Valuation models (DCF, relative valuations, sensitivity)
└── /outputs                # Reports, watchlists, decision logs
```

## Roadmap

- **Month 4**: MVP (10 stocks end-to-end)
- **Month 6**: Beta (50 stocks, 80% accuracy)
- **Month 8**: Production (200 stocks, <24hr turnaround)
- **Month 12**: Scale (1000+ stocks)

## Documentation

**[📚 Complete Documentation](docs/README.md)** - Modular design docs organized by topic:

- **[Architecture](docs/architecture/)** - System design, memory, agents, protocols (7 docs)
- **[Operations](docs/operations/)** - Pipeline, human integration, data management (3 docs)
- **[Learning](docs/learning/)** - Learning systems, feedback loops, metrics (3 docs)
- **[Implementation](docs/implementation/)** - Roadmap, tech stack, compliance (4 docs)
- **[Design Decisions](design-decisions/)** - Architectural deep-dives
- **[Examples](examples/)** - Code samples (to be added)

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
