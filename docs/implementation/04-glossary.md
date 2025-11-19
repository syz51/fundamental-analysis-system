# Glossary

## Overview

This glossary defines key terms, concepts, and acronyms used throughout the multi-agent fundamental analysis system documentation. Terms are organized by category for easy reference.

The system combines financial analysis terminology, system architecture concepts, and memory system vocabulary.

---

## System Architecture Terms

### Agent

Autonomous software component specialized in specific analysis tasks. Each agent has defined responsibilities, domain expertise, and the ability to collaborate with other agents.

_Example: The Financial Analyst Agent calculates ratios and identifies accounting red flags._

### Agent Track Record

Historical performance measurement of an agent's predictions and recommendations, used to weight credibility in debates and decisions.

_Metric: Accuracy score by domain and context, updated at outcome checkpoints._

### Collaboration Session

Temporary shared memory space where multiple agents exchange findings, challenge conclusions, and build consensus during an analysis.

_Duration: Typically spans analysis phases 3-4 (days 3-9)._

### Coordination Layer

System layer responsible for workflow orchestration, conflict resolution, and inter-agent communication facilitation. Includes Lead Coordinator, Debate Facilitator, and QC Agent.

_Location: Middle layer between human interface and specialist agents._

### Gate (Human Decision Gate)

Critical decision point in the analysis workflow where human input or approval is required before proceeding. System includes Gates 1-6.

_Types: Screening validation, research direction, assumption validation, debate arbitration, final decision, learning validation._

### Human-in-the-Loop (HITL)

Design pattern where humans provide oversight, guidance, and final approval at critical junctures while AI handles routine analysis.

_Philosophy: Human augmentation, not replacement._

### Knowledge Graph

Graph database (Neo4j) storing all historical analyses, patterns, decisions, outcomes, and relationships as nodes and edges for efficient traversal and pattern matching.

_Schema: Nodes (Company, Analysis, Pattern, Decision, Agent, Outcome) + Relationships (HAS_ANALYSIS, LED_TO, SIMILAR_TO, etc.)._

### Specialist Agent Layer

System layer containing domain-focused agents (Screening, Business, Financial, Strategy, Valuation) that perform deep analysis in their respective areas.

_Characteristic: Each has local L2 memory cache for domain-specific patterns._

### Support Layer

System layer containing infrastructure agents (Data Collector, News Monitor, Report Writer, Knowledge Base Agent) that enable specialist agents.

_Function: Data acquisition, monitoring, documentation, memory management._

---

## Memory System Terms

### L1 Memory (Working Memory)

Fastest, smallest, most volatile agent memory tier. Holds immediate context for current analysis (active calculations, debate context).

_Storage: RAM/Redis, Size: ~100 items per agent, TTL: Hours, Access: <10ms_

### L2 Memory (Specialized Cache)

Medium-speed agent-specific cache for domain patterns and frequently accessed data. Each specialist agent maintains its own L2 cache.

_Storage: Local database/Redis, Size: ~10,000 items per agent, TTL: Weeks, Access: <100ms_

### L3 Memory (Central Knowledge Graph)

Permanent institutional knowledge repository storing all analyses, patterns, decisions, and outcomes in graph structure.

_Storage: Neo4j, Size: Unlimited, TTL: Permanent, Access: <1s_

### Memory Synchronization

Event-driven protocol for propagating discoveries from agent local memory (L1/L2) to central knowledge graph (L3) and broadcasting to other agents.

**Three Priority Levels**:

- **Critical** (<2s): Debates, challenges, human gates - immediate bidirectional sync with snapshots
- **High** (<10s): Important insights (importance > 0.7), alerts, findings with precedent
- **Normal** (5min): Routine updates, batch operations, background synchronization

_Trigger: Event-driven based on message type and importance, plus periodic 5-minute normal sync._

### Cache Hit Rate

Percentage of data queries successfully served from L1/L2 memory tiers without requiring L3 (Neo4j) access. Measured per-item basis across all agent queries.

**Calculation**: `(L1 hits + L2 hits) / Total queries × 100%`

**Target**: >80% hit rate by Phase 4 optimization

**Excludes**: L3 queries are cache misses, not counted in hit rate

