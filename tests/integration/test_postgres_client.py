"""Tests for PostgreSQL client."""

from collections.abc import AsyncGenerator
from datetime import date
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from storage.postgres_client import (
    BalanceSheetData,
    CashFlowData,
    CompanyData,
    DocumentMetadata,
    IncomeStatementData,
    PostgresClient,
)


@pytest.fixture
async def pg_client(run_migrations: None, postgres_url: str) -> AsyncGenerator[PostgresClient]:  # noqa: ARG001 - fixture dependency
    """Create PostgreSQL client for testing using testcontainer's dynamic URL."""
    # Convert to SQLAlchemy async format
    test_db_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://").replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )

    client = PostgresClient(database_url=test_db_url, pool_size=2, max_overflow=3)
    yield client
    await client.close()


@pytest.fixture
async def clean_tables(pg_client: PostgresClient) -> None:
    """Clean test tables before each test."""
    async with pg_client.session() as session:
        # Clean in reverse FK dependency order
        await session.execute(text("TRUNCATE financial_data.cash_flows CASCADE"))
        await session.execute(text("TRUNCATE financial_data.balance_sheets CASCADE"))
        await session.execute(text("TRUNCATE financial_data.income_statements CASCADE"))
        await session.execute(text("TRUNCATE document_registry.filings CASCADE"))
        await session.execute(text("TRUNCATE metadata.companies CASCADE"))


@pytest.mark.usefixtures("clean_tables")
@pytest.mark.requires_postgresql
@pytest.mark.integration
@pytest.mark.xdist_group("postgres_serial")
class TestCompanyMetadata:
    """Tests for company metadata operations."""

    async def test_upsert_company_insert(self, pg_client: PostgresClient) -> None:
        """Test inserting new company."""
        await pg_client.upsert_company(
            CompanyData(
                ticker="AAPL",
                cik="0000320193",
                company_name="Apple Inc.",
                sector="Technology",
                industry="Consumer Electronics",
                exchange="NASDAQ",
            )
        )

        company = await pg_client.get_company_metadata("AAPL")
        assert company is not None
        assert company["ticker"] == "AAPL"
        assert company["cik"] == "0000320193"
        assert company["company_name"] == "Apple Inc."
        assert company["sector"] == "Technology"
        assert company["industry"] == "Consumer Electronics"
        assert company["exchange"] == "NASDAQ"
        assert company["country"] == "US"

    async def test_upsert_company_update(self, pg_client: PostgresClient) -> None:
        """Test updating existing company."""
        # Insert
        await pg_client.upsert_company(
            CompanyData(
                ticker="AAPL",
                cik="0000320193",
                company_name="Apple Inc.",
                sector="Technology",
            )
        )

        # Update with new sector
        await pg_client.upsert_company(
            CompanyData(
                ticker="AAPL",
                cik="0000320193",
                company_name="Apple Inc.",
                sector="Consumer Goods",
                industry="Electronics",
            )
        )

        company = await pg_client.get_company_metadata("AAPL")
        assert company is not None
        assert company["sector"] == "Consumer Goods"
        assert company["industry"] == "Electronics"

    async def test_get_nonexistent_company(self, pg_client: PostgresClient) -> None:
        """Test fetching company that doesn't exist."""
        company = await pg_client.get_company_metadata("NONEXIST")
        assert company is None


