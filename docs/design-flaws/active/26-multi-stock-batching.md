---
flaw_id: 26
title: Multi-Stock Failure Batching Undefined
status: active
priority: medium
phase: 2
effort_weeks: 2
impact: Inefficient recovery when shared failures affect multiple stocks
blocks: ['Batch recovery efficiency']
depends_on: ['DD-012 (pause/resume)', 'Flaw #24 (alerts)']
domain: ['operations']
sub_issues:
  - id: E1
    severity: medium
    title: Failure correlation detection missing
  - id: E2
    severity: medium
    title: Batch pause capability undefined
  - id: E3
    severity: low
    title: Parallel resume orchestration missing
discovered: 2025-11-18
---

# Flaw #26: Multi-Stock Failure Batching Undefined

**Status**: 🔴 ACTIVE
**Priority**: Medium
**Impact**: Inefficient recovery when shared failures affect multiple stocks
**Phase**: Phase 2 (Months 3-4)

---

## Problem Description

No specification for handling failures that affect multiple stocks simultaneously:

1. **E1**: Failure correlation detection missing (detect shared root cause)
2. **E2**: Batch pause capability undefined (pause all affected vs. individual)
3. **E3**: Parallel resume orchestration missing (resume all at once vs. sequential)

### Sub-Issue E1: Failure Correlation Detection Missing

**Problem**: When 5 stocks fail within minutes due to shared issue, system treats as 5 independent failures.

**Example Scenario**:

```text
2:47 PM - Koyfin API rate limit exceeded (quota: 100 req/hour)

Strategy Analyst failures (5 stocks within 3 minutes):
  2:47:15 - AAPL Strategy Analyst fails
  2:47:42 - MSFT Strategy Analyst fails
  2:48:03 - GOOGL Strategy Analyst fails
  2:48:31 - AMZN Strategy Analyst fails
  2:49:05 - META Strategy Analyst fails

Current Behavior: Treats as 5 independent failures
  → 5 separate pause operations
  → 5 separate checkpoints saved
  → 5 separate alerts sent (per user requirement)
  → Human investigates 5 times, discovers same root cause

Desired Behavior: Detect correlation
  → Identify shared root cause: "Koyfin rate limit"
  → Group 5 failures into batch
  → Single investigation, single fix
  → Batch resume all 5 stocks
```

**Correlation Signals**:

- Same error type (API rate limit 429)
- Same data source (Koyfin)
- Same agent type (Strategy Analyst)
- Temporal proximity (within 5 minutes)
- Same error message substring

**Missing**:

- Correlation detection algorithm
- Batch failure record (link 5 failures together)
- Root cause inference (why did all 5 fail?)

---

### Sub-Issue E2: Batch Pause Capability Undefined

**Problem**: No specification for batch pausing multiple stocks at once.

**Batch Pause**: Uses BatchManager component from DD-012 for concurrent pause/resume operations (5 parallel default)

**Current Pause API** (from DD-012):

```python
# Individual pause only
pause_analysis(stock_ticker='AAPL', reason='agent_failure')
pause_analysis(stock_ticker='MSFT', reason='agent_failure')
pause_analysis(stock_ticker='GOOGL', reason='agent_failure')
# ... repeat for each stock
```

**User Requirement** (from discussion): Pause all affected stocks when correlation detected

**Needed Batch Pause**:

```python
# Batch pause
pause_batch(
    stock_tickers=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'],
    reason='koyfin_rate_limit',
    batch_id='batch_20251118_1447'
)
```

**Questions**:

- Pause all simultaneously or sequential?
- Single database transaction or individual?
- Rollback if one pause fails?
- How to represent batch in dashboard?

---

### Sub-Issue E3: Parallel Resume Orchestration Missing

**Problem**: When human resolves shared issue, how to resume all 5 stocks?

**User Requirement** (from discussion): Allow parallel resume (no forced sequential)

**Current Resume Challenges**:

```text
Human upgrades Koyfin to paid tier at 3:15 PM.
Clicks "Resume All" for 5 paused stocks.

Questions:
  1. Resume all 5 simultaneously or respect concurrency limit?
     → Respect limit (max 3 Strategy Analysts)

  2. Which stocks start first if >concurrency?
     → Priority queue: highest progress first? Oldest pause first?

  3. Track batch resume progress?
     → "2/5 stocks resumed, 3 queued"

  4. Handle individual resume failure within batch?
     → Continue others or abort batch?

  5. Update batch status when all complete?
     → Mark batch as "fully resumed"
```

**Missing Orchestration**:

- Priority queue for batch resume
- Concurrency limit enforcement
- Individual failure handling
- Progress tracking UI

---

## Recommended Solution

### Failure Correlation Detection

