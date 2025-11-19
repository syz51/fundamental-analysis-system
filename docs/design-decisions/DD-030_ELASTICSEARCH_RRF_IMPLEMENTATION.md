# DD-030: Elasticsearch Client-Side RRF Implementation

## Status

Accepted

## Context

The original design for the Fundamental Analysis System's search architecture (DD-027 and DD-029) specified using **Elasticsearch 8+** as the unified engine for hybrid search. Specifically, it proposed using the native `retriever` API with **Reciprocal Rank Fusion (RRF)** to merge keyword (BM25) and vector (kNN) search results server-side.

### The Problem

During implementation (Phase 1), we discovered that the native `retriever` API with RRF is a **Platinum/Enterprise** feature in Elasticsearch 8.14.0. The default Docker image (`docker.elastic.co/elasticsearch/elasticsearch:8.14.0`) operates under a **Basic (Free)** license by default.

Attempting to use the native RRF syntax resulted in the following error:
`AuthorizationException(403, 'security_exception', 'current license is non-compliant for [Reciprocal Rank Fusion (RRF)]')`

We require a solution that:

1. Maintains the **Hybrid Search** capability (combining precision of keywords with semantic understanding of vectors).
2. Operates within the **Basic (Free)** license constraints of the project.
3. Avoids the complexity and cost of upgrading to a paid Enterprise license for the prototype/MVP phase.

## Decision

We will implement **Client-Side Reciprocal Rank Fusion (RRF)** within the Python `SearchClient` instead of relying on the server-side RRF feature.

### Implementation Details

The `search_tool` logic for `search_type="hybrid"` has been modified to:

1. **Parallel Execution**: Use `asyncio.gather` to execute two independent search requests to Elasticsearch in parallel:
   - **Query A (BM25)**: A standard `bool` query matching the `text` field.
   - **Query B (kNN)**: A `knn` vector search against the `embedding` field.
2. **Client-Side Fusion**: Pass the two result lists to a local `_rrf_merge` function.
3. **RRF Algorithm**: Apply the standard RRF formula to calculate a new score for each document:
   $$ Score(d) = \sum\_{q \in Q} \frac{1}{k + rank(d, q)} $$
   - Where $k$ is set to **60** (default standard).
   - $rank(d, q)$ is the 1-indexed rank of document $d$ in the result list for query $q$ (matching academic standard).
4. **Sorting**: The final merged list is sorted by the calculated RRF score in descending order.

### comparison: Original vs. Implemented Design

| Feature          | Original Design (DD-027/029) | Implemented Solution (DD-030)                     |
| :--------------- | :--------------------------- | :------------------------------------------------ |
| **Hybrid Logic** | Server-side `retriever` API  | Client-side Python logic                          |
| **Algorithm**    | Native RRF                   | Custom RRF (`_rrf_merge`)                         |
| **Execution**    | Single HTTP Request          | Two Parallel HTTP Requests                        |
| **License Req.** | Platinum / Enterprise        | **Basic (Free)**                                  |
| **Complexity**   | Lower (delegated to DB)      | Higher (managed in code)                          |
| **Latency**      | Optimized by DB engine       | Slightly higher (network RTT + Python processing) |

### Updated Component Architecture

**`src/storage/search_tool.py`**:

- **`SearchClient.search_tool`**: Now orchestrates the parallel queries.
- **`SearchClient._rrf_merge`**: New helper method implementing the fusion math.
- **Dependencies**: Added `collections.defaultdict` for efficient score aggregation.

## Consequences

### Positive

- **License Compliance**: Fully compatible with the free Basic license, removing barriers to adoption and testing.

- **Flexibility**: The RRF constant $k$ and the fusion logic are now fully customizable in Python code, allowing for future tuning (e.g., weighting BM25 higher than Vector) without waiting for ES API updates.
- **No Infrastructure Change**: We continue to use the same standard Elasticsearch Docker container without needing custom plugins or license management.

### Negative

- **Network Overhead**: Hybrid search now requires **two** network round-trips (conceptually) instead of one, though they are executed in parallel.

- **Data Transfer**: We fetch full metadata for both result sets (e.g., Top 50 BM25 + Top 50 kNN) to the application layer before merging, which transfers more data than a server-side merge would.
- **Pagination Complexity**: Implementing deep pagination (e.g., "Page 10") is harder with client-side fusion because we only merge the "Top N" results from each query. (Current mitigation: We only support retrieving the top `limit` results, which fits the Agent use case).

### Future Mitigation

If performance becomes a bottleneck or deep pagination is required:

1. **Linear Combination**: We can switch to a server-side `bool` query that linearly combines BM25 and kNN scores (`score = bm25_score + knn_score`). This is supported on the Basic license but requires careful score normalization (as BM25 scores are unbounded while Cosine similarity is 0-1).
2. **Upgrade**: If the project scales to an enterprise environment, we can revert to the native `retriever` API by simply updating the `SearchClient` logic.

## Implementation Notes and Future Work

### RRF Rank Calculation Clarification

The RRF algorithm implemented in `SearchClient._rrf_merge` uses `1.0 / (k + rank + 1)`. While the design document stated "$rank(d, q)$ is the 0-based position", the code's `rank + 1` effectively makes it a 1-based rank for the formula, which is a common and standard practice for RRF implementations. This ensures that the first result (rank 0 in a 0-based list) receives `1.0 / (k + 1)` score contribution, aligning with standard RRF conventions.

### Pending Implementation Items

1. **Real Embedding Model Integration**: The `SearchClient._generate_embedding` method currently uses a mock (placeholder) implementation. This needs to be replaced with an actual call to an embedding service (e.g., OpenAI API) or a local embedding model.

### Completed Enhancements

1. **Robust Error Handling** ✅: Implemented comprehensive error handling in both `elasticsearch_setup.py` and `search_tool.py`:
   - **Retry Logic**: Exponential backoff decorator with configurable max retries (default: 3 attempts)
   - **Circuit Breaker Pattern**: Prevents cascading failures with configurable threshold (default: 5 failures) and timeout (default: 60s)
   - **Specific Exception Handling**: Differentiated handling for `ConnectionError`, `ConnectionTimeout`, `ApiError` (including 429 rate limiting), and `TransportError`
   - **Enhanced Logging**: Request/response context logging with error types and query details
   - **Connection Retry**: Initial connection attempts with exponential backoff in `initialize_indices`

2. **Monitoring & Logging** ✅: Implemented basic observability in `search_tool.py`:
   - **Request Logging**: Query parameters, search type, indices, ticker, filters
   - **Success Logging**: Result count for each successful search
   - **Error Logging**: Exception types, query context, index information
   - **Circuit Breaker State Tracking**: Failure counts and state transitions (closed/open/half-open)
   - **Kibana Dashboard**: Already deployed in docker-compose.yml for visualization (Phase 3)
   - **Future**: Prometheus/Grafana metrics stack deferred to Phase 4

## References

- Elasticsearch RRF Documentation (Enterprise): [Reciprocal Rank Fusion](https://www.elastic.co/guide/en/elasticsearch/reference/current/rrf.html)

- RRF Paper: _Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). Reciprocal rank fusion outperforms condorcet and individual rank learning methods._
