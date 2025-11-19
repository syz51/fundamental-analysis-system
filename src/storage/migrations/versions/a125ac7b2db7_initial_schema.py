"""Initial schema

Revision ID: a125ac7b2db7
Revises:
Create Date: 2025-11-19 07:05:45.930324

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a125ac7b2db7"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 00_init_schemas.sql
    op.execute("CREATE SCHEMA IF NOT EXISTS financial_data")
    op.execute("CREATE SCHEMA IF NOT EXISTS market_data")
    op.execute("CREATE SCHEMA IF NOT EXISTS metadata")
    op.execute("CREATE SCHEMA IF NOT EXISTS document_registry")
    op.execute("CREATE SCHEMA IF NOT EXISTS workflow")
    op.execute("CREATE SCHEMA IF NOT EXISTS access_tracking")
    op.execute("CREATE SCHEMA IF NOT EXISTS outcomes")

    # 01_workflow_schema.sql
    op.execute("""
    CREATE TABLE IF NOT EXISTS workflow.agent_checkpoints (
        id SERIAL PRIMARY KEY,
        stock_ticker VARCHAR(10) NOT NULL,
        agent_type VARCHAR(50) NOT NULL,
        analysis_id UUID NOT NULL,
        checkpoint_time TIMESTAMP NOT NULL,
        progress_pct DECIMAL(5,2),
        current_subtask VARCHAR(100),
        completed_subtasks TEXT[],
        pending_subtasks TEXT[],
        working_memory JSONB,
        interim_results JSONB,
        agent_config JSONB,
        l1_snapshot JSONB,
        l1_snapshot_hash TEXT,
        failure_reason TEXT,
        error_details JSONB,
        retry_count INT DEFAULT 0,
        agent_version VARCHAR(20),
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE (analysis_id, agent_type, checkpoint_time)
    )
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_stock_agent ON workflow.agent_checkpoints(stock_ticker, agent_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_analysis ON workflow.agent_checkpoints(analysis_id)"
    )

    op.execute("""
    CREATE TABLE IF NOT EXISTS workflow.batch_pause_operations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        batch_name VARCHAR(100) NOT NULL,
        pause_reason TEXT NOT NULL,
        stock_ids TEXT[] NOT NULL,
        total_count INTEGER NOT NULL,
        paused_count INTEGER DEFAULT 0,
        resumed_count INTEGER DEFAULT 0,
        failed_count INTEGER DEFAULT 0,
        status VARCHAR(20) NOT NULL CHECK (status IN ('IN_PROGRESS', 'COMPLETED', 'PARTIALLY_FAILED', 'FAILED')),
        concurrency_limit INTEGER DEFAULT 5,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        completed_at TIMESTAMP,
        CHECK (total_count = array_length(stock_ids, 1))
    )
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_batch_name ON workflow.batch_pause_operations(batch_name)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_batch_status ON workflow.batch_pause_operations(status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_batch_created ON workflow.batch_pause_operations(created_at)"
    )

    op.execute("""
    CREATE TABLE IF NOT EXISTS workflow.paused_analyses (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        stock_id VARCHAR(10) NOT NULL,
        pause_reason TEXT NOT NULL,
        pause_trigger VARCHAR(20) NOT NULL CHECK (pause_trigger IN ('AUTO_TIER2', 'MANUAL', 'GATE_TIMEOUT', 'GATE_REJECTION')),
        pause_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
        resume_timestamp TIMESTAMP,
        checkpoint_id INTEGER NOT NULL,
        failed_agent VARCHAR(50),
        resume_dependencies JSONB,
        status VARCHAR(20) NOT NULL CHECK (status IN ('PAUSING', 'PAUSED', 'RESUMING', 'RESUMED', 'STALE', 'EXPIRED')),
        created_by VARCHAR(100) NOT NULL,
        batch_id UUID,
        alert_day3_sent BOOLEAN DEFAULT FALSE,
        alert_day7_sent BOOLEAN DEFAULT FALSE,
        extended_until TIMESTAMP,
        extension_reason TEXT,
        FOREIGN KEY (checkpoint_id) REFERENCES workflow.agent_checkpoints(id),
        FOREIGN KEY (batch_id) REFERENCES workflow.batch_pause_operations(id)
    )
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_paused_stock_status ON workflow.paused_analyses(stock_id, status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_paused_timestamp ON workflow.paused_analyses(pause_timestamp)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_paused_batch ON workflow.paused_analyses(batch_id) WHERE batch_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_stale_candidates ON workflow.paused_analyses(pause_timestamp) WHERE status = 'PAUSED'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_alert_day3 ON workflow.paused_analyses(pause_timestamp, alert_day3_sent) WHERE status = 'PAUSED' AND alert_day3_sent = FALSE"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_alert_day7 ON workflow.paused_analyses(pause_timestamp, alert_day7_sent) WHERE status = 'PAUSED' AND alert_day7_sent = FALSE"
    )

    op.execute("""
    CREATE TABLE IF NOT EXISTS workflow.resume_plans (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        paused_analysis_id UUID NOT NULL,
        restart_agents TEXT[] NOT NULL,
        skip_agents TEXT[] NOT NULL,
        wait_agents TEXT[] NOT NULL,
        plan_created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        executed_at TIMESTAMP,
        execution_status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (execution_status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED')),
        FOREIGN KEY (paused_analysis_id) REFERENCES workflow.paused_analyses(id) ON DELETE CASCADE
    )
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_resume_paused_analysis ON workflow.resume_plans(paused_analysis_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_resume_execution_status ON workflow.resume_plans(execution_status)"
    )

    op.execute("""
    CREATE TABLE IF NOT EXISTS workflow.failure_correlations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        error_signature VARCHAR(16) NOT NULL,
        detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
        correlation_window_min INTEGER DEFAULT 5,
        failure_ids UUID[] NOT NULL,
        stock_tickers TEXT[] NOT NULL,
        failure_count INTEGER NOT NULL,
        root_cause TEXT,
        inference_confidence DECIMAL(3,2),
        data_sources TEXT[],
        agent_types TEXT[],
        error_types TEXT[],
        batch_id UUID,
        batch_triggered_at TIMESTAMP,
        resolved_at TIMESTAMP,
        resolution_action VARCHAR(50),
        FOREIGN KEY (batch_id) REFERENCES workflow.batch_pause_operations(id)
    )
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_signature ON workflow.failure_correlations(error_signature)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_detected_at ON workflow.failure_correlations(detected_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_unresolved ON workflow.failure_correlations(resolved_at) WHERE resolved_at IS NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_batch ON workflow.failure_correlations(batch_id) WHERE batch_id IS NOT NULL"
    )

    # 02_logging_schema.sql
    op.execute("""
    CREATE TABLE IF NOT EXISTS access_tracking.file_access_log (
        id BIGSERIAL,
        file_id VARCHAR(255) NOT NULL,
        access_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        access_type VARCHAR(50),
        agent_id VARCHAR(100),
        tier_at_access VARCHAR(10),
        PRIMARY KEY (id, access_timestamp)
    ) PARTITION BY RANGE (access_timestamp)
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_file_access_timestamp ON access_tracking.file_access_log(access_timestamp)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_file_id_timestamp ON access_tracking.file_access_log(file_id, access_timestamp DESC)"
    )

    op.execute("DROP MATERIALIZED VIEW IF EXISTS access_tracking.file_access_weekly")
    op.execute("""
    CREATE MATERIALIZED VIEW access_tracking.file_access_weekly AS
    SELECT
        file_id,
        COUNT(*) as access_count_7d,
        MAX(access_timestamp) as last_access,
        MAX(tier_at_access) as current_tier,
        CASE 
            WHEN MAX(tier_at_access) = 'warm' AND COUNT(*) >= 10 THEN true
            WHEN MAX(tier_at_access) = 'cold' AND COUNT(*) >= 3 THEN true
            ELSE false
        END as promotion_candidate
    FROM access_tracking.file_access_log
    WHERE access_timestamp > NOW() - INTERVAL '7 days'
    GROUP BY file_id
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_weekly_promotion ON access_tracking.file_access_weekly(promotion_candidate) WHERE promotion_candidate = true"
    )

    op.execute("""
    CREATE TABLE IF NOT EXISTS public.memory_access_audit (
        id BIGSERIAL,
        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        actor_id VARCHAR(100) NOT NULL,
        actor_role VARCHAR(50) NOT NULL,
        resource_type VARCHAR(50) NOT NULL,
        resource_id VARCHAR(255) NOT NULL,
        action VARCHAR(50) NOT NULL,
        authorized BOOLEAN NOT NULL,
        old_value JSONB,
        new_value JSONB,
        action_reason TEXT,
        request_context JSONB,
        PRIMARY KEY (id, timestamp)
    ) PARTITION BY RANGE (timestamp)
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON public.memory_access_audit(timestamp DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_actor ON public.memory_access_audit(actor_id, timestamp DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_resource ON public.memory_access_audit(resource_type, resource_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_unauthorized ON public.memory_access_audit(authorized) WHERE authorized = false"
    )

    # 03_outcomes_schema.sql
    op.execute("""
    CREATE TABLE IF NOT EXISTS outcomes.predictions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        stock_ticker VARCHAR(10) NOT NULL,
        agent_id VARCHAR(50) NOT NULL,
        analysis_id UUID,
        prediction_date DATE NOT NULL,
        target_date DATE NOT NULL,
        time_horizon VARCHAR(20),
        metric_name VARCHAR(50) NOT NULL,
        predicted_value DECIMAL(15, 4),
        confidence_score DECIMAL(3, 2),
        rationale TEXT,
        pattern_ids TEXT[],
        created_at TIMESTAMP DEFAULT NOW()
    )
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pred_ticker ON outcomes.predictions(stock_ticker)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pred_target ON outcomes.predictions(target_date)"
    )

    op.execute("""
    CREATE TABLE IF NOT EXISTS outcomes.actuals (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        stock_ticker VARCHAR(10) NOT NULL,
        metric_name VARCHAR(50) NOT NULL,
        period_end_date DATE NOT NULL,
        actual_value DECIMAL(15, 4) NOT NULL,
        source VARCHAR(50),
        recorded_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(stock_ticker, metric_name, period_end_date)
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS outcomes.prediction_outcomes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        prediction_id UUID NOT NULL,
        actual_id UUID,
        accuracy_score DECIMAL(5, 4),
        error_magnitude DECIMAL(15, 4),
        error_percentage DECIMAL(5, 2),
        outcome_verdict VARCHAR(20),
        evaluated_at TIMESTAMP DEFAULT NOW(),
        FOREIGN KEY (prediction_id) REFERENCES outcomes.predictions(id),
        FOREIGN KEY (actual_id) REFERENCES outcomes.actuals(id)
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS outcomes.lessons_learned (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        outcome_id UUID NOT NULL,
        agent_id VARCHAR(50) NOT NULL,
        root_cause_category VARCHAR(50),
        detailed_analysis TEXT,
        adjustment_action VARCHAR(50),
        created_at TIMESTAMP DEFAULT NOW(),
        FOREIGN KEY (outcome_id) REFERENCES outcomes.prediction_outcomes(id)
    )
    """)


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS outcomes CASCADE")
    op.execute("DROP SCHEMA IF EXISTS access_tracking CASCADE")
    op.execute("DROP SCHEMA IF EXISTS workflow CASCADE")
    op.execute("DROP SCHEMA IF EXISTS document_registry CASCADE")
    op.execute("DROP SCHEMA IF EXISTS metadata CASCADE")
    op.execute("DROP SCHEMA IF EXISTS market_data CASCADE")
    op.execute("DROP SCHEMA IF EXISTS financial_data CASCADE")