```python
class FailureCorrelator:
    """Detect correlated failures and group into batches"""

    CORRELATION_WINDOW_MINUTES = 5
    MIN_BATCH_SIZE = 2

    def correlate_failures(self, failure_events):
        """Group failures by correlation"""

        # Group by error signature
        by_signature = defaultdict(list)

        for event in failure_events:
            signature = self.get_error_signature(event)
            by_signature[signature].append(event)

        # Create batches for correlated failures
        batches = []
        for signature, events in by_signature.items():
            # Check temporal proximity
            events_sorted = sorted(events, key=lambda e: e.timestamp)
            first_ts = events_sorted[0].timestamp
            last_ts = events_sorted[-1].timestamp
            time_span_min = (last_ts - first_ts).total_seconds() / 60

            if time_span_min <= self.CORRELATION_WINDOW_MINUTES and \
               len(events) >= self.MIN_BATCH_SIZE:
                # Correlated batch detected
                batch = FailureBatch(
                    batch_id=f"batch_{first_ts.strftime('%Y%m%d_%H%M')}",
                    error_signature=signature,
                    failure_events=events,
                    root_cause=self.infer_root_cause(signature),
                    detected_at=datetime.utcnow()
                )
                batches.append(batch)

        return batches

    def get_error_signature(self, event):
        """Generate error signature for correlation"""

        return (
            event.agent_type,
            event.error_type,
            event.data_source,
            self.normalize_error_message(event.error_message)
        )

    def normalize_error_message(self, message):
        """Normalize error message for matching"""

        # Remove stock-specific details
        normalized = re.sub(r'\b[A-Z]{1,5}\b', 'TICKER', message)  # AAPL → TICKER
        normalized = re.sub(r'\d+', 'NUM', normalized)             # 429 → NUM

        return normalized

    def infer_root_cause(self, signature):
        """Infer root cause from error signature"""

        agent_type, error_type, data_source, _ = signature

        if error_type == 'RateLimitError':
            return f"{data_source} API rate limit exceeded"
        elif error_type == 'TimeoutError':
            return f"{data_source} API timeout"
        elif error_type == 'AuthenticationError':
            return f"{data_source} API authentication failure"
        elif error_type == 'NetworkError':
            return f"{data_source} network connectivity issue"
        else:
            return f"{agent_type} failure via {data_source}"
```

### Batch Pause API

```python
class BatchPauseManager:
    """Handle batch pause/resume operations"""

    def pause_batch(self, stock_tickers, reason, batch_id=None):
        """Pause multiple stocks as batch"""

        if batch_id is None:
            batch_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Create batch record
        batch_record = {
            'batch_id': batch_id,
            'stock_tickers': stock_tickers,
            'reason': reason,
            'paused_at': datetime.utcnow(),
            'status': 'paused',
            'pause_count': len(stock_tickers)
        }

        db.insert('batch_operations', batch_record)

        # Pause each stock (in transaction for atomicity)
        with db.transaction():
            for ticker in stock_tickers:
                self.pause_manager.pause_analysis(
                    stock_ticker=ticker,
                    reason=reason,
                    batch_id=batch_id  # Link to batch
                )

        logger.info(f"Batch pause complete: {batch_id} - {len(stock_tickers)} stocks")

        return batch_record

    def resume_batch(self, batch_id, priority_order='progress_desc'):
        """Resume all stocks in batch"""

        # Get batch record
        batch = db.query(
            "SELECT * FROM batch_operations WHERE batch_id = %s",
            (batch_id,)
        ).one()

        # Get pause records for each stock
        pause_records = db.query(
            "SELECT * FROM paused_analyses "
            "WHERE stock_ticker = ANY(%s) AND batch_id = %s",
            (batch['stock_tickers'], batch_id)
        ).all()

        # Sort by priority
        if priority_order == 'progress_desc':
            # Resume highest progress first
            pause_records.sort(
                key=lambda r: r['checkpoint_progress_pct'],
                reverse=True
            )
        elif priority_order == 'timestamp_asc':
            # Resume oldest first (FIFO)
            pause_records.sort(key=lambda r: r['paused_at'])

        # Create resume plan with concurrency management
        resume_plan = self.create_batch_resume_plan(pause_records)

        # Execute resume
        self.execute_batch_resume(resume_plan)

        # Update batch status
        db.execute(
            "UPDATE batch_operations SET status = 'resuming', resumed_at = NOW() "
            "WHERE batch_id = %s",
            (batch_id,)
        )

        return resume_plan

    def create_batch_resume_plan(self, pause_records):
        """Create resume plan respecting concurrency limits"""

        # Group by agent type
        by_agent = defaultdict(list)
        for record in pause_records:
            agent_type = record['failed_agent']
            by_agent[agent_type].append(record)

        plan = BatchResumePlan()

        # Schedule within concurrency limits
        for agent_type, records in by_agent.items():
            concurrency_limit = AGENT_CONCURRENCY[agent_type]

            # Immediate (up to concurrency limit)
            immediate = records[:concurrency_limit]
            for record in immediate:
                plan.add_task(
                    stock_ticker=record['stock_ticker'],
                    agent_type=agent_type,
                    schedule='immediate',
                    priority=records.index(record)
                )

            # Queued (beyond limit)
            queued = records[concurrency_limit:]
            for record in queued:
                plan.add_task(
                    stock_ticker=record['stock_ticker'],
                    agent_type=agent_type,
                    schedule='queued',
                    priority=records.index(record)
                )

        return plan

    def execute_batch_resume(self, plan):
        """Execute batch resume with queue management"""

        # Start immediate tasks
        for task in plan.immediate_tasks:
            self.resume_manager.resume_analysis(task.stock_ticker)

        # Queue remaining tasks
        for task in plan.queued_tasks:
            self.queue_manager.enqueue_resume(
                stock_ticker=task.stock_ticker,
                agent_type=task.agent_type,
                priority=task.priority,
                on_slot_available=self.resume_manager.resume_analysis
            )

        logger.info(
            f"Batch resume started: {len(plan.immediate_tasks)} immediate, "
            f"{len(plan.queued_tasks)} queued"
        )
```

