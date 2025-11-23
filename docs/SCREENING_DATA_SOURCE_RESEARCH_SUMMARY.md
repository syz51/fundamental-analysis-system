# Screening Data Source Research Summary

**Date**: 2025-11-23
**Research Question**: SimFin vs EdgarTools for S&P 500 screening
**Decision**: Use EdgarTools (DD-033)

---

## Executive Summary

Comprehensive research comparing SimFin API vs EdgarTools for screening S&P 500 companies resulted in decision to use **EdgarTools for both screening and deep analysis** (unified data source approach).

**Key Finding**: EdgarTools supports **on-demand per-company queries** (not just bulk download), fundamentally changing the cost-benefit analysis.

**Outcome**: Save $180/year with only 1 additional day of development effort.

---

## Research Overview

### Initial Assumption

**Problem**: Screening Agent (Days 1-2) needs financial data for 500 S&P companies
**Proposed Solution** (DD-032): Third-party API for screening, SEC EDGAR for deep analysis (hybrid)
**Candidate API**: SimFin START tier ($15/month)

### Critical Discovery

**SimFin Pattern**: Bulk download ALL 5,000+ US companies → local filtering
**EdgarTools Pattern**: On-demand per-company queries → optional bulk caching

**Previous misconception**: EdgarTools requires bulk download like SimFin
**Reality**: EdgarTools supports selective queries by default

---

## Key Findings

### 1. Data Access Patterns

| Aspect                  | SimFin                    | EdgarTools                   |
| ----------------------- | ------------------------- | ---------------------------- |
| **Query pattern**       | Bulk download mandatory   | On-demand queries (default)  |
| **For S&P 500**         | Download 5,000+ companies | Query only 500 needed        |
| **Selective retrieval** | ❌ No                     | ✅ Yes                       |
| **Bulk caching**        | Mandatory (Parquet)       | Optional (performance boost) |

### 2. Performance

**S&P 500 Screening (500 companies)**:

| Metric           | SimFin START        | EdgarTools                       |
| ---------------- | ------------------- | -------------------------------- |
| First run        | 5 min (bulk 5,000+) | 2.5 min (query 500 @ 10 req/sec) |
| Repeat run       | <1 min (cached)     | <1 min (HTTP cache)              |
| Rate limit       | 5 req/sec           | 10 req/sec                       |
| Wasted bandwidth | 4,500 non-needed    | 0                                |

**Winner**: EdgarTools (faster, more efficient)

### 3. Cost Analysis

**SimFin Value Proposition**: Save ~8 hours dev time (field mapping + ratio calculators)
**SimFin Cost**: $180/year

**Effective rate**: $180 ÷ 8 hours = $22.50/hour

**3-Year TCO**:

- EdgarTools: $0 (10 days dev)
- SimFin START: $540 (9 days dev + $180/yr)
- SimFin BASIC (with ROIC): $1,260 (8 days dev + $420/yr)

**Winner**: EdgarTools (lowest TCO)

### 4. Data Quality

| Stage         | Required | SimFin | EdgarTools                          |
| ------------- | -------- | ------ | ----------------------------------- |
| Screening     | 95%+     | ~95%   | 95% (Tier 0) or 98.55% (multi-tier) |
| Deep Analysis | 98.55%   | N/A    | 98.55% (multi-tier)                 |

**Winner**: EdgarTools (consistent quality across pipeline)

### 5. Feature Comparison

**SimFin Advantages**:

- Pre-normalized field names (save ~2hr)
- Pre-calculated ratios: ROE, ROA, margins (save ~4hr)
- Ready pandas DataFrames (save ~2hr)
- **Total dev time saved**: ~8 hours (~1 day)

**SimFin Limitations**:

- ❌ ROIC not included (need upgrade to BASIC $420/yr OR manual calc)
- ❌ Two data sources (consistency risk)
- ❌ Vendor lock-in
- ❌ Black box (no learning capability)
- ❌ Bulk download inefficiency

**EdgarTools Advantages**:

- ✅ $0 cost (free SEC EDGAR API)
- ✅ On-demand queries (query only what you need)
- ✅ Single source of truth (no consistency risk)
- ✅ Full control (customize edge cases, validation)
- ✅ Learning capability (QC Agent improves parser per DD-031)
- ✅ Already building it (DD-031 for deep analysis)

**EdgarTools Tradeoffs**:

- Need to implement field mapping (~2hr)
- Need to implement ratio calculators (~4hr, but ROIC needed anyway)
- ~1 day additional upfront dev

---

## Decision Rationale

### Why EdgarTools Won

