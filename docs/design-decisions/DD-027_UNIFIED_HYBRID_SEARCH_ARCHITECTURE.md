# DD-027: Unified Hybrid Search & Memory Architecture

## Status

Accepted

## Context

The fundamental analysis system relies on agents that require three distinct types of data retrieval to function effectively:

1. **Precise Keyword Search**: Locating specific tickers (`$AAPL`), regulation codes (`Section 13(d)`), or accounting terms (`EBITDA`) where exact matches are non-negotiable.
2. **Semantic Vector Search**: Understanding conceptual similarities (e.g., matching "supply chain disruption" with "logistics bottleneck") to capture context and risks that keyword search misses.
3. **High-Speed Working Memory**: Instant access to active variables and sub-task states during agent execution.

**The Previous Approach (Fragmented)** proposed a split architecture:

- **Text Search**: Elasticsearch (for keywords).
- **Vector Search**: A separate dedicated Vector Database (e.g., Pinecone, Weaviate) for embeddings.
- **L1 Memory**: Undefined "In-Memory" store.
- **Knowledge Graph**: Neo4j.

**The Problem**:

- **Synchronization Complexity**: Maintaining perfect consistency between a text store (Elasticsearch) and a vector store (Pinecone) is operationally brittle. If a 10-K is updated, it must be updated in two places atomically to avoid data drift.
- **Hybrid Scoring Difficulty**: Merging a BM25 score (from Text DB) with a Cosine Similarity score (from Vector DB) requires complex client-side logic and normalization, often leading to poor ranking results.
- **Operational Overhead**: Managing three distinct database technologies (Graph, Text, Vector) increases infrastructure costs and maintenance burden.

## Decision

We will consolidate the search and vector retrieval requirements into a **Single Unified Engine** using **Elasticsearch 8+**, and explicitly select **Redis** for high-speed working memory.

### 1. Unified Search Engine: Elasticsearch 8+

We will use Elasticsearch 8+ as the sole provider for both **Text (BM25)** and **Vector (kNN)** search.

- **Hybrid Search**: We will utilize Elasticsearch's native `retriever` framework to execute hybrid queries that combine keyword precision with semantic understanding in a single request.
- **Scoring**: We will use **Reciprocal Rank Fusion (RRF)** to normalize and merge scores from text and vector matches automatically.

### 2. L1 Working Memory: Redis 7+

We select **Redis** for the L1 Agent Working Memory tier.

- **Rationale**: Agents require sub-millisecond latency for reading/writing state variables during "thinking" loops. Elasticsearch (<100ms) is too slow for this tight loop. Redis provides the required microsecond-scale performance.

### 3. Structural Knowledge: Neo4j

Neo4j remains the authority for the **Knowledge Graph Structure** (Relationships).

- **Role**: Neo4j stores the _map_ (Nodes/Edges/IDs).
- **Integration**: Elasticsearch stores the _content_ (Text/Vectors) associated with those IDs.
- **Workflow**: Agents query Neo4j to find _who_ is related (e.g., "Competitors of AAPL"), then query Elasticsearch to find _what_ they said (e.g., "Semantic search for 'risk' in the filings of those specific Competitors").

## Detailed Rationale

### Why Unified Hybrid Search?

Financial analysis is rarely exclusively "keyword" or "semantic"; it is almost always **Hybrid**.

- _Example_: An agent needs to find "discussions about **AI revenue** (Semantic) in **2024** (Metadata) for **Hardware Companies** (Metadata/Keyword)."
- **Pure Vector Failure**: Searching vectors for "AI revenue" might return software companies (Microsoft) when we strictly want hardware.
- **Pure Text Failure**: Searching keywords for "AI revenue" might miss a document discussing "Machine Learning monetization" (semantically identical).

Elasticsearch 8 allows us to execute this as a single atomic query:

```json
{
  "retriever": {
    "rrf": {
      "retrievers": [
        { "standard": { "query": { "term": { "sector": "Hardware" } } } },
        { "knn": { "field": "embedding", "query_vector": [...] } }
      ]
    }
  }
}
```

This eliminates the "Frankenstein" architecture of stitching results from two different databases.

### Why Not a Dedicated Vector DB (e.g., Pinecone)?

While dedicated vector databases excel at massive scale (billions of vectors, e.g., image search), our use case (financial filings for ~2,000 companies) fits comfortably within Elasticsearch's performance envelope (<100ms). The operational cost of adding a distinct database solely for vectors outweighs the marginal performance gain for our dataset size.

## Memory Tier Architecture

This decision finalizes the technology mapping for the 3-Tier Memory System:

| Tier   | Name                 | Type | Technology                                          | Content                                                                 | Latency    |
| :----- | :------------------- | :--- | :-------------------------------------------------- | :---------------------------------------------------------------------- | :--------- |
| **L1** | **Working Memory**   | Hot  | **Redis**                                           | Active variables, session state, sub-task progress.                     | **<1ms**   |
| **L2** | **Agent Memory**     | Warm | **Elasticsearch**                                   | Agent-specific patterns (Vectors), recent findings.                     | **<100ms** |
| **L3** | **Global Knowledge** | Cold | **Neo4j** (Structure) + **Elasticsearch** (Content) | The "Source of Truth": Relationships, full history, validated patterns. | **<500ms** |

## Consequences

### Positive

- **Operational Simplicity**: Reduced infrastructure footprint (1 cluster for all search).

* **Data Consistency**: Text and Vectors are stored in the same document index; updates are atomic. No synchronization lag.
* **Better Ranking**: Native RRF ensures higher quality search results than manual score merging.
* **Cost**: Eliminates the licensing/hosting cost of a separate vector database.

### Negative

- **Tuning Complexity**: Hybrid search requires tuning the balance between BM25 and kNN weights, which can be non-trivial.

* **Cluster Criticality**: Elasticsearch becomes a single point of failure for _all_ search capabilities (Text and Vector). High Availability (HA) configuration is critical.

## Implementation Notes

- **Index Mapping**: All major indices (`sec_filings`, `news`) must define both `text` fields (for BM25) and `dense_vector` fields (for kNN).

* **Embedding Model**: We will standardise on a specific embedding model (e.g., OpenAI `text-embedding-3-small` or a local BERT model) to ensuring vector compatibility across the system.
* **Agent Tooling**: The search tool exposed to agents must accept a `search_type` parameter (`keyword`, `semantic`, or `hybrid`) to allow agents to choose the right strategy for their specific question.
