# Failure Correlation System

**Status**: Approved
**Date**: 2025-11-18
**Decider(s)**: System Architect
**Related Docs**: [Agents Coordination](../architecture/05-agents-coordination.md), [Analysis Pipeline](../operations/01-analysis-pipeline.md), [Tech Requirements](../implementation/02-tech-requirements.md)
**Related Decisions**: [DD-012 Workflow Pause/Resume](DD-012_WORKFLOW_PAUSE_RESUME.md), [DD-015 Agent Failure Alert System](DD-015_AGENT_FAILURE_ALERT_SYSTEM.md)

---

## Context

System can handle batch pause/resume (DD-012) and alerts (DD-015), but lacks automatic detection of correlated failures. When shared root cause affects multiple stocks (Koyfin quota exhaustion → 5 stocks fail), system treats as 5 independent failures.

**Current State**:

- BatchManager exists (DD-012) with pause/resume API
- Alert system (DD-015) supports batch alerts (separate cards)
- No automatic failure correlation detection
- Manual identification required to group related failures
- Inefficient recovery: investigate same API quota issue 5 times vs once

**Why Address Now**:

- DD-012/DD-015 infrastructure complete, ready for correlation layer
- Resolves Flaw #26 E1 (correlation detection) and E2 (auto-batch trigger)
- Production readiness: prevents wasted investigation of duplicate root causes
- Phase 2 deployment: automated correlation reduces human workload

**Example Impact**: 5 stocks (AAPL, MSFT, GOOGL, AMZN, TSLA) all fail at 2:47 PM due to Koyfin API quota. Current: 5 separate investigations, human manually identifies common root cause, manually groups for batch resume. Desired: FailureCorrelator detects correlation within 30s, auto-triggers batch pause, single alert "Koyfin quota exceeded - 5 stocks paused", one-click batch resume.

---

## Decision

**Implement FailureCorrelator component with error signature generation, temporal correlation algorithm (5min window), root cause inference engine, and automatic batch operation triggering.**

System provides:

- Automatic correlation detection (<30s from first failure)
- Error signature algorithm (agent_type, error_type, data_source, normalized_msg)
- Temporal clustering (failures within 5min window)
- Root cause inference (API quota vs network vs data source patterns)
- Auto-batch threshold (3+ correlated failures → batch pause trigger)
- Integration with DD-012 BatchManager and DD-015 AlertManager
- Database schema (failure_correlations table)

---

## Options Considered

### Option 1: FailureCorrelator with Auto-Batch Trigger (CHOSEN)

**Description**: Dedicated correlation detection component, error signature generation, automatic batch triggering when 3+ failures match.

**Pros**:

- Automatic detection within 30s (vs manual grouping)
- Error signatures enable precise matching (no false positives)
- Root cause inference reduces investigation time (5 stocks → 1 diagnosis)
- Integrates cleanly with DD-012/DD-015 (correlation → batch pause → alert)
- Temporal clustering prevents false correlation (5min window)
- Extensible for ML-based correlation patterns (future enhancement)

**Cons**:

- New component complexity (FailureCorrelator class)
- Error signature normalization logic (vendor-specific error formats)
- Database overhead (failure_correlations table, signatures)
- False negatives risk (different errors, same root cause)

**Estimated Effort**: 2 weeks (Week 1: FailureCorrelator + signatures, Week 2: root cause inference + integration)

---

### Option 2: Manual Correlation Only

**Description**: Rely on human to identify correlations, manually trigger batch operations.

**Pros**:

- No new code required (DD-012 already supports manual batch)
- Zero false positives (human judgment)
- Simpler system (fewer components)

**Cons**:

- Slow detection (hours vs seconds - human must notice pattern)
- Scalability issue (100 stocks → human can't track correlations)
- Wastes human time (manual grouping, repetitive investigation)
- Defeats purpose of DD-012 batch efficiency
- Defeats automation goal of multi-agent system

**Estimated Effort**: 0 weeks (status quo)

---

### Option 3: Simple String Matching (No Signatures)

**Description**: Match failures by exact error message string equality.

**Pros**:

- Simpler implementation (no normalization logic)
- Faster matching (string equality vs signature generation)
- Lower database overhead

**Cons**:

- High false negative rate (same quota error, different messages: "Quota exceeded: 1000/1000" vs "Rate limit reached")
- Vendor-specific variations not handled (Koyfin vs Bloomberg error formats)
- Timestamps/UUIDs in errors prevent matching
- No semantic understanding (different wording, same root cause)

**Estimated Effort**: 1 week

---

## Rationale

**Option 1 (FailureCorrelator) chosen** because:

1. **Automatic detection**: 30s vs hours (manual). Production system requires immediate correlation to prevent duplicate investigations.

2. **Error signatures**: Normalize vendor-specific errors, filter timestamps/UUIDs, enable semantic matching. "Koyfin quota 1000/1000" and "Koyfin rate limit reached" both map to signature `koyfin_api_quota_exceeded`.

3. **Root cause inference**: 5 stocks fail with same signature → infer "Koyfin API quota", not "AAPL business issue". Saves human investigation time.

4. **Auto-batch trigger**: Detected correlation immediately calls `BatchManager.pause_batch()`. No manual grouping required.

5. **DD-012/DD-015 integration**: FailureCorrelator → BatchManager → AlertManager. Correlation layer completes pause/resume/alert pipeline.

6. **Unblocks Flaw #26**: E1 (correlation detection) fully resolved, E2 (auto-batch trigger) fully resolved. E3 already resolved by DD-012.

**Acceptable tradeoffs**:

- FailureCorrelator complexity: necessary for production-scale automation (100+ stocks)
- Error signature normalization: one-time cost per error type, reusable across vendors
- False negatives: conservative 5min window + signature matching reduces risk, manual override available
- 2-week implementation: justified by automated correlation efficiency

---

## Consequences

### Positive Impacts

- ✅ **Automatic correlation**: <30s detection vs hours (manual)
- ✅ **Root cause inference**: 5 failures → 1 diagnosis (not 5 investigations)
- ✅ **Auto-batch trigger**: Detected correlation → batch pause (no manual grouping)
- ✅ **Efficiency gains**: Shared failures resolved once, batch resumed together
- ✅ **Scalability**: Handles 100+ stocks (manual correlation impossible at scale)
- ✅ **DD-012 completion**: Batch infrastructure now automated (not manual-only)
- ✅ **Flaw #26 resolution**: E1/E2 fully resolved (E3 already complete via DD-012)

### Negative Impacts / Tradeoffs

- ❌ **Complexity**: FailureCorrelator class, signature generation, normalization logic
- ❌ **Database overhead**: failure_correlations table, error signatures indexed
- ❌ **False negatives risk**: Different errors, same root cause (mitigated by inference)
- ❌ **Vendor-specific tuning**: Error signature patterns per data provider
- ❌ **Testing complexity**: Multi-stock correlation scenarios, timing edge cases

**Mitigations**:

- Conservative 5min window prevents false positives (unrelated failures grouped)
- Manual override: human can force batch grouping if auto-detection misses
- Error signature library: reusable patterns across vendors (one-time cost)
- Root cause inference: machine learning enhancement planned (Phase 4)

### Affected Components

**New Components**:

- `FailureCorrelator` class (signature generation, correlation detection, root cause inference)
- `failure_correlations` table (correlation records, signatures, batch links)
- `error_signature_library` module (reusable normalization patterns)

**Modified Components**:

- `lead_coordinator.py`: Subscribe to failure events, call FailureCorrelator
- `BatchManager` (DD-012): Accept auto-trigger from FailureCorrelator
- `AlertManager` (DD-015): Include root cause in batch alert messages
- `base_agent.py`: Emit failure events with error context

**Documentation Updates**:

- `05-agents-coordination.md`: Add FailureCorrelator to coordination layer
- `01-analysis-pipeline.md`: Update failure handling flow (correlation step)
- `02-tech-requirements.md`: Add failure_correlations table schema
- `26-multi-stock-batching.md`: Move from active/ to resolved/, mark E1/E2 resolved

---

## Implementation Notes

### FailureCorrelator Component

**Purpose**: Detect correlated failures, infer root cause, trigger batch operations

**API**:

```python
class FailureCorrelator:
    """Detect and correlate agent failures across stocks"""

    def on_agent_failure(
        self,
        stock_ticker: str,
        agent_type: str,
        error_type: str,
        error_message: str,
        data_source: str,
        timestamp: datetime
    ) -> CorrelationResult:
        """
        Analyze failure for correlation with recent failures

        Returns: CorrelationResult{
            is_correlated: bool,
            correlation_id: UUID | None,
            correlated_stocks: List[str],
            root_cause: str | None,
            batch_triggered: bool
        }
        """

    def generate_error_signature(
        self,
        agent_type: str,
        error_type: str,
        data_source: str,
        error_message: str
    ) -> str:
        """
        Generate normalized error signature for matching

        Returns: Hash of (agent_type, error_type, data_source, normalized_message)
        """

    def detect_correlation(
        self,
        signature: str,
        timestamp: datetime,
        window_minutes: int = 5
    ) -> List[UUID]:
        """
        Find failures with matching signature within time window

        Returns: List of failure IDs within 5min window
        """

    def infer_root_cause(
        self,
        signature: str,
        correlated_failures: List[dict]
    ) -> str:
        """
        Infer root cause from signature and failure pattern

        Returns: Human-readable root cause (e.g., "Koyfin API quota exceeded")
        """

    def trigger_batch_pause(
        self,
        stock_ids: List[str],
        root_cause: str,
        correlation_id: UUID
    ) -> BatchPauseResult:
        """
        Auto-trigger batch pause via DD-012 BatchManager

        Returns: BatchPauseResult from BatchManager
        """
```

### Error Signature Generation

**Algorithm**:

```python
def generate_error_signature(self, agent_type, error_type, data_source, error_message):
    """Generate normalized error signature"""

    # 1. Normalize error message (remove timestamps, IDs, numbers)
    normalized = self._normalize_message(error_message)

    # 2. Extract semantic pattern
    pattern = self._extract_pattern(normalized)

    # 3. Generate hash
    signature_input = f"{agent_type}:{error_type}:{data_source}:{pattern}"
    signature = hashlib.sha256(signature_input.encode()).hexdigest()[:16]

    return signature

def _normalize_message(self, message):
    """Normalize error message for matching"""

    # Remove timestamps
    message = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', 'TIMESTAMP', message)

    # Remove UUIDs
    message = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', 'UUID', message)

    # Remove request IDs
    message = re.sub(r'request_id=\w+', 'request_id=REQ_ID', message)

    # Remove quota numbers (normalize to threshold pattern)
    message = re.sub(r'quota:\s*\d+/\d+', 'quota:LIMIT_EXCEEDED', message)
    message = re.sub(r'rate limit:\s*\d+\s*requests', 'rate limit:EXCEEDED', message)

    # Lowercase
    message = message.lower()

    return message

def _extract_pattern(self, normalized_message):
    """Extract semantic pattern from normalized message"""

    # Quota/rate limit patterns
    if 'quota' in normalized_message and 'limit_exceeded' in normalized_message:
        return 'api_quota_exceeded'
    if 'rate limit' in normalized_message and 'exceeded' in normalized_message:
        return 'api_rate_limit_exceeded'

    # Network patterns
    if 'timeout' in normalized_message or 'connection refused' in normalized_message:
        return 'network_timeout'
    if 'connection reset' in normalized_message or 'connection closed' in normalized_message:
        return 'network_connection_error'

    # Data availability patterns
    if '404' in normalized_message or 'not found' in normalized_message:
        return 'data_not_found'
    if 'missing required' in normalized_message or 'field not present' in normalized_message:
        return 'data_missing_field'

    # Fallback: use first 50 chars of normalized message
    return normalized_message[:50]
```

**Example Signatures**:

| Original Error                                                          | Normalized Pattern                 | Signature               |
| ----------------------------------------------------------------------- | ---------------------------------- | ----------------------- |
| `Koyfin API quota exceeded: 1000/1000 (request_id=abc123)`             | `api_quota_exceeded`               | `koyfin:quota:api:abc1` |
| `Koyfin rate limit reached - 1000 requests/hour (req_id=xyz789)`       | `api_rate_limit_exceeded`          | `koyfin:quota:api:abc1` |
| `Bloomberg terminal timeout after 30s (2025-11-18T14:27:33)`           | `network_timeout`                  | `bloomberg:net:term:ef2` |
| `SEC EDGAR filing not found: 10-K for 2024-Q3 (ticker=AAPL)`           | `data_not_found`                   | `sec:404:edgar:3f9a`    |
| `Financial data missing required field 'revenue' (stock_id=MSFT-uuid)` | `data_missing_field`               | `findata:miss:api:7b2c` |

### Correlation Detection Algorithm

**Temporal Clustering (5min Window)**:

```python
def detect_correlation(self, signature, timestamp, window_minutes=5):
    """Find failures with matching signature within time window"""

    # Query failures within 5min window, same signature
    window_start = timestamp - timedelta(minutes=window_minutes)
    window_end = timestamp + timedelta(minutes=window_minutes)

    correlated_failures = db.query("""
        SELECT id, stock_ticker, agent_type, error_type, data_source, timestamp
        FROM agent_failures
        WHERE error_signature = %s
          AND timestamp BETWEEN %s AND %s
          AND status = 'ACTIVE'  -- Not already resolved
        ORDER BY timestamp
    """, (signature, window_start, window_end)).all()

    return correlated_failures

def on_agent_failure(self, stock_ticker, agent_type, error_type, error_message, data_source, timestamp):
    """Main correlation detection flow"""

    # 1. Generate error signature
    signature = self.generate_error_signature(agent_type, error_type, data_source, error_message)

    # 2. Detect correlations within 5min window
    correlated_failures = self.detect_correlation(signature, timestamp, window_minutes=5)

    # 3. Check batch threshold (3+ failures = batch)
    if len(correlated_failures) >= 3:
        # Create correlation record
        correlation_id = self._create_correlation_record(
            signature=signature,
            failures=correlated_failures
        )

        # Infer root cause
        root_cause = self.infer_root_cause(signature, correlated_failures)

        # Extract stock IDs
        stock_ids = [f['stock_ticker'] for f in correlated_failures]

        # Auto-trigger batch pause
        batch_result = self.trigger_batch_pause(stock_ids, root_cause, correlation_id)

        return CorrelationResult(
            is_correlated=True,
            correlation_id=correlation_id,
            correlated_stocks=stock_ids,
            root_cause=root_cause,
            batch_triggered=True,
            batch_id=batch_result.batch_id
        )
    else:
        # Not correlated (< 3 failures), handle individually
        return CorrelationResult(
            is_correlated=False,
            correlation_id=None,
            correlated_stocks=[],
            root_cause=None,
            batch_triggered=False
        )
```

### Root Cause Inference

**Inference Rules**:

```python
def infer_root_cause(self, signature, correlated_failures):
    """Infer root cause from error signature and failure pattern"""

    # Extract common attributes
    data_sources = set(f['data_source'] for f in correlated_failures)
    agent_types = set(f['agent_type'] for f in correlated_failures)
    error_types = set(f['error_type'] for f in correlated_failures)

    # Rule 1: API quota (3+ stocks, same data source, quota error)
    if len(correlated_failures) >= 3 and len(data_sources) == 1:
        if 'quota' in signature or 'rate_limit' in signature:
            source = list(data_sources)[0]
            return f"{source} API quota exceeded"

    # Rule 2: Network outage (5+ stocks, same data source, network error)
    if len(correlated_failures) >= 5 and len(data_sources) == 1:
        if 'timeout' in signature or 'connection' in signature:
            source = list(data_sources)[0]
            return f"{source} network connectivity issue"

    # Rule 3: Data unavailability (3+ stocks, 404/not found)
    if len(correlated_failures) >= 3:
        if '404' in signature or 'not_found' in signature:
            source = list(data_sources)[0] if len(data_sources) == 1 else 'data source'
            return f"{source} data temporarily unavailable"

    # Rule 4: Agent bug (3+ stocks, same agent type, same error)
    if len(agent_types) == 1 and len(error_types) == 1:
        agent = list(agent_types)[0]
        error = list(error_types)[0]
        return f"{agent} agent failure - {error}"

    # Fallback: generic correlation
    return f"Shared failure affecting {len(correlated_failures)} stocks"
```

**Example Inferences**:

| Correlated Failures                                | Inference Rule | Root Cause                         |
| -------------------------------------------------- | -------------- | ---------------------------------- |
| 5 stocks, Koyfin, quota error                      | Rule 1         | "Koyfin API quota exceeded"        |
| 8 stocks, Bloomberg, timeout error                 | Rule 2         | "Bloomberg network connectivity"   |
| 4 stocks, SEC EDGAR, 404 error                     | Rule 3         | "SEC EDGAR data unavailable"       |
| 3 stocks, Financial Analyst, OOM error             | Rule 4         | "Financial Analyst OOM failure"    |
| 3 stocks, mixed sources/agents                     | Fallback       | "Shared failure - 3 stocks"        |

### Auto-Batch Trigger Integration

**FailureCorrelator → BatchManager**:

```python
def trigger_batch_pause(self, stock_ids, root_cause, correlation_id):
    """Auto-trigger batch pause when correlation detected"""

    # Call DD-012 BatchManager
    batch_result = self.batch_manager.pause_batch(
        stock_ids=stock_ids,
        reason=f"Correlated failure: {root_cause}",
        correlation_id=correlation_id,
        max_concurrency=5  # Default from DD-012
    )

    # Log correlation → batch link
    db.execute("""
        UPDATE failure_correlations
        SET batch_id = %s, batch_triggered_at = NOW()
        WHERE id = %s
    """, (batch_result.batch_id, correlation_id))

    logger.info(f"Auto-triggered batch pause: {len(stock_ids)} stocks, root cause: {root_cause}")

    return batch_result
```

**BatchManager → AlertManager**:

```python
# In BatchManager.pause_batch() (DD-012)
def pause_batch(self, stock_ids, reason, correlation_id=None, max_concurrency=5):
    """Batch pause with alert integration"""

    # Create batch record
    batch_id = self._create_batch_record(stock_ids, reason)

    # Pause each stock (DD-012 logic)
    for stock_id in stock_ids:
        self.pause_manager.pause_analysis(
            stock_id=stock_id,
            reason=reason,
            checkpoint_id=...,
            trigger_source='AUTO_BATCH_CORRELATION'
        )

    # Trigger batch alert (DD-015)
    # Note: DD-015 requirement = separate cards per stock
    self.alert_manager.on_batch_failure(
        stock_ids=stock_ids,
        root_cause=reason,  # "Correlated failure: Koyfin API quota exceeded"
        batch_id=batch_id,
        correlation_id=correlation_id
    )

    return BatchPauseResult(
        batch_id=batch_id,
        total_stocks=len(stock_ids),
        paused_count=len(stock_ids)
    )
```

### Database Schema

#### Table: `failure_correlations`

```sql
CREATE TABLE failure_correlations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Correlation metadata
    error_signature VARCHAR(16) NOT NULL,  -- Generated signature hash
    detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    correlation_window_min INTEGER DEFAULT 5,

    -- Correlated failures
    failure_ids UUID[] NOT NULL,  -- FK to agent_failures.id
    stock_tickers TEXT[] NOT NULL,
    failure_count INTEGER NOT NULL,

    -- Root cause inference
    root_cause TEXT,
    inference_confidence DECIMAL(3,2),  -- 0.00-1.00
    data_sources TEXT[],  -- Unique data sources involved
    agent_types TEXT[],  -- Unique agent types involved
    error_types TEXT[],  -- Unique error types involved

    -- Batch operation linkage
    batch_id UUID,  -- FK to batch_pause_operations.id (DD-012)
    batch_triggered_at TIMESTAMP,

    -- Resolution tracking
    resolved_at TIMESTAMP,
    resolution_action VARCHAR(50),  -- 'batch_resumed', 'manually_resolved', 'expired'

    FOREIGN KEY (batch_id) REFERENCES batch_pause_operations(id),
    INDEX idx_signature (error_signature),
    INDEX idx_detected_at (detected_at),
    INDEX idx_unresolved (resolved_at) WHERE resolved_at IS NULL,
    INDEX idx_batch (batch_id) WHERE batch_id IS NOT NULL
);
```

**Retention Policy**:

| Status           | Retention | Action                 |
| ---------------- | --------- | ---------------------- |
| Unresolved       | 14 days   | Active                 |
| Resolved         | 90 days   | Archive to cold storage|
| Archived         | 1 year    | Purge (audit log kept) |

### Lead Coordinator Integration

**Failure Event Subscription**:

```python
# In lead_coordinator.py
class LeadCoordinator:
    def __init__(self):
        self.failure_correlator = FailureCorrelator(
            batch_manager=self.batch_manager,
            alert_manager=self.alert_manager
        )

    def on_agent_failure_event(self, event):
        """Handle agent failure events"""

        # Attempt correlation detection
        correlation_result = self.failure_correlator.on_agent_failure(
            stock_ticker=event.stock_ticker,
            agent_type=event.agent_type,
            error_type=event.error_type,
            error_message=event.error_message,
            data_source=event.data_source,
            timestamp=event.timestamp
        )

        if correlation_result.batch_triggered:
            logger.info(
                f"Batch pause auto-triggered: {correlation_result.root_cause} "
                f"({len(correlation_result.correlated_stocks)} stocks)"
            )
        else:
            # No correlation, handle as individual failure (DD-012)
            self.pause_manager.pause_analysis(
                stock_id=event.stock_ticker,
                reason=event.error_message,
                checkpoint_id=event.checkpoint_id,
                trigger_source='AUTO_TIER2'
            )
```

### Testing Requirements

- **Signature generation**: Test normalization logic, various error formats, hash consistency
- **Correlation detection**: 5min window, edge cases (failures at window boundary)
- **Root cause inference**: All 4 inference rules, fallback logic
- **Auto-batch trigger**: 3+ correlated failures → batch pause, <3 → individual pause
- **DD-012 integration**: FailureCorrelator → BatchManager API calls
- **DD-015 integration**: Batch pause → alert with root cause
- **False negatives**: Different errors, same root cause (manual override available)
- **Concurrency**: 10 stocks fail simultaneously, all detected within 30s

**Estimated Implementation Effort**: 2 weeks

- Week 1: FailureCorrelator class, error signature generation, correlation detection algorithm, database schema
- Week 2: Root cause inference engine, auto-batch trigger integration, Lead Coordinator integration, testing

**Dependencies**:

- DD-012 BatchManager (prerequisite - implemented)
- DD-015 AlertManager (prerequisite - implemented)
- PostgreSQL infrastructure (exists)
- agent_failures table (exists from DD-011)

---

## Open Questions

**Resolved** (from design discussions):

1. ✅ Correlation threshold: 3+ failures (balance false positives vs sensitivity)
2. ✅ Time window: 5min (short enough to avoid unrelated failures, long enough for clusters)
3. ✅ Signature algorithm: Hash of normalized (agent_type, error_type, data_source, pattern)
4. ✅ Root cause inference: Rule-based (Phase 2), ML-based enhancement (Phase 4)
5. ✅ Auto-batch trigger: 3+ correlated → immediate batch pause
6. ✅ Manual override: Human can force batch grouping if auto-detection misses

**Pending**: None - design is complete, ready for implementation in Phase 2

**Blocking**: No

---

## References

- [Flaw #26: Multi-Stock Batching](../design-flaws/resolved/26-multi-stock-batching.md) - E1/E2 resolved by DD-017
- [DD-012: Workflow Pause/Resume](DD-012_WORKFLOW_PAUSE_RESUME.md) - provides BatchManager
- [DD-015: Agent Failure Alert System](DD-015_AGENT_FAILURE_ALERT_SYSTEM.md) - alert integration
- [Agents Coordination](../architecture/05-agents-coordination.md) - FailureCorrelator placement
- [Analysis Pipeline](../operations/01-analysis-pipeline.md) - failure handling flow

---

## Status History

| Date       | Status   | Notes                                  |
| ---------- | -------- | -------------------------------------- |
| 2025-11-18 | Approved | Design finalized, resolves Flaw #26 E1/E2 |

---

## Notes

Failure correlation detection is critical for production efficiency. Without it, system cannot:

- Automatically detect shared root causes (Koyfin quota → 5 stocks)
- Trigger batch pause without manual grouping
- Infer root cause for faster resolution (1 diagnosis vs 5 investigations)
- Scale to 100+ stocks (manual correlation impossible)

Priority: Medium - completes DD-012/DD-015 infrastructure, resolves Flaw #26 (E1/E2). E3 already resolved by DD-012.