1. **Already building it**: DD-031 selected EdgarTools + multi-tier parser for deep analysis
2. **Cost savings**: $180/year saved vs only 1 day extra dev (~$200 value)
3. **Better architecture**: Single source of truth, no data reconciliation
4. **Better performance**: 2.5 min vs 5 min, 10 req/sec vs 5 req/sec
5. **More efficient**: Query 500 companies, not 5,000+
6. **Full control**: Customize edge cases, implement learning loops
7. **Higher quality**: 98.55% achievable (vs SimFin ~95%)

### When SimFin Would Make Sense

✅ Production rush (need immediate screening, can't wait 1 day dev)
✅ No in-house dev capacity (buy vs build)
✅ Cost not a concern ($180/year acceptable)
✅ Don't need ROIC (or willing to pay $420/year for BASIC tier)

**Current situation**: Design phase, budget-conscious, building parser anyway → EdgarTools wins decisively.

---

## Implementation Plan

### Architecture

**Unified Data Source Approach**:

```
Screening (Days 1-2):
  EdgarTools on-demand queries
    ↓ 500 S&P companies @ 10 req/sec (2.5 min)
  Field mapper (US-GAAP → standard names)
    ↓ Handle XBRL concept variations
  Metrics calculator
    ↓ CAGR, margins, ROE/ROA/ROIC, debt ratios
  Screening filters
    ↓ 10-20 candidates
  Human Gate 1

Deep Analysis (Days 3-7):
  Same EdgarTools infrastructure
    ↓ Full 10-K/10-Q parsing (multi-tier)
  Qualitative data extraction
    ↓ MD&A, risk factors, amendments
  Business/Financial/Strategy Agents
```

### Key Components

**New Screening-Specific**:

- `src/screening/field_mapper.py`: Map US-GAAP XBRL concepts to standard names
- `src/screening/metrics_calculator.py`: Calculate CAGR, margins, ratios
- `src/screening/screener.py`: Main screening orchestrator
- `src/screening/sp500_loader.py`: S&P 500 ticker list loader

**Reused from DD-031**:

- `src/data_collector/filing_parser.py`: EdgarTools wrapper
- `src/data_collector/validation.py`: Data quality validation
- EdgarTools 3.0.0+ dependency

### Performance Specs

**S&P 500 Screening**:

- API calls: ~1,500 (3 per company)
- Time: 2.5 min @ 10 req/sec, 5 min @ 5 req/sec (CAUTION mode)
- Memory: ~500MB (pandas DataFrames)
- Quality: 95% (Tier 0) or 98.55% (multi-tier)

**Per-Company**:

- Single company: 1-3 seconds
- 100 companies: ~30 seconds

### Development Timeline

**Phase 1** (Core components): 3 days

- Field mapper: 0.5 days
- Metrics calculator: 1.5 days
- Main screener: 1 day

**Phase 2** (S&P 500 integration): 1 day

- S&P 500 loader: 0.25 days
- Execution script: 0.25 days
- Testing: 0.5 days

**Phase 3** (Testing & optimization): 1 day

- Unit tests: 0.5 days
- Integration tests: 0.5 days

**Total**: 5 days

---

## Documentation Created

### Design Decisions

1. **DD-033_SCREENING_DATA_SOURCE_EDGARTOOLS.md**
   - Comprehensive decision document
   - SimFin vs EdgarTools analysis (4 options)
   - Rationale, tradeoffs, consequences
   - Status: Approved

### Implementation Guides

2. **plans/edgartools-screening-implementation.md**
   - Step-by-step implementation guide
   - Code examples (field mapper, metrics calculator, screener)
   - Testing strategy
   - Performance optimization
   - Troubleshooting

### Archives

3. **plans/archive/SIMFIN_EVALUATION_ARCHIVED.md**
   - Archive note for SimFin research
   - References to DD-033

### Updated Files

4. **CLAUDE.md** (Data Sources section)
   - Updated to reflect EdgarTools unified approach
   - Performance specs, cost, quality metrics
   - Reference to DD-033

---

## Research Methodology

### Phase 1: SimFin Deep Dive

**Tools**: Task agent with Plan subagent
**Focus**: SimFin API capabilities, pricing, data access patterns
**Duration**: ~2 hours

**Key Questions Answered**:

- ✅ Does SimFin require bulk download? → Yes (all 5,000+ US companies)
- ✅ Are ratios pre-calculated? → Partially (ROE/ROA yes, ROIC no in START tier)
- ✅ What's the screening workflow? → Bulk download → local filtering
- ✅ Performance characteristics? → 5 min bulk download, <1 min cached
- ✅ Cost? → $180/year (START), $420/year (BASIC with ROIC)

### Phase 2: SimFin vs SEC EDGAR Comparison

**Focus**: Cost-benefit analysis
**Key Finding**: "If you're building EdgarTools parser anyway, why pay $180/year for pre-processing?"

### Phase 3: EdgarTools Capabilities Research

**Tools**: Task agent with Plan subagent
**Focus**: EdgarTools data access patterns
**Duration**: ~1 hour

**Critical Discovery**:

- ✅ Does EdgarTools require bulk download? → **NO** (supports on-demand queries)
- ✅ Selective retrieval possible? → **YES** (per-company, per-metric)
- ✅ Performance? → 2.5 min for S&P 500 (faster than SimFin)
- ✅ Caching? → Built-in HTTP cache + optional bulk cache

**Impact**: Invalidated SimFin's primary advantage ("no bulk download needed")

### Phase 4: Final Comparison & Decision

**Framework**: Cost, performance, quality, architecture, maintainability
**Result**: EdgarTools wins on all dimensions except convenience (1 day extra dev)
**Decision**: EdgarTools for unified data sourcing

---

## Lessons Learned

### 1. Challenge Assumptions Early

**Assumption**: "EdgarTools requires bulk download, so SimFin's on-demand API is better"
**Reality**: EdgarTools supports on-demand queries by default

**Impact**: This assumption would have cost $180/year unnecessarily

**Lesson**: Research tool capabilities thoroughly before making cost/benefit assumptions

### 2. Total Cost of Ownership > Upfront Cost

**Naive analysis**: "SimFin saves 1 day dev, worth it"
**TCO analysis**: 1 day saved (~$200) vs $180/year = break-even at 1.1 years

**Lesson**: For recurring costs, always calculate 3-5 year TCO

### 3. Architecture Matters

**Hybrid approach** (SimFin + EdgarTools):

- Two data sources → reconciliation complexity
- Consistency risk → QC Agent overhead
- Vendor dependency → operational risk

**Unified approach** (EdgarTools only):

- Single source of truth → simpler architecture
- No reconciliation → less code
- No vendor lock-in → less risk

**Lesson**: Architectural simplicity has hidden value beyond direct costs

### 4. "Buy vs Build" Depends on Context

**SimFin makes sense when**:

- Production rush (no time for 1 day dev)
- No dev capacity (can't build)
- Cost not a concern

**Build makes sense when** (this project):

- Already building similar tool (EdgarTools for deep analysis)
- Budget-conscious ($180/year matters)
- Design phase (1 day dev acceptable)
- Want full control (learning loops, customization)

**Lesson**: "Buy vs build" decision depends heavily on project context

---

## Next Steps

### Immediate (Phase 1)

1. ✅ Create DD-033 decision document → **DONE**
2. ✅ Create implementation guide → **DONE**
3. ✅ Update CLAUDE.md → **DONE**
4. ⏳ Implement field mapper (0.5 days)
5. ⏳ Implement metrics calculator (1.5 days)
6. ⏳ Implement main screener (1 day)

### Near-term (Phase 2)

7. ⏳ Implement S&P 500 loader (0.25 days)
8. ⏳ Create execution script (0.25 days)
9. ⏳ Integration testing (0.5 days)

### Future Optimizations

- Enable bulk caching if running daily screening
- Upgrade to full multi-tier (98.55%) if Tier 0 quality insufficient
- Implement parallel processing (ThreadPoolExecutor, respect rate limits)
- Add checkpoint-based resume for interruption recovery

---

## References

### Research Sources

**SimFin**:

- Website: <https://simfin.com>
- Documentation: <https://simfin.readthedocs.io/>
- Pricing: FREE (5Y), START ($15/mo, 10Y), BASIC ($35/mo, 15Y + ROIC)

**EdgarTools**:

- GitHub: <https://github.com/dgunning/edgartools>
- Performance: 10-30x faster than alternatives
- Rate handling: 10 req/sec (SEC limit)

**SEC EDGAR**:

- Rate limit: 10 requests/second
- Cost: Free
- Authoritative source

### Related Decisions

- **DD-031**: SEC Filing Parser Tool Selection (EdgarTools + multi-tier)
- **DD-033**: Screening Data Source Selection (EdgarTools chosen)

### Documentation

- **Decision**: docs/design-decisions/DD-033_SCREENING_DATA_SOURCE_EDGARTOOLS.md
- **Implementation**: plans/edgartools-screening-implementation.md
- **Archive**: plans/archive/SIMFIN_EVALUATION_ARCHIVED.md
- **Project guide**: CLAUDE.md (Data Sources section updated)

---

## Conclusion

**Decision**: Use EdgarTools for both screening and deep analysis (unified data source)

**Rationale**:

- $180/year saved (vs SimFin)
- 2-3 days dev time saved (no separate API integration)
- Single source of truth (better architecture)
- Faster screening (2.5 min vs 5 min)
- Full control & learning capability

**Cost**: Only 1 additional day of upfront development (field mapping + ratio calculators)

**Benefit**: $540 saved over 3 years + architectural simplicity + full control

**Winner**: EdgarTools by decisive margin

---

**Prepared by**: System Architect
**Date**: 2025-11-23
**Status**: Research Complete, Implementation Ready
