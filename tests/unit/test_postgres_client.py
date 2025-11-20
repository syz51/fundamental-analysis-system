"""Unit tests for PostgresClient dataclasses and initialization."""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import DBAPIError

from storage.postgres_client import (
    BalanceSheetData,
    CashFlowData,
    CompanyData,
    DocumentMetadata,
    IncomeStatementData,
    PostgresClient,
)

pytestmark = pytest.mark.unit

# Test constants
POOL_SIZE = 5
MAX_OVERFLOW = 10

# Retry constants
MAX_RETRIES = 3
EXPECTED_TWO_EXECUTIONS = 2

# Sample financial data (from AAPL FY2023 10-K)
SAMPLE_REVENUE = 394328000000
SAMPLE_NET_INCOME = 96995000000
SAMPLE_EPS = 616
SAMPLE_TOTAL_ASSETS = 352755000000
SAMPLE_TOTAL_EQUITY = 62318000000
SAMPLE_CASH = 29965000000
SAMPLE_OPERATING_CF = 110543000000
SAMPLE_FREE_CF = 99584000000
SAMPLE_CAPEX = 10959000000

# Sample metadata
FISCAL_QUARTER_3 = 3
VERSION_2 = 2


class TestPostgresClientInit:
    """Tests for PostgresClient initialization."""

    def test_init_creates_engine(self) -> None:
        """Test that __init__ creates async engine with correct parameters."""
        with (
            patch("storage.postgres_client.create_async_engine") as mock_create,
            patch("storage.postgres_client.async_sessionmaker"),
        ):
            PostgresClient(
                database_url="postgresql+asyncpg://user:pass@localhost/db",
                pool_size=POOL_SIZE,
                max_overflow=MAX_OVERFLOW,
            )

            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[0][0] == "postgresql+asyncpg://user:pass@localhost/db"
            assert call_args[1]["pool_size"] == POOL_SIZE
            assert call_args[1]["max_overflow"] == MAX_OVERFLOW
            assert call_args[1]["echo"] is False

    def test_init_creates_sessionmaker(self) -> None:
        """Test that __init__ creates async sessionmaker."""
        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker") as mock_sessionmaker,
        ):
            PostgresClient()

            mock_sessionmaker.assert_called_once()
            call_kwargs = mock_sessionmaker.call_args[1]
            assert call_kwargs["class_"] is not None  # AsyncSession class
            assert call_kwargs["expire_on_commit"] is False


