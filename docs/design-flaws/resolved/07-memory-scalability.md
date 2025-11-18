---
flaw_id: 7
title: Memory Scalability vs Performance Targets
status: resolved
priority: high
phase: 3
effort_weeks: 4
impact: Performance targets achievable with optimization framework
blocks: []
depends_on: ['#2 event-driven sync', 'operational agents']
domain: ['memory']
resolved: 2025-11-17
resolution: DD-005 Memory Scalability Optimization
---

# Flaw #7: Memory Scalability vs Performance Targets

**Status**: RESOLVED ✅ (2025-11-17)
**Priority**: High
**Impact**: Performance targets achievable with 6-strategy optimization framework
**Resolution**: [DD-005: Memory Scalability Optimization](../../design-decisions/DD-005_MEMORY_SCALABILITY_OPTIMIZATION.md)

---

## 7. Memory Scalability vs Performance Targets

### Problem Description

**Current State**: System targets ambitious scale with contradictory performance requirements.

From v2.0 Appendix E:

```yaml
Memory System Metrics:
  Memory Retrieval Speed: <500ms
  Memory Utilization: >90

Key Milestones:
  Scale-up (Month 12): 1000+ stocks
```

### The Math Problem

**Graph Complexity Growth**:

```text
Knowledge Graph Size:
  - 1000 stocks
  - Average 3 analyses per stock = 3,000 analyses
  - Each analysis links to:
    * 1 company node
    * 5 pattern nodes (avg)
    * 1 decision node
    * 1 outcome node
    * 5 agent nodes (avg)
    * 10 related analyses (similar companies, precedents)

  Relationships per analysis: ~23
  Total relationships: 3,000 × 23 = 69,000 relationships

After 3 years:
  - 1000 stocks × 3 analyses/year × 3 years = 9,000 analyses
  - 9,000 × 23 = 207,000 relationships

After 5 years:
  - 15,000 analyses
  - 345,000 relationships
```

**Query Performance**:

Typical memory query:

```cypher
MATCH (a:Analysis)-[:SIMILAR_TO*1..3]-(similar:Analysis)
WHERE a.company = 'MSFT'
  AND similarity_score > 0.8
RETURN similar, similar.outcome, similar.lessons_learned
ORDER BY similarity_score DESC
LIMIT 10
```

**Problem**:

- Graph traversal with `*1..3` (up to 3 hops)
- At 15,000 analyses: explores exponentially growing paths
- Each node has ~23 edges → 23^3 = 12,167 possible paths per start node
- Query time: 2-5 seconds (exceeds 500ms target by 4-10×)

**Memory Utilization Conflict**:

- Target: >90% of decisions use historical context
- Reality: If retrieval takes 2-5 seconds per query
- Each analysis needs 3-5 memory queries
- Total memory overhead: 6-25 seconds per analysis
- Phase 2 (parallel analysis) runs 4 agents simultaneously
- 4 agents × 5 queries × 3 seconds = 60 seconds memory overhead
- Doesn't fit in 12-day timeline

### Specific Performance Bottlenecks

**1. Graph Query Explosion**:

```python
# This query gets slower as graph grows
def find_similar_analyses(self, company):
    # Variable-length path traversal
    similar = self.graph_db.query("""
        MATCH (c:Company {ticker: $ticker})-[:HAS_ANALYSIS]->(a:Analysis)
        MATCH (a)-[:SIMILAR_TO*1..3]-(similar:Analysis)
        WHERE similarity_score > 0.8
        RETURN similar
    """, ticker=company)

    # At 1000 stocks: ~100ms
    # At 10,000 analyses: ~1,500ms (exceeds budget)
    # At 50,000 analyses: ~8,000ms (unusable)
```

**2. Pattern Matching Overhead**:

```python
# Matching patterns for new analysis
def match_patterns(self, analysis):
    patterns = self.kb.get_all_patterns()  # Could be 1000+ patterns

    matches = []
    for pattern in patterns:  # O(n) per analysis
        if pattern.matches(analysis):  # Complex matching logic
            matches.append(pattern)

    # At 100 patterns: ~50ms
    # At 1000 patterns: ~500ms (at budget limit)
    # At 5000 patterns: ~2,500ms (exceeds budget)
```

**3. Agent Credibility Calculation**:

```python
# Calculate credibility for each agent on each decision
def get_agent_credibility(self, agent, context):
    # Scans all historical agent decisions
    historical = self.kb.get_agent_decisions(agent.id)  # Could be 10,000+

    # Filter by context
    relevant = [d for d in historical if d.context_matches(context)]

    # Calculate accuracy
    accuracy = sum(d.accuracy for d in relevant) / len(relevant)

    # At 1000 decisions per agent: ~100ms
    # At 10,000 decisions per agent: ~800ms (exceeds budget)
```

### Impact Assessment

