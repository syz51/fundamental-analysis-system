# Agent Failure Alert System

**Status**: Approved
**Date**: 2025-11-18
**Decider(s)**: System Architect
**Related Docs**: [Human Integration](../operations/02-human-integration.md), [Analysis Pipeline](../operations/01-analysis-pipeline.md), [System Overview](../architecture/01-system-overview.md)
**Related Decisions**: [DD-012 Workflow Pause/Resume](DD-012_WORKFLOW_PAUSE_RESUME.md), [DD-011 Agent Checkpoint System](DD-011_AGENT_CHECKPOINT_SYSTEM.md)

---

## Context

Agent failures between scheduled human gates go unnoticed for hours/days. System has 6 scheduled gates for strategic decisions but no event-driven alerts for infrastructure failures.

**Current State**:

- Human interaction only at 6 scheduled gates (1-6 per pipeline)
- Agent failures paused via DD-012 but human not notified
- No acknowledgment tracking (delivery vs opened vs acted upon)
- Undefined batch notification strategy (5 stocks fail → 5 alerts or 1?)

**Why Address Now**:

- Blocks production reliability (failures silently accumulate)
- DD-012 pause/resume requires alert integration (pause triggers)
- Resolves Flaw #24 (all 3 sub-issues C1/C2/C3)
- Phase 2 production: human must know when analyses paused

**Example Impact**: AAPL Strategy Analyst fails Day 5 at 2:47 PM (Koyfin quota). DD-012 auto-pauses analysis, saves checkpoint. Human unaware until Gate 3 on Day 10 (3 days later). Human: "Why wasn't I alerted immediately?"

---

## Decision

**Implement event-driven alert system with AGENT_FAILURE priority, multi-channel delivery (SMS/push/email/dashboard), acknowledgment tracking, retry mechanism (30min intervals), and batch alert support (separate cards per user requirement).**

System provides:

- Immediate alerts for agent failures (<30s from failure detection)
- Acknowledgment tracking (sent → delivered → opened → acted)
- Retry mechanism (30min intervals, max 3 retries, escalation after 90min)
- Batch alert support (separate cards for shared failures, "Resume All" button)
- Integration with DD-012 (pause events trigger alerts)
- Alert database schema (agent_failure_alerts, alert_acknowledgments)

---

## Options Considered

### Option 1: Event-Driven Alert System with Acknowledgment (CHOSEN)

**Description**: New AGENT_FAILURE priority, multi-channel delivery, acknowledgment tracking, retry mechanism, dashboard UI.

**Pros**:

- Immediate notification (<30s), prevents hours/days delay
- Multi-channel redundancy (SMS + push + email + dashboard)
- Acknowledgment tracking verifies human saw alert
- Retry mechanism handles delivery failures
- Batch support (separate cards) meets user requirement
- Integrates cleanly with DD-012 pause/resume

**Cons**:

- New infrastructure (AlertManager, database tables, dashboard UI)
- SMS/push integration complexity (Twilio, Firebase)
- Retry logic adds scheduler overhead
- Batch alerts (separate cards) may clutter dashboard

**Estimated Effort**: 2 weeks (Week 1: backend/DB, Week 2: UI/retry)

---

### Option 2: Dashboard-Only Alerts (No SMS/Push)

**Description**: Display alerts on dashboard only, no SMS/push/email.

**Pros**:

- Simpler implementation (no external services)
- Lower cost (no Twilio/Firebase fees)
- Less integration complexity

**Cons**:

- Human must check dashboard proactively (defeats "alert" purpose)
- No notifications if human offline/away from computer
- High risk of missed failures (defeats reliability goal)
- No redundancy if dashboard service down

**Estimated Effort**: 1 week

---

### Option 3: Grouped Batch Alerts (1 Alert for 5 Stocks)

**Description**: Group shared-root-cause failures into single alert.

**Pros**:

- Cleaner UI (1 card vs 5 cards)
- Less alert fatigue
- Easy to see root cause (Koyfin quota → 5 stocks)

**Cons**:

- User explicitly rejected this approach (wants separate cards)
- Hides per-stock details (checkpoint progress, pending subtasks)
- Harder to track per-stock resolution
- Cannot resume individual stocks (must resume all or none)