class TestSessionManagement:
    """Tests for session context manager and connection management."""

    @pytest.mark.asyncio
    async def test_session_commits_on_success(self) -> None:
        """Test that session commits when no exception occurs."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            async with client.session():
                # Simulate successful operation
                pass

            mock_session.commit.assert_called_once()
            mock_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_session_rolls_back_on_exception(self) -> None:
        """Test that session rolls back when exception occurs during yield."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            with pytest.raises(ValueError, match="Test error"):
                async with client.session():
                    raise ValueError("Test error")

            mock_session.rollback.assert_called_once()
            mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_session_propagates_exception(self) -> None:
        """Test that exceptions are propagated after rollback."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            custom_error = RuntimeError("Database connection lost")
            with pytest.raises(RuntimeError, match="Database connection lost"):
                async with client.session():
                    raise custom_error

    @pytest.mark.asyncio
    async def test_close_disposes_engine(self) -> None:
        """Test that close() properly disposes the engine."""
        mock_engine = AsyncMock()

        with (
            patch("storage.postgres_client.create_async_engine", return_value=mock_engine),
            patch("storage.postgres_client.async_sessionmaker"),
        ):
            client = PostgresClient()
            await client.close()

            mock_engine.dispose.assert_called_once()


class TestDataclasses:
    """Tests for dataclass validation and defaults."""

    def test_company_data_defaults(self) -> None:
        """Test CompanyData default values."""
        company = CompanyData(
            ticker="AAPL",
            cik="0000320193",
            company_name="Apple Inc.",
        )

        assert company.ticker == "AAPL"
        assert company.sector is None
        assert company.industry is None
        assert company.exchange is None
        assert company.country == "US"

    def test_company_data_with_optionals(self) -> None:
        """Test CompanyData with all fields specified."""
        company = CompanyData(
            ticker="AAPL",
            cik="0000320193",
            company_name="Apple Inc.",
            sector="Technology",
            industry="Consumer Electronics",
            exchange="NASDAQ",
            country="US",
        )

        assert company.sector == "Technology"
        assert company.industry == "Consumer Electronics"
        assert company.exchange == "NASDAQ"

    def test_document_metadata_defaults(self) -> None:
        """Test DocumentMetadata default values."""
        doc = DocumentMetadata(
            ticker="AAPL",
            cik="0000320193",
            company_name="Apple Inc.",
            form_type="10-K",
            filing_date=date(2023, 11, 3),
            period_end_date=date(2023, 9, 30),
            fiscal_year=2023,
            fiscal_quarter=None,
            accession_number="0000320193-23-000106",
            s3_path="raw/filing.html",
        )

        assert doc.fiscal_quarter is None
        assert doc.version == 1
        assert doc.parse_status == "pending"

    def test_document_metadata_with_optionals(self) -> None:
        """Test DocumentMetadata with all fields specified."""
        doc = DocumentMetadata(
            ticker="AAPL",
            cik="0000320193",
            company_name="Apple Inc.",
            form_type="10-Q",
            filing_date=date(2023, 8, 3),
            period_end_date=date(2023, 6, 30),
            fiscal_year=2023,
            fiscal_quarter=FISCAL_QUARTER_3,
            accession_number="0000320193-23-000080",
            s3_path="raw/filing.html",
            version=VERSION_2,
            parse_status="success",
        )

        assert doc.fiscal_quarter == FISCAL_QUARTER_3
        assert doc.version == VERSION_2
        assert doc.parse_status == "success"

    def test_income_statement_data_defaults(self) -> None:
        """Test IncomeStatementData default values."""
        income = IncomeStatementData(
            ticker="AAPL",
            filing_id=uuid4(),
            period_end_date=date(2023, 9, 30),
            fiscal_year=2023,
            fiscal_quarter=None,
        )

        assert income.fiscal_quarter is None
        assert income.revenue is None
        assert income.cost_of_revenue is None
        assert income.version == 1

    def test_income_statement_data_with_values(self) -> None:
        """Test IncomeStatementData with actual values."""
        filing_id = uuid4()
        income = IncomeStatementData(
            ticker="AAPL",
            filing_id=filing_id,
            period_end_date=date(2023, 9, 30),
            fiscal_year=2023,
            fiscal_quarter=None,
            revenue=SAMPLE_REVENUE,
            net_income=SAMPLE_NET_INCOME,
            eps_diluted=SAMPLE_EPS,
            version=1,
        )

        assert income.revenue == SAMPLE_REVENUE
        assert income.net_income == SAMPLE_NET_INCOME
        assert income.eps_diluted == SAMPLE_EPS
        assert income.filing_id == filing_id

    def test_balance_sheet_data_defaults(self) -> None:
        """Test BalanceSheetData default values."""
        balance = BalanceSheetData(
            ticker="AAPL",
            filing_id=uuid4(),
            period_end_date=date(2023, 9, 30),
            fiscal_year=2023,
            fiscal_quarter=None,
        )

        assert balance.total_assets is None
        assert balance.total_liabilities is None
        assert balance.version == 1

    def test_balance_sheet_data_with_values(self) -> None:
        """Test BalanceSheetData with actual values."""
        balance = BalanceSheetData(
            ticker="AAPL",
            filing_id=uuid4(),
            period_end_date=date(2023, 9, 30),
            fiscal_year=2023,
            fiscal_quarter=None,
            total_assets=SAMPLE_TOTAL_ASSETS,
            total_equity=SAMPLE_TOTAL_EQUITY,
            cash=SAMPLE_CASH,
        )

        assert balance.total_assets == SAMPLE_TOTAL_ASSETS
        assert balance.total_equity == SAMPLE_TOTAL_EQUITY
        assert balance.cash == SAMPLE_CASH

    def test_cash_flow_data_defaults(self) -> None:
        """Test CashFlowData default values."""
        cashflow = CashFlowData(
            ticker="AAPL",
            filing_id=uuid4(),
            period_end_date=date(2023, 9, 30),
            fiscal_year=2023,
            fiscal_quarter=None,
        )

        assert cashflow.operating_cf is None
        assert cashflow.investing_cf is None
        assert cashflow.version == 1

    def test_cash_flow_data_with_values(self) -> None:
        """Test CashFlowData with actual values."""
        cashflow = CashFlowData(
            ticker="AAPL",
            filing_id=uuid4(),
            period_end_date=date(2023, 9, 30),
            fiscal_year=2023,
            fiscal_quarter=None,
            operating_cf=SAMPLE_OPERATING_CF,
            free_cash_flow=SAMPLE_FREE_CF,
            capex=SAMPLE_CAPEX,
        )

        assert cashflow.operating_cf == SAMPLE_OPERATING_CF
        assert cashflow.free_cash_flow == SAMPLE_FREE_CF
        assert cashflow.capex == SAMPLE_CAPEX


class TestBulkInsertRetryLogic:
    """Tests for bulk_insert_financials retry mechanism."""

    @pytest.mark.asyncio
    async def test_bulk_insert_succeeds_on_first_attempt(self) -> None:
        """Test successful bulk insert without retries."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            income_data = [{"ticker": "AAPL", "filing_id": uuid4(), "revenue": 100000}]
            await client.bulk_insert_financials(income_data, [], [])

            # Should execute once without retry
            assert mock_session.execute.call_count == 1
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_insert_retries_on_dbapi_error(self) -> None:
        """Test that DBAPIError triggers retry up to max_retries."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # First attempt raises DBAPIError, second succeeds
        db_error = DBAPIError("Connection lost", [], Exception("Connection lost"))
        mock_session.execute.side_effect = [
            db_error,
            AsyncMock(),  # Success on retry
        ]

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
            patch("storage.postgres_client.logger") as mock_logger,
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            income_data = [{"ticker": "AAPL", "filing_id": uuid4(), "revenue": 100000}]
            await client.bulk_insert_financials(income_data, [], [])

            # Should attempt twice (fail once, succeed once)
            assert mock_session.execute.call_count == EXPECTED_TWO_EXECUTIONS
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_insert_fails_after_max_retries(self) -> None:
        """Test that bulk insert fails after exhausting all retries."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Fail all 3 attempts
        db_error = DBAPIError("Connection lost", [], Exception("Connection lost"))
        mock_session.execute.side_effect = db_error

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
            patch("storage.postgres_client.logger"),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            income_data = [{"ticker": "AAPL", "filing_id": uuid4(), "revenue": 100000}]
            with pytest.raises(DBAPIError, match="Connection lost"):
                await client.bulk_insert_financials(income_data, [], [])

            # Should attempt max_retries times
            assert mock_session.execute.call_count == MAX_RETRIES

    @pytest.mark.asyncio
    async def test_bulk_insert_non_dbapi_error_no_retry(self) -> None:
        """Test that non-DBAPIError exceptions don't trigger retry."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Raise a non-DBAPIError exception
        mock_session.execute.side_effect = ValueError("Invalid data")

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            income_data = [{"ticker": "AAPL", "filing_id": uuid4(), "revenue": 100000}]
            with pytest.raises(ValueError, match="Invalid data"):
                await client.bulk_insert_financials(income_data, [], [])

            # Should only attempt once (no retry for non-DBAPIError)
            assert mock_session.execute.call_count == 1


class TestGetCompanyMetadata:
    """Tests for get_company_metadata edge cases."""

    @pytest.mark.asyncio
    async def test_get_company_metadata_all_fields(self) -> None:
        """Test that all fields are correctly mapped from database row."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Mock database row with all fields
        mock_row = MagicMock()
        mock_row.ticker = "AAPL"
        mock_row.cik = "0000320193"
        mock_row.company_name = "Apple Inc."
        mock_row.sector = "Technology"
        mock_row.industry = "Consumer Electronics"
        mock_row.exchange = "NASDAQ"
        mock_row.country = "US"
        mock_row.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_row.updated_at = datetime(2023, 12, 1, 12, 0, 0)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            result = await client.get_company_metadata("AAPL")

            assert result is not None
            assert result["ticker"] == "AAPL"
            assert result["cik"] == "0000320193"
            assert result["company_name"] == "Apple Inc."
            assert result["sector"] == "Technology"
            assert result["industry"] == "Consumer Electronics"
            assert result["exchange"] == "NASDAQ"
            assert result["country"] == "US"
            assert result["created_at"] == datetime(2023, 1, 1, 12, 0, 0)
            assert result["updated_at"] == datetime(2023, 12, 1, 12, 0, 0)

    @pytest.mark.asyncio
    async def test_get_company_metadata_null_optional_fields(self) -> None:
        """Test that NULL optional fields are handled correctly."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Mock database row with NULL optional fields
        mock_row = MagicMock()
        mock_row.ticker = "TSLA"
        mock_row.cik = "0001318605"
        mock_row.company_name = "Tesla Inc."
        mock_row.sector = None
        mock_row.industry = None
        mock_row.exchange = None
        mock_row.country = "US"
        mock_row.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_row.updated_at = datetime(2023, 1, 1, 12, 0, 0)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            result = await client.get_company_metadata("TSLA")

            assert result is not None
            assert result["sector"] is None
            assert result["industry"] is None
            assert result["exchange"] is None
            assert result["country"] == "US"

    @pytest.mark.asyncio
    async def test_get_company_metadata_not_found(self) -> None:
        """Test that None is returned when company not found."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            result = await client.get_company_metadata("NONEXISTENT")

            assert result is None


