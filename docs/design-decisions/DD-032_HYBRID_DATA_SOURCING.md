# Hybrid Data Sourcing Strategy

**Status**: Under Review
**Date**: 2025-11-20
**Decider(s)**: System Architect
**Related Docs**: `plans/data-collector-implementation.md`
**Related Decisions**: DD-031 (SEC Filing Parser Tool Selection)

---

## Context

Data Collector Agent requires financial data for two distinct use cases with different quality requirements:

1. **Screening Stage (Days 1-2)**: Filter S&P 500 companies using quantitative metrics (10Y revenue CAGR, margins, ROE/ROA/ROIC)
2. **Deep Analysis Stage (Days 3-7)**: Comprehensive research requiring high-quality data, qualitative sections, amendment tracking

**Original Plan**: Parse all SEC filings upfront (20K filings backfill, 4.2 hours, $88 cost)

**Question**: Do we need to parse SEC filings for screening, or can we use pre-aggregated data from third-party APIs for initial filtering?

**Key Requirements**:

**Screening Stage**:

- Quantitative metrics only (revenue, EPS, margins, debt ratios)
- 10Y/5Y revenue CAGR calculation
- Company summaries for candidate selection
- Fast execution (immediate availability)
- Moderate quality acceptable (95% good data)

**Deep Analysis Stage**:

- Full 10Y historical data (40 filings: 10-K + 10-Q × 10 years)
- Qualitative sections (MD&A, risk factors, business description)
- Amendment tracking (original vs restated for red flag detection)
- Context disambiguation (consolidated vs parent-only)
- High quality critical (98.55% good data with validation)

---

## Decision

Use third-party financial data API for screening stage, SEC EDGAR parsing for deep analysis stage (hybrid approach)

**NOTE**: Specific API provider TBD - pending evaluation of options

**Architecture**:

```text
Screening Stage (Days 1-2):
  Financial Data API (TBD)
    ↓ Fetch revenue, margins, ROE for all S&P 500
  Screening Agent applies quantitative filters
    ↓ 10Y CAGR ≥ 15%, margins ≥ 8%, etc.
  Generate numerical summaries
    ↓ "Company X: 18% 10Y CAGR, 12% margin, ROE 15%"
  Human Gate 1 (select ~10-20 candidates)

Deep Analysis Stage (Days 3-7, after Gate 1):
  Human approves Company X
    ↓
  Data Collector: Fetch 40 filings from SEC EDGAR
    ↓ Multi-tier parser (EdgarTools + Tiers 1.5-4)
  Extract financial + qualitative data (98.55% quality)
    ↓ Store in PostgreSQL + MinIO
  Business/Financial/Strategy Agents analyze
```

**Target**: 0 hours screening backfill, cost TBD based on API selection

---

## Options Considered

### Option 1: Third-Party API Only (No SEC Parsing)

**Description**: Use third-party financial data API for all stages (screening + deep analysis)

**Pros**:

- Simplest implementation (single data source)
- No parsing complexity
- Immediate availability
- Potentially low cost

**Cons**:

- **No qualitative data**: Missing MD&A, risk factors, business descriptions (Phase 2 requirement)
- **No amendment tracking**: Can't detect restatement patterns (QC Agent requirement)
- **No context disambiguation**: Unknown if consolidated vs parent-only (data quality risk)
- **Unknown historical depth**: May not have full 10Y quarterly data for all companies
- **No validation control**: Can't implement balance sheet checks, false positive detection
- **No learning capability**: Black box, can't improve over time
- **Quality concerns**: May be insufficient for deep analysis (need 98.55%)

**Estimated Effort**: 2-3 days integration (varies by provider)

---

### Option 2: SEC EDGAR Only (No Third-Party Aggregated Data)

**Description**: Parse all SEC filings upfront for screening + deep analysis (original plan per DD-031)

**Pros**:

- Single authoritative data source (SEC)
- Full control over quality, validation, edge case handling
- Qualitative data available from start
- Amendment tracking, context disambiguation
- Learning capability via multi-tier recovery

**Cons**:

- **4.2 hour upfront backfill** before screening can start (20K filings)
- **$88 upfront cost** (vs $0 for Yahoo Finance screening)
- **Complexity upfront**: Need full parser implementation in Phase 1
- **Slower iteration**: Can't validate screening logic until backfill complete

**Estimated Effort**: 10 days (per DD-031, data-collector-implementation.md)

---

### Option 3: Hybrid Approach (Third-Party API + SEC EDGAR) - CHOSEN

