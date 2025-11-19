# DD-029: Elasticsearch Index Mapping Standard

## Status

Accepted

## Context

The fundamental analysis system uses Elasticsearch 8+ as the unified engine for both text (BM25) and vector (kNN) search (per DD-027). Agents query three primary document types across analyses:

1. **SEC Filings**: 10-K, 10-Q, 8-K, proxy statements (~80,000 documents: 2,000 companies × 4 filings/year × 10 years)
2. **Earnings Transcripts**: Quarterly earnings calls, investor days (~40,000 transcripts: 2,000 companies × 4 calls/year × 5 years)
3. **News Articles**: Real-time news monitoring, event tracking (~500,000 articles: 2,000 companies × ~250 articles/year)

Agents require hybrid queries that combine:
- **Keyword precision**: Exact ticker symbols (`$AAPL`), regulation codes (`Section 13(d)`), accounting terms (`EBITDA`)
- **Semantic understanding**: Conceptual similarity ("supply chain disruption" = "logistics bottleneck")
- **Metadata filtering**: Date ranges, sector classification, filing types

### The Problem

Without a standardized schema, several issues emerge:

**Cross-Index Query Fragmentation**: Agents need to search across document types (e.g., "Find all 2024 mentions of AI revenue in filings AND transcripts AND news for $AAPL"). Without common field names (`ticker`, `date`, `text`), this requires custom query logic per index.

**Embedding Incompatibility**: If indices use different embedding models (OpenAI ada-002 vs BERT) or dimensions (1536 vs 768), vector similarity across indices produces meaningless results.

**Inconsistent Hybrid Scoring**: Reciprocal Rank Fusion (RRF) merges BM25 and kNN scores. If indices have different field mappings (`content` vs `text`, `embedding_vector` vs `embedding`), hybrid queries fail or require index-specific query templates.

**Schema Drift**: Without standards, Phase 2 implementation may create `sec_filings` with field `company_ticker`, Phase 3 adds `transcripts` with field `ticker_symbol`, and Phase 4 discovers cross-index queries require reindexing everything to align.

**Agent Tool Complexity**: Agents should call `search_tool(query="AI revenue", ticker="AAPL", search_type="hybrid")` without knowing index-specific schema details. Current fragmentation would require exposing index schemas to agent logic.

## Decision

We will adopt a **Shared Core Schema + Domain Extensions** approach with standardized field mappings across all Elasticsearch indices.

### 1. Core Schema (All Indices)

All indices (`sec_filings`, `transcripts`, `news`) **MUST** include these 14 fields to enable cross-index queries and consistent hybrid search:

```json
{
  "mappings": {
    "properties": {
      // === Identity ===
      "doc_id": {
        "type": "keyword",
        "doc_values": true
      },
      "doc_type": {
        "type": "keyword",
        "doc_values": true
      },
      "source": {
        "type": "keyword",
        "doc_values": true
      },

      // === Company Linking ===
      "ticker": {
        "type": "keyword",
        "doc_values": true
      },
      "company_name": {
        "type": "text",
        "fields": {
          "keyword": {
            "type": "keyword",
            "ignore_above": 256
          }
        }
      },
      "cik": {
        "type": "keyword",
        "doc_values": true
      },

      // === Temporal ===
      "date": {
        "type": "date",
        "format": "strict_date_optional_time||epoch_millis"
      },
      "fiscal_year": {
        "type": "integer"
      },
      "fiscal_quarter": {
        "type": "keyword"
      },

      // === Classification ===
      "sector": {
        "type": "keyword",
        "doc_values": true
      },
      "industry": {
        "type": "keyword",
        "doc_values": true
      },

      // === Search Fields (REQUIRED for hybrid search) ===
      "text": {
        "type": "text",
        "analyzer": "financial_analyzer"
      },
      "embedding": {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine",
        "index_options": {
          "type": "hnsw",
          "m": 16,
          "ef_construction": 100
        }
      },

      // === Metadata ===
      "indexed_at": {
        "type": "date"
      },
      "updated_at": {
        "type": "date"
      }
    }
  }
}
```

**Field Naming Conventions**:
- **snake_case**: All field names use lowercase with underscores (`company_name`, not `companyName`)
- **Singular nouns**: Prefer singular (`ticker`, not `tickers`) unless field is truly multi-valued
- **No abbreviations**: Use `fiscal_quarter` not `fq`, `fiscal_year` not `fy` (exception: `cik` is standard SEC terminology)

### 2. Domain-Specific Extensions

Each index extends the core schema with fields unique to its document type.

#### 2.1 `sec_filings` Index