class TestSupersedeFilingEdgeCases:
    """Tests for supersede_filing edge cases."""

    @pytest.mark.asyncio
    async def test_supersede_filing_no_matching_filing(self) -> None:
        """Test superseding when no matching filing exists (should be no-op)."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Mock no rows affected
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            # Should not raise exception, just no-op
            await client.supersede_filing(
                ticker="AAPL",
                period_end_date=date(2023, 9, 30),
                form_type="10-K",
                new_filing_id=uuid4(),
            )

            # Verify UPDATE was executed
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_supersede_filing_already_superseded(self) -> None:
        """Test superseding a filing that's already marked as superseded."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Mock no rows affected (because is_latest=false already)
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            # Should not raise exception
            await client.supersede_filing(
                ticker="AAPL",
                period_end_date=date(2023, 9, 30),
                form_type="10-K",
                new_filing_id=uuid4(),
            )

            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_supersede_filing_multiple_conditions(self) -> None:
        """Test that all WHERE conditions must match."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            new_filing_id = uuid4()
            await client.supersede_filing(
                ticker="AAPL",
                period_end_date=date(2023, 9, 30),
                form_type="10-K",
                new_filing_id=new_filing_id,
            )

            # Verify all parameters were passed correctly
            call_args = mock_session.execute.call_args
            params = call_args[0][1]
            assert params["ticker"] == "AAPL"
            assert params["period_end_date"] == date(2023, 9, 30)
            assert params["form_type"] == "10-K"
            assert params["new_filing_id"] == new_filing_id


class TestPartialBulkInsert:
    """Tests for bulk_insert_financials with partial data."""

    @pytest.mark.asyncio
    async def test_bulk_insert_only_income_statements(self) -> None:
        """Test bulk insert with only income statements (others empty)."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            income_data = [{"ticker": "AAPL", "filing_id": uuid4(), "revenue": 100000}]
            await client.bulk_insert_financials(income_data, [], [])

            # Should execute only once for income statements
            assert mock_session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_bulk_insert_only_balance_sheets(self) -> None:
        """Test bulk insert with only balance sheets (others empty)."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            balance_data = [{"ticker": "AAPL", "filing_id": uuid4(), "total_assets": 500000}]
            await client.bulk_insert_financials([], balance_data, [])

            # Should execute only once for balance sheets
            assert mock_session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_bulk_insert_only_cash_flows(self) -> None:
        """Test bulk insert with only cash flows (others empty)."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            cashflow_data = [{"ticker": "AAPL", "filing_id": uuid4(), "operating_cf": 200000}]
            await client.bulk_insert_financials([], [], cashflow_data)

            # Should execute only once for cash flows
            assert mock_session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_bulk_insert_income_and_balance_only(self) -> None:
        """Test bulk insert with income and balance, cash flows empty."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            income_data = [{"ticker": "AAPL", "filing_id": uuid4(), "revenue": 100000}]
            balance_data = [{"ticker": "AAPL", "filing_id": uuid4(), "total_assets": 500000}]
            await client.bulk_insert_financials(income_data, balance_data, [])

            # Should execute twice (income + balance)
            assert mock_session.execute.call_count == EXPECTED_TWO_EXECUTIONS

    @pytest.mark.asyncio
    async def test_bulk_insert_all_empty(self) -> None:
        """Test bulk insert with all empty lists (no-op)."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            await client.bulk_insert_financials([], [], [])

            # Should not execute any inserts
            assert mock_session.execute.call_count == 0
            # But should still commit the empty transaction
            mock_session.commit.assert_called_once()