### Batch Alert Strategy

**User Requirement**: 5 separate cards (not grouped)

**Implementation**:

```python
class BatchAlertManager:
    """Manage alerts for batch failures"""

    def send_batch_alerts(self, failure_batch):
        """Send separate alerts for each failure (per user requirement)"""

        # Send individual alert for each stock
        alerts = []
        for event in failure_batch.failure_events:
            alert = self.alert_manager.send_agent_failure_alert(event)
            alerts.append(alert)

        # Add batch context to each alert
        for alert in alerts:
            alert.metadata['batch_id'] = failure_batch.batch_id
            alert.metadata['batch_size'] = len(failure_batch.failure_events)
            alert.metadata['root_cause'] = failure_batch.root_cause

        # Show summary banner in dashboard if >3 alerts
        if len(alerts) > 3:
            self.dashboard.show_batch_summary(
                batch_id=failure_batch.batch_id,
                alert_count=len(alerts),
                root_cause=failure_batch.root_cause,
                affected_stocks=failure_batch.stock_tickers,
                actions=['Resume All', 'Cancel All']
            )

        logger.info(f"Batch alerts sent: {len(alerts)} separate cards")

        return alerts
```

### Database Schema

```sql
CREATE TABLE batch_operations (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(50) UNIQUE NOT NULL,

    -- Batch details
    stock_tickers TEXT[] NOT NULL,
    reason TEXT,
    root_cause TEXT,

    -- Status
    status VARCHAR(20),  -- 'paused', 'resuming', 'completed', 'failed'
    paused_at TIMESTAMP,
    resumed_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Counts
    pause_count INT,
    resume_success_count INT DEFAULT 0,
    resume_failure_count INT DEFAULT 0,

    INDEX idx_batch_id (batch_id),
    INDEX idx_status (status)
);

-- Extend paused_analyses to link to batch
ALTER TABLE paused_analyses
ADD COLUMN batch_id VARCHAR(50) REFERENCES batch_operations(batch_id);
```

---

## Implementation Plan

**Week 1**: Failure correlation detection, batch record schema
**Week 2**: Batch pause/resume API, concurrency management, parallel resume orchestration

---

## Success Criteria

- ✅ Detect correlated failures within 5min window (95% accuracy)
- ✅ Batch pause completes <10s for 5 stocks (atomic transaction)
- ✅ Parallel resume respects concurrency limits (no overload)
- ✅ Individual resume failure doesn't abort batch (continue others)
- ✅ Batch resume progress tracked in dashboard (real-time updates)

---

## Dependencies

- **Blocks**: Batch recovery efficiency
- **Depends On**: Flaw #23 (pause/resume infrastructure), Flaw #24 (alert system)
- **Related**: Flaw #22 (checkpoints for each stock in batch)

---

## Files Affected

**New Files**:

- `src/coordination/failure_correlator.py` - Correlation detection
- `src/coordination/batch_manager.py` - Batch pause/resume logic
- `migrations/xxx_batch_operations.sql` - PostgreSQL schema

**Modified Files**:

- `src/coordination/pause_manager.py` - Add batch_id parameter
- `src/alerts/agent_failure_alerts.py` - Add batch context to alerts
- `src/dashboard/batch_summary_view.py` - Batch summary banner
- `docs/operations/02-human-integration.md` - Document batch alert strategy