@pytest.mark.usefixtures("clean_tables")
@pytest.mark.requires_postgresql
@pytest.mark.integration
@pytest.mark.xdist_group("postgres_serial")
class TestDocumentRegistry:
    """Tests for document registry operations."""

    async def test_insert_filing(self, pg_client: PostgresClient) -> None:
        """Test inserting filing metadata."""
        # Insert company first (FK requirement)
        await pg_client.upsert_company(
            CompanyData(
                ticker="AAPL",
                cik="0000320193",
                company_name="Apple Inc.",
            )
        )

        filing_id = await pg_client.insert_document_metadata(
            DocumentMetadata(
                ticker="AAPL",
                cik="0000320193",
                company_name="Apple Inc.",
                form_type="10-K",
                filing_date=date(2023, 11, 3),
                period_end_date=date(2023, 9, 30),
                fiscal_year=2023,
                fiscal_quarter=None,
                accession_number="0000320193-23-000106",
                s3_path="raw/sec_filings/AAPL/2023/0000320193-23-000106.html",
                parse_status="success",
            )
        )

        assert isinstance(filing_id, UUID)

    async def test_check_filing_exists(self, pg_client: PostgresClient) -> None:
        """Test checking if filing exists."""
        await pg_client.upsert_company(CompanyData(ticker="AAPL", cik="0000320193", company_name="Apple Inc."))

        # Should not exist initially
        exists = await pg_client.check_filing_exists("0000320193", "0000320193-23-000106")
        assert exists is False

        # Insert filing
        await pg_client.insert_document_metadata(
            DocumentMetadata(
                ticker="AAPL",
                cik="0000320193",
                company_name="Apple Inc.",
                form_type="10-K",
                filing_date=date(2023, 11, 3),
                period_end_date=date(2023, 9, 30),
                fiscal_year=2023,
                fiscal_quarter=None,
                accession_number="0000320193-23-000106",
                s3_path="raw/sec_filings/AAPL/2023/0000320193-23-000106.html",
            )
        )

        # Should exist now
        exists = await pg_client.check_filing_exists("0000320193", "0000320193-23-000106")
        assert exists is True

    async def test_duplicate_filing_raises_error(self, pg_client: PostgresClient) -> None:
        """Test that inserting duplicate filing raises IntegrityError."""
        await pg_client.upsert_company(CompanyData(ticker="AAPL", cik="0000320193", company_name="Apple Inc."))

        # Insert first filing
        await pg_client.insert_document_metadata(
            DocumentMetadata(
                ticker="AAPL",
                cik="0000320193",
                company_name="Apple Inc.",
                form_type="10-K",
                filing_date=date(2023, 11, 3),
                period_end_date=date(2023, 9, 30),
                fiscal_year=2023,
                fiscal_quarter=None,
                accession_number="0000320193-23-000106",
                s3_path="raw/sec_filings/AAPL/2023/0000320193-23-000106.html",
            )
        )

        # Attempt to insert duplicate (same ticker, period, form_type, version)
        with pytest.raises(IntegrityError):
            await pg_client.insert_document_metadata(
                DocumentMetadata(
                    ticker="AAPL",
                    cik="0000320193",
                    company_name="Apple Inc.",
                    form_type="10-K",
                    filing_date=date(2023, 11, 3),
                    period_end_date=date(2023, 9, 30),
                    fiscal_year=2023,
                    fiscal_quarter=None,
                    accession_number="0000320193-23-000106-DUPLICATE",  # Different accession
                    s3_path="raw/sec_filings/AAPL/2023/duplicate.html",
                )
            )

    async def test_supersede_filing(self, pg_client: PostgresClient) -> None:
        """Test marking filing as superseded by new version."""
        await pg_client.upsert_company(CompanyData(ticker="AAPL", cik="0000320193", company_name="Apple Inc."))

        # Insert original filing (version 1)
        filing_id_v1 = await pg_client.insert_document_metadata(
            DocumentMetadata(
                ticker="AAPL",
                cik="0000320193",
                company_name="Apple Inc.",
                form_type="10-K",
                filing_date=date(2023, 11, 3),
                period_end_date=date(2023, 9, 30),
                fiscal_year=2023,
                fiscal_quarter=None,
                accession_number="0000320193-23-000106",
                s3_path="raw/sec_filings/AAPL/2023/0000320193-23-000106.html",
                version=1,
            )
        )

        # Insert amended filing (version 2)
        filing_id_v2 = await pg_client.insert_document_metadata(
            DocumentMetadata(
                ticker="AAPL",
                cik="0000320193",
                company_name="Apple Inc.",
                form_type="10-K",
                filing_date=date(2023, 12, 15),
                period_end_date=date(2023, 9, 30),
                fiscal_year=2023,
                fiscal_quarter=None,
                accession_number="0000320193-23-000120",  # Amended filing
                s3_path="raw/sec_filings/AAPL/2023/0000320193-23-000120.html",
                version=2,
            )
        )

        # Supersede v1 with v2
        await pg_client.supersede_filing(
            ticker="AAPL",
            period_end_date=date(2023, 9, 30),
            form_type="10-K",
            new_filing_id=filing_id_v2,
        )

        # Verify v1 is marked as superseded (trigger should have done this automatically)
        async with pg_client.session() as session:
            result = await session.execute(
                text("SELECT is_latest FROM document_registry.filings WHERE filing_id = :id"),
                {"id": filing_id_v1},
            )
            is_latest = result.scalar_one()
            assert is_latest is False


