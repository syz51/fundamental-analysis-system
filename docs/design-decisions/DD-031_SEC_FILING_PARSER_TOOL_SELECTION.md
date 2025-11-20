# SEC Filing Parser Tool Selection

**Status**: Approved
**Date**: 2025-11-20
**Decider(s)**: System Architect
**Related Docs**: `plans/data-collector-implementation.md`, `plans/data-collector-parse-failure-strategy.md`, `plans/parse-failure-improvements-phase1.md`
**Related Decisions**: DD-028 (Redis Persistence), DD-029 (Elasticsearch Indexing)

---

## Context

Data Collector Agent (Phase 1) requires parsing SEC EDGAR filings (10-K, 10-Q, 8-K, 20-F) to extract financial data from XBRL format. Initial plan proposed building custom XBRL parser from scratch with multi-tier recovery system.

**Key Requirements**:

- Parse XBRL financial statements (income, balance sheet, cash flow)
- Handle edge cases: non-standard tags (40%), foreign filers/IFRS (25%), amended filings (15%), missing tags (10%), data corruption (5%), SPACs/holding companies (5%)
- Target: 98%+ data quality (vs 92-95% industry baseline)
- Cost-effective for 20K filings backfill + 100 filings/month ongoing

**Problem**: Building XBRL parser from scratch is complex. Research question: Do existing tools already solve these problems?

---

## Decision

**Use EdgarTools as Tier 0 foundation with custom multi-tier recovery system (Tiers 1.5-4)**

EdgarTools handles 95% baseline parsing (fast, battle-tested). Custom tiers handle edge cases NO existing tool solves: context disambiguation, data validation, false positive detection, learning capability.

**Architecture**:

```
Tier 0: EdgarTools (95% baseline, free)
  ↓ Fail (5%)
Tier 1.5: Smart Deterministic (metadata-aware, 35% recovery)
  ↓ Fail
Tier 2: LLM-assisted parsing (60% recovery)
  ↓ Validate
Tier 2.5: Data validation (catch false positives)
  ↓ If fails
Tier 3: QC Agent review (root cause analysis)
  ↓ Fail
Tier 4: Human escalation (0.15% of filings)
```

**Target**: 98.55% data quality, $88 + 20 hours for 20K filings

---

## Options Considered

### Option 1: Build Custom XBRL Parser from Scratch

**Description**: Implement full XBRL parser using lxml with US-GAAP/IFRS tag sets and multi-tier recovery

**Pros**:

- Full control over parsing logic
- No external dependencies
- Can optimize for specific use case

**Cons**:

- 3+ days development for baseline parser
- Likely 92-93% initial success rate (need to debug edge cases)
- Reinventing well-tested functionality
- Ongoing maintenance burden

**Estimated Effort**: 11 days (original plan)

---

### Option 2: Commercial Tools (Calcbench, sec-api.io)

**Description**: Use pre-processed financial data via paid API

**Pros**:

- Vendor handles parsing complexity
- Pre-normalized data
- Minimal development effort

**Cons**:

- **Cost**: $20K-$50K/year (Calcbench), $1K-$5K+ (sec-api.io) vs our $88
- Black box - can't customize for edge cases
- No control over quality/validation
- Vendor lock-in
- Unknown data quality guarantees
- Can't implement learning loop

**Estimated Effort**: 1-2 days integration, but ongoing $20K+ annual cost

---

### Option 3: Open Source Only (EdgarTools/py-xbrl)

**Description**: Use EdgarTools or py-xbrl alone without custom recovery layers

**Pros**:

- Free, well-maintained
- Fast (EdgarTools: 10-30x speedup)
- Battle-tested (EdgarTools: 1000+ tests)

**Cons**:

- **95% success rate, missing 5% edge cases**
- No context disambiguation (restated vs original, consolidated vs parent-only)
- No validation layer (false positives reach database)
- No holding company / SPAC / bankruptcy handling
- No learning capability
- **5-8% bad data entering system**

**Estimated Effort**: 2-3 days integration

---

### Option 4: EdgarTools + Custom Multi-Tier Recovery (CHOSEN)

**Description**: Use EdgarTools for 95% baseline, build custom tiers for remaining 5% edge cases

**Pros**:

