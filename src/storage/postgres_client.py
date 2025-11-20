"""PostgreSQL client for data collector agent.

Provides async interface for:
- Document registry (SEC filings metadata)
- Financial data (income statements, balance sheets, cash flows)
- Company metadata
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from typing import Any, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (  # type: ignore[attr-defined]
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)


@dataclass
class CompanyData:
    """Company metadata for upsert operations."""

    ticker: str
    cik: str
    company_name: str
    sector: str | None = None
    industry: str | None = None
    exchange: str | None = None
    country: str = "US"


@dataclass
class DocumentMetadata:
    """Filing metadata for document registry."""

    ticker: str
    cik: str
    company_name: str
    form_type: str
    filing_date: date
    period_end_date: date
    fiscal_year: int
    fiscal_quarter: int | None
    accession_number: str
    s3_path: str
    parse_status: str = "pending"
    version: int = 1


@dataclass
class IncomeStatementData:
    """Income statement financial data."""

    ticker: str
    filing_id: UUID
    period_end_date: date
    fiscal_year: int
    fiscal_quarter: int | None
    revenue: int | None = None
    cost_of_revenue: int | None = None
    gross_profit: int | None = None
    operating_income: int | None = None
    net_income: int | None = None
    eps_basic: int | None = None
    eps_diluted: int | None = None
    shares_outstanding: int | None = None
    version: int = 1


@dataclass
class BalanceSheetData:
    """Balance sheet financial data."""

    ticker: str
    filing_id: UUID
    period_end_date: date
    fiscal_year: int
    fiscal_quarter: int | None
    total_assets: int | None = None
    current_assets: int | None = None
    cash: int | None = None
    accounts_receivable: int | None = None
    inventory: int | None = None
    total_liabilities: int | None = None
    current_liabilities: int | None = None
    total_debt: int | None = None
    accounts_payable: int | None = None
    total_equity: int | None = None
    retained_earnings: int | None = None
    version: int = 1


@dataclass
class CashFlowData:
    """Cash flow statement financial data."""

    ticker: str
    filing_id: UUID
    period_end_date: date
    fiscal_year: int
    fiscal_quarter: int | None
    operating_cf: int | None = None
    investing_cf: int | None = None
    financing_cf: int | None = None
    capex: int | None = None
    free_cash_flow: int | None = None
    dividends_paid: int | None = None
    version: int = 1


class PostgresClient:
    """Async PostgreSQL client for data collector operations."""

    def __init__(
        self,
        database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fundamental_analysis",
        pool_size: int = 5,
        max_overflow: int = 15,
    ):
        """Initialize PostgreSQL client with connection pool.

        Args:
            database_url: PostgreSQL connection URL
            pool_size: Minimum connection pool size
            max_overflow: Maximum overflow connections
        """
        self.engine: AsyncEngine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            echo=False,  # Set to True for SQL debug logging
        )
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        """Context manager for database sessions with auto-rollback on error."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        """Close database connection pool."""
        await self.engine.dispose()  # type: ignore[no-untyped-call]

    # ========== Company Metadata ==========

    async def upsert_company(self, company: CompanyData) -> None:
        """Insert or update company metadata.

        Args:
            company: Company metadata to upsert
        """
        async with self.session() as session:
            query = text("""
                INSERT INTO metadata.companies (
                    ticker, cik, company_name, sector, industry, exchange, country, created_at, updated_at
                )
                VALUES (:ticker, :cik, :company_name, :sector, :industry, :exchange, :country, NOW(), NOW())
                ON CONFLICT (ticker) DO UPDATE SET
                    cik = EXCLUDED.cik,
                    company_name = EXCLUDED.company_name,
                    sector = EXCLUDED.sector,
                    industry = EXCLUDED.industry,
                    exchange = EXCLUDED.exchange,
                    country = EXCLUDED.country,
                    updated_at = NOW()
            """)
            await session.execute(
                query,
                {
                    "ticker": company.ticker,
                    "cik": company.cik,
                    "company_name": company.company_name,
                    "sector": company.sector,
                    "industry": company.industry,
                    "exchange": company.exchange,
                    "country": company.country,
                },
            )

    async def get_company_metadata(self, ticker: str) -> dict[str, Any] | None:
        """Fetch company metadata by ticker.

        Args:
            ticker: Stock ticker

        Returns:
            Company metadata dict or None if not found
        """
        async with self.session() as session:
            query = text("SELECT * FROM metadata.companies WHERE ticker = :ticker")
            result = await session.execute(query, {"ticker": ticker})
            row = result.fetchone()
            if row:
                return {
                    "ticker": row.ticker,
                    "cik": row.cik,
                    "company_name": row.company_name,
                    "sector": row.sector,
                    "industry": row.industry,
                    "exchange": row.exchange,
                    "country": row.country,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
            return None

    # ========== Document Registry ==========

    async def insert_document_metadata(self, metadata: DocumentMetadata) -> UUID:
        """Insert filing metadata into document registry.

        Args:
            metadata: Filing metadata to insert

        Returns:
            UUID of inserted filing record

        Raises:
            IntegrityError: If duplicate filing exists
        """
        async with self.session() as session:
            query = text("""
                INSERT INTO document_registry.filings (
                    ticker, cik, company_name, form_type, filing_date, period_end_date,
                    fiscal_year, fiscal_quarter, accession_number, s3_path, parse_status, version
                )
                VALUES (
                    :ticker, :cik, :company_name, :form_type, :filing_date, :period_end_date,
                    :fiscal_year, :fiscal_quarter, :accession_number, :s3_path, :parse_status, :version
                )
                RETURNING filing_id
            """)
            result = await session.execute(
                query,
                {
                    "ticker": metadata.ticker,
                    "cik": metadata.cik,
                    "company_name": metadata.company_name,
                    "form_type": metadata.form_type,
                    "filing_date": metadata.filing_date,
                    "period_end_date": metadata.period_end_date,
                    "fiscal_year": metadata.fiscal_year,
                    "fiscal_quarter": metadata.fiscal_quarter,
                    "accession_number": metadata.accession_number,
                    "s3_path": metadata.s3_path,
                    "parse_status": metadata.parse_status,
                    "version": metadata.version,
                },
            )
            filing_id = result.scalar_one()
            return cast(UUID, filing_id)

    async def check_filing_exists(self, cik: str, accession_number: str) -> bool:
        """Check if filing already exists in registry.

        Args:
            cik: SEC CIK
            accession_number: SEC accession number

        Returns:
            True if filing exists, False otherwise
        """
        async with self.session() as session:
            query = text("""
                SELECT EXISTS(
                    SELECT 1 FROM document_registry.filings
                    WHERE cik = :cik AND accession_number = :accession_number
                )
            """)
            result = await session.execute(query, {"cik": cik, "accession_number": accession_number})
            return cast(bool, result.scalar_one())

    async def supersede_filing(
        self,
        ticker: str,
        period_end_date: date,
        form_type: str,
        new_filing_id: UUID,
    ) -> None:
        """Mark old filing as superseded by new version.

        Args:
            ticker: Stock ticker
            period_end_date: Period end date
            form_type: Filing form type
            new_filing_id: UUID of new filing version
        """
        async with self.session() as session:
            query = text("""
                UPDATE document_registry.filings
                SET is_latest = false, superseded_by = :new_filing_id, updated_at = NOW()
                WHERE ticker = :ticker
                  AND period_end_date = :period_end_date
                  AND form_type = :form_type
                  AND is_latest = true
            """)
            await session.execute(
                query,
                {
                    "ticker": ticker,
                    "period_end_date": period_end_date,
                    "form_type": form_type,
                    "new_filing_id": new_filing_id,
                },
            )

    # ========== Financial Data ==========

    async def insert_income_statement(self, data: IncomeStatementData) -> UUID:
        """Insert income statement data.

        Args:
            data: Income statement data to insert

        Returns:
            UUID of inserted record
        """
        async with self.session() as session:
            query = text("""
                INSERT INTO financial_data.income_statements (
                    ticker, filing_id, period_end_date, fiscal_year, fiscal_quarter,
                    revenue, cost_of_revenue, gross_profit, operating_income, net_income,
                    eps_basic, eps_diluted, shares_outstanding, version
                )
                VALUES (
                    :ticker, :filing_id, :period_end_date, :fiscal_year, :fiscal_quarter,
                    :revenue, :cost_of_revenue, :gross_profit, :operating_income, :net_income,
                    :eps_basic, :eps_diluted, :shares_outstanding, :version
                )
                RETURNING id
            """)
            result = await session.execute(
                query,
                {
                    "ticker": data.ticker,
                    "filing_id": data.filing_id,
                    "period_end_date": data.period_end_date,
                    "fiscal_year": data.fiscal_year,
                    "fiscal_quarter": data.fiscal_quarter,
                    "revenue": data.revenue,
                    "cost_of_revenue": data.cost_of_revenue,
                    "gross_profit": data.gross_profit,
                    "operating_income": data.operating_income,
                    "net_income": data.net_income,
                    "eps_basic": data.eps_basic,
                    "eps_diluted": data.eps_diluted,
                    "shares_outstanding": data.shares_outstanding,
                    "version": data.version,
                },
            )
            return cast(UUID, result.scalar_one())

    async def insert_balance_sheet(self, data: BalanceSheetData) -> UUID:
        """Insert balance sheet data.

        Args:
            data: Balance sheet data to insert

        Returns:
            UUID of inserted record
        """
        async with self.session() as session:
            query = text("""
                INSERT INTO financial_data.balance_sheets (
                    ticker, filing_id, period_end_date, fiscal_year, fiscal_quarter,
                    total_assets, current_assets, cash, accounts_receivable, inventory,
                    total_liabilities, current_liabilities, total_debt, accounts_payable,
                    total_equity, retained_earnings, version
                )
                VALUES (
                    :ticker, :filing_id, :period_end_date, :fiscal_year, :fiscal_quarter,
                    :total_assets, :current_assets, :cash, :accounts_receivable, :inventory,
                    :total_liabilities, :current_liabilities, :total_debt, :accounts_payable,
                    :total_equity, :retained_earnings, :version
                )
                RETURNING id
            """)
            result = await session.execute(
                query,
                {
                    "ticker": data.ticker,
                    "filing_id": data.filing_id,
                    "period_end_date": data.period_end_date,
                    "fiscal_year": data.fiscal_year,
                    "fiscal_quarter": data.fiscal_quarter,
                    "total_assets": data.total_assets,
                    "current_assets": data.current_assets,
                    "cash": data.cash,
                    "accounts_receivable": data.accounts_receivable,
                    "inventory": data.inventory,
                    "total_liabilities": data.total_liabilities,
                    "current_liabilities": data.current_liabilities,
                    "total_debt": data.total_debt,
                    "accounts_payable": data.accounts_payable,
                    "total_equity": data.total_equity,
                    "retained_earnings": data.retained_earnings,
                    "version": data.version,
                },
            )
            return cast(UUID, result.scalar_one())

    async def insert_cash_flow(self, data: CashFlowData) -> UUID:
        """Insert cash flow statement data.

        Args:
            data: Cash flow data to insert

        Returns:
            UUID of inserted record
        """
        async with self.session() as session:
            query = text("""
                INSERT INTO financial_data.cash_flows (
                    ticker, filing_id, period_end_date, fiscal_year, fiscal_quarter,
                    operating_cf, investing_cf, financing_cf, capex, free_cash_flow,
                    dividends_paid, version
                )
                VALUES (
                    :ticker, :filing_id, :period_end_date, :fiscal_year, :fiscal_quarter,
                    :operating_cf, :investing_cf, :financing_cf, :capex, :free_cash_flow,
                    :dividends_paid, :version
                )
                RETURNING id
            """)
            result = await session.execute(
                query,
                {
                    "ticker": data.ticker,
                    "filing_id": data.filing_id,
                    "period_end_date": data.period_end_date,
                    "fiscal_year": data.fiscal_year,
                    "fiscal_quarter": data.fiscal_quarter,
                    "operating_cf": data.operating_cf,
                    "investing_cf": data.investing_cf,
                    "financing_cf": data.financing_cf,
                    "capex": data.capex,
                    "free_cash_flow": data.free_cash_flow,
                    "dividends_paid": data.dividends_paid,
                    "version": data.version,
                },
            )
            return cast(UUID, result.scalar_one())

    async def bulk_insert_financials(
        self,
        income_statements: list[dict[str, Any]],
        balance_sheets: list[dict[str, Any]],
        cash_flows: list[dict[str, Any]],
    ) -> None:
        """Bulk insert financial statements with transaction.

        Args:
            income_statements: List of income statement dicts
            balance_sheets: List of balance sheet dicts
            cash_flows: List of cash flow dicts

        Raises:
            DBAPIError: On database errors (retryable)
            IntegrityError: On constraint violations
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with self.session() as session:
                    # Insert income statements
                    if income_statements:
                        await session.execute(
                            text("""
                                INSERT INTO financial_data.income_statements (
                                    ticker, filing_id, period_end_date, fiscal_year, fiscal_quarter,
                                    revenue, cost_of_revenue, gross_profit, operating_income, net_income,
                                    eps_basic, eps_diluted, shares_outstanding, version
                                )
                                VALUES (
                                    :ticker, :filing_id, :period_end_date, :fiscal_year, :fiscal_quarter,
                                    :revenue, :cost_of_revenue, :gross_profit, :operating_income, :net_income,
                                    :eps_basic, :eps_diluted, :shares_outstanding, :version
                                )
                            """),
                            income_statements,
                        )

                    # Insert balance sheets
                    if balance_sheets:
                        await session.execute(
                            text("""
                                INSERT INTO financial_data.balance_sheets (
                                    ticker, filing_id, period_end_date, fiscal_year, fiscal_quarter,
                                    total_assets, current_assets, cash, accounts_receivable, inventory,
                                    total_liabilities, current_liabilities, total_debt, accounts_payable,
                                    total_equity, retained_earnings, version
                                )
                                VALUES (
                                    :ticker, :filing_id, :period_end_date, :fiscal_year, :fiscal_quarter,
                                    :total_assets, :current_assets, :cash, :accounts_receivable, :inventory,
                                    :total_liabilities, :current_liabilities, :total_debt, :accounts_payable,
                                    :total_equity, :retained_earnings, :version
                                )
                            """),
                            balance_sheets,
                        )

                    # Insert cash flows
                    if cash_flows:
                        await session.execute(
                            text("""
                                INSERT INTO financial_data.cash_flows (
                                    ticker, filing_id, period_end_date, fiscal_year, fiscal_quarter,
                                    operating_cf, investing_cf, financing_cf, capex, free_cash_flow,
                                    dividends_paid, version
                                )
                                VALUES (
                                    :ticker, :filing_id, :period_end_date, :fiscal_year, :fiscal_quarter,
                                    :operating_cf, :investing_cf, :financing_cf, :capex, :free_cash_flow,
                                    :dividends_paid, :version
                                )
                            """),
                            cash_flows,
                        )
                    break  # Success, exit retry loop

            except DBAPIError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Database error on attempt {attempt + 1}/{max_retries}: {e}")
                    continue
                raise