_Purpose: Optimize memory tier sizing and caching strategies to reduce latency._

### Pattern

Recognized recurring relationship between conditions and outcomes, stored in knowledge graph and used to inform future analyses.

_Example: "Cloud transition leader" pattern has 85% success rate based on 23 historical companies._

### Pattern Decay

Phenomenon where historical patterns lose predictive power over time due to market evolution, regime changes, or structural breaks.

_Mitigation: Continuous monitoring, automatic deprecation at <65% accuracy, regime-dependent validity conditions._

### Pattern Lifecycle

Progression of pattern validation stages: `candidate` → `statistically_validated` → `human_approved` → `active` → `deprecated`.

_Critical: Patterns only used in decisions after `human_approved` status._

### Precedent

Historical situation similar to current analysis, retrieved from knowledge graph to provide context and inform decisions.

_Query: Semantic similarity search + metadata filtering (sector, market regime, pattern type)._

### Hybrid Memory Model

Three-tier memory architecture combining centralized knowledge graph (L3) with distributed agent-specific caches (L2) and working memory (L1).

_Advantage: Balances speed (local caches) with shared institutional knowledge (central graph)._

---

## Learning System Terms

### Blind Testing

Validation technique where pattern performance is tracked without agent awareness to prevent gaming of metrics and ensure unbiased measurement.

_Purpose: Anti-confirmation bias mechanism._

### Confidence Calibration

Process of adjusting prediction confidence scores based on historical accuracy to ensure confidence levels match actual outcomes.

_Example: If agent is correct 70% when claiming 90% confidence, calibrate down by 20 percentage points._

### Confirmation Bias

Systematic error where system reinforces existing beliefs by preferring confirming evidence and propagating false patterns.

_Prevention: Hold-out validation, blind testing, control groups, Gate 6 human review._

### Control Group

Baseline analysis performed without using a specific pattern, used to A/B test whether pattern actually improves predictions.

_Requirement: Pattern must show statistically significant improvement (p < 0.05) vs. control._

### False Pattern

Spurious correlation incorrectly identified as meaningful pattern, typically due to overfitting, small sample size, or confounding variables.

_Target: <10% false pattern rate through rigorous validation._

### Gate 6 (Learning Validation Gate)

Human oversight checkpoint where all system learnings (patterns, credibility changes, lessons) are reviewed and approved before use in future decisions.

_Frequency: Monthly or after 50 new outcomes, prevents confirmation bias loop._

### Hold-Out Validation

Technique where data is split into training (70%), validation (15%), and test (15%) sets to ensure patterns generalize to unseen data.

_Critical: Patterns discovered on training set only, tested on validation/test sets before approval._

### Lesson Learned

Documented insight from outcome tracking, capturing why predictions were incorrect and how to improve future accuracy.

_Example: "Supply chain improvements overestimated in retail → cap inventory benefit at 1% max"._

### Outcome Tracking

Systematic monitoring of prediction accuracy by comparing actual results to forecasts at checkpoints (30, 90, 180, 365 days).

_Purpose: Measure agent performance, identify lessons, update credibility scores._

### Pattern Mining

Process of discovering recurring patterns in historical analyses and outcomes through statistical analysis and machine learning.

_Validation Required: Hold-out testing, statistical significance (p < 0.05), causal mechanism, human approval._

### Self-Improvement Loop

Automated process where agents identify systematic errors, generate corrections, backtest improvements, and update decision logic.

_Constraint: All learning updates must pass Gate 6 validation before activation._

### Statistical Significance

Requirement that pattern relationships are unlikely due to chance (p-value < 0.05) before being considered valid.

_Prevents: Random noise being mistaken for meaningful patterns._

---

## Financial Analysis Terms

### CAGR (Compound Annual Growth Rate)

Annualized growth rate over multiple years, calculated as: `(Ending Value / Beginning Value) ^ (1 / Years) - 1`

_Usage: 10-year revenue CAGR is key screening metric._

### DCF (Discounted Cash Flow)

Valuation method calculating intrinsic value by discounting projected future cash flows to present value.

_Formula: `PV = Σ (FCF_t / (1 + WACC)^t) + Terminal Value`_