```json
{
  "mappings": {
    "properties": {
      // ... Core schema fields (14 required fields)

      // === Filing-Specific ===
      "filing_type": {
        "type": "keyword",
        "doc_values": true
      },
      "accession_number": {
        "type": "keyword",
        "doc_values": true
      },
      "section": {
        "type": "keyword",
        "doc_values": true
      },
      "url": {
        "type": "keyword",
        "index": false
      },
      "file_size": {
        "type": "long"
      },

      // === Financial Context (Optional - for filtering) ===
      "revenue": {
        "type": "long"
      },
      "net_income": {
        "type": "long"
      },
      "market_cap": {
        "type": "long"
      }
    }
  }
}
```

**Use Case Examples**:
- "Find all 10-K Risk Factors sections mentioning supply chain for hardware companies in 2024"
  - Filter: `filing_type=10-K`, `section=Risk-Factors`, `sector=Hardware`, `fiscal_year=2024`
  - Hybrid search: `text` (BM25) + `embedding` (kNN) for "supply chain"

#### 2.2 `transcripts` Index

```json
{
  "mappings": {
    "properties": {
      // ... Core schema fields (14 required fields)

      // === Transcript-Specific ===
      "call_type": {
        "type": "keyword",
        "doc_values": true
      },
      "speaker": {
        "type": "keyword",
        "doc_values": true
      },
      "speaker_role": {
        "type": "keyword",
        "doc_values": true
      },
      "segment": {
        "type": "keyword",
        "doc_values": true
      },
      "duration_seconds": {
        "type": "integer"
      },

      // === Sentiment (Optional - Phase 3+) ===
      "sentiment_score": {
        "type": "float"
      }
    }
  }
}
```

**Use Case Examples**:
- "Find CEO prepared remarks about margin expansion in Q4 2024 earnings calls"
  - Filter: `call_type=earnings`, `speaker_role=CEO`, `segment=prepared-remarks`, `fiscal_quarter=Q4`, `fiscal_year=2024`
  - Hybrid search: `text` + `embedding` for "margin expansion"

#### 2.3 `news` Index

```json
{
  "mappings": {
    "properties": {
      // ... Core schema fields (14 required fields)

      // === News-Specific ===
      "headline": {
        "type": "text",
        "analyzer": "financial_analyzer",
        "boost": 2.0
      },
      "author": {
        "type": "keyword",
        "doc_values": true
      },
      "publication": {
        "type": "keyword",
        "doc_values": true
      },
      "url": {
        "type": "keyword",
        "index": false
      },
      "word_count": {
        "type": "integer"
      },

      // === Event Tracking ===
      "event_type": {
        "type": "keyword",
        "doc_values": true
      },
      "mentioned_tickers": {
        "type": "keyword",
        "doc_values": true
      }
    }
  }
}
```

**Use Case Examples**:
- "Find Bloomberg articles about M&A events mentioning $AAPL or $GOOGL in 2024"
  - Filter: `publication=Bloomberg`, `event_type=M&A`, `mentioned_tickers=[AAPL, GOOGL]`, `date=[2024-01-01 TO 2024-12-31]`
  - Hybrid search: `headline` (boosted) + `text` + `embedding`

### 3. Embedding Field Specification

All indices use **identical embedding configuration** to ensure cross-index vector similarity is meaningful:

```json
{
  "embedding": {
    "type": "dense_vector",
    "dims": 1536,              // Custom embedding model (user-specified, deferred)
    "index": true,             // Enable kNN search
    "similarity": "cosine",    // Cosine distance (range: -1 to 1, higher = more similar)
    "index_options": {
      "type": "hnsw",          // Hierarchical Navigable Small World graph
      "m": 16,                 // Connections per layer (higher = better recall, slower indexing)
      "ef_construction": 100   // Candidates during indexing (higher = better accuracy, slower)
    }
  }
}
```

**Embedding Model**:
- **Decision**: Custom embedding model (user-specified, final choice deferred to Phase 2)
- **Dimension**: 1536 (standard for OpenAI text-embedding-3-small, adjust if custom model differs)
- **Consistency requirement**: ALL indices must use the SAME model and dimension
- **Update protocol**: If model changes, ALL indices must be reindexed simultaneously

**Distance Metric**:
- **Cosine similarity**: Normalized dot product, ideal for text embeddings (measures angle, not magnitude)
- **Range**: -1 (opposite) to 1 (identical), typical text similarity: 0.7-0.95
- **Why not Euclidean/dot product**: Cosine normalizes for document length (long vs short texts comparable)