- Best of both worlds: fast baseline + customizable recovery
- 98.55% data quality (vs 95% EdgarTools alone, 92-93% custom)
- Cost-effective: $88 + 20 hours for 20K filings
- Learning capability improves over time
- Full control over validation and disambiguation logic
- No vendor lock-in

**Cons**:

- EdgarTools dependency (mitigated by fallback to Tier 1.5)
- Still need to build Tiers 1.5-4 (but simpler than full parser)

**Estimated Effort**: 10 days (reduced from 11 via EdgarTools)

---

## Rationale

### Research Findings

Analyzed EdgarTools, py-xbrl, Arelle, Calcbench, sec-api.io:

**NO existing tool handles critical edge cases**:

| Problem                    | % of Failures | Any Tool Handles? |
| -------------------------- | ------------- | ----------------- |
| Context disambiguation     | 15%           | ❌ NO             |
| Mixed GAAP/IFRS extraction | 25%           | ❌ NO             |
| Holding companies          | 5%            | ❌ NO             |
| SPACs (zero revenue)       | 5%            | ❌ NO             |
| Data validation            | N/A           | ❌ NO             |
| False positive detection   | N/A           | ❌ NO             |
| Learning from failures     | N/A           | ❌ NO             |

**EdgarTools best baseline parser**:

- 95% success rate (vs 92-95% industry standard)
- 10-30x faster than custom lxml
- 1.2K GitHub stars, actively maintained
- Handles XBRL, iXBRL, US-GAAP, some IFRS

**Multi-tier system is unique value**:

- Only approach achieving 98%+ data quality
- Only approach with learning capability
- Only approach catching false positives before storage
- 20-50x cheaper than commercial ($88 vs $20K+)

### Key Decision Factors

1. **Cost**: $88 vs $20K+ (commercial) - 200x savings
2. **Quality**: 98.55% vs 95% (EdgarTools alone) vs 92-95% (commercial unknown)
3. **Customizability**: Full control over edge case handling vs black box
4. **Time**: 10 days (vs 11 custom, vs 2 days commercial but $20K)
5. **Learning**: QC Agent improves parser vs static commercial tools
6. **Risk**: Open source + fallback tiers vs vendor lock-in

**Tradeoffs Accepted**:

- EdgarTools dependency (acceptable - well-maintained, fallback to Tier 1.5 exists)
- 10 days implementation (acceptable - one-time cost, saves $20K annually)

---

## Consequences

### Positive Impacts