@pytest.mark.usefixtures("clean_tables")
@pytest.mark.requires_postgresql
@pytest.mark.integration
@pytest.mark.xdist_group("postgres_serial")
class TestFinancialData:
    """Tests for financial data operations."""

    @pytest.fixture
    async def setup_company_and_filing(self, pg_client: PostgresClient) -> UUID:
        """Setup company and filing for financial data tests."""
        await pg_client.upsert_company(CompanyData(ticker="AAPL", cik="0000320193", company_name="Apple Inc."))

        filing_id = await pg_client.insert_document_metadata(
            DocumentMetadata(
                ticker="AAPL",
                cik="0000320193",
                company_name="Apple Inc.",
                form_type="10-K",
                filing_date=date(2023, 11, 3),
                period_end_date=date(2023, 9, 30),
                fiscal_year=2023,
                fiscal_quarter=None,
                accession_number="0000320193-23-000106",
                s3_path="raw/sec_filings/AAPL/2023/0000320193-23-000106.html",
            )
        )
        return filing_id

    async def test_insert_income_statement(self, pg_client: PostgresClient, setup_company_and_filing: UUID) -> None:
        """Test inserting income statement data."""
        filing_id = setup_company_and_filing

        income_id = await pg_client.insert_income_statement(
            IncomeStatementData(
                ticker="AAPL",
                filing_id=filing_id,
                period_end_date=date(2023, 9, 30),
                fiscal_year=2023,
                fiscal_quarter=None,
                revenue=394328000000,  # $394.3B in whole dollars
                cost_of_revenue=214137000000,
                gross_profit=180191000000,
                operating_income=114301000000,
                net_income=96995000000,
                eps_basic=623,  # $6.23 in cents
                eps_diluted=616,  # $6.16 in cents
                shares_outstanding=15552752000,
            )
        )

        assert isinstance(income_id, UUID)

    async def test_insert_balance_sheet(self, pg_client: PostgresClient, setup_company_and_filing: UUID) -> None:
        """Test inserting balance sheet data."""
        filing_id = setup_company_and_filing

        balance_id = await pg_client.insert_balance_sheet(
            BalanceSheetData(
                ticker="AAPL",
                filing_id=filing_id,
                period_end_date=date(2023, 9, 30),
                fiscal_year=2023,
                fiscal_quarter=None,
                total_assets=352755000000,
                current_assets=143566000000,
                cash=29965000000,
                accounts_receivable=60932000000,
                inventory=6331000000,
                total_liabilities=290437000000,
                current_liabilities=145308000000,
                total_debt=111088000000,
                accounts_payable=62611000000,
                total_equity=62318000000,
                retained_earnings=1408000000,
            )
        )

        assert isinstance(balance_id, UUID)

    async def test_insert_cash_flow(self, pg_client: PostgresClient, setup_company_and_filing: UUID) -> None:
        """Test inserting cash flow data."""
        filing_id = setup_company_and_filing

        cashflow_id = await pg_client.insert_cash_flow(
            CashFlowData(
                ticker="AAPL",
                filing_id=filing_id,
                period_end_date=date(2023, 9, 30),
                fiscal_year=2023,
                fiscal_quarter=None,
                operating_cf=110543000000,
                investing_cf=-7077000000,
                financing_cf=-108488000000,
                capex=10959000000,
                free_cash_flow=99584000000,
                dividends_paid=14996000000,
            )
        )

        assert isinstance(cashflow_id, UUID)

    async def test_bulk_insert_financials(self, pg_client: PostgresClient, setup_company_and_filing: UUID) -> None:
        """Test bulk inserting multiple financial statements."""
        filing_id = setup_company_and_filing

        income_statements = [
            {
                "ticker": "AAPL",
                "filing_id": filing_id,
                "period_end_date": date(2023, 9, 30),
                "fiscal_year": 2023,
                "fiscal_quarter": 4,
                "revenue": 89498000000,
                "cost_of_revenue": None,
                "gross_profit": None,
                "operating_income": None,
                "net_income": 22956000000,
                "eps_basic": None,
                "eps_diluted": None,
                "shares_outstanding": None,
                "version": 1,
            }
        ]

        balance_sheets = [
            {
                "ticker": "AAPL",
                "filing_id": filing_id,
                "period_end_date": date(2023, 9, 30),
                "fiscal_year": 2023,
                "fiscal_quarter": 4,
                "total_assets": 352755000000,
                "current_assets": None,
                "cash": None,
                "accounts_receivable": None,
                "inventory": None,
                "total_liabilities": None,
                "current_liabilities": None,
                "total_debt": None,
                "accounts_payable": None,
                "total_equity": 62318000000,
                "retained_earnings": None,
                "version": 1,
            }
        ]

        cash_flows = [
            {
                "ticker": "AAPL",
                "filing_id": filing_id,
                "period_end_date": date(2023, 9, 30),
                "fiscal_year": 2023,
                "fiscal_quarter": 4,
                "operating_cf": 26346000000,
                "investing_cf": None,
                "financing_cf": None,
                "capex": None,
                "free_cash_flow": 23804000000,
                "dividends_paid": None,
                "version": 1,
            }
        ]

        # Should not raise
        await pg_client.bulk_insert_financials(
            income_statements=income_statements,
            balance_sheets=balance_sheets,
            cash_flows=cash_flows,
        )

    async def test_bulk_insert_empty_lists(self, pg_client: PostgresClient) -> None:
        """Test bulk insert with empty lists (no-op case)."""
        # Should not raise even with all empty lists
        await pg_client.bulk_insert_financials(
            income_statements=[],
            balance_sheets=[],
            cash_flows=[],
        )

    async def test_bulk_insert_partial_data(self, pg_client: PostgresClient, setup_company_and_filing: UUID) -> None:
        """Test bulk insert with only some statement types."""
        filing_id = setup_company_and_filing

        # Only income statements
        income_only = [
            {
                "ticker": "AAPL",
                "filing_id": filing_id,
                "period_end_date": date(2023, 6, 30),
                "fiscal_year": 2023,
                "fiscal_quarter": 3,
                "revenue": 81797000000,
                "cost_of_revenue": None,
                "gross_profit": None,
                "operating_income": None,
                "net_income": 19881000000,
                "eps_basic": None,
                "eps_diluted": None,
                "shares_outstanding": None,
                "version": 1,
            }
        ]
        await pg_client.bulk_insert_financials(
            income_statements=income_only,
            balance_sheets=[],
            cash_flows=[],
        )

        # Only balance sheets
        balance_only = [
            {
                "ticker": "AAPL",
                "filing_id": filing_id,
                "period_end_date": date(2023, 6, 30),
                "fiscal_year": 2023,
                "fiscal_quarter": 3,
                "total_assets": 335000000000,
                "current_assets": None,
                "cash": None,
                "accounts_receivable": None,
                "inventory": None,
                "total_liabilities": None,
                "current_liabilities": None,
                "total_debt": None,
                "accounts_payable": None,
                "total_equity": 60000000000,
                "retained_earnings": None,
                "version": 1,
            }
        ]
        await pg_client.bulk_insert_financials(
            income_statements=[],
            balance_sheets=balance_only,
            cash_flows=[],
        )

        # Only cash flows
        cash_only = [
            {
                "ticker": "AAPL",
                "filing_id": filing_id,
                "period_end_date": date(2023, 6, 30),
                "fiscal_year": 2023,
                "fiscal_quarter": 3,
                "operating_cf": 25000000000,
                "investing_cf": None,
                "financing_cf": None,
                "capex": None,
                "free_cash_flow": 22000000000,
                "dividends_paid": None,
                "version": 1,
            }
        ]
        await pg_client.bulk_insert_financials(
            income_statements=[],
            balance_sheets=[],
            cash_flows=cash_only,
        )

    async def test_version_history(self, pg_client: PostgresClient, setup_company_and_filing: UUID) -> None:
        """Test that version history is maintained correctly."""
        filing_id = setup_company_and_filing

        # Insert version 1
        income_id_v1 = await pg_client.insert_income_statement(
            IncomeStatementData(
                ticker="AAPL",
                filing_id=filing_id,
                period_end_date=date(2023, 9, 30),
                fiscal_year=2023,
                fiscal_quarter=None,
                revenue=394328000000,
                net_income=96995000000,
                version=1,
            )
        )

        # Insert version 2 (restated)
        income_id_v2 = await pg_client.insert_income_statement(
            IncomeStatementData(
                ticker="AAPL",
                filing_id=filing_id,
                period_end_date=date(2023, 9, 30),
                fiscal_year=2023,
                fiscal_quarter=None,
                revenue=394000000000,  # Slightly different
                net_income=96900000000,  # Slightly different
                version=2,
            )
        )

        # Check that v1 is no longer latest (trigger should have updated it)
        async with pg_client.session() as session:
            result = await session.execute(
                text("SELECT is_latest FROM financial_data.income_statements WHERE id = :id"),
                {"id": income_id_v1},
            )
            is_latest_v1 = result.scalar_one()
            assert is_latest_v1 is False

            result = await session.execute(
                text("SELECT is_latest FROM financial_data.income_statements WHERE id = :id"),
                {"id": income_id_v2},
            )
            is_latest_v2 = result.scalar_one()
            assert is_latest_v2 is True


