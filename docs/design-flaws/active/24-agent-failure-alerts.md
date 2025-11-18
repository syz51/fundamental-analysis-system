---
flaw_id: 24
title: Agent Failure Human Alerts Missing
status: active
priority: high
phase: 2
effort_weeks: 2
impact: Infrastructure failures go unnoticed, analyses silently fail
blocks: ['Production reliability', 'Human-in-the-loop effectiveness']
depends_on: ['DD-012 (workflow pause/resume)']
domain: ['operations', 'human-integration']
sub_issues:
  - id: C1
    severity: high
    title: No event-driven alerts for agent failures
  - id: C2
    severity: medium
    title: Alert acknowledgment tracking missing
  - id: C3
    severity: medium
    title: Batch failure notification strategy undefined
discovered: 2025-11-18
---

# Flaw #24: Agent Failure Human Alerts Missing

**Status**: 🔴 ACTIVE
**Priority**: High
**Impact**: Infrastructure failures go unnoticed, analyses silently fail
**Phase**: Phase 2 (Months 3-4)

---

## Problem Description

No event-driven human alerts for agent failures - only 6 scheduled gates trigger human interaction:

1. **C1**: No alert mechanism for agent failures (infrastructure/API/data issues)
2. **C2**: Alert acknowledgment tracking missing (did human see/respond?)
3. **C3**: Batch failure notification strategy undefined (5 stocks fail - 5 alerts or 1?)

### Sub-Issue C1: No Event-Driven Alerts for Agent Failures

**Current State**: Human interaction only at 6 scheduled decision gates

**Problem**: Agent failures between gates go unnoticed until next gate (hours/days later)

**Example**:
```text
Phase 2 Day 5 (between Gate 2 and Gate 3):
  2:47 PM - Strategy Analyst fails (Koyfin rate limit)
  ❌ No immediate alert to human
  ❌ Analysis pauses but human unaware
  ❌ Dashboard shows "in progress" (misleading)

Next Gate 3 (Valuation assumptions):
  Day 10 - Human sees incomplete analysis (3 days later!)
  Human: "Why didn't anyone tell me this failed on Day 5?"
```

**Current Alert System** (from `docs/operations/02-human-integration.md`):

Only covers scheduled gates:
- Gate 1 (24hr): Screening validation
- Gate 2 (12hr): Research direction
- Gate 3 (24hr): Valuation assumptions
- Gate 4 (6hr): Debate arbitration
- Gate 5 (blocking): Final decision
- Gate 6 (48hr): Learning validation

**Missing**:
- Infrastructure failure alerts (API quota, network, database)
- Agent crash alerts (exception, timeout, OOM)
- Data quality alerts (missing filings, corrupted data)
- Dependency failure alerts (upstream service down)

---

### Sub-Issue C2: Alert Acknowledgment Tracking Missing

**Problem**: No way to verify human received/responded to alert.

**Current Gate Timeout Behavior**:
- Gate times out → auto-action (conservative default)
- But for agent failures, **human must respond** (no auto-action)

**Missing Acknowledgment Flow**:
```text
Agent failure detected → Alert sent

Questions:
  1. Did human receive alert (email/SMS delivered)?
  2. Did human see alert (opened notification)?
  3. Did human acknowledge alert (clicked button)?
  4. Did human take action (resolved issue or cancelled analysis)?

If no acknowledgment after 2hr:
  5. Escalate? To whom?
  6. Retry notification? Different channel?
  7. Auto-cancel analysis? (user requirement: NO - always wait)
```

**User Requirement** (from discussion): Always wait for human, no timeout fallbacks

**Implementation Gap**: Need acknowledgment tracking + escalation path

---

### Sub-Issue C3: Batch Failure Notification Strategy Undefined

**Problem**: If 5 stocks fail due to shared issue (Koyfin quota), how to notify?

**User Requirement** (from discussion): Show 5 separate cards (not grouped)

**Current Uncertainty**:
```text
Koyfin rate limit affects 5 stocks at 2:47 PM:
  AAPL - Strategy Analyst failed
  MSFT - Strategy Analyst failed
  GOOGL - Strategy Analyst failed
  AMZN - Strategy Analyst failed
  META - Strategy Analyst failed

Notification Options:
  A) 5 separate alerts (user preference)
     - Pro: Clear per-stock status
     - Con: Alert fatigue, cluttered UI

  B) 1 grouped alert (rejected)
     - Pro: Clean UI, single action
     - Con: Hides per-stock details

  C) 1 summary + 5 detail cards
     - Pro: Overview + granularity
     - Con: Complexity
```

**User Decision**: Option A (5 separate cards)

**Missing Details**:
- Dashboard UI for multiple simultaneous alerts
- "Resume All" batch action button
- Per-stock vs. batch resolution tracking

