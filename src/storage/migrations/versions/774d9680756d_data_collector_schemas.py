"""data_collector_schemas

Revision ID: 774d9680756d
Revises: a125ac7b2db7
Create Date: 2025-11-19 13:43:24.806646

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '774d9680756d'
down_revision: Union[str, Sequence[str], None] = 'a125ac7b2db7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ========== metadata.companies ==========
    op.execute("""
    CREATE TABLE IF NOT EXISTS metadata.companies (
        ticker VARCHAR(10) PRIMARY KEY,
        cik VARCHAR(10) NOT NULL UNIQUE,
        company_name VARCHAR(255) NOT NULL,
        sector VARCHAR(100),
        industry VARCHAR(100),
        exchange VARCHAR(20),
        country VARCHAR(2) DEFAULT 'US',
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_companies_cik ON metadata.companies(cik)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_companies_sector ON metadata.companies(sector)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_companies_industry ON metadata.companies(industry)")

    # ========== document_registry.filings (partitioned by year) ==========
    op.execute("""
    CREATE TABLE IF NOT EXISTS document_registry.filings (
        filing_id UUID DEFAULT gen_random_uuid(),
        ticker VARCHAR(10) NOT NULL,
        cik VARCHAR(10) NOT NULL,
        company_name VARCHAR(255) NOT NULL,
        form_type VARCHAR(10) NOT NULL,
        filing_date DATE NOT NULL,
        period_end_date DATE NOT NULL,
        fiscal_year INTEGER NOT NULL,
        fiscal_quarter INTEGER CHECK (fiscal_quarter BETWEEN 1 AND 4),
        accession_number VARCHAR(20) NOT NULL,
        s3_path TEXT NOT NULL,
        parse_status VARCHAR(20) DEFAULT 'pending' CHECK (parse_status IN ('pending', 'success', 'failed', 'skipped')),
        version INTEGER NOT NULL DEFAULT 1,
        is_latest BOOLEAN NOT NULL DEFAULT true,
        superseded_by UUID,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
        PRIMARY KEY (filing_id, fiscal_year),
        FOREIGN KEY (ticker) REFERENCES metadata.companies(ticker) ON DELETE CASCADE
    ) PARTITION BY RANGE (fiscal_year)
    """)

    # Create partitions for 2019-2030 (11 years)
    for year in range(2019, 2031):
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS document_registry.filings_{year}
        PARTITION OF document_registry.filings
        FOR VALUES FROM ({year}) TO ({year + 1})
        """)

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_filings_accession ON document_registry.filings(accession_number, version, fiscal_year)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_filings_ticker ON document_registry.filings(ticker)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_filings_date ON document_registry.filings(filing_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_filings_form ON document_registry.filings(form_type)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_filings_composite ON document_registry.filings(ticker, period_end_date, form_type, version, fiscal_year)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_filings_latest ON document_registry.filings(ticker, is_latest) WHERE is_latest = true")

    # ========== financial_data.income_statements (partitioned by fiscal_year) ==========
    op.execute("""
    CREATE TABLE IF NOT EXISTS financial_data.income_statements (
        id UUID DEFAULT gen_random_uuid(),
        ticker VARCHAR(10) NOT NULL,
        filing_id UUID NOT NULL,
        period_end_date DATE NOT NULL,
        fiscal_year INTEGER NOT NULL,
        fiscal_quarter INTEGER CHECK (fiscal_quarter BETWEEN 1 AND 4),
        revenue BIGINT,
        cost_of_revenue BIGINT,
        gross_profit BIGINT,
        operating_income BIGINT,
        net_income BIGINT,
        eps_basic BIGINT,
        eps_diluted BIGINT,
        shares_outstanding BIGINT,
        version INTEGER NOT NULL DEFAULT 1,
        is_latest BOOLEAN NOT NULL DEFAULT true,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        PRIMARY KEY (id, fiscal_year)
    ) PARTITION BY RANGE (fiscal_year)
    """)

    # Create partitions for 2019-2030
    for year in range(2019, 2031):
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS financial_data.income_statements_{year}
        PARTITION OF financial_data.income_statements
        FOR VALUES FROM ({year}) TO ({year + 1})
        """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_income_ticker ON financial_data.income_statements(ticker)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_income_period ON financial_data.income_statements(period_end_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_income_filing ON financial_data.income_statements(filing_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_income_composite ON financial_data.income_statements(ticker, period_end_date, version, fiscal_year)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_income_latest ON financial_data.income_statements(ticker, is_latest) WHERE is_latest = true")

    # ========== financial_data.balance_sheets (partitioned by fiscal_year) ==========
    op.execute("""
    CREATE TABLE IF NOT EXISTS financial_data.balance_sheets (
        id UUID DEFAULT gen_random_uuid(),
        ticker VARCHAR(10) NOT NULL,
        filing_id UUID NOT NULL,
        period_end_date DATE NOT NULL,
        fiscal_year INTEGER NOT NULL,
        fiscal_quarter INTEGER CHECK (fiscal_quarter BETWEEN 1 AND 4),
        total_assets BIGINT,
        current_assets BIGINT,
        cash BIGINT,
        accounts_receivable BIGINT,
        inventory BIGINT,
        total_liabilities BIGINT,
        current_liabilities BIGINT,
        total_debt BIGINT,
        accounts_payable BIGINT,
        total_equity BIGINT,
        retained_earnings BIGINT,
        version INTEGER NOT NULL DEFAULT 1,
        is_latest BOOLEAN NOT NULL DEFAULT true,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        PRIMARY KEY (id, fiscal_year)
    ) PARTITION BY RANGE (fiscal_year)
    """)

    # Create partitions for 2019-2030
    for year in range(2019, 2031):
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS financial_data.balance_sheets_{year}
        PARTITION OF financial_data.balance_sheets
        FOR VALUES FROM ({year}) TO ({year + 1})
        """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_balance_ticker ON financial_data.balance_sheets(ticker)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_balance_period ON financial_data.balance_sheets(period_end_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_balance_filing ON financial_data.balance_sheets(filing_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_balance_composite ON financial_data.balance_sheets(ticker, period_end_date, version, fiscal_year)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_balance_latest ON financial_data.balance_sheets(ticker, is_latest) WHERE is_latest = true")

    # ========== financial_data.cash_flows (partitioned by fiscal_year) ==========
    op.execute("""
    CREATE TABLE IF NOT EXISTS financial_data.cash_flows (
        id UUID DEFAULT gen_random_uuid(),
        ticker VARCHAR(10) NOT NULL,
        filing_id UUID NOT NULL,
        period_end_date DATE NOT NULL,
        fiscal_year INTEGER NOT NULL,
        fiscal_quarter INTEGER CHECK (fiscal_quarter BETWEEN 1 AND 4),
        operating_cf BIGINT,
        investing_cf BIGINT,
        financing_cf BIGINT,
        capex BIGINT,
        free_cash_flow BIGINT,
        dividends_paid BIGINT,
        version INTEGER NOT NULL DEFAULT 1,
        is_latest BOOLEAN NOT NULL DEFAULT true,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        PRIMARY KEY (id, fiscal_year)
    ) PARTITION BY RANGE (fiscal_year)
    """)

    # Create partitions for 2019-2030
    for year in range(2019, 2031):
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS financial_data.cash_flows_{year}
        PARTITION OF financial_data.cash_flows
        FOR VALUES FROM ({year}) TO ({year + 1})
        """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_cashflow_ticker ON financial_data.cash_flows(ticker)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cashflow_period ON financial_data.cash_flows(period_end_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cashflow_filing ON financial_data.cash_flows(filing_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_cashflow_composite ON financial_data.cash_flows(ticker, period_end_date, version, fiscal_year)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cashflow_latest ON financial_data.cash_flows(ticker, is_latest) WHERE is_latest = true")

    # ========== Triggers for auto-updating is_latest ==========
    # Trigger function to mark old versions as not latest
    op.execute("""
    CREATE OR REPLACE FUNCTION update_latest_version()
    RETURNS TRIGGER AS $$
    BEGIN
        -- Mark all previous versions as not latest
        UPDATE document_registry.filings
        SET is_latest = false, updated_at = NOW()
        WHERE ticker = NEW.ticker
          AND period_end_date = NEW.period_end_date
          AND form_type = NEW.form_type
          AND version < NEW.version;

        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trigger_update_filing_latest
    AFTER INSERT ON document_registry.filings
    FOR EACH ROW
    EXECUTE FUNCTION update_latest_version();
    """)

    # Similar triggers for financial statements
    op.execute("""
    CREATE OR REPLACE FUNCTION update_latest_income()
    RETURNS TRIGGER AS $$
    BEGIN
        UPDATE financial_data.income_statements
        SET is_latest = false
        WHERE ticker = NEW.ticker
          AND period_end_date = NEW.period_end_date
          AND version < NEW.version;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trigger_update_income_latest
    AFTER INSERT ON financial_data.income_statements
    FOR EACH ROW
    EXECUTE FUNCTION update_latest_income();
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION update_latest_balance()
    RETURNS TRIGGER AS $$
    BEGIN
        UPDATE financial_data.balance_sheets
        SET is_latest = false
        WHERE ticker = NEW.ticker
          AND period_end_date = NEW.period_end_date
          AND version < NEW.version;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trigger_update_balance_latest
    AFTER INSERT ON financial_data.balance_sheets
    FOR EACH ROW
    EXECUTE FUNCTION update_latest_balance();
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION update_latest_cashflow()
    RETURNS TRIGGER AS $$
    BEGIN
        UPDATE financial_data.cash_flows
        SET is_latest = false
        WHERE ticker = NEW.ticker
          AND period_end_date = NEW.period_end_date
          AND version < NEW.version;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trigger_update_cashflow_latest
    AFTER INSERT ON financial_data.cash_flows
    FOR EACH ROW
    EXECUTE FUNCTION update_latest_cashflow();
    """)


def downgrade() -> None:
    """Downgrade schema."""

    # Drop triggers first
    op.execute("DROP TRIGGER IF EXISTS trigger_update_cashflow_latest ON financial_data.cash_flows")
    op.execute("DROP TRIGGER IF EXISTS trigger_update_balance_latest ON financial_data.balance_sheets")
    op.execute("DROP TRIGGER IF EXISTS trigger_update_income_latest ON financial_data.income_statements")
    op.execute("DROP TRIGGER IF EXISTS trigger_update_filing_latest ON document_registry.filings")

    # Drop trigger functions
    op.execute("DROP FUNCTION IF EXISTS update_latest_cashflow()")
    op.execute("DROP FUNCTION IF EXISTS update_latest_balance()")
    op.execute("DROP FUNCTION IF EXISTS update_latest_income()")
    op.execute("DROP FUNCTION IF EXISTS update_latest_version()")

    # Drop financial tables (partitions will be dropped automatically)
    op.execute("DROP TABLE IF EXISTS financial_data.cash_flows CASCADE")
    op.execute("DROP TABLE IF EXISTS financial_data.balance_sheets CASCADE")
    op.execute("DROP TABLE IF EXISTS financial_data.income_statements CASCADE")

    # Drop document_registry tables
    op.execute("DROP TABLE IF EXISTS document_registry.filings CASCADE")

    # Drop metadata tables
    op.execute("DROP TABLE IF EXISTS metadata.companies CASCADE")
