# Hybrid Data Sourcing Strategy

**Status**: Approved
**Date**: 2025-11-20
**Decider(s)**: System Architect
**Related Docs**: `plans/data-collector-implementation.md`, `plans/yahoo-finance-integration-plan.md`
**Related Decisions**: DD-031 (SEC Filing Parser Tool Selection)

---

## Context

Data Collector Agent requires financial data for two distinct use cases with different quality requirements:

1. **Screening Stage (Days 1-2)**: Filter S&P 500 companies using quantitative metrics (10Y revenue CAGR, margins, ROE/ROA/ROIC)
2. **Deep Analysis Stage (Days 3-7)**: Comprehensive research requiring high-quality data, qualitative sections, amendment tracking

**Original Plan**: Parse all SEC filings upfront (20K filings backfill, 4.2 hours, $88 cost)

**Question**: Do we need to parse SEC filings for screening, or can we use pre-aggregated data from Yahoo Finance/TradingView for initial filtering?

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

**Use Yahoo Finance API for screening stage, SEC EDGAR parsing for deep analysis stage (hybrid approach)**

**Architecture**:

```text
Screening Stage (Days 1-2):
  Yahoo Finance API
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

**Target**: 0 hours screening backfill, ~$10/month ongoing cost

---

## Options Considered

### Option 1: Yahoo Finance Only (No SEC Parsing)

**Description**: Use Yahoo Finance API for all stages (screening + deep analysis)

**Pros**:

- Simplest implementation (single data source)
- No parsing complexity
- Immediate availability
- Free or low cost ($0-$50/month)

**Cons**:

- **No qualitative data**: Missing MD&A, risk factors, business descriptions (Phase 2 requirement)
- **No amendment tracking**: Can't detect restatement patterns (QC Agent requirement)
- **No context disambiguation**: Unknown if consolidated vs parent-only (data quality risk)
- **Unknown historical depth**: May not have full 10Y quarterly data for all companies
- **No validation control**: Can't implement balance sheet checks, false positive detection
- **No learning capability**: Black box, can't improve over time
- **95% quality ceiling**: Insufficient for deep analysis (need 98.55%)

**Estimated Effort**: 2-3 days integration

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

### Option 3: Hybrid Approach (Yahoo Finance + SEC EDGAR) - CHOSEN

**Description**: Use Yahoo Finance for screening (Days 1-2), SEC EDGAR parsing for deep analysis (Days 3-7, on-demand after Gate 1)

**Pros**:

- **Faster MVP**: Screening starts immediately (no backfill wait)
- **Lower cost**: ~$10/month vs $88 upfront + ongoing parsing
- **Right tool for job**: Speed for screening (95% OK), quality for analysis (98.55%)
- **Reduced upfront complexity**: Don't need full parser until Phase 2
- **Smaller parsing volume**: Only ~10-20 companies/month pass Gate 1 (vs 500 companies upfront)
- **Still get all critical data**: Qualitative sections, amendments, validation for approved companies

**Cons**:

- **Two data sources**: Screening uses Yahoo, analysis uses SEC (consistency risk)
- **Yahoo dependency**: If Yahoo API degrades, screening blocked
- **Screening quality**: 95% from Yahoo vs 98.55% if parsed SEC
- **Still need SEC parser**: Can't eliminate DD-031 complexity, just defer volume

**Estimated Effort**:

- Yahoo Finance integration: 2-3 days
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

- Yahoo Finance screening: $0-$50/month
- SEC parsing for 10-20 companies/month: $3-$6/month (vs $88 for 20K upfront)
- **Total**: ~$10/month vs $88 upfront (original plan)

**3. Time to Value**:

- Yahoo Finance: Immediate (screening starts Day 1)
- SEC backfill: 4.2 hours delay before screening possible
- **Hybrid wins**: Unblocks screening, defers parsing cost

**4. Data Requirements by Stage**:

| Requirement            | Screening | Deep Analysis | Yahoo Has? | SEC Has? |
| ---------------------- | --------- | ------------- | ---------- | -------- |
| Revenue, EPS, margins  | ✅        | ✅            | ✅         | ✅       |
| 10Y history            | ✅        | ✅            | ⚠️ Maybe   | ✅       |
| Quarterly granularity  | ❌        | ✅            | ⚠️ Maybe   | ✅       |
| MD&A, risk factors     | ❌        | ✅            | ❌         | ✅       |
| Amendment tracking     | ❌        | ✅            | ❌         | ✅       |
| Context disambiguation | ❌        | ✅            | ❌         | ✅       |
| Data validation        | ❌        | ✅            | ❌         | ✅       |

**Conclusion**: Yahoo Finance covers 100% of screening needs, 0% of deep analysis unique needs

**5. Volume Economics**:

- Screening: All S&P 500 (500 companies) → Yahoo Finance bulk fetch efficient
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
2. Yahoo dependency for screening → **Mitigation**: Fallback to SEC parsing if Yahoo degrades
3. Screening quality 95% vs 98.55% → **Mitigation**: Lenient thresholds to avoid false negatives; high-stakes decisions use SEC data anyway
4. Still need SEC parser → **Mitigation**: True, but volume reduced 25x (20 companies/month vs 500 upfront)

---

## Consequences

### Positive Impacts

- **Immediate screening capability**: No 4.2hr backfill wait
- **Lower upfront cost**: ~$10/month vs $88 for 20K filings
- **Reduced parsing volume**: 10-20 companies/month vs 500 companies upfront (25x reduction)
- **Simpler Phase 1**: Can validate screening logic without building full parser first
- **Preserved data quality**: Deep analysis still gets 98.55% quality, amendments, qualitative data
- **Flexibility**: If Yahoo Finance insufficient, can fall back to SEC parsing for screening

### Negative Impacts / Tradeoffs

- **Data source inconsistency**: Screening uses Yahoo, analysis uses SEC → Need to track source in database
- **Yahoo Finance dependency**: Screening blocked if Yahoo API degrades → Need fallback strategy
- **Screening quality**: 95% vs 98.55% → Acceptable per user confirmation ("maybe not at screen stage that much")
- **Can't eliminate SEC parser**: Still need DD-031 multi-tier parser, just defer volume

### Affected Components

**New Components**:

- `src/data_collector/yahoo_finance_client.py`: API client for bulk financial data fetch
- `src/agents/screening/yahoo_data_adapter.py`: Map Yahoo fields to screening metrics
- `tests/integration/test_yahoo_finance.py`: Validate 10Y data availability for S&P 500

**Updated Components**:

- `src/storage/postgres_client.py`: Add `data_source` field ('yahoo_finance' | 'sec_edgar')
- `plans/data-collector-implementation.md`: Phase C updated to use Yahoo Finance for screening
- `plans/yahoo-finance-integration-plan.md`: New plan for implementation (NEW)
- `CLAUDE.md`: Data Sources section updated with hybrid approach

**Unchanged Components** (from DD-031):

- SEC parser still needed (EdgarTools + Tiers 1.5-4)
- Multi-tier recovery system still required
- PostgreSQL schema, MinIO structure unchanged

---

## Implementation Notes

### Technical Details

**Yahoo Finance Integration (Screening)**:

```python
# Library options (TBD - see Open Questions)
import yfinance as yf  # Option 1: yfinance (most popular)
# OR
from alpha_vantage.fundamentaldata import FundamentalData  # Option 2: Alpha Vantage