**HNSW Parameters**:
- **`m=16`**: Balanced tradeoff (m=4 fast/low recall, m=32 slow/high recall, 16 = sweet spot)
- **`ef_construction=100`**: Good accuracy without excessive indexing time (increase to 200 if recall <0.95)
- **`ef_search`**: Set at query time (default 100, increase to 500 for higher recall at cost of latency)

### 4. Text Analyzer Configuration

Custom `financial_analyzer` for domain-specific text processing:

```json
{
  "settings": {
    "analysis": {
      "analyzer": {
        "financial_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": [
            "lowercase",
            "asciifolding",
            "financial_stop",
            "financial_synonyms",
            "english_stemmer"
          ]
        }
      },
      "filter": {
        "financial_stop": {
          "type": "stop",
          "stopwords": ["the", "a", "an", "and", "or", "but"]
        },
        "financial_synonyms": {
          "type": "synonym",
          "synonyms": [
            "EBITDA, Earnings Before Interest Taxes Depreciation Amortization",
            "P/E, price to earnings, price earnings ratio, PE ratio",
            "M&A, mergers and acquisitions, merger, acquisition",
            "ROE, return on equity",
            "ROA, return on assets",
            "ROIC, return on invested capital",
            "FCF, free cash flow",
            "CAGR, compound annual growth rate",
            "AI, artificial intelligence, machine learning, ML",
            "EPS, earnings per share"
          ]
        },
        "english_stemmer": {
          "type": "stemmer",
          "language": "english"
        }
      }
    }
  }
}
```

**Design Rationale**:
- **Conservative stopwords**: Remove common words (`the`, `a`) but keep domain terms (`AI`, `debt`, `margin`)
- **Financial synonyms**: Map acronyms to full terms for better recall (search "EBITDA" matches "Earnings Before...")
- **Stemming**: Normalize word forms (`margins` → `margin`, `growing` → `grow`) for broader matching
- **ASCII folding**: Handle accented characters in company names (Nestlé → Nestle)

**Testing Analyzer**:
```json
POST /sec_filings/_analyze
{
  "analyzer": "financial_analyzer",
  "text": "Apple's EBITDA margins grew 15% year-over-year"
}

// Expected tokens:
// ["apple", "ebitda", "earnings", "before", "interest", "taxes", "depreciation",
//  "amortization", "margin", "grew", "15", "year", "over", "year"]
```

### 5. Index Settings (Production)

Standardized settings for high availability and performance:

```json
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 2,
    "refresh_interval": "30s",
    "max_result_window": 10000,

    // === Merge Policy (Optimize for search performance) ===
    "index.merge.policy.max_merged_segment": "5gb",
    "index.merge.policy.segments_per_tier": 10,

    // === Translog Durability ===
    "index.translog.durability": "async",
    "index.translog.sync_interval": "5s",

    // === Analysis Settings ===
    "analysis": {
      // ... (financial_analyzer config from Section 4)
    }
  }
}
```

**Sharding Strategy**:
- **3 shards**: Distribute 80K-500K documents across 3 shards (27K-167K docs/shard)
- **Why not 5 shards**: Over-sharding increases coordination overhead for small dataset
- **Why not 1 shard**: Single shard limits horizontal scaling and search parallelization

**Replication Strategy**:
- **2 replicas**: Total 3 copies (1 primary + 2 replicas) for 99.9% availability
- **HA benefit**: Tolerate 2 node failures without data loss
- **Read scaling**: 3x read capacity (queries distributed across primary + replicas)

**Refresh Interval**:
- **30s**: Balance real-time visibility vs indexing throughput
- **Tradeoff**: Newly indexed documents visible after 30s (vs 1s default) but 3x faster indexing
- **Use case fit**: News articles delayed by 30s acceptable (not sub-second trading system)

**Translog Settings**:
- **Async durability**: Fsync every 5s instead of every request (faster writes, 5s data loss risk)
- **Rationale**: Documents sourced from durable storage (S3 raw filings), acceptable to lose 5s of indexing progress on crash

### 6. Agent Search Tool Interface

Agents query Elasticsearch via a **schema-agnostic search tool** that abstracts index-specific details:

```python
def search_tool(
    query: str,
    ticker: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    doc_types: list[str] | None = None,  # ["filing", "transcript", "news"]
    search_type: str = "hybrid",          # "keyword" | "semantic" | "hybrid"
    filters: dict | None = None,          # {"filing_type": "10-K", "sector": "Technology"}
    limit: int = 10
) -> list[SearchResult]:
    """
    Universal search across all Elasticsearch indices using standardized schema.

    Example:
        search_tool(
            query="supply chain disruption risks",
            ticker="AAPL",
            start_date="2024-01-01",
            end_date="2024-12-31",
            doc_types=["filing", "news"],
            search_type="hybrid",
            filters={"filing_type": "10-K"},
            limit=5
        )
    """
    pass
```

