# Macro & Industry Analysis Enhancement Plan

**Date**: 2025-11-18

**Status**: Research Complete, Awaiting Implementation Decision

**Related**: Architecture v2.0 Enhancement

---

## Executive Summary

### Problem Statement

Current system lacks systematic macro and industry analysis:

- **No macro analysis**: Economic conditions, interest rates, sector rotation not analyzed
- **No industry trends**: Sector-level competitive dynamics, regulatory trends missing
- **Bottom-up only**: Company screening without top-down macro/sector context
- **Reactive not proactive**: News Monitor alerts on events but no systematic analysis

### Solution: Add 2 New Specialist Agents

**Macro Analyst Agent**:

- Market regime analysis (expansion/recession/late-cycle)
- Economic indicators (GDP, inflation, rates, PMI)
- Sector favorability scores
- Discount rate guidance for valuation
- Monthly reports + event-driven updates

**Industry Analyst Agent**:

- Porter's 5 Forces for industries
- Competitive landscape analysis
- Peer group definitions + comp tables
- Industry health scoring
- Quarterly reports + event-driven updates

### Key Findings

**Top-Down IS Fundamental Analysis**:

- Professional firms combine both approaches
- Top-down: Macro → Sector → Stock (asset allocation, timing)
- Bottom-up: Company fundamentals (stock selection)
- Best practice: Use BOTH together

**Existing Asset: Regime Detection**:

- Already have 6 market regimes (DD-008:184-199)
- Currently for agent credibility only
- Can reuse for macro analysis (no rebuild needed)

**Gradual Rollout Required**:

- Start 2 sectors (Tech, Consumer Discretionary)
- Expand to 5 sectors by Phase 2
- Full 11 GICS sectors by Phase 3
- Phased reduces risk, validates methodology

**Bidirectional Feedback Essential**:

- Industry forecasts → Companies (top-down context)
- Company actuals → Industry updates (bottom-up ground truth)
- Real firms do this (quarterly earnings → revise industry outlook)

---

## Recommendations

### Primary Recommendation: New Dedicated Agents

**Add 2 specialist agents** (vs expanding existing agents)

**Rationale**:

- Different expertise (macro economics ≠ company valuation)
- Different update cadence (monthly/quarterly vs per-stock)
- Centralized analysis (run once, reuse across 1000s stocks)
- Mirrors professional firm structure (proven model)
- Avoids scope creep in existing agents

**Integration**:

- Macro Analyst → Screening (sector scores), Valuation (discount rates)
- Industry Analyst → Financial Analyst (peer benchmarks), Business Research (competitive context)
- Reuse existing regime detection (DD-008), add analysis layer

### Implementation Approach

**Phased Launch**:

1. **Phase 1 (Months 3-4)**: Macro Analyst only, free data, 2 sectors
2. **Phase 2 (Months 5-6)**: Industry Analyst added, 5 sectors
3. **Phase 3 (Months 7-8)**: Full 11 sectors, add LLM layer to regime
4. **Phase 4+ (Months 9-12)**: Paid data sources, refinements

**Launch Order**: Macro first (establishes regime context before industry details)

---

## Data Sources

### By Phase Progression

**Phase 1-2 (MVP)**: Free Only - $0/year

- FRED: Macro indicators (GDP, CPI, unemployment, Fed rates)
- IMF: Global macro data
- OECD: 27 EU countries + OECD, 700 indicators
- SEC EDGAR: Company filings, GICS classifications
- CBOE: VIX, volatility indices
- Alpha Vantage: Economic indicators (8 categories)
- Coverage: Macro analysis + basic sector classification

**Phase 3-4 (Growth)**: Add Basic Paid - $12K-$25K/year

- IBISWorld: $15K-$25K/yr (unlimited industry reports)
- OR FactSet Basic: $12K-$20K/yr (company data, screening)
- Continue free macro sources
- Coverage: Macro + industry reports for target sectors

**Scale/Production**: Premium Platforms - $32K-$50K/year

- Bloomberg Terminal: $32K/yr (comprehensive, institutional quality)
- OR FactSet Enterprise: $50K/yr (heavy customization)
- Coverage: Full macro + industry + real-time monitoring

### IBISWorld vs FactSet Comparison