### DCA (Dollar Cost Averaging)

Investment strategy of buying fixed dollar amounts at regular intervals to reduce timing risk.

_System Use: Watchlist Manager generates DCA recommendations for approved positions._

### KPI (Key Performance Indicator)

Quantifiable metric used to evaluate company performance and progress toward objectives.

_Examples: Customer acquisition cost (CAC), lifetime value (LTV), monthly recurring revenue (MRR)._

### Moat (Competitive Moat)

Sustainable competitive advantage that protects company from competition and allows long-term profitability.

_Types: Network effects, switching costs, economies of scale, brand, intellectual property._

### Red Flag

Warning sign in financial statements or business operations suggesting potential problems or accounting manipulation.

_Examples: Related-party transactions, excessive management compensation, aggressive revenue recognition, cash flow mismatches._

### ROA (Return on Assets)

Profitability metric measuring net income generated per dollar of assets: `ROA = Net Income / Total Assets`

_Interpretation: Higher is better, compare to industry peers._

### ROE (Return on Equity)

Profitability metric measuring net income generated per dollar of shareholder equity: `ROE = Net Income / Shareholder Equity`

_DuPont Formula: `ROE = (Net Margin) × (Asset Turnover) × (Equity Multiplier)`_

### ROIC (Return on Invested Capital)

Efficiency metric measuring returns generated on capital deployed: `ROIC = NOPAT / Invested Capital`

_Interpretation: ROIC > WACC indicates value creation._

### SWOT Analysis

Strategic planning framework analyzing Strengths, Weaknesses, Opportunities, and Threats.

_System Use: Business Research Agent maintains SWOT for each company analyzed._

---

## Data & Infrastructure Terms

### Checkpoint

Scheduled time point (30, 90, 180, 365 days post-decision) when actual outcomes are compared to predictions.

_Purpose: Measure accuracy, extract lessons, update agent credibility._

### Cypher

Query language for Neo4j graph database, used to traverse relationships and retrieve patterns.

_Example: `MATCH (a:Analysis)-[:SIMILAR_TO]->(b) WHERE similarity > 0.8 RETURN b`_

### Embedding

Dense vector representation of text enabling semantic similarity search.

_Model: Custom embedding model (1536 dimensions), stored in Elasticsearch `dense_vector` fields alongside text content for hybrid search (DD-027, DD-029)._

### Graph Algorithm

Algorithm that operates on graph structure (nodes and edges) to identify patterns, communities, importance.

_Examples: PageRank (pattern importance), community detection (pattern clustering), shortest path (precedent search)._

### Message Queue

Asynchronous communication infrastructure (Kafka) enabling agents to exchange findings, challenges, and memory sync events.

_Topics: agent.findings, agent.challenges, memory.sync, memory.updates, human.gates, outcomes.tracking_

### Pipeline

End-to-end analysis workflow from screening to final decision, typically 12 days for full fundamental analysis.

_Phases: Screening (days 1-2), Parallel Analysis (days 3-7), Debate (days 8-9), Valuation (days 10-11), Documentation (day 12)._

### Semantic Search

Search technique using embeddings (kNN vector search) to find content similar in meaning, not just keyword matches. Combined with BM25 text search via Reciprocal Rank Fusion (RRF) for hybrid queries.

_Implementation: Elasticsearch 8+ `dense_vector` fields with cosine similarity, HNSW indexing (DD-027). Use Case: Find precedents and patterns semantically similar to current situation._

### Vector Database (Deprecated)

**Status**: Consolidated into Elasticsearch per DD-027.

Previously considered separate databases (Pinecone, Weaviate, Qdrant) for vector storage. Current architecture uses Elasticsearch 8+ unified hybrid search combining text (BM25) and vector (kNN) in single indices, avoiding sync complexity and enabling atomic updates.

_See: DD-027 Unified Hybrid Search Architecture, DD-029 Elasticsearch Index Mapping Standard._

---

## Workflow & Process Terms

### Autopilot Mode

Operational mode where system proceeds automatically with minimal human intervention, using conservative defaults.

_Best For: Low-risk screening, position monitoring, watchlist management._

### Collaborative Mode