@pytest.mark.usefixtures("clean_tables")
@pytest.mark.requires_postgresql
@pytest.mark.integration
@pytest.mark.xdist_group("postgres_serial")
class TestPartitioning:
    """Tests for partition functionality."""

    async def test_data_across_partitions(self, pg_client: PostgresClient) -> None:
        """Test inserting data across multiple year partitions."""
        await pg_client.upsert_company(CompanyData(ticker="AAPL", cik="0000320193", company_name="Apple Inc."))

        # Insert filings for different years (should go to different partitions)
        years = [2020, 2021, 2022, 2023]
        for year in years:
            await pg_client.insert_document_metadata(
                DocumentMetadata(
                    ticker="AAPL",
                    cik="0000320193",
                    company_name="Apple Inc.",
                    form_type="10-K",
                    filing_date=date(year, 11, 3),
                    period_end_date=date(year, 9, 30),
                    fiscal_year=year,
                    fiscal_quarter=None,
                    accession_number=f"0000320193-{year}-000106",
                    s3_path=f"raw/sec_filings/AAPL/{year}/filing.html",
                )
            )

        # Verify all inserted
        async with pg_client.session() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM document_registry.filings WHERE ticker = 'AAPL'"))
            count = result.scalar_one()
            expected_filing_count = 4
            assert count == expected_filing_count