**Hybrid Query Example** (generated by `search_tool` when `search_type="hybrid"`):

```json
{
  "query": {
    "bool": {
      "must": [
        {
          "retriever": {
            "rrf": {
              "retrievers": [
                {
                  "standard": {
                    "query": {
                      "match": {
                        "text": "supply chain disruption risks"
                      }
                    }
                  }
                },
                {
                  "knn": {
                    "field": "embedding",
                    "query_vector": [0.123, 0.456, ...],  // 1536-dim vector
                    "k": 50,
                    "num_candidates": 100
                  }
                }
              ],
              "rank_window_size": 100,
              "rank_constant": 60
            }
          }
        }
      ],
      "filter": [
        {"term": {"ticker": "AAPL"}},
        {"term": {"filing_type": "10-K"}},
        {"range": {"date": {"gte": "2024-01-01", "lte": "2024-12-31"}}}
      ]
    }
  },
  "size": 5
}
```

## Consequences

### Positive

**Cross-Index Queries**:
- Agents search across filings, transcripts, news with **single query** using common fields
- Example: "Find AI revenue mentions in 2024 for $AAPL" searches 3 indices seamlessly
- No index-specific query logic required in agent code

**Embedding Compatibility**:
- Identical embedding config (1536-dim, cosine, HNSW) ensures meaningful cross-index similarity
- Can compare semantic similarity between 10-K text and news article (both use same vector space)
- Prevents "frankenstein vectors" (mixing ada-002 + BERT embeddings)