Recommended operational mode where human provides input at key gates while AI handles detailed analysis.

_Best For: New position analysis, high-conviction investments, major decisions._

### Debate Protocol

Structured process for agents to challenge conclusions, demand evidence, and resolve disagreements through facilitated discussion.

_Steps: Challenge issued → Acknowledgment (15 min) → Evidence provided (1 hour) → Resolution or human escalation._

### Training Mode

Operational mode with active human guidance throughout, used for system improvement and complex situations.

_Best For: Edge cases, new sectors, learning from human expertise._

### Escalation

Process of raising unresolved agent disagreements to human for arbitration when evidence-based resolution fails.

_Trigger: Unresolved after 1-hour challenge-response cycle._

### Watchlist

Curated list of analyzed stocks being monitored for entry points, thesis validation, and position management.

_Managed By: Watchlist Manager Agent with alert triggers and periodic reviews._

---

## Compliance & Governance Terms

### Audit Trail

Complete, tamper-evident record of all decisions, reasoning, data sources, and human inputs.

_Retention: Permanent for decisions and reports, 7 years for audit logs._

### Chinese Wall

Information barrier preventing mixing of public and private data or creating conflicts of interest.

_Implementation: Access controls, separate databases, audit logging._

### GDPR (General Data Protection Regulation)

EU regulation governing personal data privacy and protection.

_System Impact: Minimal (no personal data stored), applies to user/analyst data only._

### Material Non-Public Information (MNPI)

Private information about a company that could affect stock price if publicly known, illegal to trade on.

_System Policy: Only public data sources, no insider sources, strict MNPI prohibition._

### Reg FD (Regulation Fair Disclosure)

SEC rule requiring companies to disclose material information to all investors simultaneously.

_System Compliance: Only public sources, timestamp verification, equal information access._

---

## Metrics & Performance Terms

### Accuracy Score

Percentage of predictions that were correct, measured at outcome checkpoints.

_Calculation: Correct predictions / Total predictions, by agent/domain/timeframe._

### Confidence Score

System's self-assessed probability that a prediction or recommendation is correct.

_Calibration: Adjusted based on historical accuracy (e.g., 90% confidence should be correct 90% of time)._

### Coverage

Percentage of decisions leveraging historical context and memory.

_Target: >90% memory utilization in analyses._

### False Positive/Negative Rate

Percentage of screening candidates that should have been rejected/accepted but weren't, determined at Gate 5 final decision.

**False Positive**: Stock screened in by Screening Agent, later rejected at Gate 5 (failed final investment decision)

**False Negative**: Stock screened out by Screening Agent, would have passed Gate 5 if analyzed (identified through post-hoc review of near-miss candidates)

**Determination Point**: Gate 5 final decision (human approval/rejection)

**Labeling**: Human decision at Gate 5 marks screening outcome as FP; periodic reviews identify FN

_Monitoring: Track by pattern, learn root causes, update screening logic._

### Learning Rate

Rate of improvement in prediction accuracy over time, typically measured quarterly.

_Target: 5%+ improvement per quarter._

### Memory Utilization

Percentage of analyses that successfully query and apply historical patterns and precedents.

_Target: >80% utilization by Month 12._

### Pattern Accuracy

Percentage of time a pattern's predicted outcome matches actual outcome.

_Threshold: >70% for active patterns, <65% triggers deprecation._

---

## Acronyms & Abbreviations