---

## Recommended Solution

### New Alert Priority: AGENT_FAILURE

Extend current 4-level priority system with agent failure priority:

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

### Alert Triggering Logic

```python
class AgentFailureAlertManager:
    """Manage alerts for agent failures"""

    def on_agent_failure(self, agent_failure_event):
        """Trigger alert when agent fails"""

        # Pause analysis first (from Flaw #23)
        self.lead_coordinator.pause_analysis(
            stock_ticker=agent_failure_event.stock_ticker,
            reason='agent_failure',
            failed_agent=agent_failure_event.agent_type
        )

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
                'day': agent_failure_event.day
            }
        )

        # Send via all channels
        self.send_alert(alert, channels=['SMS', 'push', 'email', 'dashboard'])

        # Track acknowledgment
        self.track_acknowledgment(alert)

        return alert

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

### Alert UI (Dashboard)

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

### Acknowledgment API

```python
class AlertAcknowledgmentAPI:
    """Track human acknowledgment of alerts"""

    def acknowledge_alert(self, alert_id, user_id, action=None):
        """Record human acknowledgment"""

        db.execute(
            "UPDATE alert_acknowledgments "
            "SET acknowledged_at = NOW(), acknowledged_by = %s, action_taken = %s "
            "WHERE alert_id = %s",
            (user_id, action, alert_id)
        )

        # Cancel retry scheduler
        scheduler.cancel(task='retry_unacknowledged_alert', args=(alert_id,))

        # Log acknowledgment
        logger.info(f"Alert {alert_id} acknowledged by {user_id}, action: {action}")

    def get_acknowledgment_status(self, alert_id):
        """Check if alert acknowledged"""

        ack = db.query(
            "SELECT acknowledged_at, acknowledged_by, action_taken "
            "FROM alert_acknowledgments WHERE alert_id = %s",
            (alert_id,)
        ).one()

        return {
            'acknowledged': ack['acknowledged_at'] is not None,
            'acknowledged_at': ack['acknowledged_at'],
            'acknowledged_by': ack['acknowledged_by'],
            'action_taken': ack['action_taken']
        }
```

### Database Schema

```sql
CREATE TABLE agent_failure_alerts (
    id SERIAL PRIMARY KEY,
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
    checkpoint_progress DECIMAL(5,2),
    phase VARCHAR(50),
    day INT,
    completed_subtasks TEXT[],
    pending_subtasks TEXT[],

    -- Resolution
    resolved_at TIMESTAMP,
    resolution_action VARCHAR(50),  -- 'resumed', 'cancelled', 'escalated'

    INDEX idx_ticker (stock_ticker),
    INDEX idx_unresolved (resolved_at) WHERE resolved_at IS NULL
);

CREATE TABLE alert_acknowledgments (
    id SERIAL PRIMARY KEY,
    alert_id INT REFERENCES agent_failure_alerts(id),

    -- Acknowledgment tracking
    sent_at TIMESTAMP NOT NULL,
    acknowledged_at TIMESTAMP,
    acknowledged_by VARCHAR(100),
    action_taken VARCHAR(50),

    -- Delivery tracking
    channels_sent TEXT[],
    channels_opened TEXT[],
    retry_count INT DEFAULT 0,

    INDEX idx_unacknowledged (acknowledged_at) WHERE acknowledged_at IS NULL
);
```

---

## Implementation Plan

**Week 1**: Alert priority system, database schema, triggering logic
**Week 2**: Dashboard UI, acknowledgment tracking, retry mechanism

---

## Success Criteria

- ✅ Agent failure triggers alert <30s (SMS/push/email/dashboard)
- ✅ Unacknowledged alerts retried after 30min (up to 3 retries)
- ✅ Batch failures show separate cards (per user requirement)
- ✅ Human acknowledgment tracked (opened, clicked, action taken)
- ✅ Zero missed failures in 100-test simulation

---

## Dependencies

- **Blocks**: Production reliability (human awareness of failures)
- **Depends On**: DD-012 (workflow pause/resume) - Integrates with DD-012 pause/resume system for alert triggers (pause initiated, reminders, auto-resume notifications)
- **Related**: Flaw #26 (multi-stock batching - batch alert strategy)

---

## Files Affected

**New Files**:
- `src/alerts/agent_failure_alerts.py` - Alert manager, acknowledgment tracker
- `src/dashboard/alert_views.py` - Dashboard UI components
- `migrations/xxx_agent_failure_alerts.sql` - PostgreSQL schema

**Modified Files**:
- `src/coordination/lead_coordinator.py` - Trigger alerts on agent failure
- `docs/operations/02-human-integration.md` - Add AGENT_FAILURE priority
- `docs/architecture/01-system-overview.md` - Update human interaction points
