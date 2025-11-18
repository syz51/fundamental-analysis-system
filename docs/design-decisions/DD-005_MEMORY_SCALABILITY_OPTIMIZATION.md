# Memory Scalability Optimization

**Status**: Approved
**Date**: 2025-11-17
**Decider(s)**: System Architect
**Related Docs**: [Memory System](../architecture/02-memory-system.md), [System Overview](../architecture/01-system-overview.md), [Knowledge Base Agent](../architecture/04-agents-support.md), [Tech Requirements](../implementation/02-tech-requirements.md)
**Related Decisions**: DD-002 (Event-Driven Memory Sync)
**Resolves**: [Flaw #7: Memory Scalability](../design-flaws/resolved/07-memory-scalability.md)

---

## Context

System targets ambitious scale (1000+ stocks, <24hr analysis) with performance requirements that become mathematically impossible without optimization:

```yaml
Target Performance:
  Memory Retrieval: <500ms (p95)
  Memory Utilization: >90% of decisions use historical context
  Scale: 1000+ stocks analyzed

Reality at Scale (5 years, 15K analyses):
  Graph traversal queries: 2-5 seconds (4-10× over budget)
  Pattern matching: 500-2,500ms (linear growth with patterns)
  Credibility calculation: 800ms+ (linear growth with history)
  Total per analysis: 2,800ms+ (5-6× over budget)
```

**Critical Bottlenecks Identified**:

1. **Graph Query Explosion**: Variable-length path traversal (`*1..3`) explores 23^3 = 12,167 possible paths per node at scale → 1,500-8,000ms queries

2. **Pattern Matching Overhead**: O(n) growth with pattern count (50ms at 100 patterns → 2,500ms at 5K patterns)

3. **Agent Credibility Calculation**: Full scan of agent history (100ms at 1K decisions → 800ms at 10K decisions)

**Impact**: Each analysis requires 3-5 memory queries. At 4 parallel agents × 5 queries × 3 seconds = 60 seconds memory overhead per analysis. Breaks <24hr pipeline target.

---

## Decision

**Implement 6-strategy optimization framework to achieve revised performance targets:**

1. Query optimization & indexing (pre-computed similarity, materialized views)
2. Tiered caching strategy (L1/L2/L3 with cache warming)
3. Query budget enforcement (500ms hard timeout with fallbacks)
4. Incremental updates (credibility scoring without full scans)
5. Parallel query execution (concurrent memory fetches)
6. Memory pruning strategy (archive >2yr memories, keep <50K active nodes)

**Revised Performance Targets**:

| Metric             | Original  | Revised                        |
| ------------------ | --------- | ------------------------------ |
| Memory retrieval   | <500ms    | <200ms cached, <500ms uncached |
| Memory utilization | >90%      | >85%                           |
| Cache hit rate     | N/A       | >80%                           |
| Graph size         | Unlimited | <50K active nodes              |

Tech stack deferred to implementation phase (requires extensive research for production-ready solutions).

---

## Consequences

### Positive Impacts

- **Performance**: 10-15× faster queries at scale (<200ms vs 2-5s)
- **Scalability**: Supports 1000+ stock target without pipeline degradation
- **Reliability**: Query timeouts prevent runaway queries from blocking analysis
- **Efficiency**: 80%+ cache hit rate eliminates redundant expensive queries
- **Memory hygiene**: Pruning keeps graph manageable, prevents unbounded growth

### Negative Impacts / Tradeoffs

- **Complexity**: Multi-tier caching, indexing, pruning = significant infrastructure & code complexity
- **Approximation**: Timeout fallbacks may return approximate/cached results (slightly stale or incomplete)
- **Memory utilization**: Reduced from >90% to >85% target (some queries may timeout)
- **Infrastructure cost**: L1/L2 cache layers require additional compute/storage resources
- **Maintenance**: Index rebuilds, cache warming, pruning require ongoing operational overhead
- **Dev effort**: 4-6 weeks implementation across multiple phases

### Affected Components

- **Memory System (02-memory-system.md)**: Enhanced with caching layers, query optimization, pruning
- **Knowledge Base Agent (04-agents-support.md)**: Add query budgets, timeout handling, cache warming
- **All Specialist Agents**: Consume memory through optimized layer (transparent change)
- **System Overview (01-system-overview.md)**: Updated performance constraints
- **Tech Requirements (02-tech-requirements.md)**: Add caching infra, monitoring metrics
- **Roadmap (01-roadmap.md)**: Phase 3 benchmarking, optimization tasks

---

## Implementation Strategies

### 1. Query Optimization & Indexing

**Pre-Computed Similarity Index**:

- Compute pairwise analysis similarities offline (nightly/weekly batch)
- Store top-K similar analyses per company (e.g., top 10)
- Query becomes simple lookup vs expensive graph traversal
- Reduces 2-5s graph traversal → <50ms index lookup

**Materialized Views**:

- Top patterns by sector
- Agent credibility scores (cached, incrementally updated)
- Company history summaries

**Index Rebuild Strategy**:

- Incremental updates during day (new analyses added)
- Full rebuild weekly (recalculate similarities, prune stale entries)
- Offline batch process, minimal impact on runtime queries

### 2. Tiered Caching Strategy

**3-Layer Cache Architecture**:

```text
L1 Cache (Hot, <10ms):
  - Recent/frequent queries
  - 1hr TTL, 500MB max
  - Tech: In-memory cache (Redis, Memcached, or equivalent)

L2 Cache (Warm, <50ms):
  - Local LRU cache per agent
  - 10K entry limit
  - Tech: In-process memory

L3 Storage (Cold, <500ms):
  - Full knowledge graph
  - Persistent storage
  - Tech: Graph database or equivalent
```

**Cache Warming**:

- Before analysis starts, predictively load likely queries:
  - `similar_analyses:{company}`
  - `sector_patterns:{sector}`
  - `company_history:{company}`
  - `peer_comparisons:{sector}`
- Async pre-loading minimizes runtime cache misses

**Cache Invalidation**:

- L1: TTL-based (1hr)
- L2: LRU eviction
- L3: Always fresh (source of truth)

### 3. Query Budget Enforcement

**Hard 500ms Timeout**:

- All memory queries wrapped with timeout enforcement
- If query exceeds budget, return fallback result

**Fallback Strategies**:

- Approximate result: Top-5 instead of top-10 similar analyses
- Cached result: Return stale cached data (marked with timestamp)
- Sampling: Return subset of pattern matches (e.g., 50% sample)

**Monitoring**:

- Track timeout frequency by query type
- Alert if >5% queries timeout (indicates need for optimization)

### 4. Incremental Updates

**Agent Credibility Scoring**:

- Current: Full scan of agent history on each query (O(n) with decision count)
- Optimized: Incremental update with decay-based averaging

```python
# Conceptual approach (not implementation):
# Instead of recalculating from all historical decisions,
# update incrementally when new decision added:
new_score = (current_score * count * decay_factor + new_accuracy) / (count * decay_factor + 1)
```

**Reduces**: 800ms full scan → <10ms incremental update

### 5. Parallel Query Execution

**Concurrent Memory Fetches**:

- Each analysis needs multiple memory queries (similar analyses, patterns, history, precedents)
- Execute all in parallel vs sequential
- Fail gracefully if individual query fails (don't block entire analysis)

**Performance Gain**:

- Sequential: 5 queries × 200ms = 1,000ms
- Parallel: max(5 queries) = 200ms (5× faster)

### 6. Memory Pruning Strategy

**Archive Threshold**: >2 years old

**Pruning Criteria** (must meet 2+ to prune):

- Age >2 years
- Access frequency <3 (rarely used)
- Relevance score <0.3
- Superseded by better/newer memory

**Summarization Before Archive**:

- Extract key findings, outcome, lessons learned
- Store lightweight summary in active graph
- Archive full detail to cold storage (S3, warehouse, or equivalent)

**Graph Size Target**: <50K active nodes

**Pruning Frequency**: Monthly review of pruning candidates

---

## Benchmarking Requirements

Before implementing optimizations, establish baseline performance and validate assumptions:

### 1. Graph Query Performance

**Test Scenarios**:

- 100 analyses (MVP scale)
- 1,000 analyses (Beta scale)
- 5,000 analyses (Production scale)
- 15,000 analyses (5-year scale)

**Queries to Benchmark**:

```cypher
# Variable-length path traversal (similarity search)
MATCH (a:Analysis)-[:SIMILAR_TO*1..3]-(similar:Analysis)
WHERE a.company = 'MSFT' AND similarity_score > 0.8
RETURN similar
ORDER BY similarity_score DESC
LIMIT 10
```

**Expected Results** (per Flaw #7 analysis):

- 100 analyses: ~100ms
- 1K analyses: ~500ms
- 5K analyses: ~1,500ms
- 15K analyses: ~5,000ms

**Validates**: Graph query explosion hypothesis

### 2. Pattern Matching Performance

**Test Scenarios**:

- 100 patterns
- 1,000 patterns
- 5,000 patterns

**Benchmark**: Time to match all patterns against new analysis (O(n) linear search)

**Expected Results**:

- 100 patterns: ~50ms
- 1K patterns: ~500ms
- 5K patterns: ~2,500ms

**Validates**: Pattern matching overhead hypothesis

### 3. Credibility Calculation Performance

**Test Scenarios**:

- 1,000 decisions per agent
- 10,000 decisions per agent

**Benchmark**: Time to compute agent credibility score via full historical scan

**Expected Results**:

- 1K decisions: ~100ms
- 10K decisions: ~800ms

**Validates**: Credibility calculation bottleneck hypothesis

### 4. End-to-End Memory Overhead

**Test Scenario**: Complete analysis with realistic memory usage

**Benchmark**:

- Run 1 analysis with 5 memory queries (similar, patterns, history, sector, precedents)
- Measure total memory overhead

**Expected Results**:

- Without optimization: 5 queries × 500-3,000ms = 2,500-15,000ms
- Target with optimization: 5 queries × 50-200ms (parallel) = 50-200ms

**Validates**: Overall performance improvement target (10-15× speedup)

### 5. Cache Hit Rate Validation

**Test Scenario**: Run 10 analyses sequentially on related companies (same sector)

**Benchmark**:

- Measure cache hit rate for sector patterns, peer comparisons
- Expected: 60-80% hit rate after first analysis (subsequent analyses reuse cached data)

**Validates**: Cache effectiveness assumption

### Benchmark Execution Plan

1. **Phase 1 (Months 1-2)**: Baseline benchmarks with minimal data
2. **Phase 3 (Months 5-6)**: Re-benchmark at beta scale (50 stocks, ~150 analyses)
3. **Phase 4 (Months 7-8)**: Re-benchmark at production scale (200 stocks, ~600 analyses)
4. **Phase 5 (Month 12)**: Stress test at target scale (1000 stocks, ~3K analyses)

### Success Criteria

- Confirm bottlenecks match predictions (graph queries, pattern matching, credibility calc)
- Validate optimization impact (>10× speedup on slow queries)
- Identify unexpected bottlenecks early (before production deployment)

---

## Implementation Timeline

**Phase 1 (Months 1-2)**: Baseline & Infrastructure

- Establish benchmarking harness
- Run baseline performance tests
- Set up monitoring infrastructure

**Phase 2 (Months 3-4)**: MVP - No Optimization

- Build core system without optimizations
- Validate baseline performance at MVP scale (10 stocks)
- Identify first bottlenecks

**Phase 3 (Months 5-6)**: Optimization Deployment

- Implement tiered caching (L1/L2/L3)
- Deploy query indexing (pre-computed similarities)
- Add query budget enforcement (timeouts)
- Re-benchmark at beta scale (50 stocks)

**Phase 4 (Months 7-8)**: Advanced Optimization

- Implement incremental credibility updates
- Build similarity index rebuild pipeline
- Deploy parallel query execution
- Implement pruning strategy

**Phase 5 (Months 9-12)**: Tuning & Validation

- Tune cache parameters (TTLs, sizes)
- Optimize index rebuild frequency
- Validate at production scale (200-1000 stocks)
- A/B test optimization strategies

---

## Open Questions

1. **Cache technology selection**: Redis vs Memcached vs in-process cache? Requires research on production use cases, performance, operational complexity

2. **Graph database choice**: Neo4j vs PostgreSQL+pgvector vs other? Need to evaluate query performance, scalability, operational maturity

3. **Index rebuild frequency**: Nightly vs weekly vs on-demand? Monitor staleness tolerance vs rebuild overhead

4. **Pruning aggressiveness**: 2yr threshold sufficient or need 3yr for rare patterns? Validate with historical pattern frequencies in Phase 3-4

5. **Approximation acceptability**: When queries timeout, how accurate do fallback results need to be? Need user research on quality vs speed tradeoffs

**Blocking**: No - can proceed with conservative defaults (e.g., popular open-source tech, weekly rebuilds, 2yr pruning). Tune based on operational data.

---

## References

- [Flaw #7: Memory Scalability](../design-flaws/resolved/07-memory-scalability.md) - Original problem analysis with detailed math
- [Memory System Architecture](../architecture/02-memory-system.md) - Updated with optimization strategies
- [System Overview](../architecture/01-system-overview.md) - Performance targets
- [Knowledge Base Agent](../architecture/04-agents-support.md) - Query budget implementation
- [Tech Requirements](../implementation/02-tech-requirements.md) - Infrastructure specs
- [Roadmap](../implementation/01-roadmap.md) - Phased optimization deployment
- DD-002 (Event-Driven Memory Sync) - Related memory system enhancement

---

## Status History

| Date       | Status   | Notes                                                    |
| ---------- | -------- | -------------------------------------------------------- |
| 2025-11-17 | Proposed | Resolving Flaw #7 memory scalability                     |
| 2025-11-17 | Approved | Approved by system architect with tech-agnostic approach |

---

## Notes

**Tech-Agnostic Approach**: Specific technologies (Redis, Neo4j, etc.) not finalized. Requires extensive research during implementation phase to evaluate production-grade options. Design decisions focus on architectural strategies (caching, indexing, pruning) that apply regardless of specific tech choices.

**Benchmarking Before Implementation**: Critical to validate assumptions with real data before committing to optimization strategies. Baseline benchmarks confirm bottlenecks, validate projected performance improvements.

**Graceful Degradation**: Query timeouts with fallback results ensure system continues functioning even if individual queries slow. Prefers approximate/stale results over blocking entire analysis pipeline.

**Pruning Philosophy**: 2yr threshold with summarization balances long-term memory retention (institutional knowledge) with graph scalability (performance). Rare high-value patterns get extensions via adaptive probation (see DD-004 Gate 6 parameter optimization).

**Conservative Targets**: Revised memory utilization (85% vs 90%) and cache hit rate (80%) provide buffer for real-world variability. Better to under-promise and over-deliver than commit to impossible targets.