**Estimated Effort**: 1.5 weeks

---

## Rationale

**Option 1 (event-driven + acknowledgment) chosen** because:

1. **Immediate awareness**: <30s alert prevents hours/days delay. Critical for production reliability.

2. **Multi-channel redundancy**: SMS/push/email + dashboard ensures human receives alert even if one channel fails or human away from computer.

3. **Acknowledgment tracking**: Distinguishes sent vs delivered vs opened vs acted. Enables retry logic and escalation.

4. **User requirement**: Separate cards for batch failures (not grouped). User wants per-stock visibility and independent resume.

5. **DD-012 integration**: Pause events trigger alerts. AlertManager provides notification layer for PauseManager.

6. **Unblocks production**: Human cannot deploy to production without confidence failures detected immediately.

**Acceptable tradeoffs**:

- AlertManager complexity: necessary for production-grade reliability
- SMS/push costs: critical infrastructure, low volume (<10 failures/day expected)
- Dashboard clutter (batch alerts): user preference, mitigated with summary banner if >3 alerts
- 2-week implementation: justified by production reliability requirement

---

## Consequences

### Positive Impacts

- ✅ **Immediate failure awareness**: Human notified <30s from failure
- ✅ **Multi-channel redundancy**: SMS + push + email + dashboard
- ✅ **Delivery verification**: Acknowledgment tracking (sent/delivered/opened/acted)
- ✅ **Retry mechanism**: 30min retry if unacknowledged, max 3 attempts
- ✅ **Batch support**: Separate cards (user requirement), "Resume All" button
- ✅ **DD-012 integration**: Pause triggers alert, timeout reminders
- ✅ **Production readiness**: No silent failures, human in control

### Negative Impacts / Tradeoffs

- ❌ **Complexity**: AlertManager, acknowledgment tracker, retry scheduler
- ❌ **External dependencies**: Twilio (SMS), Firebase (push), SendGrid (email)
- ❌ **Database overhead**: 2 new tables (agent_failure_alerts, alert_acknowledgments)
- ❌ **Cost**: SMS/push per alert (estimate $0.01/alert, ~$3/month for 300 alerts)
- ❌ **Alert fatigue risk**: Batch failures (5 separate cards) may overwhelm UI
- ❌ **Testing complexity**: Multi-channel delivery, retry logic, acknowledgment tracking

**Mitigations**:

- Summary banner if >3 alerts (reduces visual clutter)
- Escalation after 3 retries prevents infinite retry loops
- Graceful degradation (if SMS fails, push/email still sent)
- Throttling policy (max 10 alerts/5min prevents spam)

### Affected Components

**New Components**:

- `AgentFailureAlertManager` class (trigger, format, track acknowledgment)
- `AlertAcknowledgmentTracker` class (delivery tracking, retry scheduler)
- `DashboardAlertView` component (alert cards, "Resume All" button)
- `agent_failure_alerts` table (stock, agent, error, checkpoint progress)
- `alert_acknowledgments` table (sent_at, acknowledged_at, channels, retry_count)

**Modified Components**:

- `PauseManager` (DD-012): Call AlertManager on pause_analysis()
- `lead_coordinator.py`: Alert on Tier 2 failures
- `dashboard/alert_views.py`: New alert feed, card components
- `notification_service.py`: Add SMS/push channel integrations

**Documentation Updates**:

- `02-human-integration.md`: Add AGENT_FAILURE priority level
- `01-system-overview.md`: Add AlertManager to Human Interface layer
- `DD-012_WORKFLOW_PAUSE_RESUME.md`: Add bidirectional dependency note

---

## Implementation Notes

### AGENT_FAILURE Priority Level

Extends existing 4-level priority system (CRITICAL/HIGH/MEDIUM/LOW) with agent failure priority:

```python
ALERT_PRIORITIES = {
    'AGENT_FAILURE': {
        'timeout_hours': None,  # Must wait for human (no auto-action)
        'channels': ['SMS', 'push', 'email', 'dashboard'],
        'escalation': 'Block pipeline, await human resolution',
        'acknowledgment_required': True,
        'batch_similar': False,  # Send separate alerts (user preference)
        'retry_unacknowledged_min': 30  # Re-send if not acknowledged
    },
    'CRITICAL': {  # Existing - debates blocking decisions
        'timeout_hours': 2,
        'channels': ['SMS', 'push'],
        'escalation': 'Conservative default fallback',
        'acknowledgment_required': False
    },
    'HIGH': {  # Existing - critical-path debates
        'timeout_hours': 6,
        'channels': ['push', 'email'],
        'escalation': 'Auto-resolve via credibility',
        'acknowledgment_required': False
    },
    'MEDIUM': {  # Existing - valuation decisions
        'timeout_hours': 24,
        'channels': ['email', 'dashboard'],
        'escalation': 'Conservative estimates',
        'acknowledgment_required': False
    },
    'LOW': {  # Existing - supporting analysis
        'timeout_hours': 48,
        'channels': ['dashboard'],
        'escalation': 'Defer to next gate',
        'acknowledgment_required': False
    }
}
```

### AgentFailureAlertManager

**Purpose**: Trigger alerts when agents fail, format messages, track acknowledgment

**API**:

```python
class AgentFailureAlertManager:
    """Manage alerts for agent failures"""

    def on_agent_failure(
        self,
        stock_ticker: str,
        agent_type: str,
        error_type: str,
        error_message: str,
        checkpoint_id: UUID,
        phase: str,
        day: int,
        progress_pct: float,
        completed_subtasks: List[str],
        pending_subtasks: List[str]
    ) -> Alert:
        """
        Trigger alert when agent fails

        Called by PauseManager immediately after pause_analysis()

        Returns: Alert object with alert_id
        """

    def format_alert_message(self, event: AgentFailureEvent) -> str:
        """Format human-readable alert message"""

    def track_acknowledgment(self, alert: Alert) -> None:
        """Create acknowledgment record, schedule retry"""

    def retry_unacknowledged_alert(self, alert_id: UUID) -> None:
        """Resend alert if not acknowledged after 30min"""

    def escalate_alert(self, alert: Alert) -> None:
        """Escalate after 3 failed retry attempts (90min)"""
```

**Trigger Logic**:

```python
def on_agent_failure(self, agent_failure_event):
    """Trigger alert when agent fails"""

    # Create alert
    alert = Alert(
        priority='AGENT_FAILURE',
        stock_ticker=agent_failure_event.stock_ticker,
        title=f'Agent Failure: {agent_failure_event.agent_type}',
        message=self.format_alert_message(agent_failure_event),
        action_buttons=['View Details', 'Resume Analysis', 'Cancel Analysis'],
        metadata={
            'agent_type': agent_failure_event.agent_type,
            'error': agent_failure_event.error,
            'checkpoint_progress': agent_failure_event.progress_pct,
            'phase': agent_failure_event.phase,
            'day': agent_failure_event.day,
            'checkpoint_id': agent_failure_event.checkpoint_id
        }
    )

    # Send via all channels
    self.send_alert(alert, channels=['SMS', 'push', 'email', 'dashboard'])

    # Track acknowledgment
    self.track_acknowledgment(alert)

    return alert
```

**Message Format**:

```python
def format_alert_message(self, event):
    """Format human-readable alert message"""

    return f"""🔴 AGENT FAILURE - Action Required

Stock: {event.stock_ticker} ({event.company_name})
Agent: {event.agent_type.replace('_', ' ').title()}
Status: PAUSED at {event.progress_pct}% (Phase {event.phase} Day {event.day})

Error: {event.error_type} - {event.error_message}
Completed: {', '.join(event.completed_subtasks)}
Pending: {', '.join(event.pending_subtasks)}

Action: Resolve {event.root_cause_hint}, then click "Resume"
"""
```

### Acknowledgment Tracking

**Purpose**: Verify human received/opened/acted on alert

**Tracking States**:

1. **SENT**: Alert sent via all channels, awaiting delivery confirmation
2. **DELIVERED**: Channel confirms delivery (SMS delivered, email accepted)
3. **OPENED**: Human opened notification (push clicked, email opened, dashboard viewed)
4. **ACKNOWLEDGED**: Human clicked action button (View Details, Resume, Cancel)

**Retry Logic**:

```python
def track_acknowledgment(self, alert):
    """Track if human acknowledged alert"""

    # Create acknowledgment record
    ack_record = {
        'alert_id': alert.id,
        'sent_at': datetime.utcnow(),
        'acknowledged_at': None,
        'acknowledged_by': None,
        'action_taken': None,
        'channels_sent': ['SMS', 'push', 'email', 'dashboard'],
        'channels_opened': [],
        'retry_count': 0
    }

    db.insert('alert_acknowledgments', ack_record)

    # Schedule retry if not acknowledged
    scheduler.schedule(
        task='retry_unacknowledged_alert',
        args=(alert.id,),
        delay_minutes=30
    )

def retry_unacknowledged_alert(self, alert_id):
    """Resend alert if not acknowledged after 30min"""

    ack = db.query(
        "SELECT * FROM alert_acknowledgments WHERE alert_id = %s",
        (alert_id,)
    ).one()

    if ack['acknowledged_at'] is None:
        # Not acknowledged - resend
        alert = self.get_alert(alert_id)

        logger.warning(f"Alert {alert_id} not acknowledged after 30min, resending")

        # Resend via all channels
        self.send_alert(alert, channels=['SMS', 'push', 'email'])

        # Update retry count
        db.execute(
            "UPDATE alert_acknowledgments SET retry_count = retry_count + 1 "
            "WHERE alert_id = %s",
            (alert_id,)
        )

        # Schedule next retry if still not acknowledged
        if ack['retry_count'] < 3:
            scheduler.schedule(
                task='retry_unacknowledged_alert',
                args=(alert_id,),
                delay_minutes=30
            )
        else:
            # Escalate after 3 retries (90 min)
            self.escalate_alert(alert)
```

**Escalation Policy**:

- After 3 retries (90min total): Log critical error, send to secondary contact (if configured)
- No auto-cancel (user requirement: always wait for human)
- Alert remains active until human acknowledges

### Dashboard Alert UI

**Alert Card Component** (per user requirement: separate cards, not grouped):

```python
class DashboardAlertView:
    """Dashboard alert cards for agent failures"""

    def render_alert_card(self, alert):
        """Render individual alert card"""

        # User requirement: Separate cards for batch failures
        return f"""
        <div class="alert-card priority-{alert.priority}">
            <div class="alert-header">
                <span class="icon">🔴</span>
                <h3>{alert.title}</h3>
                <span class="timestamp">{alert.sent_at.strftime('%I:%M %p')}</span>
            </div>

            <div class="alert-body">
                <div class="stock-info">
                    <strong>{alert.stock_ticker}</strong> - {alert.metadata['company_name']}
                </div>

                <div class="failure-details">
                    <p><strong>Agent:</strong> {alert.metadata['agent_type']}</p>
                    <p><strong>Progress:</strong> {alert.metadata['checkpoint_progress']}%</p>
                    <p><strong>Phase:</strong> {alert.metadata['phase']} Day {alert.metadata['day']}</p>
                    <p><strong>Error:</strong> {alert.metadata['error']}</p>
                </div>

                <div class="subtask-status">
                    <p>✅ Completed: {alert.metadata['completed_subtasks']}</p>
                    <p>⏸️ Pending: {alert.metadata['pending_subtasks']}</p>
                </div>
            </div>

            <div class="alert-actions">
                <button onclick="viewDetails('{alert.id}')">View Details</button>
                <button onclick="resumeAnalysis('{alert.stock_ticker}')" class="primary">
                    Resume Analysis
                </button>
                <button onclick="cancelAnalysis('{alert.stock_ticker}')" class="secondary">
                    Cancel Analysis
                </button>
            </div>
        </div>
        """

    def render_batch_alerts(self, alerts):
        """Render multiple alerts (user requirement: separate cards)"""

        # Show summary banner if >3 alerts
        summary = ""
        if len(alerts) > 3:
            summary = f"""
            <div class="batch-summary">
                <p>⚠️ {len(alerts)} analyses paused due to failures</p>
                <button onclick="resumeAll()">Resume All</button>
            </div>
            """

        # Render individual cards (not grouped)
        cards = "\n".join(self.render_alert_card(alert) for alert in alerts)

        return summary + cards
```

### Database Schema

#### Table 1: `agent_failure_alerts`