@pytest.mark.usefixtures("clean_tables")
@pytest.mark.requires_postgresql
@pytest.mark.integration
@pytest.mark.xdist_group("postgres_serial")
class TestErrorHandling:
    """Tests for error handling and edge cases."""

    async def test_connection_pool(self) -> None:
        """Test connection pool limits."""
        client = PostgresClient(pool_size=2, max_overflow=1)  # Small pool for testing

        try:
            # Open multiple concurrent sessions (more than pool size)
            sessions = []
            for _ in range(3):  # 3 sessions, pool_size=2, max_overflow=1
                session = client.session_factory()
                sessions.append(session)

            # Should not raise (overflow should handle it)
            for session in sessions:
                await session.close()

        finally:
            await client.close()

    async def test_invalid_foreign_key(self, pg_client: PostgresClient) -> None:
        """Test that invalid FK raises IntegrityError."""
        # Try to insert filing without company
        with pytest.raises(IntegrityError):
            await pg_client.insert_document_metadata(
                DocumentMetadata(
                    ticker="NONEXIST",  # Company doesn't exist
                    cik="0000000000",
                    company_name="Nonexistent Inc.",
                    form_type="10-K",
                    filing_date=date(2023, 11, 3),
                    period_end_date=date(2023, 9, 30),
                    fiscal_year=2023,
                    fiscal_quarter=None,
                    accession_number="0000000000-23-000001",
                    s3_path="raw/sec_filings/NONEXIST/2023/filing.html",
                )
            )