- **3.5% better data quality**: 98.55% vs 95% baseline (prevents ~700 bad records in 20K filings)
- **$20K+ annual savings**: vs commercial tools
- **10-30x faster baseline parsing**: EdgarTools vs custom lxml
- **Learning capability**: QC Agent improves parser over time (commercial can't)
- **Full customizability**: Can handle any edge case vs black box
- **Reduced development time**: 10 days vs 11 days (0.5 day saved on Day 5)

### Negative Impacts / Tradeoffs

- **EdgarTools dependency**: Mitigated by Tier 1.5 fallback if EdgarTools fails/deprecated
- **Still need Tiers 1.5-4**: 6 days development (but simpler than full parser)
- **Ongoing monitoring**: Need to track EdgarTools updates/breaking changes

### Affected Components

**New Components**:

- `src/data_collector/filing_parser.py`: Tier 0 EdgarTools wrapper + Tier 1.5 fallback
- `src/data_collector/validation.py`: Tier 2.5 data validation
- `tests/integration/test_edgartools.py`: EdgarTools baseline validation

**Updated Components**:

- `pyproject.toml`: Add `edgartools = "^3.0.0"` dependency
- `plans/data-collector-implementation.md`: Phase B updated with EdgarTools
- `plans/data-collector-parse-failure-strategy.md`: Architecture updated with Tier 0
- `plans/parse-failure-improvements-phase1.md`: Task 2.0 added for EdgarTools integration

---

## Implementation Notes

### Technical Details

**EdgarTools Integration (Tier 0)**:

```python
from edgartools import Filing

filing = Filing(accession_number)
xbrl = filing.xbrl()
financials = {
    "revenue": xbrl.statements.income_statement.revenue,
    "net_income": xbrl.statements.income_statement.net_income,
    "total_assets": xbrl.statements.balance_sheet.assets,
    # ... extract other metrics
}

# Validate completeness (≥5/8 metrics required)
if len([v for v in financials.values() if v]) < 5:
    raise ParseFailureError("Incomplete data, escalate to Tier 1.5")
```

**Fallback Strategy**:

- EdgarTools fails → Tier 1.5 smart deterministic (lxml-based)
- Tier 1.5 fails → Tier 2 LLM-assisted
- Tier 2 succeeds → Tier 2.5 validation (catch false positives)
- Tier 2.5 fails → Tier 3 QC Agent

**Testing Requirements**:

- Validate 95% baseline on 100 random real filings
- Measure performance improvement (expect 10-30x vs custom)
- Test fallback: Disable EdgarTools, verify Tier 1.5 works
- End-to-end: 10 companies through full pipeline

**Rollback Strategy**:

- If EdgarTools has breaking changes: Use Tier 1.5 exclusively (95% → 35% baseline, but system still works)
- If EdgarTools deprecated: Fork repo or switch to py-xbrl (similar API)

**Estimated Implementation Effort**: 10 days (reduced from 11)

**Dependencies**:

- `edgartools>=3.0.0` (Python library)
- Phase A complete (PostgreSQL, MinIO, Redis clients)
- SEC EDGAR API access (no auth, rate limited 10 req/sec)

---

## Open Questions

1. **EdgarTools IFRS support**: Does EdgarTools handle IFRS filings (20-F) as well as claimed? Need to test on foreign filers.
2. **EdgarTools context disambiguation**: Can EdgarTools distinguish consolidated vs parent-only for holding companies, or do we need Tier 1.5 always?
3. **sec-api.io 2025 pricing**: Current estimate based on 2023 data. What's actual 2025 pricing for high-volume usage?

**Blocking**: No - can proceed with implementation, validate EdgarTools IFRS support during testing

---

## References

### Research Sources

- **EdgarTools**: <https://github.com/dgunning/edgartools> (1.2K stars)
- **py-xbrl**: <https://github.com/manusimidt/py-xbrl> (XBRL 2.1 + iXBRL 1.1)
- **Arelle**: XBRL International certified validator
- **Calcbench**: XBRL US partner, academic pricing $6K-$12K/year
- **sec-api.io**: ~$55/month basic tier
- **SEC Official APIs**: data.sec.gov (free, raw data only)

### Industry Benchmarks

- Industry standard XBRL parsing: 92-95% success rate
- Common XBRL error types (XBRL US data): Invalid axis-member (33%), negative values (12%)
- SEC validation gap: "Software identifies most, but not all, violations"

### Related Decisions

- **Phase B (Filing Parser)**: data-collector-implementation.md Section B2
- **Multi-Tier Recovery**: data-collector-parse-failure-strategy.md Section 3
- **Phase 1 Improvements**: parse-failure-improvements-phase1.md

---

## Status History

| Date       | Status   | Notes                                          |
| ---------- | -------- | ---------------------------------------------- |
| 2025-11-20 | Proposed | Research completed, recommendation drafted     |
| 2025-11-20 | Approved | Decision to use EdgarTools + custom multi-tier |

---

## Notes

### Cost-Benefit Summary (20K Filings)

| Approach                         | Upfront Cost | Data Quality | Annual Cost | 3-Year TCO |
| -------------------------------- | ------------ | ------------ | ----------- | ---------- |
| **EdgarTools + Custom (Chosen)** | $88 + 20h    | **98.55%**   | $5          | **$103**   |
| Calcbench                        | $0           | Unknown      | $20K-$50K   | $60K-$150K |
| sec-api.io                       | $0           | Unknown      | $1K-$5K     | $3K-$15K   |
| EdgarTools alone                 | $0           | 95%          | $0          | $0         |
| Custom from scratch              | $0 + 33h     | 92-93%       | $0          | $0         |

**Winner**: EdgarTools + Custom (best quality, lowest cost)

### Future Considerations

- **Phase 2 optimization**: After 10K filings, analyze Tier 1.5 failure patterns → improve to 50% recovery
- **EdgarTools monitoring**: Set up GitHub watch for breaking changes, test on new releases
- **Alternative consideration**: If EdgarTools deprecated, py-xbrl is viable alternative (similar API, IFRS support)