| Feature      | IBISWorld                                       | FactSet                                       |
| ------------ | ----------------------------------------------- | --------------------------------------------- |
| **Strength** | Industry reports (narratives, trends, Porter's) | Company financials, comp tables, screening    |
| **Coverage** | 700+ US industries, qualitative depth           | Global companies, real-time quantitative data |
| **Format**   | PDF reports (20-100 pages)                      | Structured data (API, Excel)                  |
| **Cost**     | $15K-$25K/yr unlimited                          | Basic $12K-$20K, Enterprise $50K+             |
| **Best For** | Industry Analyst (competitive landscape)        | Financial Analyst (peer benchmarks)           |
| **Use Case** | Porter's forces, industry trends, narratives    | Comp tables, screening, quantitative analysis |

**Complementary**: Both together ($30K-$45K/yr total) provides qualitative + quantitative coverage

**Budget Option**: IBISWorld only for MVP, add FactSet in Scale phase

---

## Phased Industry Coverage Rollout

### Phase 1 (Months 3-4): MVP - 2 Sectors

**Sectors**: Technology (XLK), Consumer Discretionary (XLY)

**Rationale**:

- High market cap (35% S&P 500)
- Well-documented (abundant data)
- Dynamic (tests feedback loop effectiveness)
- Likely user interest

**Scope**:

- GICS industry group level (e.g., Software, Semiconductors)
- Quarterly industry reports (simplified templates)
- Peer groups for top 10 companies per industry
- ~8 industry group analyses total

**Deliverables**:

- 2 sector reports
- Comp tables for 20 companies
- Industry health scores

**Success Metrics**:

- Peer group accuracy (vs Street comps)
- Industry trend accuracy (vs post-quarter reality)
- Company feedback integration rate

### Phase 2 (Months 5-6): Expansion - 5 Sectors

**Add**: Healthcare (XLV), Financials (XLF), Industrials (XLI)

**Total Coverage**: 5 sectors (~70% S&P 500)

**Why These**:

- Healthcare: Regulatory complexity (tests sophistication)
- Financials: Different metrics (interest rates, capital ratios)
- Industrials: Economic sensitivity (cyclical dynamics)

**Enhancements**:

- Sector rotation dashboard operational
- Cross-sector feedback loops
- Macro linkages (rates → Financials, GDP → Industrials)

### Phase 3 (Months 7-8): Full Coverage - 11 Sectors

**Add**: Energy (XLE), Materials (XLB), Real Estate (XLRE), Utilities (XLU), Comm Services (XLC), Consumer Staples (XLP)

**Total Coverage**: All 11 GICS sectors (100%)

**Enhancements**:

- Commodity-linked sectors (Energy, Materials)
- REIT-specific metrics (Real Estate)
- Defensive sector dynamics (Utilities, Staples)
- Full sector rotation model operational

### Phase 4+ (Months 9-12): Refinement

**Focus**: Sub-industry granularity (74 GICS industries)

**Enhancements**:

- International coverage (if applicable)
- Alternative data integration
- Advanced regime detection (ML ensemble)
- Full bidirectional feedback operational

### Coverage Order Options

**Option A: By Market Cap** (recommended Phases 2-3)

- Covers largest segments first, maximizes portfolio impact
- Order: Tech (28%) → Financials (13%) → Healthcare (12%) → etc.

**Option B: By User Interest**

- Analyze screening history, watchlist
- Cover most-used sectors first (immediate value)
- Cons: May create coverage gaps

**Option C: By Complexity** (easiest → hardest)

- Easy: Consumer (stable, mature)
- Medium: Tech, Healthcare (fast change, well-documented)
- Hard: Financials (different metrics), Energy (commodities)
- Pros: Learning curve, build expertise gradually

**Option D: Balanced Mix** (recommended Phase 1)

- 1 large + 1 volatile (Tech + Consumer Discretionary)
- Tests system with different dynamics
- Validates methodology before scaling

**Recommendation**: Option D for Phase 1, Option A (market cap) for Phases 2-3

---

## Company → Industry Feedback Loop

### Real-World Practice

Professional firms: Company analysts provide ground truth to industry analysts

- Quarterly earnings → update industry forecasts
- Example: "3 semiconductor companies missed auto demand → revise auto semiconductor outlook"

### Bidirectional Flow Design

**Industry → Company (Top-Down Context)**:

- Frequency: Quarterly + ad-hoc (regime changes)
- Content: Industry growth forecasts, competitive shifts, regulatory changes, peer benchmarks
- Storage: Neo4j relationships (Industry_Analyst → Company node)

**Company → Industry (Bottom-Up Signals)**:

- Frequency: Event-driven (earnings, guidance, material events)
- Triggers:
  - Metric deviates >15% from industry forecast
  - Management contradicts industry thesis
  - 3+ companies signal same trend (auto-escalate)
  - Red flag detected
- Content: Actual vs expected variance, qualitative signals, company KPIs
- Storage: Neo4j relationships (Company node → Industry_Analyst)
- Action: Industry Analyst reviews forecast, updates if 3+ confirm

### Feedback Protocol

1. Company Analyst completes quarterly analysis
2. Automatic check: Compare metrics vs Industry forecast
3. Threshold breached (>15%): Alert Industry Analyst
4. Industry Analyst: Review other companies, validate trend
5. Update: If 3+ companies confirm, revise industry forecast, broadcast to all analysts
6. Learning: Track forecast accuracy, identify blind spots

### Example Workflow

**Scenario**: Industry Analyst forecasts retail e-commerce growth at 8%

**Q2 Results**: AMZN +15%, SHOP +18%, ETSY +12% (3 companies beat by >5%)

**Trigger**: Auto-escalate to Industry Analyst (3+ companies signal)

**Action**: Review broader retail data, find consumer shift accelerating

**Update**: Revise e-commerce growth to 12%, update all retail company models

**Learning**: Store pattern "Post-pandemic e-commerce stickier than assumed"

**Future**: Next quarter, proactively monitor for demand sustainability

---

## Regime Detection Strategy

### Existing Asset: DD-008 Regime System

**Already Implemented** (DD-008:184-199):

- **6 Market Regimes**:
  1. BULL_LOW_RATES (S&P +10%+, Fed <3%, VIX <20)
  2. BULL_HIGH_RATES (S&P +10%+, Fed ≥3%)
  3. BEAR_HIGH_RATES (S&P negative, Fed ≥3%, VIX >25)
  4. BEAR_LOW_RATES (S&P negative, Fed <3%)
  5. HIGH_VOLATILITY (VIX >30)
  6. NORMAL (default)

**Current Use**: Agent credibility scoring only (which agent performs best in which regime)

**Detection Logic**: Daily monitoring (S&P 500, Fed Funds via FRED, VIX)

**Gap**: Regime DETECTED but not ANALYZED for investment decisions

### Enhancement: Add Analysis Layer

**Phase 1-2**: Rule-Based Foundation

- Reuse DD-008 regime detection (no rebuild)
- Add Macro Analyst to analyze implications:
  - Sector favorability by regime
  - Discount rate guidance
  - Scenario probabilities
- Target: 85% accuracy (based on NBER validation)

**Phase 3**: Add LLM Layer (Hybrid)

- LLM analyzes regime + indicators + news
- Outputs: Classification + confidence + narrative rationale
- Rule-based acts as fallback if LLM confidence <0.7
- Human validation via Gate 6
- Target: 90% accuracy (LLM + human oversight)

**Phase 4+**: Optional ML Enhancement

- If LLM insufficient, train ML classifier
- Ensemble: Rule-based (40%) + LLM (40%) + ML (20%)
- Backtesting on 1990-2024 data
- Target: 95% accuracy

### Method Comparison

| Approach          | Accuracy | Explainability               | Cost   | Complexity | Recommended Phase     |
| ----------------- | -------- | ---------------------------- | ------ | ---------- | --------------------- |
| **Rule-Based**    | 85%      | High (clear thresholds)      | Low    | Low        | Phase 1-2 (MVP)       |
| **LLM-Augmented** | 90%      | Medium (narrative rationale) | Medium | Medium     | Phase 3 (enhancement) |
| **ML Ensemble**   | 95%      | Low (black box)              | High   | High       | Phase 4+ (optional)   |

**Recommendation**: Hybrid approach

- Phase 1-2: Rule-based (fast, transparent, reuses DD-008)
- Phase 3: Add LLM (context-aware, fits agent framework)
- Phase 4+: Add ML only if needed (most complexity)

**Why Hybrid**:

- Explainability: Rule-based provides transparent baseline
- Adaptability: LLM handles novel situations (e.g., pandemic)
- Agent integration: LLM fits naturally as Macro Analyst
- Validation: Human review at Gate 6 prevents false regime propagation

---

## Peer Selection Workflow

### Real-World Practice

**Who Owns What**:

1. **Industry Analyst**: Maintains industry universe

   - Master list of companies per industry
   - Updates quarterly (IPOs, M&A, reclassifications)
   - Publishes industry benchmarks (median margins, multiples)

2. **Equity Analyst**: Selects specific peers

   - Chooses comparables from industry universe
   - Applies filters (size, business model, geography)
   - Responsible for defensibility
   - Updates when strategy shifts or M&A

3. **Handoff**:
   - Initiating coverage: Equity requests universe from Industry
   - Quarterly: Industry pushes universe changes to all equity analysts
   - Validation: Industry challenges inappropriate peer selections

### System Implementation

**Agent Responsibilities**:

| Agent                 | Role                                                                                                                                                                                                                  |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Industry Analyst**  | - Maintains industry universe (master list)<br>- Defines industry benchmarks (median metrics)<br>- Updates universe quarterly<br>- Validates Financial Analyst selections<br>- Challenges missing/inappropriate peers |
| **Financial Analyst** | - Selects specific peers for target company<br>- Applies filters (size, business model, geography)<br>- Documents rationale<br>- Updates when company/peer shifts<br>- Compares to peer benchmarks                    |
| **Valuation Agent**   | - Uses peer group for multiples (P/E, EV/EBITDA)<br>- Validates vs industry benchmarks<br>- Highlights outliers (premium/discount)                                                                                    |

### Workflow Example (NVDA)

**Step 1**: Screening Agent identifies NVDA

**Step 2**: Industry Analyst (triggered)

- Determines industry: "Semiconductors - GPU/AI Accelerators"
- Provides universe: [NVDA, AMD, INTC, QCOM, AVGO, MRVL]
- Industry benchmarks: Median gross margin 55%, R&D 18%, growth 12%

**Step 3**: Financial Analyst

- Receives universe from Industry Analyst
- Applies filters:
  - Size: Market cap 0.5x-2x NVDA ($500B-$2T) → Excludes AMD/INTC (too small)
  - Business model: GPU revenue >50% → AMD matches, INTC too diversified
  - End markets: Datacenter + gaming → AMD matches
- **Final peers**: AMD (direct), AVGO (datacenter semis), QCOM (mobile semis), AAPL/MSFT (scale comps)
- Documents rationale per peer

**Step 4**: Validation

- Financial Analyst sends peers to Industry Analyst
- Industry Analyst checks: Within universe? Cross-industry justified? Missing obvious peers?
- Suggests: Consider MRVL (datacenter connectivity)
- If major disagreement → debate protocol

**Step 5**: Human Gate 2

- Human reviews peer group
- Can override/add (e.g., "Add TSMC as ecosystem comp")

### Peer Group Size

**Question**: How many comparables to include?

**Options**:

- **3-5 peers (focused)**: Direct comparables only

  - Pros: Easy to analyze, clear comparison
  - Cons: May miss breadth, outliers skew

- **8-10 peers (comprehensive)**: Direct + secondary + scale comps
  - Pros: Robust benchmarks, outlier-resistant
  - Cons: Dilutes direct comps, harder to explain

**Real-World Standard**: 5-7 peers

- Primary 3-4: Direct business model comparables
- Secondary 2-3: Scale/valuation comps

**Recommendation**: 5-7 peers (balanced)

---

## Report Deliverables

### Macro Analyst Reports

**Monthly Macro Report**:

**Format**: PDF (8-12 pages) + Dashboard (interactive)

**Structure**:

1. Executive Summary (1 page): Current regime, confidence, key drivers, month-over-month changes
2. Economic Indicators (2-3 pages): GDP, employment, inflation, monetary policy, credit
3. Regime Analysis (2 pages): Historical context, leading indicators, transition probabilities, scenarios
4. Sector Implications (2-3 pages): Sector positioning, overweights/underweights, macro sensitivities, rotation recs
5. Risks & Catalysts (1-2 pages): Upside/downside risks, policy uncertainties, event calendar
6. Appendix: Data tables, indicator time series, forecast comparisons

**Dashboard**:

- Real-time regime probability gauge
- Indicator heatmap (green/yellow/red)
- Yield curve visualization
- Sector rotation matrix
- Economic calendar

**Frequency**:

- Monthly report (1st week of month)
- Ad-hoc updates (regime change, major Fed announcement)

**Recipients**:

- Gate 1 (if regime impacts screening)
- Gate 2 (if regime shift affects research priorities)
- Gate 5 (final decision context)
- All agents (adjust forecasts)

### Industry Analyst Reports

**Quarterly Industry Report**:

**Format**: PDF (15-25 pages per industry) + Comp Tables (Excel/dashboard)

**Structure**:

1. Executive Summary (1-2 pages): Health rating, key trends, outlook shift, recommendations
2. Industry Overview (2-3 pages): Market size/growth, segmentation, demand/supply dynamics
3. Competitive Landscape (3-4 pages): Market share, new entrants/exits, Porter's forces, differentiation
4. Financial Benchmarking (3-5 pages): Comp tables, peer distributions, trend analysis, red flags
5. Regulatory & Macro (2-3 pages): Regulatory changes, macro sensitivity, geopolitical risks
6. Outlook & Catalysts (2-3 pages): Forecast, long-term themes, catalysts, risk factors
7. Peer Definitions (1-2 pages): Industry universe, sub-industry segmentation, selection criteria
8. Appendix (5-10 pages): Detailed comp tables, valuation multiples, industry KPIs

**Comp Table Example**:

| Company    | Mkt Cap | Rev Growth | Gross Margin | Op Margin | Rule of 40 | EV/Sales | P/E     |
| ---------- | ------- | ---------- | ------------ | --------- | ---------- | -------- | ------- |
| NVDA       | $1.2T   | 50%        | 75%          | 55%       | 105        | 35.0x    | 75x     |
| AMD        | $200B   | 18%        | 51%          | 10%       | 28         | 8.0x     | 50x     |
| **Median** | -       | **18%**    | **55%**      | **20%**   | **38**     | **8.0x** | **50x** |

**Frequency**:

- Quarterly full report (~2 weeks post-quarter)
- Monthly light updates (metrics, market share)
- Event-driven (M&A, regulatory, competitive disruptions)

**Recipients**:

- Gate 2 (research direction)
- Gate 3 (assumption validation vs industry norms)
- Gate 5 (final decision, company ranking)
- Financial/Business/Valuation Agents (benchmarks, context)

### Report Trigger Logic

**Industry Reports**:

- **News-driven**: Material event → immediate evaluation (2-5 page update)

  - Examples: M&A, regulatory change, 3+ companies signal trend

- **Monthly (without news)**: Light update

  - Dashboard refresh, comp table update
  - No full report unless material change

- **Quarterly**: Comprehensive report (scheduled, regardless of news)
  - Full Porter's forces, benchmarks, outlook

**Summary**: Event → immediate, Monthly → light, Quarterly → comprehensive

### Integration with Human Gates

| Gate                     | Receives                                                              | Usage                                                 |
| ------------------------ | --------------------------------------------------------------------- | ----------------------------------------------------- |
| **Gate 1** (Screening)   | Macro: Current regime, sector favorability                            | Validate screening aligned with macro context         |
| **Gate 2** (Research)    | Industry: Competitive landscape, trends<br>Macro: Sector implications | Prioritize research focus areas                       |
| **Gate 3** (Assumptions) | Industry: Comp tables, benchmarks<br>Macro: GDP/inflation forecasts   | Validate company assumptions vs industry + macro      |
| **Gate 4** (Debate)      | Industry: Peer benchmarks<br>Macro: Regime context                    | Arbitrate disagreements with data                     |
| **Gate 5** (Decision)    | **Full Package**: Macro + Industry + Company                          | Holistic decision (quality + attractiveness + timing) |
| **Gate 6** (Learning)    | Pattern discoveries, credibility updates                              | Validate macro/industry patterns statistically sound  |

---

## Implementation Answers (8 Clarifications)

### 1. Data Sources

**Decision**: List all options for later choice

**Options Documented**:

- Free: FRED, IMF, OECD, SEC, Alpha Vantage ($0/yr)
- Basic Paid: IBISWorld ($15K-$25K), FactSet Basic ($12K-$20K)
- Premium: Bloomberg ($32K), FactSet Enterprise ($50K+)
- Comparison table provided (strengths, coverage, format, cost)

**Both IBISWorld + FactSet?**

- Yes, complementary (qualitative + quantitative)
- Combined: $30K-$45K/yr
- Alternative: IBISWorld only for MVP

**Status**: User to investigate/decide budget later

### 2. Dashboard Tool

**Options**:

- Build custom: Plotly Dash, Streamlit (Python-based, full control)
- License: Tableau, Power BI (enterprise features, cost $70-$150/user/mo)

**Decision**: Later during implementation

### 3. Regime Settings

**Finding**: Already exist in DD-008!

- 6 regimes defined (BULL_LOW_RATES, BULL_HIGH_RATES, etc.)
- Detection logic implemented (S&P, Fed, VIX via FRED)
- Current use: Agent credibility only

**Gap**: Not used for macro analysis/investment decisions

**Solution**: Macro Analyst reuses detection, adds analysis layer

- No rebuild needed
- Input: Current regime (from DD-008)
- Output: Sector favorability, discount rate guidance, scenarios

**Threshold**: 0.6 (aggressive) vs 0.8 (conservative)

- Decision: Later during implementation (start 0.7, tune based on backtest)

### 4. Industry Report Frequency

**Clarified Trigger Logic**:

- **News**: Material event → immediate evaluation
- **Monthly (without news)**: Light update (dashboard, no full report)
- **Quarterly**: Comprehensive report (scheduled)

**Question**: Quarterly sufficient or monthly for volatile sectors (tech)?

- Decision: Start quarterly all sectors, add monthly for tech if needed (Phase 3+)

### 5. Peer Group Size

**Meaning**: How many companies to compare against

**Options**:

- 3-5 (focused): Direct comps only
- 8-10 (comprehensive): Direct + secondary + scale

**Real-world**: 5-7 peers typical

- Primary 3-4: Direct business model
- Secondary 2-3: Scale/valuation

**Recommendation**: 5-7 peers (balanced)

**Decision**: Confirmed, use 5-7 as default

### 6. Launch Strategy

**Decision**: Macro first

**Rationale**:

- Establishes regime context before industry details
- Simpler to implement (1 agent vs 2)
- Validates methodology before Industry Analyst
- Industry Analyst needs macro context (regime → sector favorability)

**Status**: Confirmed

### 7. LLM Choice

**Options**:

- GPT-4: Financial reasoning leader (better earnings predictions)
- Claude Opus: Productivity/Excel leader (80% accuracy, 20% productivity gains)

**Trade-offs**:

- GPT-4: Better quantitative analysis
- Claude: Better qualitative reasoning, document analysis

**Decision**: Later during implementation

- Likely Claude (already using Anthropic, qualitative strength for Porter's/narratives)
- Can A/B test both

### 8. Industry Coverage Order

**Options Documented**:

- A: By market cap (covers largest first)
- B: By user interest (screening history)
- C: By complexity (easiest → hardest)
- D: Balanced mix (1 large + 1 volatile)

**Recommendation**: D for Phase 1 (Tech + Consumer Disc), then A (market cap)

**Rationale**:

- Tests different dynamics (fast-moving + cyclical)
- Validates methodology before scaling
- Then maximize portfolio impact (market cap order)

**Decision**: Confirmed approach, exact order after seeing screening patterns

---

## Design Decisions Needed

### To Be Created (New DDs)

**High Priority**:

1. `DD-[XXX]_MACRO_ANALYST_AGENT.md`

   - Responsibilities, deliverables, memory, integration
   - Regime analysis (reuse DD-008 detection)
   - Sector favorability scoring
   - Monthly reports + dashboard

2. `DD-[YYY]_INDUSTRY_ANALYST_AGENT.md`

   - Responsibilities, deliverables, memory, integration
   - Porter's forces, competitive landscape
   - Peer universe maintenance
   - Quarterly reports + comp tables
   - Gradual rollout (2→5→11 sectors)

3. `DD-[ZZZ]_COMPANY_INDUSTRY_FEEDBACK.md`

   - Bidirectional flow design
   - Event triggers (>15% variance, 3+ companies)
   - Feedback protocol
   - Neo4j storage

4. `DD-[AAA]_PEER_SELECTION_WORKFLOW.md`
   - Industry owns universe, Financial selects peers
   - Validation protocol
   - Debate escalation for disagreements
   - Peer group size (5-7 standard)

**Medium Priority**: 5. `DD-[BBB]_MACRO_INDUSTRY_REPORTS.md`

- Report formats, structures, frequencies
- Dashboard specifications
- Gate integration
- Trigger logic (event vs scheduled)

6. `DD-[CCC]_DATA_SOURCES_STRATEGY.md`
   - Free → paid progression
   - IBISWorld vs FactSet comparison
   - Budget options by phase
   - API integration requirements

### Architecture Docs to Update

**Must Update**:

1. `docs/architecture/01-system-overview.md`

   - Agent count: 13 → 15 agents
   - 5-layer diagram (add Macro + Industry to Specialist layer)
   - Update agent list

2. `docs/architecture/03-agents-specialist.md`

   - Add Macro Analyst (section 6)
   - Add Industry Analyst (section 7)
   - Integration with existing agents

3. `docs/operations/01-analysis-pipeline.md`

   - Add Phase 0 (async macro/industry analysis, cached)
   - Update Days 1-2 (screening with sector scores)
   - Update Days 10-11 (valuation with macro context)
   - Timeline unchanged: 12 days

4. `docs/operations/02-human-integration.md`

   - Gate 1: Macro context (regime, sector favorability)
   - Gate 2: Industry reports (research direction)
   - Gate 3: Industry benchmarks + macro assumptions
   - Gate 5: Full macro + industry + company package

5. `docs/operations/03-data-management.md`

   - Macro data sources (FRED, IMF, OECD)
   - Industry data sources (IBISWorld, FactSet options)
   - API integrations

6. `CLAUDE.md`
   - Update agent list (15 total)
   - Add Macro Analyst, Industry Analyst to 13 types section
   - Update tech stack (data sources)

---

## Deferred Decisions

**To Be Decided During Implementation**:

1. **Data Source Budget**: Free only vs IBISWorld vs FactSet vs Bloomberg

   - Depends on: Budget approval, user priorities
   - Timeline: Before Phase 3

2. **Dashboard Tool**: Build (Plotly) vs Buy (Tableau)

   - Depends on: Budget, team skills, feature requirements
   - Timeline: Phase 2-3

3. **Regime Detection Threshold**: 0.6 vs 0.7 vs 0.8 confidence

   - Depends on: Backtesting results, human review capacity
   - Timeline: Phase 1 implementation

4. **LLM Provider**: GPT-4 vs Claude Opus

   - Depends on: Performance testing, cost analysis
   - Timeline: Phase 3 (LLM layer addition)

5. **Industry Report Frequency**: Quarterly all vs monthly for volatile sectors

   - Depends on: Phase 1 results, sector dynamics
   - Timeline: Phase 2-3

6. **Industry Coverage Order**: Exact sector sequence

   - Depends on: User screening patterns, watchlist analysis
   - Timeline: After Phase 1 design docs complete

7. **Peer Group Size**: 5-7 default, but allow flexibility per industry?

   - Depends on: Industry concentration (semiconductors few players, retail many)
   - Timeline: Phase 2 implementation

8. **Industry Analyst Launch**: Phase 1 (with Macro) vs Phase 2 (after Macro proven)
   - Depends on: Implementation capacity, risk tolerance
   - Timeline: Before Phase 1 start

---

## Next Steps

### Immediate (Documentation)

1. **Create 4 core DDs** (XXX, YYY, ZZZ, AAA):

   - Macro Analyst Agent
   - Industry Analyst Agent
   - Company→Industry Feedback
   - Peer Selection Workflow

2. **Update 6 architecture docs**:
   - System overview, Specialist agents, Pipeline, Human integration, Data management, CLAUDE.md

### Phase 1 Preparation (Before Implementation)

3. **Finalize deferred decisions**:

   - Data sources (at minimum: confirm free sources for MVP)
   - Regime threshold (run backtests, pick starting value)
   - Industry Analyst launch timing (Phase 1 or 2?)

4. **Technical setup**:

   - FRED API access (free, register for key)
   - Data pipeline (fetch GDP, CPI, rates, VIX)
   - Neo4j schema (industry universe, feedback relationships)

5. **Template creation**:
   - Monthly macro report template
   - Quarterly industry report template
   - Dashboard wireframes

### Phase 1 Implementation (Months 3-4)

6. **Macro Analyst MVP**:

   - Regime analysis (reuse DD-008 detection)
   - Sector favorability scores (basic model)
   - Monthly report generation
   - Integration with Screening Agent

7. **Validation**:

   - Backtest regime accuracy (2020-2024 data)
   - Test sector favorability predictions
   - Human review (Gate 1) feedback

8. **Decision checkpoint**: Proceed to Phase 2 (Industry Analyst) or refine Macro?

---

## Risk Register

| Risk                                          | Impact | Likelihood | Mitigation                                                         |
| --------------------------------------------- | ------ | ---------- | ------------------------------------------------------------------ |
| **Insufficient free data quality**            | High   | Medium     | Fallback paid sources, validate FRED completeness before commit    |
| **Regime detection false signals**            | High   | Medium     | Human validation at gates, confidence intervals, LLM layer Phase 3 |
| **Industry Analyst overwhelmed (11 sectors)** | Medium | High       | Phased rollout (2→5→11), quarterly not monthly updates             |
| **Company→Industry feedback too noisy**       | Medium | Medium     | 15% variance threshold, require 3+ companies to trigger            |
| **Peer selection debates slow pipeline**      | Medium | Low        | Industry validation async, debate only if major disagreement       |
| **Report generation latency**                 | Low    | Medium     | Template automation, cache sector data, batch processing           |
| **Budget rejected for paid data**             | High   | Low        | MVP proven with free data first, demonstrate ROI for Phase 3       |
| **Macro/Industry not actionable**             | High   | Low        | Tight integration with gates, agents use reports for decisions     |

---

## Success Metrics

### Phase 1 (Macro Analyst)

**Regime Detection**:

- Accuracy: >85% vs NBER classification (backtest 2020-2024)
- Timeliness: Detect regime change within 1 month
- False positive rate: <15%

**Sector Favorability**:

- Correlation: >0.6 with actual sector performance (3mo forward)
- Screening improvement: Top-ranked sectors outperform bottom by >5%
- Human override rate: <20% (Gate 1)

**Reports**:

- Generation time: <2 hours (automated)
- Human review time: <30min (Gate 1)
- Actionability: >70% of recommendations adopted

### Phase 2 (Industry Analyst)

**Peer Groups**:

- Accuracy: >80% match with Street consensus comps
- Coverage: 90% of screened companies have peer groups
- Debate rate: <10% of peer selections escalate to debate

**Industry Forecasts**:

- Accuracy: Within 5% of actual industry growth (1 quarter forward)
- Feedback rate: >30% of companies trigger feedback (>15% variance)
- Update responsiveness: Industry forecast revised within 1 week of 3+ signals

**Reports**:

- Generation time: <5 hours per industry (quarterly)
- Comp table completeness: 100% coverage for target companies
- Human review time: <1 hour per industry (Gate 2)

### Phase 3+ (Full System)

**Integration**:

- Pipeline speed: 12-day timeline maintained (macro/industry async)
- Agent adoption: >80% of agents reference macro/industry reports
- Human gate efficiency: Gate review time reduced by 20% (better context)

**Decision Quality**:

- Investment accuracy: >5% improvement with macro/industry context
- Risk mitigation: Early detection of sector headwinds (>60% catch rate)
- Position sizing: Better calibration (macro alignment increases conviction)

---

## Appendix: Research Methodology

### Research Conducted

**Investment Industry Practices**:

- Goldman Sachs, Piper Sandler team structures
- Dodge & Cox macro/fundamental integration
- Wolfe Research sector expansion strategy
- Real-world peer selection workflows

**Technical Approaches**:

- NBER recession detection methods (Bayesian, GDP-based)
- GPT-4 financial analysis research (earnings predictions)
- Claude productivity benchmarks (Norwegian wealth fund)
- LLM vs ML vs rule-based regime detection

**Data Source Analysis**:

- FRED, IMF, OECD coverage maps
- IBISWorld vs FactSet vs Bloomberg feature comparison
- Industry data provider pricing (as of 2024-2025)
- Free vs paid trade-offs by phase

### Key Insights

1. **Top-down IS fundamental analysis**: Not separate strategy, professional firms combine both
2. **Regime detection exists**: DD-008 already implemented, just add analysis layer
3. **Bidirectional feedback standard**: Real firms update industry views based on company results
4. **Phased rollout proven**: Wolfe Research scaled 2→8 sectors over 5 years, validates gradual approach
5. **Hybrid regime detection best**: Rule-based (explainable) + LLM (adaptive) > pure ML (black box)
6. **Industry Analyst owns universe**: Equity analysts select from universe, not build from scratch
7. **5-7 peers typical**: Professional reports use focused comps, not exhaustive lists
8. **Reports must be actionable**: Monthly macro, quarterly industry, event-driven updates

### Sources

- Investment firm structures: Public disclosures, analyst coverage lists
- Regime detection: NBER methodology papers, academic research
- LLM financial analysis: GPT-4 earnings research, Claude productivity studies
- Data sources: Provider websites, pricing as of Q4 2024-Q1 2025
- Real-world workflows: Industry standards, analyst reports

---

**Document Version**: 1.0
**Last Updated**: 2025-11-18
**Next Review**: After Phase 1 DD creation