| Bottleneck         | Current | At Scale    | Impact                      |
| ------------------ | ------- | ----------- | --------------------------- |
| Graph queries      | 100ms   | 1,500ms+    | Misses 500ms target by 3×   |
| Pattern matching   | 50ms    | 500-2,500ms | Linear growth with patterns |
| Credibility calc   | 100ms   | 800ms       | Linear growth with history  |
| Total per analysis | 250ms   | 2,800ms+    | Exceeds budget by 5-6×      |

### Recommended Solution

#### 1. Query Optimization & Indexing

```python
class OptimizedKnowledgeGraph:
    """Optimized graph queries with caching and indexing"""

    def __init__(self):
        # Pre-computed indexes
        self.similarity_index = {}  # company -> [similar_analyses]
        self.pattern_index = {}     # pattern_id -> [matching_analyses]
        self.sector_index = {}      # sector -> [analyses]

        # Materialized views
        self.top_patterns_by_sector = {}
        self.agent_credibility_cache = {}

        # Query budget enforcement
        self.max_query_time_ms = 500

    def find_similar_analyses_optimized(self, company, max_results=10):
        """Optimized similarity search"""

        # Check cache first
        cache_key = f"similar:{company}:{max_results}"
        if cache_key in self.similarity_index:
            return self.similarity_index[cache_key]

        # Use pre-computed similarity matrix instead of graph traversal
        similar = self.similarity_matrix.get_top_k(
            company,
            k=max_results,
            min_score=0.8
        )

        # Cache result
        self.similarity_index[cache_key] = similar

        return similar

    def build_similarity_index(self):
        """Pre-compute similarity graph (runs offline)"""

        all_analyses = self.kb.get_all_analyses()

        # Compute pairwise similarities (batch process)
        similarity_matrix = np.zeros((len(all_analyses), len(all_analyses)))

        for i, analysis_i in enumerate(all_analyses):
            for j, analysis_j in enumerate(all_analyses[i+1:], start=i+1):
                similarity = self.compute_similarity(analysis_i, analysis_j)
                similarity_matrix[i,j] = similarity
                similarity_matrix[j,i] = similarity

        # Store top-K for each analysis
        for i, analysis in enumerate(all_analyses):
            top_k_indices = np.argsort(similarity_matrix[i])[-11:-1]  # Top 10 (excluding self)
            top_k_scores = similarity_matrix[i][top_k_indices]

            self.similarity_matrix.store(
                analysis.id,
                similar_ids=[all_analyses[j].id for j in top_k_indices],
                scores=top_k_scores
            )

        # Rebuild index nightly or weekly
        self.last_index_build = now()
```

#### 2. Tiered Caching Strategy

```python
class TieredMemoryCache:
    """Multi-level cache for memory operations"""

    def __init__(self):
        # L1: Hot cache (Redis, <10ms access)
        self.l1_cache = RedisCache(
            ttl_seconds=3600,  # 1 hour
            max_size_mb=500
        )

        # L2: Warm cache (Local memory, <50ms access)
        self.l2_cache = LRUCache(
            max_size=10000
        )

        # L3: Cold storage (Neo4j, <500ms access)
        self.l3_storage = Neo4jKnowledgeGraph()

    async def get_memory(self, key, query_fn):
        """Tiered cache lookup"""

        # Try L1 (fastest)
        result = await self.l1_cache.get(key)
        if result:
            return result

        # Try L2
        result = self.l2_cache.get(key)
        if result:
            # Promote to L1
            await self.l1_cache.set(key, result)
            return result

        # Fall back to L3 (slowest)
        result = await query_fn()  # Execute actual query

        # Cache in all tiers
        self.l2_cache.set(key, result)
        await self.l1_cache.set(key, result)

        return result

    def warm_cache_for_analysis(self, company):
        """Pre-load cache before analysis starts"""

        # Predict what memory queries will be needed
        likely_queries = [
            f"similar_analyses:{company}",
            f"sector_patterns:{company.sector}",
            f"company_history:{company}",
            f"peer_comparisons:{company.sector}"
        ]

        # Load into cache asynchronously
        for query in likely_queries:
            self.preload_to_cache(query)
```

#### 3. Query Budget Enforcement

```python
class QueryBudgetEnforcer:
    """Ensure queries stay within time budget"""

    def __init__(self):
        self.max_query_time_ms = 500
        self.max_concurrent_queries = 10

    async def execute_with_budget(self, query_fn, fallback_fn=None):
        """Execute query with timeout"""

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                query_fn(),
                timeout=self.max_query_time_ms / 1000  # Convert to seconds
            )
            return result

        except asyncio.TimeoutError:
            # Query exceeded budget
            self.log_budget_violation(query_fn)

            if fallback_fn:
                # Use cheaper fallback
                return await fallback_fn()
            else:
                # Return cached/approximate result
                return self.get_approximate_result(query_fn)

    def get_approximate_result(self, query_fn):
        """Return approximate result when exact query too slow"""

        # Use sampling or approximation
        # E.g., instead of finding all similar analyses,
        # return top 5 from cache

        query_type = self.identify_query_type(query_fn)

        if query_type == 'similarity':
            # Return top 5 instead of top 10
            return self.cached_top_results(query_fn, limit=5)

        elif query_type == 'pattern_match':
            # Use top-K patterns instead of all patterns
            return self.top_k_patterns(k=100)

        else:
            # Generic approximation
            return self.sample_results(query_fn, sample_rate=0.5)
```