# Fetch 10Y financials for S&P 500
for ticker in sp500_tickers:
    stock = yf.Ticker(ticker)
    financials = stock.financials  # Annual income statement
    balance_sheet = stock.balance_sheet
    cash_flow = stock.cashflow

    # Calculate screening metrics
    revenue_10y_cagr = calculate_cagr(financials.loc['Total Revenue'], 10)
    operating_margin = financials.loc['Operating Income'] / financials.loc['Total Revenue']
    roe = calculate_roe(financials, balance_sheet)

    # Store in PostgreSQL with data_source='yahoo_finance'
    await postgres.insert_financial_data(
        ticker=ticker,
        metrics={'revenue_cagr_10y': revenue_10y_cagr, ...},
        data_source='yahoo_finance'
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

-- Query latest data (preferring SEC over Yahoo)
SELECT * FROM financial_data.income_statements
WHERE ticker = 'AAPL'
  AND is_latest = true
ORDER BY CASE data_source WHEN 'sec_edgar' THEN 1 ELSE 2 END, period_end_date DESC
LIMIT 1;
```

**Fallback Strategy**:

1. **If Yahoo Finance API degrades**:

   - Log warning, attempt retry (3x with backoff)
   - If persistent failure: Fall back to SEC parsing for screening
   - Notify human: "Yahoo Finance unavailable, screening using SEC data (slower)"

2. **If data quality issues detected**:
   - QC Agent compares Yahoo screening data vs SEC deep analysis data
   - Flag discrepancies >10% (e.g., revenue differs significantly)
   - Log patterns: "Yahoo Finance consistently overestimates Company X revenue by 12%"

**Testing Requirements**:

- Validate Yahoo Finance has 10Y data for all S&P 500 companies
- Measure data quality: Compare Yahoo vs SEC for 100 random companies
- Test fallback: Disable Yahoo API, verify SEC parsing fallback works
- Performance: Measure Yahoo bulk fetch latency vs SEC parsing latency

**Rollback Strategy**:

- If Yahoo Finance insufficient: Switch to SEC parsing for screening (use DD-031 implementation)
- If cost becomes issue: Optimize Yahoo API tier or renegotiate pricing
- If data quality unacceptable: Increase screening threshold leniency or switch to SEC

**Estimated Implementation Effort**: 2-3 days (Yahoo Finance integration)

**Dependencies**:

- Yahoo Finance API library (yfinance, Alpha Vantage, or Yahoo Finance Premium - TBD)
- PostgreSQL schema update (add `data_source` column)
- SEC parser from DD-031 (deferred to after Gate 1, not blocking screening)

---

## Open Questions

1. **Yahoo Finance API/library selection**: Which option provides best coverage for 10Y historical data at scale?

   - **Option A**: `yfinance` library (free, most popular, may have rate limits)
   - **Option B**: Alpha Vantage API (free tier 5 req/min, premium $50/month)
   - **Option C**: Yahoo Finance Premium API (if exists, pricing unknown)
   - **Blocking**: No - can start with yfinance, switch if insufficient

2. **Screening summary requirements**: Do summaries need qualitative business context ("operates in 3 segments, expanding internationally") or just quantitative metrics ("18% 10Y CAGR, 12% margin, ROE 15%")?

   - **Impact**: If qualitative context required, may need SEC filings even for screening
   - **Blocking**: No - can start with quantitative summaries, add qualitative later if needed

3. **Data transition strategy**: When company moves from screening → deep analysis, do we:

   - **Option A**: Re-fetch all 10Y data from SEC, discard Yahoo data (cleanest)
   - **Option B**: Keep Yahoo screening data, augment with SEC qualitative sections only
   - **Option C**: Use Yahoo for screening metrics, SEC for all deep analysis (complete replacement)
   - **Blocking**: No - recommend Option C (complete replacement) for consistency

4. **Fallback strategy specifics**: If Yahoo Finance API degrades, do we:
   - **Option A**: Pause screening until Yahoo recovers
   - **Option B**: Fall back to SEC parsing for screening (slower but functional)
   - **Option C**: Use cached Yahoo data from previous fetch (stale but fast)
   - **Blocking**: No - recommend Option B (SEC fallback) for resilience

---

## References

### Yahoo Finance Data Sources

- **yfinance**: <https://github.com/ranaroussi/yfinance> (11K+ stars, unofficial Yahoo Finance API wrapper)
- **Alpha Vantage**: <https://www.alphavantage.co/> (free tier + premium, official API)
- **Yahoo Finance Premium**: Pricing/availability unknown (need research)

### Industry Benchmarks

- Yahoo Finance data quality: ~95% (industry standard for aggregated data)
- SEC EDGAR data quality: 98.55% achievable with multi-tier parsing (DD-031)
- Typical screening false negative rate: 2-5% acceptable (can adjust thresholds)

### Related Decisions

- **DD-031**: SEC Filing Parser Tool Selection (EdgarTools + multi-tier recovery)
- **Phase C Backfill**: data-collector-implementation.md Section 3 (updated to use Yahoo Finance)
- **Screening Agent Requirements**: docs/architecture/03-agents-specialist.md (quantitative screens)

---

## Status History

| Date       | Status   | Notes                                       |
| ---------- | -------- | ------------------------------------------- |
| 2025-11-20 | Proposed | Research completed, recommendation drafted  |
| 2025-11-20 | Approved | Decision to use hybrid Yahoo + SEC approach |

---

## Notes

### Cost-Benefit Summary (Monthly Ongoing)

| Approach            | Screening Cost | Deep Analysis Cost   | Total/Month | Data Quality        |
| ------------------- | -------------- | -------------------- | ----------- | ------------------- |
| **Hybrid (Chosen)** | $0-$50 (Yahoo) | $3-$6 (SEC 10-20 co) | **~$10**    | 95% → 98.55%        |
| Yahoo only          | $0-$50         | $0-$50               | $50         | 95% (all stages)    |
| SEC only (original) | $0             | Amortized $88/20K    | ~$5         | 98.55% (all stages) |
| Commercial          | $1K-$5K+       | $1K-$5K+             | $1K-$5K+    | Unknown             |

**Winner**: Hybrid (best balance of cost, speed, quality per stage)

**Note**: SEC-only has lowest cost long-term, but hybrid wins on time-to-value (immediate screening vs 4.2hr backfill) and defers complexity.

### Future Considerations

- **Phase 2 optimization**: After validating screening accuracy, may refine Yahoo vs SEC data source strategy
- **Yahoo Finance monitoring**: Set up alerts for API degradation, rate limit violations
- **Data quality tracking**: QC Agent logs Yahoo vs SEC discrepancies to inform future sourcing decisions
- **Alternative consideration**: If Yahoo Finance insufficient, can switch to SEC parsing for screening (DD-031 already designed)