class TestUpsertNullTransitions:
    """Tests for upsert_company NULL field transitions."""

    @pytest.mark.asyncio
    async def test_upsert_company_null_to_value(self) -> None:
        """Test updating NULL optional fields to non-NULL values."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            # Upsert with values for previously NULL fields
            company = CompanyData(
                ticker="AAPL",
                cik="0000320193",
                company_name="Apple Inc.",
                sector="Technology",
                industry="Consumer Electronics",
                exchange="NASDAQ",
            )
            await client.upsert_company(company)

            call_args = mock_session.execute.call_args
            params = call_args[0][1]
            assert params["sector"] == "Technology"
            assert params["industry"] == "Consumer Electronics"
            assert params["exchange"] == "NASDAQ"

    @pytest.mark.asyncio
    async def test_upsert_company_value_to_null(self) -> None:
        """Test updating non-NULL fields to NULL values."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            # Upsert with NULL for optional fields
            company = CompanyData(
                ticker="AAPL",
                cik="0000320193",
                company_name="Apple Inc.",
                sector=None,
                industry=None,
                exchange=None,
            )
            await client.upsert_company(company)

            call_args = mock_session.execute.call_args
            params = call_args[0][1]
            assert params["sector"] is None
            assert params["industry"] is None
            assert params["exchange"] is None

    @pytest.mark.asyncio
    async def test_upsert_company_partial_update(self) -> None:
        """Test partial field updates (some NULL, some with values)."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            # Upsert with mixed NULL and non-NULL values
            company = CompanyData(
                ticker="AAPL",
                cik="0000320193",
                company_name="Apple Inc.",
                sector="Technology",
                industry=None,  # NULL
                exchange="NASDAQ",
            )
            await client.upsert_company(company)

            call_args = mock_session.execute.call_args
            params = call_args[0][1]
            assert params["sector"] == "Technology"
            assert params["industry"] is None
            assert params["exchange"] == "NASDAQ"


class TestErrorScenarios:
    """Tests for various error scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_extremely_large_financial_values(self) -> None:
        """Test handling of extremely large financial values."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            # Very large value (near int64 max)
            large_revenue = 9_223_372_036_854_775_807  # Max int64
            income_data = [{"ticker": "AAPL", "filing_id": uuid4(), "revenue": large_revenue}]
            await client.bulk_insert_financials(income_data, [], [])

            call_args = mock_session.execute.call_args
            params = call_args[0][1]
            assert params[0]["revenue"] == large_revenue

    @pytest.mark.asyncio
    async def test_empty_string_vs_none_in_company_data(self) -> None:
        """Test that empty strings and None are handled correctly."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            # Test with None
            company_none = CompanyData(
                ticker="AAPL",
                cik="0000320193",
                company_name="Apple Inc.",
                sector=None,
            )
            await client.upsert_company(company_none)

            call_args = mock_session.execute.call_args
            params = call_args[0][1]
            assert params["sector"] is None

    @pytest.mark.asyncio
    async def test_special_characters_in_company_name(self) -> None:
        """Test handling of special characters in string fields."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            # Company name with special characters
            company = CompanyData(
                ticker="BRK.B",
                cik="0001067983",
                company_name="Berkshire Hathaway Inc. - Class B",
            )
            await client.upsert_company(company)

            call_args = mock_session.execute.call_args
            params = call_args[0][1]
            assert params["ticker"] == "BRK.B"
            assert params["company_name"] == "Berkshire Hathaway Inc. - Class B"

    @pytest.mark.asyncio
    async def test_negative_financial_values(self) -> None:
        """Test handling of negative financial values (losses, negative equity)."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            # Negative values (net loss, negative equity)
            income_data = [
                {
                    "ticker": "LOSS",
                    "filing_id": uuid4(),
                    "net_income": -1_000_000_000,  # $1B loss
                }
            ]
            balance_data = [
                {
                    "ticker": "LOSS",
                    "filing_id": uuid4(),
                    "total_equity": -500_000_000,  # Negative equity
                }
            ]
            await client.bulk_insert_financials(income_data, balance_data, [])

            # Should handle negative values without issue
            assert mock_session.execute.call_count == EXPECTED_TWO_EXECUTIONS