#### 4. Incremental Updates Instead of Full Scans

```python
class IncrementalMemoryUpdate:
    """Update memory incrementally instead of full scans"""

    def update_agent_credibility_incremental(self, agent, new_decision):
        """Update credibility without rescanning all history"""

        # Load current credibility from cache
        current = self.cache.get(f"credibility:{agent.id}")

        if not current:
            # First time - must compute from scratch
            current = self.compute_credibility_full(agent)

        # Incremental update
        updated = self.incremental_credibility_update(
            current_score=current.score,
            current_count=current.decision_count,
            new_decision_accuracy=new_decision.accuracy,
            decay_factor=0.98  # Slight decay of old decisions
        )

        # Update cache
        self.cache.set(f"credibility:{agent.id}", updated)

        return updated

    def incremental_credibility_update(self, current_score, current_count,
                                      new_decision_accuracy, decay_factor):
        """Efficient incremental average update"""

        # Decay old average slightly
        decayed_total = current_score * current_count * decay_factor

        # Add new decision
        new_total = decayed_total + new_decision_accuracy
        new_count = (current_count * decay_factor) + 1

        # New average
        new_score = new_total / new_count

        return CredibilityScore(
            score=new_score,
            decision_count=new_count,
            last_updated=now()
        )
```

#### 5. Parallel Query Execution

```python
class ParallelMemoryQueries:
    """Execute multiple memory queries in parallel"""

    async def gather_memory_context(self, analysis):
        """Fetch all needed memory in parallel"""

        # Define all memory queries needed
        queries = [
            ('similar', self.find_similar_analyses(analysis.company)),
            ('patterns', self.match_patterns(analysis)),
            ('history', self.get_company_history(analysis.company)),
            ('sector', self.get_sector_context(analysis.sector)),
            ('precedents', self.find_precedents(analysis))
        ]

        # Execute all in parallel
        results = await asyncio.gather(
            *[query[1] for query in queries],
            return_exceptions=True  # Don't fail if one query fails
        )

        # Combine results
        memory_context = {}
        for (key, _), result in zip(queries, results):
            if not isinstance(result, Exception):
                memory_context[key] = result
            else:
                # Log error but continue
                self.log_query_error(key, result)
                memory_context[key] = None

        return memory_context
```

#### 6. Memory Pruning Strategy

```python
class MemoryPruning:
    """Prune low-value memories to keep graph manageable"""

    def prune_obsolete_memories(self):
        """Remove low-value memories periodically"""

        # Identify candidates for pruning
        candidates = self.identify_pruning_candidates()

        for memory in candidates:
            if self.should_prune(memory):
                # Don't delete - archive
                self.archive_memory(memory)
                self.remove_from_active_graph(memory)

    def should_prune(self, memory):
        """Determine if memory should be archived"""

        criteria = {
            'age': (now() - memory.created_date).days > 1095,  # >3 years old
            'access_frequency': memory.access_count < 3,  # Rarely accessed
            'relevance': memory.relevance_score < 0.3,  # Low relevance
            'superseded': self.has_better_memory(memory)  # Newer better memory exists
        }

        # Prune if meets multiple criteria
        return sum(criteria.values()) >= 2

    def summarize_before_pruning(self, memory):
        """Create summary before archiving full detail"""

        summary = {
            'original_id': memory.id,
            'key_findings': memory.extract_key_findings(),
            'outcome': memory.outcome,
            'lessons': memory.lessons_learned,
            'links_preserved': memory.get_critical_relationships()
        }

        # Store lightweight summary in graph
        # Archive full detail in cold storage
        return summary
```

### Performance Targets Revised

| Metric             | Original Target | Revised Target                       | Strategy                 |
| ------------------ | --------------- | ------------------------------------ | ------------------------ |
| Memory retrieval   | <500ms          | <200ms (cached)<br><500ms (uncached) | Tiered caching           |
| Memory utilization | >90%            | >85%                                 | Some queries may timeout |
| Query budget       | None            | 500ms hard limit                     | Budget enforcement       |
| Cache hit rate     | N/A             | >80%                                 | Pre-warming              |
| Graph size         | Unlimited       | <50K active nodes                    | Pruning strategy         |

### Implementation Timeline

1. **Month 1**: Implement tiered caching and indexing
2. **Month 2**: Add query budget enforcement
3. **Month 3**: Deploy incremental updates
4. **Month 4**: Build similarity index
5. **Month 5**: Implement pruning strategy
6. **Month 6**: Optimize and tune

---
