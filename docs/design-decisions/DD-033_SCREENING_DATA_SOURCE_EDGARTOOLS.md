# Screening Data Source: EdgarTools vs Third-Party APIs

**Status**: Approved
**Date**: 2025-11-23
**Decider(s)**: System Architect
**Related Docs**: `plans/edgartools-screening-implementation.md`, `plans/simfin-integration-plan.md` (archived)
**Related Decisions**: DD-031 (SEC Filing Parser Tool Selection), DD-032 (Hybrid Data Sourcing Strategy)

---

## Context

Screening Agent (Days 1-2) requires financial data for S&P 500 companies to filter candidates using quantitative metrics (10Y revenue CAGR, margins, ROE/ROA/ROIC, debt ratios). DD-032 proposed hybrid approach: third-party API for screening, SEC EDGAR for deep analysis (Days 3-7).

**Research Question**: Should we use third-party aggregated data API (SimFin, Finnhub, etc.) for screening, or use SEC EDGAR (EdgarTools) for both screening and deep analysis?

**Key Considerations**:

- DD-031 already selected EdgarTools + multi-tier system for deep analysis
- Budget constraint: $0-$50/month
- Performance target: <10 min for S&P 500 screening
- Quality requirement: 95%+ for screening, 98.55% for deep analysis

**SimFin Evaluation**:

- **Cost**: $15/month (START tier) for 10Y historical data
- **Pattern**: Bulk download ALL US companies → local filtering
- **Rationale**: Pre-normalized data, pre-calculated ratios, immediate availability

**Critical Discovery**: EdgarTools supports **on-demand per-company queries** (not just bulk download), fundamentally changing the cost-benefit analysis.

---

## Decision

**Use EdgarTools for BOTH screening and deep analysis (unified data source approach)**

Abandon hybrid two-source strategy. Parse SEC filings directly for screening using EdgarTools on-demand queries. No third-party aggregated data APIs needed.

**Architecture**:

```text
Screening Stage (Days 1-2):
  EdgarTools on-demand queries
    ↓ Query 500 S&P companies (2.5-5 min, 10 req/sec)
  Calculate screening metrics locally
    ↓ Revenue CAGR, margins, ROE/ROA/ROIC, debt ratios
  Filter candidates
    ↓ 10-20 companies pass criteria
  Human Gate 1 (select candidates)

Deep Analysis Stage (Days 3-7, after Gate 1):
  Same EdgarTools infrastructure
    ↓ Fetch 10Y historical filings (40 per company)
  Multi-tier parser (Tiers 0-4, 98.55% quality)
    ↓ Extract financials + qualitative sections
  Business/Financial/Strategy Agents analyze
```

**Cost**: $0/month (free SEC EDGAR API)
**Performance**: 2.5 min for S&P 500 screening (at 10 req/sec rate limit)

---

## Options Considered

### Option 1: SimFin START Tier ($15/month) for Screening

**Description**: Use SimFin API for screening (Days 1-2), EdgarTools for deep analysis (Days 3-7)

**Pros**:

- Pre-normalized field names (save ~2hr mapping US-GAAP tags)
- Pre-calculated ratios (ROE, ROA, margins) - save ~4hr implementation
- Ready pandas DataFrames (save ~2hr structuring)
- Built-in caching (convenience)

**Cons**:

- **$180/year cost** (vs $0 for EdgarTools)
- **Still need EdgarTools** for deep analysis (two data sources)
- **ROIC not included** (need manual calculation anyway)
- **Bulk download pattern** (must download 5,000+ US stocks, not just S&P 500)
- **Data consistency risk** (screening uses SimFin, analysis uses SEC)
- **No learning capability** (black box, can't improve over time)
- **Vendor lock-in**
- **No qualitative data** (if needed for screening summaries)

**SimFin Pattern**:

```python
# Bulk download ALL US companies
hub = sf.StockHub(market='us', refresh_days=7)
df = hub.fin_signals()  # Downloads 5,000+ companies

# Filter to S&P 500 locally
sp500_data = df.loc[sp500_tickers]
candidates = sp500_data[screening_criteria]
```

**Estimated Cost**: $180/year + EdgarTools parser development
**Estimated Effort**: 2-3 days integration + 10 days EdgarTools (same as Option 2)

---

### Option 2: EdgarTools for Both Screening and Deep Analysis (CHOSEN)

**Description**: Use EdgarTools on-demand queries for screening, same tool for deep analysis (unified approach)

**Pros**:

- **$0 cost** (free SEC EDGAR API, already building parser per DD-031)
- **Single authoritative source** (no data consistency risk)
- **On-demand queries** (query only 500 S&P companies, not 5,000+ US stocks)
- **Faster screening** (2.5 min at 10 req/sec vs SimFin 5 min bulk download)
- **Full control** (customize edge cases, validation, learning loops)
- **98.55% quality** (same multi-tier system for both stages)
- **Learning capability** (QC Agent improves parser per DD-031)
- **No vendor lock-in**
- **Qualitative data available** (MD&A, risk factors if needed for summaries)
- **Already building it** (no additional integration work)

**Cons**:

- Need to implement field standardization (~2hr)
- Need to implement ratio calculators (~4hr, but required for ROIC anyway)
- Slightly more upfront dev work (~1 day vs buying pre-made API)

**EdgarTools Pattern**:

```python
# Query individual companies on-demand
for ticker in sp500_tickers:  # Only 500, not 5,000+
    company = Company(ticker)
    financials = company.get_financials()  # API call to SEC

    # Calculate metrics locally
    revenue_cagr = calculate_cagr(financials.get_revenue(), 10)
    roe = calculate_roe(financials)
    roic = calculate_roic(financials)

    if meets_criteria(revenue_cagr, roe, roic):
        candidates.append(ticker)
```

**Estimated Cost**: $0/year
**Estimated Effort**: 10 days (same as DD-031, no additional work)

---

### Option 3: Finnhub Free Tier for Screening

**Description**: Use Finnhub free API (60 calls/min) for screening, EdgarTools for deep analysis

**Pros**:

- Free ($0 cost)
- Pre-aggregated data

**Cons**:

- **Rate limit**: 60 calls/min = 1 call/sec (500 companies = 8.3 min minimum)
- **Unknown data coverage** (10Y historical available for all S&P 500?)
- **Unknown quality** (no documented quality guarantees)
- **Still need EdgarTools** (two data sources, consistency risk)
- **API reliability unknown**
- **Additional integration effort** (2-3 days)

**Estimated Cost**: $0/year + EdgarTools parser development
**Estimated Effort**: 2-3 days integration + 10 days EdgarTools

---

### Option 4: Commercial Tools (Calcbench, sec-api.io)

**Description**: Use paid commercial API for pre-processed financial data

**Pros**:

- Vendor handles all parsing
- High-quality data (typically)

**Cons**:

- **Prohibitive cost**: $1K-$50K/year (vs $0 SEC EDGAR)
- **Outside budget constraint** ($0-$50/month)
- Black box (no customization)
- Vendor lock-in

**Estimated Cost**: $1K-$50K/year
**Estimated Effort**: 2-3 days integration

---

## Rationale

### Key Decision Factors

**1. EdgarTools Supports On-Demand Queries (Critical Discovery)**

**Previous assumption**: EdgarTools requires bulk download like SimFin
**Reality**: EdgarTools supports selective per-company API queries

| Feature                 | SimFin                      | EdgarTools                         |
| ----------------------- | --------------------------- | ---------------------------------- |
| **Pattern**             | Bulk download ALL companies | On-demand per-company queries      |
| **For S&P 500**         | Download 5,000+ US stocks   | Query only 500 needed companies    |
| **Selective retrieval** | ❌ No                       | ✅ Yes                             |
| **First run time**      | 5 min (bulk)                | 2.5 min (500 queries @ 10 req/sec) |
| **Wasted bandwidth**    | 4,500 non-S&P companies     | 0                                  |
| **Rate limit**          | 5 req/sec (START tier)      | 10 req/sec (SEC limit)             |

**Conclusion**: SimFin's primary advantage ("no bulk download") is invalidated. EdgarTools also supports on-demand queries and is faster.

**2. Cost-Benefit Analysis**

**SimFin value proposition**: Save ~8 hours dev time (field mapping + ratio calculators)
**SimFin cost**: $180/year

**Effective hourly rate**: $180 ÷ 8 hours = $22.50/hour

**ROIC calculation**: Required for both approaches (SimFin free tier doesn't provide, need manual calc or upgrade to BASIC $420/year)

**Comparison**:

| Approach                 | Upfront Dev                           | Annual Cost | 3-Year TCO |
| ------------------------ | ------------------------------------- | ----------- | ---------- |
| **EdgarTools (Chosen)**  | 10 days                               | $0          | **$0**     |
| SimFin START             | 9 days (saved 1 day)                  | $180        | $540       |
| SimFin BASIC (with ROIC) | 8 days (saved 2 days)                 | $420        | $1,260     |
| Finnhub free             | 12 days (2d integration + 10d parser) | $0          | $0         |

**Decision**: In design phase, 1 day saved (~$200 value at $25/hr) doesn't justify $180/year recurring cost.

**3. Data Source Consistency**

**Hybrid approach (SimFin + EdgarTools)**:

- Screening uses SimFin data
- Deep analysis uses SEC EDGAR data
- **Risk**: Discrepancies between sources (QC Agent must reconcile)
- **Complexity**: Track `data_source` field, handle conflicts

**Unified approach (EdgarTools only)**:

- Single source of truth (SEC EDGAR)
- No reconciliation needed
- Consistent quality across pipeline

**4. Quality Requirements**

| Stage         | Quality Needed  | SimFin                     | EdgarTools                          |
| ------------- | --------------- | -------------------------- | ----------------------------------- |
| Screening     | 95% acceptable  | ~95% (varies by provider)  | 95% (Tier 0) or 98.55% (multi-tier) |
| Deep Analysis | 98.55% critical | N/A (switch to EdgarTools) | 98.55% (multi-tier)                 |

**Option**: Use EdgarTools Tier 0 only for screening (95%, fast), full multi-tier for deep analysis (98.55%)

**5. Learning Capability**

**SimFin**: Black box, no improvement over time
**EdgarTools**: QC Agent learns from failures, improves parser (DD-031 design)

**6. No Additional Integration Work**

**SimFin**: 2-3 days integration + 10 days EdgarTools (already needed) = **12-13 days total**
**EdgarTools only**: 10 days (per DD-031) = **10 days total**

**Winner**: EdgarTools (2-3 days saved)

**7. Performance**

**S&P 500 screening (500 companies)**:

| Metric            | SimFin START                           | EdgarTools                         |
| ----------------- | -------------------------------------- | ---------------------------------- |
| First run         | 5 min (bulk download 5,000+ companies) | 2.5 min (query 500 @ 10 req/sec)   |
| Repeat run        | <1 min (cached)                        | <1 min (HTTP cache 10 min TTL)     |
| Bulk cache option | Mandatory                              | Optional (`download_edgar_data()`) |

**Winner**: EdgarTools (faster, more efficient)

### Tradeoffs Accepted

**Pro-EdgarTools**:

1. $180/year saved (vs SimFin)
2. Single source of truth (no consistency risk)
3. Full control & learning capability
4. Faster screening (2.5 min vs 5 min)
5. More efficient (query 500, not 5,000+ companies)
6. No additional integration work

**Con-EdgarTools**:

1. Implement field standardization (~2hr)
2. Implement ratio calculators (~4hr, but ROIC needed anyway)
3. ~1 day additional upfront dev (vs buying pre-made)

**Verdict**: Cons are one-time costs, pros are recurring benefits. EdgarTools wins decisively.

---

## Consequences

### Positive Impacts

- **$180/year saved** (vs SimFin START) or **$420/year saved** (vs SimFin BASIC with ROIC)
- **2-3 days dev time saved** (no separate API integration, EdgarTools already planned)
- **Single source of truth** (SEC EDGAR for all stages, no data reconciliation)
- **Faster screening** (2.5 min vs 5 min, 10 req/sec vs 5 req/sec)
- **More efficient** (query 500 companies, not 5,000+)
- **Learning capability** (QC Agent improves parser, vs black box API)
- **Full control** (customize edge cases, validation, quality checks)
- **Higher quality** (98.55% available for screening if needed vs ~95% SimFin)
- **No vendor lock-in**
- **Qualitative data available** (MD&A, risk factors if needed for screening summaries)

### Negative Impacts / Tradeoffs

- **~1 day additional upfront dev** (field mapping + ratio calculators)
- **ROIC calculation required** (but same as SimFin free/START tier)
- **Slightly steeper learning curve** (XBRL concepts vs pre-made API)

### Affected Components

**No New Components** (using DD-031 infrastructure):

- `src/data_collector/filing_parser.py` (already planned)
- `src/data_collector/validation.py` (already planned)
- EdgarTools dependency (already added per DD-031)

**New Screening-Specific Components**:

- `src/screening/metrics_calculator.py`: Calculate CAGR, margins, ratios from EdgarTools data
- `src/screening/field_mapper.py`: Map US-GAAP XBRL concepts to standardized field names
- `src/screening/screener.py`: Screening logic using EdgarTools queries
- `tests/unit/test_metrics_calculator.py`: Unit tests for ratio calculations

**Updated Components**:

- `plans/data-collector-implementation.md`: Remove SimFin integration, use EdgarTools for screening
- `docs/design-decisions/DD-032_HYBRID_DATA_SOURCING.md`: Mark as superseded by DD-033
- `CLAUDE.md`: Update Data Sources section (EdgarTools for all stages)

**Archived Plans**:

- `plans/simfin-integration-plan.md` → Archive (no longer pursuing)

---

## Implementation Notes

### Technical Details

**EdgarTools Screening Workflow**:

```python
from edgar import Company, set_identity

# 1. Setup (SEC requirement)
set_identity("your.email@example.com")

# 2. Define S&P 500 universe
sp500_tickers = get_sp500_tickers()  # From Wikipedia or static file

# 3. Query companies on-demand
candidates = []
for ticker in sp500_tickers:
    try:
        # On-demand API query
        company = Company(ticker)
        financials = company.get_financials()

        if not financials:
            continue

        # Calculate screening metrics
        metrics = {
            'revenue_cagr_10y': calculate_revenue_cagr(financials, years=10),
            'operating_margin_3y': calculate_avg_margin(
                financials.income.operating_income,
                financials.income.revenue,
                years=3
            ),
            'net_margin_3y': calculate_avg_margin(
                financials.income.net_income,
                financials.income.revenue,
                years=3
            ),
            'roe_3y': calculate_avg_roe(financials, years=3),
            'roa_3y': calculate_avg_roa(financials, years=3),
            'roic_3y': calculate_avg_roic(financials, years=3),
            'debt_to_equity': calculate_debt_to_equity(financials.balance),
            'current_ratio': calculate_current_ratio(financials.balance)
        }

        # Apply screening criteria
        if (metrics['revenue_cagr_10y'] > 0.08 and
            metrics['operating_margin_3y'] > 0.10 and
            metrics['roe_3y'] > 0.15 and
            metrics['roic_3y'] > 0.12 and
            metrics['debt_to_equity'] < 0.5):
            candidates.append({'ticker': ticker, **metrics})

    except Exception as e:
        logger.error(f"Failed to process {ticker}: {e}")
        continue

# 4. Output candidates for Human Gate 1
print(f"Found {len(candidates)} candidates from {len(sp500_tickers)} companies")
```

**Metric Calculation Examples**:

```python
def calculate_revenue_cagr(financials, years: int = 10) -> float:
    """Calculate N-year revenue CAGR."""
    revenue_series = financials.income.revenue.tail(years)
    start = revenue_series.iloc[0]
    end = revenue_series.iloc[-1]
    return (end / start) ** (1 / years) - 1

def calculate_avg_roe(financials, years: int = 3) -> float:
    """Calculate N-year average ROE."""
    net_income = financials.income.net_income.tail(years)
    equity = financials.balance.stockholders_equity.tail(years)
    roe = net_income / equity
    return roe.mean()

def calculate_avg_roic(financials, years: int = 3) -> float:
    """Calculate N-year average ROIC."""
    # NOPAT = Net Income + Interest Expense × (1 - Tax Rate)
    net_income = financials.income.net_income.tail(years)
    interest_expense = financials.income.interest_expense.tail(years)
    tax_rate = 0.21  # Corporate tax rate
    nopat = net_income + interest_expense * (1 - tax_rate)

    # Invested Capital = Total Debt + Total Equity - Cash
    debt = financials.balance.total_debt.tail(years)
    equity = financials.balance.stockholders_equity.tail(years)
    cash = financials.balance.cash.tail(years)
    invested_capital = debt + equity - cash

    roic = nopat / invested_capital
    return roic.mean()
```

**Field Mapping (US-GAAP → Standard Names)**:

```python
FIELD_MAPPING = {
    # Income Statement
    'Revenues': 'revenue',
    'RevenueFromContractWithCustomerExcludingAssessedTax': 'revenue',
    'OperatingIncomeLoss': 'operating_income',
    'NetIncomeLoss': 'net_income',
    'InterestExpense': 'interest_expense',

    # Balance Sheet
    'Assets': 'total_assets',
    'StockholdersEquity': 'stockholders_equity',
    'LiabilitiesAndStockholdersEquity': 'total_liabilities_equity',
    'DebtCurrent': 'current_debt',
    'LongTermDebt': 'long_term_debt',
    'CashAndCashEquivalentsAtCarryingValue': 'cash',

    # Cash Flow
    'NetCashProvidedByUsedInOperatingActivities': 'operating_cash_flow',
    'NetCashProvidedByUsedInInvestingActivities': 'investing_cash_flow',
    'NetCashProvidedByUsedInFinancingActivities': 'financing_cash_flow'
}
```

**Performance Optimization**:

```python
# Optional: Enable bulk caching for repeated analysis
from edgar import download_edgar_data, use_local_storage

# One-time: Download bulk data (~2.6GB)
download_edgar_data()

# Enable local cache (~/.edgar/)
use_local_storage()

# Now queries are instant (read from local cache)
# Useful for:
# - Daily/weekly screening runs
# - Experimenting with different criteria
# - Offline analysis
```

**Testing Requirements**:

- Validate 500 S&P companies can be queried successfully
- Measure actual screening time (target <10 min, expect 2.5-5 min)
- Verify data completeness (≥95% for screening)
- Test metric calculations (spot-check 10 companies vs known values)
- Benchmark cached vs non-cached performance

**Rollback Strategy**:

- If EdgarTools insufficient: Fall back to SimFin START tier (plan already documented)
- If SEC rate limits problematic: Enable bulk caching + run screening offline
- If data quality issues: Use full multi-tier parser for screening (slower but 98.55%)

**Estimated Implementation Effort**: 10 days (same as DD-031, no additional work)

**Dependencies**:

- EdgarTools 3.0.0+ (already added per DD-031)
- SEC EDGAR API access (free, 10 req/sec rate limit)
- S&P 500 ticker list (Wikipedia or static file)

---

## Open Questions

1. ✅ **RESOLVED**: Does EdgarTools require bulk download or support on-demand queries?

   - **Answer**: Supports both. On-demand by default, bulk caching optional for performance.

2. ✅ **RESOLVED**: How long does S&P 500 screening take with EdgarTools?

   - **Answer**: 2.5 min at 10 req/sec, 5 min at 5 req/sec (conservative CAUTION mode)

3. ✅ **RESOLVED**: Is SimFin worth $180/year for convenience?

   - **Answer**: No. EdgarTools saves ~$180/year with only 1 day additional dev time.

4. **OPEN**: Should we use Tier 0 only (95% quality, faster) or full multi-tier (98.55%, slower) for screening?

   - **Recommendation**: Tier 0 for screening (95% acceptable), full multi-tier for deep analysis
   - **Blocking**: No - can start with Tier 0, upgrade if quality insufficient

5. **OPEN**: Cache strategy - enable bulk caching upfront or rely on auto HTTP cache?
   - **Recommendation**: Start with auto HTTP cache (10 min TTL), enable bulk caching if running daily
   - **Blocking**: No - can optimize later based on usage patterns

---

## References

### Research Sources

**EdgarTools**:

- GitHub: <https://github.com/dgunning/edgartools>
- Documentation: <https://github.com/dgunning/edgartools/wiki>
- Performance: 10-30x faster than alternatives (lxml + PyArrow optimization)
- Rate handling: NORMAL (high-performance) / CAUTION (5 req/sec) / CRAWL (bulk) modes

**SimFin**:

- Website: <https://simfin.com>
- Pricing: FREE (5Y data), START ($15/mo, 10Y), BASIC ($35/mo, 15Y + derived ratios)
- Documentation: <https://simfin.readthedocs.io/>
- Pattern: Bulk download via `StockHub`, local Parquet caching

**SEC EDGAR API**:

- Rate limit: 10 requests/second (enforced via IP blocking)
- Cost: Free
- Authoritative source (no intermediary)

### Industry Benchmarks

- Third-party data quality: ~95% (industry standard)
- EdgarTools baseline: 95% (Tier 0 only)
- Multi-tier system: 98.55% (per DD-031)
- Screening false negative tolerance: 2-5% acceptable

### Related Decisions

- **DD-031**: SEC Filing Parser Tool Selection (EdgarTools + multi-tier)
- **DD-032**: Hybrid Data Sourcing Strategy (superseded by DD-033)
- **Data Collector Plan**: `plans/data-collector-implementation.md` (updated for screening)

---

## Status History

| Date       | Status   | Notes                                                |
| ---------- | -------- | ---------------------------------------------------- |
| 2025-11-23 | Proposed | Research completed on SimFin vs EdgarTools           |
| 2025-11-23 | Approved | Decision to use EdgarTools for unified data sourcing |

---

## Notes

### Cost-Benefit Summary (3-Year Analysis)

| Approach                | Upfront Dev | Annual Cost | 3-Year TCO | Data Quality     |
| ----------------------- | ----------- | ----------- | ---------- | ---------------- |
| **EdgarTools (Chosen)** | 10 days     | **$0**      | **$0**     | 95% → 98.55%     |
| SimFin START            | 9 days      | $180        | $540       | ~95% (screening) |
| SimFin BASIC (ROIC)     | 8 days      | $420        | $1,260     | ~95% (screening) |
| Finnhub free            | 12 days     | $0          | $0         | Unknown          |
| Calcbench               | 2 days      | $20K+       | $60K+      | Unknown          |

**Winner**: EdgarTools (lowest TCO, highest quality, full control)

### Performance Summary

| Metric                 | SimFin START                   | EdgarTools                       |
| ---------------------- | ------------------------------ | -------------------------------- |
| S&P 500 screening time | 5 min (first), <1 min (cached) | 2.5 min (first), <1 min (cached) |
| Rate limit             | 5 req/sec                      | 10 req/sec                       |
| Companies downloaded   | 5,000+ (all US)                | 500 (S&P only)                   |
| Wasted bandwidth       | 4,500 non-needed               | 0                                |
| Cache size             | Large (all companies)          | Minimal (queried only)           |

**Winner**: EdgarTools (faster, more efficient)

### Future Considerations

- **Bulk caching**: Enable `download_edgar_data()` if running daily screening
- **Multi-tier for screening**: Upgrade from Tier 0 (95%) to full multi-tier (98.55%) if quality insufficient
- **Alternative APIs**: Keep SimFin as fallback option if SEC EDGAR rate limits become problematic
- **Commercial tools**: Re-evaluate if budget expands significantly (>$1K/month)
- **Data monitoring**: Track screening quality, adjust strategy if needed