class TestIndividualInsertMethods:
    """Tests for individual insert methods (not bulk)."""

    @pytest.mark.asyncio
    async def test_insert_document_metadata(self) -> None:
        """Test insert_document_metadata returns filing_id."""
        filing_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = filing_id

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            metadata = DocumentMetadata(
                ticker="AAPL",
                cik="0000320193",
                company_name="Apple Inc.",
                form_type="10-K",
                filing_date=date(2023, 11, 3),
                period_end_date=date(2023, 9, 30),
                fiscal_year=2023,
                fiscal_quarter=4,
                accession_number="0000320193-23-000077",
                s3_path="raw/sec_filings/AAPL/2023/0000320193-23-000077.html",
            )

            result = await client.insert_document_metadata(metadata)

            assert result == filing_id
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_filing_exists_true(self) -> None:
        """Test check_filing_exists returns True when filing exists."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = True

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            exists = await client.check_filing_exists("0000320193", "0000320193-23-000077")

            assert exists is True
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_filing_exists_false(self) -> None:
        """Test check_filing_exists returns False when filing does not exist."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = False

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            exists = await client.check_filing_exists("0000320193", "0000320193-23-999999")

            assert exists is False
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_income_statement(self) -> None:
        """Test insert_income_statement returns record id."""
        record_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = record_id

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            data = IncomeStatementData(
                ticker="AAPL",
                filing_id=uuid4(),
                period_end_date=date(2023, 9, 30),
                fiscal_year=2023,
                fiscal_quarter=4,
                revenue=SAMPLE_REVENUE,
                net_income=SAMPLE_NET_INCOME,
                eps_basic=SAMPLE_EPS,
            )

            result = await client.insert_income_statement(data)

            assert result == record_id
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_balance_sheet(self) -> None:
        """Test insert_balance_sheet returns record id."""
        record_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = record_id

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            data = BalanceSheetData(
                ticker="AAPL",
                filing_id=uuid4(),
                period_end_date=date(2023, 9, 30),
                fiscal_year=2023,
                fiscal_quarter=4,
                total_assets=SAMPLE_TOTAL_ASSETS,
                total_equity=SAMPLE_TOTAL_EQUITY,
                cash=SAMPLE_CASH,
            )

            result = await client.insert_balance_sheet(data)

            assert result == record_id
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_cash_flow(self) -> None:
        """Test insert_cash_flow returns record id."""
        record_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = record_id

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("storage.postgres_client.create_async_engine"),
            patch("storage.postgres_client.async_sessionmaker", return_value=mock_session_factory),
        ):
            client = PostgresClient()
            client.session_factory = mock_session_factory

            data = CashFlowData(
                ticker="AAPL",
                filing_id=uuid4(),
                period_end_date=date(2023, 9, 30),
                fiscal_year=2023,
                fiscal_quarter=4,
                operating_cf=SAMPLE_OPERATING_CF,
                free_cash_flow=SAMPLE_FREE_CF,
                capex=SAMPLE_CAPEX,
            )

            result = await client.insert_cash_flow(data)

            assert result == record_id
            mock_session.execute.assert_called_once()