**Description**: Use third-party financial data API for screening (Days 1-2), SEC EDGAR parsing for deep analysis (Days 3-7, on-demand after Gate 1)

**Pros**:

- **Faster MVP**: Screening starts immediately (no backfill wait)
- **Lower cost**: Potentially lower than upfront parsing for all companies
- **Right tool for job**: Speed for screening, quality for analysis (98.55%)
- **Reduced upfront complexity**: Don't need full parser until Phase 2
- **Smaller parsing volume**: Only ~10-20 companies/month pass Gate 1 (vs 500 companies upfront)
- **Still get all critical data**: Qualitative sections, amendments, validation for approved companies

**Cons**:

- **Two data sources**: Screening uses third-party API, analysis uses SEC (consistency risk)
- **API dependency**: If API degrades, screening blocked
- **Screening quality**: Quality varies by provider vs 98.55% if parsed SEC
- **Still need SEC parser**: Can't eliminate DD-031 complexity, just defer volume

**Estimated Effort**:

- Third-party API integration: 2-3 days (varies by provider)
- SEC parser: 10 days (same as DD-031, but triggered later)
- **Total**: Same timeline, but screening unblocked earlier

---

### Option 4: Commercial Tools (Calcbench, sec-api.io)

**Description**: Use paid APIs for pre-processed financial data

**Pros**:

- Vendor handles parsing complexity
- Pre-normalized data
- Minimal development effort

**Cons**:

- **Cost**: $20K-$50K/year (Calcbench), $1K-$5K+ (sec-api.io)
- **Black box**: Can't customize for edge cases
- **No qualitative data**: Most vendors provide financials only (not MD&A, risk factors)
- **No amendment tracking**: Typically only latest restated data
- **Vendor lock-in**: Can't implement learning loop or custom validation

**Estimated Effort**: 2-3 days integration, but $20K+ annual cost

---

## Rationale

### Key Decision Factors

**1. Different Quality Needs at Different Stages**:

- **Screening**: 95% quality acceptable (rejected companies don't matter if data slightly off)
- **Deep analysis**: 98.55% quality critical (bad data leads to wrong investment decisions)
- Hybrid approach optimizes for each stage's requirements

**2. Cost-Benefit Analysis**:

- Third-party API screening: TBD (varies by provider)
- SEC parsing for 10-20 companies/month: $3-$6/month (vs $88 for 20K upfront)
- **Total**: TBD based on API selection vs $88 upfront (original plan)

**3. Time to Value**:

- Third-party API: Immediate (screening starts Day 1, subject to integration)
- SEC backfill: 4.2 hours delay before screening possible
- **Hybrid wins**: Unblocks screening, defers parsing cost

**4. Data Requirements by Stage**:

| Requirement            | Screening | Deep Analysis | 3rd Party API? | SEC Has? |
| ---------------------- | --------- | ------------- | -------------- | -------- |
| Revenue, EPS, margins  | ✅        | ✅            | Likely ✅      | ✅       |
| 10Y history            | ✅        | ✅            | Varies         | ✅       |
| Quarterly granularity  | ❌        | ✅            | Varies         | ✅       |
| MD&A, risk factors     | ❌        | ✅            | ❌             | ✅       |
| Amendment tracking     | ❌        | ✅            | ❌             | ✅       |
| Context disambiguation | ❌        | ✅            | ❌             | ✅       |
| Data validation        | ❌        | ✅            | ❌             | ✅       |

**Conclusion**: Third-party APIs typically cover screening needs, not deep analysis unique needs

**5. Volume Economics**:

- Screening: All S&P 500 (500 companies) → Third-party API bulk fetch efficient
- Deep analysis: ~10-20 companies/month pass Gate 1 → SEC parsing on-demand efficient
- Parsing all 500 upfront is wasteful when only 2-4% proceed to analysis

### Tradeoffs Accepted

**Pro-Hybrid**:

1. Faster screening (immediate vs 4.2hr backfill)
2. Lower cost (~$10/month vs $88 upfront)
3. Simpler Phase 1 (defer parser complexity)
4. Right quality for each stage

**Con-Hybrid**:

1. Two data sources (consistency risk) → **Mitigation**: Mark `data_source` in PostgreSQL, QC Agent can flag discrepancies
2. API dependency for screening → **Mitigation**: Fallback to SEC parsing if API degrades
3. Screening quality varies by provider → **Mitigation**: Lenient thresholds to avoid false negatives; high-stakes decisions use SEC data anyway
4. Still need SEC parser → **Mitigation**: True, but volume reduced 25x (20 companies/month vs 500 upfront)

---

## Consequences

### Positive Impacts

- **Immediate screening capability**: No 4.2hr backfill wait
- **Lower upfront cost**: Depends on API selection vs $88 for 20K filings
- **Reduced parsing volume**: 10-20 companies/month vs 500 companies upfront (25x reduction)
- **Simpler Phase 1**: Can validate screening logic without building full parser first
- **Preserved data quality**: Deep analysis still gets 98.55% quality, amendments, qualitative data
- **Flexibility**: If API insufficient, can fall back to SEC parsing for screening

### Negative Impacts / Tradeoffs

- **Data source inconsistency**: Screening uses API, analysis uses SEC → Need to track source in database
- **API dependency**: Screening blocked if API degrades → Need fallback strategy
- **Screening quality**: Quality varies by provider vs 98.55% from SEC
- **Can't eliminate SEC parser**: Still need DD-031 multi-tier parser, just defer volume

### Affected Components

**New Components**:

- `src/data_collector/financial_api_client.py`: API client for bulk financial data fetch (provider TBD)
- `src/agents/screening/api_data_adapter.py`: Map API fields to screening metrics
- `tests/integration/test_financial_api.py`: Validate 10Y data availability for S&P 500

**Updated Components**:

- `src/storage/postgres_client.py`: Add `data_source` field ('financial_api' | 'sec_edgar')
- `plans/data-collector-implementation.md`: Phase C updated to use financial API for screening
- `CLAUDE.md`: Data Sources section updated with hybrid approach

**Unchanged Components** (from DD-031):

- SEC parser still needed (EdgarTools + Tiers 1.5-4)
- Multi-tier recovery system still required
- PostgreSQL schema, MinIO structure unchanged

---

## Implementation Notes

### Technical Details

**Financial API Integration (Screening)**:

```python
# API provider TBD - placeholder implementation
from financial_api_client import FinancialDataClient

client = FinancialDataClient(api_key=config.api_key)

# Fetch 10Y financials for S&P 500
for ticker in sp500_tickers:
    # Fetch data from API (implementation varies by provider)
    financials = await client.get_financials(ticker, years=10)

    # Calculate screening metrics
    revenue_10y_cagr = calculate_cagr(financials.revenue, 10)
    operating_margin = financials.operating_income / financials.revenue
    roe = calculate_roe(financials)

    # Store in PostgreSQL with data_source='financial_api'
    await postgres.insert_financial_data(
        ticker=ticker,
        metrics={'revenue_cagr_10y': revenue_10y_cagr, ...},
        data_source='financial_api'
    )
```

**SEC Parsing (Deep Analysis, on-demand after Gate 1)**:

```python
# After Human Gate 1 approves Company X
approved_tickers = ['AAPL', 'MSFT', ...]  # From Gate 1

for ticker in approved_tickers:
    # Fetch 40 filings (10 years × 4 quarters)
    filings = await edgar_client.get_company_filings(
        ticker=ticker,
        form_types=['10-K', '10-Q'],
        years=10
    )

    # Multi-tier parsing (per DD-031)
    for filing in filings:
        data = await filing_parser.parse(filing)  # Tiers 0-4

        # Store in PostgreSQL with data_source='sec_edgar'
        await postgres.insert_financial_data(
            ticker=ticker,
            data=data,
            data_source='sec_edgar'
        )

        # Store raw filing in MinIO
        await s3_client.upload_filing(filing)
```

**Data Source Tracking**:

```sql
-- PostgreSQL schema addition
ALTER TABLE financial_data.income_statements
ADD COLUMN data_source VARCHAR(20) DEFAULT 'sec_edgar';

-- Query latest data (preferring SEC over third-party API)
SELECT * FROM financial_data.income_statements
WHERE ticker = 'AAPL'
  AND is_latest = true
ORDER BY CASE data_source WHEN 'sec_edgar' THEN 1 ELSE 2 END, period_end_date DESC
LIMIT 1;
```

**Fallback Strategy**:

1. **If API degrades**:

   - Log warning, attempt retry (3x with backoff)
   - If persistent failure: Fall back to SEC parsing for screening
   - Notify human: "Financial API unavailable, screening using SEC data (slower)"

2. **If data quality issues detected**:
   - QC Agent compares API screening data vs SEC deep analysis data
   - Flag discrepancies >10% (e.g., revenue differs significantly)
   - Log patterns for monitoring and provider evaluation

**Testing Requirements**:

- Validate API has 10Y data for all S&P 500 companies
- Measure data quality: Compare API vs SEC for 100 random companies
- Test fallback: Disable API, verify SEC parsing fallback works
- Performance: Measure API bulk fetch latency vs SEC parsing latency

**Rollback Strategy**:

- If API insufficient: Switch to SEC parsing for screening (use DD-031 implementation)
- If cost becomes issue: Evaluate alternative providers or switch to SEC-only
- If data quality unacceptable: Increase screening threshold leniency or switch to SEC

**Estimated Implementation Effort**: 2-3 days (varies by API provider selection)

**Dependencies**:

- Financial API selection and library integration (provider TBD)
- PostgreSQL schema update (add `data_source` column)
- SEC parser from DD-031 (deferred to after Gate 1, not blocking screening)

---

## Open Questions

1. **Financial API provider selection**: Which option provides best coverage for 10Y historical data at scale?

   - **Evaluation criteria**: Data coverage, quality, cost, rate limits, ease of integration
   - **Options to evaluate**: Various commercial and open-source financial data APIs
   - **Blocking**: Yes - must select provider before implementation

2. **Screening summary requirements**: Do summaries need qualitative business context ("operates in 3 segments, expanding internationally") or just quantitative metrics ("18% 10Y CAGR, 12% margin, ROE 15%")?

   - **Impact**: If qualitative context required, may need SEC filings even for screening
   - **Blocking**: No - can start with quantitative summaries, add qualitative later if needed

3. **Data transition strategy**: When company moves from screening → deep analysis, do we:

   - **Option A**: Re-fetch all 10Y data from SEC, discard API data (cleanest)
   - **Option B**: Keep API screening data, augment with SEC qualitative sections only
   - **Option C**: Use API for screening metrics, SEC for all deep analysis (complete replacement)
   - **Blocking**: No - recommend Option C (complete replacement) for consistency

4. **Fallback strategy specifics**: If API degrades, do we:
   - **Option A**: Pause screening until API recovers
   - **Option B**: Fall back to SEC parsing for screening (slower but functional)
   - **Option C**: Use cached API data from previous fetch (stale but fast)
   - **Blocking**: No - recommend Option B (SEC fallback) for resilience

---

## References

### Financial Data API Options (TBD)

- Various commercial and open-source providers to be evaluated
- Selection criteria: data coverage, quality, cost, rate limits, ease of integration

### Industry Benchmarks

- Third-party aggregated data quality: ~95% (industry standard)
- SEC EDGAR data quality: 98.55% achievable with multi-tier parsing (DD-031)
- Typical screening false negative rate: 2-5% acceptable (can adjust thresholds)

### Related Decisions

- **DD-031**: SEC Filing Parser Tool Selection (EdgarTools + multi-tier recovery)
- **Phase C Backfill**: data-collector-implementation.md Section 3 (updated to use Yahoo Finance)
- **Screening Agent Requirements**: docs/architecture/03-agents-specialist.md (quantitative screens)

---

## Status History

| Date       | Status       | Notes                                                  |
| ---------- | ------------ | ------------------------------------------------------ |
| 2025-11-20 | Proposed     | Research completed, recommendation drafted             |
| 2025-11-20 | Under Review | API provider selection pending, hybrid approach chosen |

---

## Notes

### Cost-Benefit Summary (Monthly Ongoing)

| Approach            | Screening Cost | Deep Analysis Cost   | Total/Month | Data Quality        |
| ------------------- | -------------- | -------------------- | ----------- | ------------------- |
| **Hybrid (Chosen)** | TBD (API)      | $3-$6 (SEC 10-20 co) | **TBD**     | Varies → 98.55%     |
| API only            | TBD            | TBD                  | TBD         | Varies (all stages) |
| SEC only (original) | $0             | Amortized $88/20K    | ~$5         | 98.55% (all stages) |
| Commercial          | $1K-$5K+       | $1K-$5K+             | $1K-$5K+    | Provider-dependent  |

**Winner**: Hybrid (best balance of cost, speed, quality per stage, pending API selection)

**Note**: SEC-only has lowest cost long-term, but hybrid wins on time-to-value (immediate screening vs 4.2hr backfill) and defers complexity.

### Future Considerations

- **Phase 2 optimization**: After validating screening accuracy, may refine API vs SEC data source strategy
- **API monitoring**: Set up alerts for API degradation, rate limit violations
- **Data quality tracking**: QC Agent logs API vs SEC discrepancies to inform future sourcing decisions
- **Alternative consideration**: If API insufficient, can switch to SEC parsing for screening (DD-031 already designed)
- **Provider evaluation**: Ongoing assessment of API alternatives as market evolves
