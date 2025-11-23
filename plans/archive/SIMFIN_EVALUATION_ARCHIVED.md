# SimFin Integration Plan - ARCHIVED

**Date Archived**: 2025-11-23
**Reason**: Superseded by DD-033 (EdgarTools screening decision)
**Decision**: DD-033_SCREENING_DATA_SOURCE_EDGARTOOLS.md

---

## Summary

SimFin was evaluated as a potential data source for screening S&P 500 companies. After comprehensive research comparing SimFin vs EdgarTools, the decision was made to use EdgarTools for both screening and deep analysis.

## Key Findings

**SimFin Approach**:

- Cost: $180/year (START tier)
- Pattern: Bulk download all US companies → local filtering
- Pros: Pre-normalized data, pre-calculated ratios
- Cons: Cost, bulk download inefficiency, no ROIC in free tier, vendor lock-in

**EdgarTools Approach** (CHOSEN):

- Cost: $0/year
- Pattern: On-demand per-company queries
- Pros: Free, faster, single source of truth, full control, learning capability
- Cons: Need to implement field mapping + ratio calculators (~1 day extra dev)

## Decision Rationale

1. **Cost**: Save $180/year with only 1 extra day of development
2. **Efficiency**: EdgarTools queries only 500 needed companies vs SimFin downloads 5,000+
3. **Performance**: 2.5 min screening (EdgarTools @ 10 req/sec) vs 5 min (SimFin @ 5 req/sec)
4. **Consistency**: Single SEC EDGAR source for all stages (no data reconciliation)
5. **Already building**: DD-031 already selected EdgarTools for deep analysis

## References

- **Research**: Comprehensive SimFin API research (2025-11-23)
- **Decision**: DD-033_SCREENING_DATA_SOURCE_EDGARTOOLS.md
- **Implementation**: plans/edgartools-screening-implementation.md

## Original Plan Location

Original SimFin integration plan was documented in research but not implemented. Details preserved in DD-033 Option 1 analysis.