```sql
CREATE TABLE agent_failure_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_ticker VARCHAR(10) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    analysis_id UUID NOT NULL,

    -- Alert details
    priority VARCHAR(20) DEFAULT 'AGENT_FAILURE',
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT NOW(),

    -- Failure context
    error_type VARCHAR(100),
    error_message TEXT,
    checkpoint_id UUID NOT NULL,  -- FK to checkpoints.id (DD-011)
    checkpoint_progress DECIMAL(5,2),
    phase VARCHAR(50),
    day INT,
    completed_subtasks TEXT[],
    pending_subtasks TEXT[],

    -- Resolution
    resolved_at TIMESTAMP,
    resolution_action VARCHAR(50),  -- 'resumed', 'cancelled', 'escalated'
    resolved_by VARCHAR(100),

    FOREIGN KEY (checkpoint_id) REFERENCES checkpoints(id),
    INDEX idx_ticker (stock_ticker),
    INDEX idx_unresolved (resolved_at) WHERE resolved_at IS NULL,
    INDEX idx_sent_at (sent_at)
);
```

#### Table 2: `alert_acknowledgments`

```sql
CREATE TABLE alert_acknowledgments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL,  -- FK to agent_failure_alerts.id

    -- Acknowledgment tracking
    sent_at TIMESTAMP NOT NULL,
    acknowledged_at TIMESTAMP,
    acknowledged_by VARCHAR(100),
    action_taken VARCHAR(50),  -- 'view_details', 'resume', 'cancel'

    -- Delivery tracking
    channels_sent TEXT[],  -- ['SMS', 'push', 'email', 'dashboard']
    channels_delivered TEXT[],  -- Channels confirmed delivered
    channels_opened TEXT[],  -- Channels human opened
    retry_count INT DEFAULT 0,
    last_retry_at TIMESTAMP,

    FOREIGN KEY (alert_id) REFERENCES agent_failure_alerts(id) ON DELETE CASCADE,
    INDEX idx_unacknowledged (acknowledged_at) WHERE acknowledged_at IS NULL,
    INDEX idx_alert (alert_id)
);
```

### DD-012 Integration (Pause/Resume)

**Pause Trigger → Alert Trigger**:

```python
# In PauseManager.pause_analysis()
def pause_analysis(self, stock_id, reason, checkpoint_id, trigger_source):
    # 1. Save checkpoint (DD-011)
    checkpoint = self.checkpoint_system.save_checkpoint(stock_id)

    # 2. Trigger alert (DD-015) - NEW
    alert = self.alert_manager.on_agent_failure(
        stock_ticker=stock_id,
        agent_type=failed_agent_type,
        error_type=error_type,
        error_message=error_message,
        checkpoint_id=checkpoint.id,
        phase=checkpoint.phase,
        day=checkpoint.day,
        progress_pct=checkpoint.progress_pct,
        completed_subtasks=checkpoint.completed_subtasks,
        pending_subtasks=checkpoint.pending_subtasks
    )

    # 3. Pause workflow (DD-012)
    self.orchestrator.pause_workflow(workflow_id)

    # 4. Update pause state
    self.update_pause_state(stock_id, status='PAUSED')

    return PauseResult(success=True, alert_id=alert.id)
```

**Alert Types from DD-012**:

1. **Pause Initiated**: Alert on initial Tier 2 failure → auto-pause
2. **Pause Reminder (Day 3)**: Reminder if paused >3 days (from DD-012 timeout escalation)
3. **Pause Warning (Day 7)**: Warning if paused >7 days
4. **Auto-Resume Success**: Notification when auto-resume succeeds
5. **Auto-Resume Failure**: Alert when auto-resume fails, re-paused
6. **Batch Resume Complete**: Notification when batch resume completes

### Batch Alert Strategy

**User Requirement**: Separate cards for batch failures (not grouped)

**Implementation**:

```python
# When 5 stocks fail from shared root cause (Koyfin quota)
def handle_batch_failure(self, stocks, root_cause):
    """
    Create separate alert for each stock (user requirement)

    Example: Koyfin quota → 5 stocks fail
    Result: 5 separate alert cards on dashboard
    """

    alerts = []
    for stock in stocks:
        # Create individual alert (not grouped)
        alert = self.on_agent_failure(
            stock_ticker=stock.ticker,
            agent_type=stock.failed_agent,
            error_type='API_QUOTA_EXCEEDED',
            error_message=f'Koyfin rate limit: {root_cause}',
            checkpoint_id=stock.checkpoint_id,
            # ... other parameters
        )
        alerts.append(alert)

    # Link alerts for batch operations (resume all)
    batch_id = self.create_batch_group(alerts)

    return alerts
```

**Dashboard Rendering**:

- 5 separate cards displayed (user preference)
- Summary banner if >3 alerts: "⚠️ 5 analyses paused due to failures"
- "Resume All" button for batch resume (calls BatchManager from DD-012)

### Multi-Channel Delivery

**Channels**:

1. **SMS** (Twilio): Highest priority, immediate delivery
2. **Push** (Firebase): Mobile/desktop notifications
3. **Email** (SendGrid): Detailed message, audit trail
4. **Dashboard**: Real-time in-app alert feed

**Graceful Degradation**:

- If SMS fails: Continue with push/email/dashboard
- If push fails: Continue with SMS/email/dashboard
- If all channels fail: Log critical error, retry after 5min

**Throttling**:

- Max 10 alerts per 5min window (prevents spam)
- If exceeded: Queue alerts, send summary instead

### Testing Requirements

- **Multi-channel delivery**: Verify all 4 channels receive alert
- **Acknowledgment tracking**: Test sent → delivered → opened → acknowledged states
- **Retry mechanism**: Verify 30min retry, max 3 attempts, escalation
- **Batch alerts**: Test separate cards rendering, "Resume All" button
- **DD-012 integration**: Pause triggers alert, alert_id linked to pause_id
- **Graceful degradation**: Test channel failures, fallback behavior
- **Throttling**: Test >10 alerts/5min, verify summary sent instead

**Estimated Implementation Effort**: 2 weeks

- Week 1: AlertManager, database schema, multi-channel integrations, acknowledgment tracking
- Week 2: Dashboard UI (alert cards, feed), retry scheduler, DD-012 integration, testing

**Dependencies**:

- DD-012 pause/resume (prerequisite - approved)
- DD-011 checkpoint system (prerequisite - implemented)
- Twilio account (SMS)
- Firebase account (push)
- SendGrid account (email)
- Scheduler infrastructure (Redis-based or cron-based)

---

## Open Questions

**Resolved** (from design discussions):

1. ✅ Batch notification strategy: Separate cards (user requirement)
2. ✅ Acknowledgment tracking: Sent → delivered → opened → acknowledged
3. ✅ Retry mechanism: 30min intervals, max 3 retries, escalation
4. ✅ Escalation policy: Log critical error, no auto-cancel (wait for human)
5. ✅ DD-012 integration: Pause triggers alert, bidirectional dependency
6. ✅ Multi-channel priority: SMS > push > email > dashboard (all sent simultaneously)

**Pending**: None - design is complete, ready for implementation in Phase 2

**Blocking**: No

---

## References

- [Flaw #24: Agent Failure Alerts](../design-flaws/active/24-agent-failure-alerts.md) - resolved by this decision
- [DD-012: Workflow Pause/Resume](DD-012_WORKFLOW_PAUSE_RESUME.md) - bidirectional dependency
- [DD-011: Agent Checkpoint System](DD-011_AGENT_CHECKPOINT_SYSTEM.md) - provides failure context
- [Human Integration](../operations/02-human-integration.md) - gate vs alert distinction
- [System Overview](../architecture/01-system-overview.md) - AlertManager in Human Interface layer

---

## Status History

| Date       | Status   | Notes                                          |
| ---------- | -------- | ---------------------------------------------- |
| 2025-11-18 | Approved | Design finalized, resolves Flaw #24 (C1/C2/C3) |

---

## Notes

Agent failure alerts are critical for production reliability. Without them, system cannot:

- Notify human immediately when agents fail (vs hours/days delay)
- Verify human received/acknowledged alerts (delivery tracking)
- Handle batch failures gracefully (separate cards per stock)
- Integrate with DD-012 pause/resume (alert on pause trigger)

Priority: High - blocks Phase 2 production readiness and resolves Flaw #24.