| Acronym | Full Term                                     | Definition                                        |
| ------- | --------------------------------------------- | ------------------------------------------------- |
| ADR     | Architecture Decision Record                  | Document capturing important architectural choice |
| API     | Application Programming Interface             | Interface for software components to communicate  |
| AOF     | Append-Only File                              | Redis persistence mechanism                       |
| CAGR    | Compound Annual Growth Rate                   | Annualized growth rate over multiple years        |
| CCPA    | California Consumer Privacy Act               | California data privacy regulation                |
| CI/CD   | Continuous Integration/Continuous Deployment  | Automated software delivery pipeline              |
| DAG     | Directed Acyclic Graph                        | Workflow structure in Airflow                     |
| DCA     | Dollar Cost Averaging                         | Fixed-amount investment strategy                  |
| DCF     | Discounted Cash Flow                          | Intrinsic valuation method                        |
| ELK     | Elasticsearch, Logstash, Kibana               | Log aggregation and analysis stack                |
| ETL     | Extract, Transform, Load                      | Data pipeline process                             |
| FCF     | Free Cash Flow                                | Cash available after capital expenditures         |
| GDPR    | General Data Protection Regulation            | EU data privacy law                               |
| GDS     | Graph Data Science                            | Neo4j graph algorithms library                    |
| HA      | High Availability                             | System design for minimal downtime                |
| HITL    | Human-in-the-Loop                             | Human oversight design pattern                    |
| JWT     | JSON Web Token                                | Authentication token format                       |
| KPI     | Key Performance Indicator                     | Quantifiable performance metric                   |
| LLM     | Large Language Model                          | AI model for natural language (GPT-4, Claude)     |
| LRU     | Least Recently Used                           | Cache eviction policy                             |
| M&A     | Mergers and Acquisitions                      | Corporate consolidation transactions              |
| MNPI    | Material Non-Public Information               | Inside information illegal to trade on            |
| MVP     | Minimum Viable Product                        | First functional system version                   |
| NLP     | Natural Language Processing                   | AI for text analysis                              |
| NOPAT   | Net Operating Profit After Tax                | Operating profit metric                           |
| P/E     | Price-to-Earnings Ratio                       | Valuation multiple                                |
| PIA     | Privacy Impact Assessment                     | Analysis of privacy risks                         |
| RBAC    | Role-Based Access Control                     | Permission system based on roles                  |
| Redis   | Remote Dictionary Server                      | In-memory data structure store                    |
| Reg FD  | Regulation Fair Disclosure                    | SEC fair disclosure rule                          |
| ROA     | Return on Assets                              | Profitability per dollar of assets                |
| ROCE    | Return on Capital Employed                    | Profitability metric                              |
| ROE     | Return on Equity                              | Profitability per dollar of equity                |
| ROI     | Return on Investment                          | Investment efficiency metric                      |
| ROIC    | Return on Invested Capital                    | Capital efficiency metric                         |
| RPO     | Recovery Point Objective                      | Maximum acceptable data loss                      |
| RTO     | Recovery Time Objective                       | Maximum acceptable downtime                       |
| SEC     | Securities and Exchange Commission            | US financial regulator                            |
| SLA     | Service Level Agreement                       | Uptime/performance guarantee                      |
| SWOT    | Strengths, Weaknesses, Opportunities, Threats | Strategic analysis framework                      |
| TTL     | Time to Live                                  | Data expiration time                              |
| WACC    | Weighted Average Cost of Capital              | Discount rate for DCF                             |

---

## Pattern-Specific Terms

### Cloud Transition Leader

Pattern identifying companies successfully migrating to cloud business models with sustained premium valuations.

_Success Rate: 85%, Examples: MSFT (2016+), CRM_

### Electric Transition Leader

Pattern for automotive companies leading electric vehicle transition.

_Success Rate: 37.5% (3 of 8), Key Factor: Manufacturing scale achievement_

### January Effect

Historical pattern of small-cap stock outperformance in January, now deprecated/weakened due to algorithmic arbitrage.

_Evolution: 71% → 45% → 38%, Updated to "January Effect in Micro Caps Only" (68%)_

### Platform Ecosystem Moat

Pattern identifying companies with network effects and developer ecosystems creating competitive advantages.

_Success Rate: 78%, Examples: AAPL, MSFT, GOOGL_

### Value Trap Tech

Pattern identifying low P/E technology companies that appear cheap but continue underperforming.

_Success Rate: 23% (inverse pattern), Examples: INTC (2020), IBM (2019)_

---

## Related Documentation

- **System Design**: See `multi_agent_fundamental_analysis_v2.0.md` for complete architecture using these terms
- **Implementation Roadmap**: See `01-roadmap.md` for phased deployment of capabilities
- **Technical Requirements**: See `02-tech-requirements.md` for infrastructure supporting these concepts
- **Risk Assessment**: See `03-risks-compliance.md` for risk mitigation using these frameworks

---

_Document Version: 2.1 | Last Updated: 2025-11-17_