**Hybrid Search Consistency**:
- All indices use `text` (BM25) + `embedding` (kNN) fields with RRF merging
- Agent tool abstracts search complexity (agents don't see index schemas)
- Single hybrid query template works across all document types

**Schema Evolution**:
- Core schema frozen (14 required fields), domain extensions flexible
- Can add `transcripts.sentiment_score` in Phase 3 without breaking existing queries
- Reindexing only required if core schema changes (rare)

**Operational Simplicity**:
- Single analyzer config (`financial_analyzer`) shared across indices
- Consistent settings (3 shards, 2 replicas, 30s refresh) simplify monitoring
- Uniform embedding model update protocol (reindex all indices simultaneously)

### Negative

**Initial Overhead**:
- Requires defining complete mappings before Phase 2 implementation
- Core schema may include fields not immediately used (e.g., `fiscal_quarter` for news articles)
- Over-specification risk (designing for hypothetical future use cases)

**Embedding Model Lock-In**:
- All indices must use same model/dimension (changing requires full reindex of all indices)
- Cannot A/B test different embedding models per index
- Migration to better model (e.g., custom model → GPT-4 embeddings) is expensive

**Field Bloat**:
- Core schema adds ~1KB overhead per document (14 required fields even if half are `null`)
- News articles don't need `fiscal_quarter` but must include field for schema consistency
- Mitigation: `null` fields excluded from `_source` compression, minimal storage impact

**Analyzer Compromise**:
- Single `financial_analyzer` may not be optimal for all document types
- News headlines may benefit from different stopwords than 10-K filings
- Mitigation: Per-field analyzers allowed (e.g., `headline` uses custom analyzer)

### Trade-offs Accepted

1. **Schema overhead for consistency**: Accept 14 required fields (even if some `null`) to enable cross-index queries. Storage cost (<1KB/doc) negligible vs query simplification.

2. **Embedding model lock-in**: Accept single model constraint to ensure vector compatibility. Model migration planned as major version upgrade (v2.0 → v3.0) with scheduled downtime.

3. **Standardized settings**: Accept 3 shards/2 replicas for all indices (even small ones) for operational simplicity. Over-provisioning small indices acceptable vs managing per-index shard configurations.

4. **30s refresh interval**: Accept 30s delay for document visibility to gain 3x indexing throughput. Agents operate on historical data (filings from prior quarters), not real-time trading signals.

## Implementation Notes

### Index Creation Sequence

**Phase 1 (Foundation)**:
1. Create `sec_filings` index with full core schema + filing extensions
2. Index 10 test companies (100 filings) to validate mappings
3. Test hybrid queries, verify analyzer behavior, tune HNSW parameters

**Phase 2 (Core Agents)**:
1. Create `transcripts` index with core schema + transcript extensions
2. Expand `sec_filings` to 50 companies (500 filings)
3. Implement cross-index search tool, validate RRF scoring

**Phase 3 (Advanced)**:
1. Create `news` index with core schema + news extensions
2. Scale to 200 companies (~2,000 filings, ~1,000 transcripts, ~50,000 news articles)
3. Add sentiment analysis fields to `transcripts` (optional)

**Phase 4 (Optimization)**:
1. Tune HNSW parameters (`m`, `ef_construction`) based on recall metrics
2. Optimize analyzer synonyms based on agent query logs
3. Scale to 1,000 companies (~10,000 filings, ~5,000 transcripts, ~250,000 news)

### Validation and Testing

**Schema Compliance Tests**:
1. Automated validation: Every document **MUST** include all 14 core fields (reject `null` for required fields like `ticker`, `date`, `text`)
2. Type checking: Verify `date` is ISO 8601, `fiscal_year` is integer, `embedding` is 1536-float array
3. CI/CD gate: Block index creation if mapping doesn't extend from core schema template

**Embedding Consistency Tests**:
1. Cross-index similarity test: Index identical text in all 3 indices → verify cosine similarity = 1.0
2. Model drift detection: Weekly batch job computes reference embedding for standard text → alert if drift >1%
3. Dimension validation: Reject documents with `len(embedding) != 1536`

**Hybrid Search Tests**:
1. Recall benchmark: Given 100 labeled query-document pairs → measure recall@10 for keyword/semantic/hybrid
2. RRF tuning: Test `rank_constant` values (20, 40, 60, 80) → select value maximizing nDCG@10
3. Latency target: p95 latency <100ms for hybrid queries (50 BM25 results + 50 kNN results merged)

**Analyzer Tests**:
1. Synonym expansion: Search "EBITDA" → verify matches documents containing "Earnings Before Interest..."
2. Stemming: Search "margins" → verify matches "margin", "marginal"
3. Stopword removal: Verify "the AI revolution" → tokens `["ai", "revolution"]` (no "the")

### Monitoring Metrics

**Schema Health**:
- `elasticsearch_schema_violations_total`: Documents rejected due to missing core fields (alert >0)
- `elasticsearch_embedding_dimension_errors_total`: Documents with wrong embedding size (alert >0)
- `elasticsearch_null_required_fields`: Count of `null` values in `ticker`, `date`, `text` (alert >10/day)

**Search Performance**:
- `elasticsearch_hybrid_query_latency_ms`: p50, p95, p99 hybrid query latency (alert if p95 >200ms)
- `elasticsearch_knn_recall_at_10`: Weekly batch recall measurement (alert if <0.90)
- `elasticsearch_rrf_rank_quality`: nDCG@10 for hybrid queries (alert if drops >10%)

**Index Health**:
- `elasticsearch_shards_unassigned`: Unassigned shards (alert >0)
- `elasticsearch_cluster_health`: Green/Yellow/Red (alert if not Green)
- `elasticsearch_indexing_rate`: Documents/second indexed (trend analysis)
- `elasticsearch_search_rate`: Queries/second (capacity planning)

### Migration and Versioning

**Embedding Model Migration**:
1. **Trigger**: New custom model available (better accuracy or lower cost)
2. **Process**:
   - Compute embeddings for **all documents** in all indices (offline batch job)
   - Create new index versions: `sec_filings_v2`, `transcripts_v2`, `news_v2`
   - Bulk reindex with new embeddings (parallel jobs, ~1hr for 100K docs)
   - Atomic alias switch: `sec_filings` → `sec_filings_v2`
   - Delete old indices after 7-day validation period
3. **Downtime**: Zero (alias switch is atomic, agents query via alias)

**Core Schema Updates**:
1. **Minor changes** (add optional field): No reindex required, update mapping via PUT API
2. **Major changes** (remove/rename required field): Requires full reindex + version bump
3. **Approval**: Core schema changes require design decision review (create DD-030+)

**Backward Compatibility**:
- Agent search tool versioned (`/api/v1/search`)
- Index aliases used for zero-downtime migrations (`sec_filings` → `sec_filings_v2`)
- Old index versions retained for 7 days post-migration (rollback window)

## Related Decisions

- **DD-027**: Unified Hybrid Search Architecture (selects Elasticsearch 8+ for text + vector search)
- **DD-005**: Knowledge Graph Performance Optimization (defines Neo4j vs Elasticsearch separation)

## References

- Elasticsearch Mapping Documentation: https://www.elastic.co/guide/en/elasticsearch/reference/current/mapping.html
- HNSW Parameters Tuning: https://www.elastic.co/guide/en/elasticsearch/reference/current/tune-knn-search.html
- Reciprocal Rank Fusion: https://www.elastic.co/guide/en/elasticsearch/reference/current/rrf.html
- Custom Analyzers: https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis-custom-analyzer.html
