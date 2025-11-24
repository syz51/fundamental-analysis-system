# EdgarTools Screening Implementation Guide

**Project**: Fundamental Analysis System - Data Collector & Screener
**Version**: 2.0
**Date**: 2025-11-24
**Status**: Ready for Implementation
**Decision**: DD-033 (Screening Data Source: EdgarTools)

---

## Executive Summary

Implementation guide for using EdgarTools to screen S&P 500 companies (Days 1-2 of analysis pipeline). Uses unified SEC EDGAR data source for both screening (Tier 0, fast) and deep analysis (multi-tier, high quality).

**Key Benefits**:

- $0 cost (vs $180/year third-party APIs)
- Single source of truth (no data consistency issues)
- On-demand queries (no bulk download required)
- Full control & learning capability
- 95% baseline quality (Tier 0) for screening speed

**Scope Clarification**:

- **Screening (Days 1-2)**: EdgarTools Tier 0 only → 95% quality, optimized for speed
- **Deep Analysis (Days 3-7)**: Multi-tier system (Tiers 0-4) → 98.55% quality (see DD-031)

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Architecture Overview](#2-architecture-overview)
3. [Implementation Phases](#3-implementation-phases)
4. [Technical Specifications](#4-technical-specifications)
5. [Checkpoint System](#5-checkpoint-system)
6. [Caching Strategy](#6-caching-strategy)
7. [Testing Strategy](#7-testing-strategy)
8. [Open Research Questions](#8-open-research-questions)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Quick Start

### 1.1 Installation

```bash
# Add dependencies
uv add edgartools pandas python-dotenv

# Verify installation
python -c "from edgar import Company; print('EdgarTools ready')"
```

### 1.2 Basic Screening Example

```python
from edgar import Company, set_identity, set_rate_limit

# Required by SEC
set_identity("your.name@example.com")
set_rate_limit('NORMAL')  # 8-9 req/sec

# Screen a single company
company = Company("AAPL")
financials = company.get_financials()

# Calculate metrics
revenue = financials.income.revenue
net_income = financials.income.net_income
roe = net_income / financials.balance.stockholders_equity

print(f"AAPL ROE (latest): {roe.iloc[-1]:.2%}")
```

### 1.3 Minimal S&P 500 Screener

```python
from edgar import Company, set_identity, set_rate_limit

set_identity("your.email@example.com")
set_rate_limit('NORMAL')  # 8-9 req/sec for production

sp500 = load_sp500_tickers()  # From State Street SPY holdings API

candidates = []
for ticker in sp500:
    try:
        company = Company(ticker)
        financials = company.get_financials()

        roe = (financials.income.net_income /
               financials.balance.stockholders_equity).iloc[-1]

        if roe > 0.15:  # 15% ROE threshold
            candidates.append(ticker)
    except Exception as e:
        print(f"Skip {ticker}: {e}")

print(f"Found {len(candidates)} candidates")
```

---

## 2. Architecture Overview

### 2.1 System Components

```text
┌─────────────────────────────────────────────────────────────┐
│                     Screening Agent                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              EdgarTools Query Layer (Tier 0 ONLY)           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │   On-Demand API Queries                              │  │
│  │   - Company.get_financials() → SEC EDGAR API        │  │
│  │   - 8-9 req/sec rate limit (production safe)        │  │
│  │   - Auto HTTP caching (10 min TTL)                  │  │
│  │   - Optional bulk cache (~/.edgar/)                 │  │
│  │   - Quality: 95% baseline (Tier 0 only)             │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                Field Mapper (RESEARCH NEEDED)                │
│  - UNKNOWN: Does EdgarTools normalize US-GAAP tags?        │
│  - If NO: Map XBRL concepts → Standard names               │
│  - If YES: Field mapper may be redundant                   │
│  - TODO: Test EdgarTools API to confirm behavior           │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Metrics Calculator                             │
│  - Revenue CAGR (10Y, 5Y)                                   │
│  - Operating/Net Margins (3Y avg)                           │
│  - ROE/ROA/ROIC (3Y avg)                                    │
│  - Debt ratios (Debt/Equity, Net Debt/EBITDA)             │
│  - Liquidity (Current Ratio, Quick Ratio)                   │
│  - LIMITATION: ROIC assumes interest_expense available      │
│  - FALLBACK NEEDED: Handle missing data gracefully          │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           Screening Logic & Validation                      │
│  - Apply configurable filters (ScreeningConfig)             │
│  - Completeness check (≥5 of 8 metrics)                    │
│  - Quality validation (95% threshold, Tier 0)               │
│  - Output: Filtered candidates for Human Gate 1            │
│  - LIMITATION: Foreign filers (IFRS) may fail               │
│  - LIMITATION: REITs, banks need special handling           │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Checkpoint Manager (DD-011)                     │
│  - Save state after each subtask (PostgreSQL + Redis)       │
│  - Enable fast recovery on failure                          │
│  - 4 checkpointed phases (see Section 5)                    │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```text
1. Load S&P 500 tickers (State Street SPY holdings API)
2. For each ticker:
   a. Query SEC EDGAR API via EdgarTools (Tier 0)
   b. Extract financial statements (income, balance, cash flow)
   c. Map XBRL concepts to standard field names (if needed - RESEARCH)
   d. Calculate screening metrics
   e. Apply filtering criteria (configurable)
   f. Save checkpoint after each major phase
   g. Collect candidates
3. Output candidate list for Human Gate 1
```

### 2.3 Module Structure

**Focused on Data Collector Agent**:

```text
src/
├── data_collector/
│   ├── __init__.py
│   ├── edgar_screening_client.py    # EdgarTools wrapper (Tier 0)
│   ├── field_mapper.py               # RESEARCH: May be redundant
│   ├── metrics_calculator.py         # Ratio calculations
│   ├── validators.py                 # Data quality checks
│   ├── sp500_loader.py               # S&P 500 ticker list (SPY API)
│   └── checkpoint_manager.py         # Checkpoint save/restore
├── config/
│   ├── __init__.py
│   └── screening.py                  # ScreeningConfig class
└── storage/
    ├── postgres_client.py            # (Already exists)
    └── redis_client.py               # (Already exists)
```

---

## 3. Implementation Phases

### Phase 1: Core Components (Days 1-3)

#### 3.1.1 EdgarTools Screening Client

**File**: `src/data_collector/edgar_screening_client.py`

```python
"""EdgarTools wrapper for screening (Tier 0 only)."""

from typing import Optional, Dict, Any
from edgar import Company, set_identity, set_rate_limit
import logging

logger = logging.getLogger(__name__)

class EdgarScreeningClient:
    """EdgarTools client optimized for screening (Tier 0, 95% quality)."""

    def __init__(self, user_email: str, rate_limit: str = 'NORMAL'):
        """Initialize EdgarTools client.

        Args:
            user_email: Email for SEC identity requirement
            rate_limit: 'NORMAL' (8-9 req/sec) or 'CAUTION' (5 req/sec)
        """
        set_identity(user_email)
        set_rate_limit(rate_limit)  # Use NORMAL for production (8-9 req/sec)

    def get_financials(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch financial statements for ticker (Tier 0 only).

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with income, balance, cashflow DataFrames or None if failed

        Note:
            - Uses Tier 0 only (95% quality, fast)
            - Deep analysis (Days 3-7) uses multi-tier (98.55%)
            - May fail for foreign filers (IFRS) - RESEARCH NEEDED
            - May fail for REITs, banks - special handling needed
        """
        try:
            company = Company(ticker)
            financials = company.get_financials()

            if not financials:
                logger.warning(f"{ticker}: No financials available")
                return None

            # RESEARCH NEEDED: Does EdgarTools normalize tag names?
            # If .income.revenue works, tags are normalized
            # If not, need to use field_mapper

            return {
                'income': financials.income.get_dataframe(),
                'balance': financials.balance.get_dataframe(),
                'cashflow': financials.cashflow.get_dataframe()
            }

        except Exception as e:
            logger.error(f"{ticker}: EdgarTools fetch failed - {e}")
            return None
```

#### 3.1.2 Field Mapper (OPTIONAL - NOT NEEDED FOR MVP)

**Status**: ✅ **RESEARCH COMPLETE** (2025-11-24)
**Decision**: **Field mapper NOT needed** - EdgarTools provides getter methods

**Findings** (see `research/FINDINGS_EdgarTools_Field_Normalization.md`):

- EdgarTools has built-in getter methods: `get_revenue()`, `get_net_income()`, etc.
- These methods handle XBRL tag variations internally
- Returns latest value as float (perfect for screening)
- 100% success rate across 10 S&P 500 companies

**Recommendation**:

- **Skip FieldMapper for MVP** (saves 200+ lines of code)
- Use EdgarTools getter methods for all basic metrics
- Optional lightweight mapper only if advanced metrics needed

**File**: `src/data_collector/field_mapper.py` (DEPRECATED - Do not implement)

```python
"""Map US-GAAP XBRL concepts to standardized field names.

DEPRECATED: EdgarTools provides built-in getter methods that handle
XBRL tag normalization internally. Field mapper not needed for basic
screening metrics.

This code is kept for reference only.
"""

from typing import Optional
import pandas as pd

class FieldMapper:
"""Handle XBRL concept name variations.

    NOTE: May be redundant if EdgarTools normalizes tags.
    Test before implementing.
    """

    # Map multiple XBRL tags to canonical names
    INCOME_MAPPING = {
        'revenue': [
            'Revenues',
            'RevenueFromContractWithCustomerExcludingAssessedTax',
            'SalesRevenueNet',
            'RevenueFromContractWithCustomerIncludingAssessedTax'
        ],
        'operating_income': [
            'OperatingIncomeLoss',
            'OperatingIncome',
            'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest'
        ],
        'net_income': [
            'NetIncomeLoss',
            'ProfitLoss',
            'NetIncomeLossAvailableToCommonStockholdersBasic'
        ],
        'interest_expense': [
            'InterestExpense',
            'InterestExpenseDebt'
        ]
    }

    BALANCE_MAPPING = {
        'total_assets': ['Assets', 'AssetsAbstract'],
        'stockholders_equity': [
            'StockholdersEquity',
            'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'
        ],
        'total_debt': [
            'DebtCurrent',
            'LongTermDebt',
            'DebtAndCapitalLeaseObligations'
        ],
        'cash': [
            'CashAndCashEquivalentsAtCarryingValue',
            'Cash',
            'CashCashEquivalentsAndShortTermInvestments'
        ],
        'current_assets': ['AssetsCurrent'],
        'current_liabilities': ['LiabilitiesCurrent']
    }

    def get_field(self, statement: pd.DataFrame, field_name: str,
                  mapping_dict: dict) -> Optional[pd.Series]:
        """Extract field from statement, trying all XBRL tag variations.

        Args:
            statement: DataFrame with XBRL concepts as index
            field_name: Canonical field name (e.g., 'revenue')
            mapping_dict: Mapping dict (INCOME_MAPPING or BALANCE_MAPPING)

        Returns:
            Series with field values, or None if not found
        """
        if field_name not in mapping_dict:
            return None

        for xbrl_tag in mapping_dict[field_name]:
            if xbrl_tag in statement.index:
                return statement.loc[xbrl_tag]

        return None

```

#### 3.1.3 Metrics Calculator

**File**: `src/data_collector/metrics_calculator.py`

```python
"""Calculate financial ratios and metrics for screening."""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from .field_mapper import FieldMapper
import logging

logger = logging.getLogger(__name__)

class MetricsCalculator:
    """Calculate screening metrics from EdgarTools financials."""

    def __init__(self, use_field_mapper: bool = True):
        """Initialize calculator.

        Args:
            use_field_mapper: Whether to use FieldMapper (RESEARCH: may be redundant)
        """
        self.mapper = FieldMapper() if use_field_mapper else None

    def calculate_revenue_cagr(self, income_stmt: pd.DataFrame,
                               years: int = 10) -> Optional[float]:
        """Calculate N-year revenue CAGR.

        LIMITATION: Requires at least N years of data.
        Recent IPOs (<10Y history) will fail.
        """
        revenue = self._get_field(income_stmt, 'revenue', self.mapper.INCOME_MAPPING)

        if revenue is None or len(revenue) < years:
            logger.warning(f"Insufficient revenue data: {len(revenue) if revenue is not None else 0} years < {years}")
            return None

        revenue = revenue.tail(years)
        start = revenue.iloc[0]
        end = revenue.iloc[-1]

        if start <= 0 or end <= 0:
            logger.warning(f"Invalid revenue values: start={start}, end={end}")
            return None

        cagr = (end / start) ** (1 / years) - 1
        return float(cagr)

    def calculate_avg_roic(self, income_stmt: pd.DataFrame,
                          balance_sheet: pd.DataFrame,
                          years: int = 3,
                          tax_rate: float = 0.21) -> Optional[float]:
        """Calculate N-year average ROIC.

        ROIC = NOPAT / Invested Capital
        NOPAT = Net Income + Interest Expense × (1 - Tax Rate)
        Invested Capital = Total Debt + Stockholders' Equity - Cash

        LIMITATION: Assumes interest_expense is available.
        If missing, assumes 0 (may understate ROIC for leveraged companies).
        FALLBACK NEEDED: Consider alternative ROIC calculation methods.
        """
        net_income = self._get_field(income_stmt, 'net_income', self.mapper.INCOME_MAPPING)
        interest_expense = self._get_field(income_stmt, 'interest_expense', self.mapper.INCOME_MAPPING)
        debt = self._get_field(balance_sheet, 'total_debt', self.mapper.BALANCE_MAPPING)
        equity = self._get_field(balance_sheet, 'stockholders_equity', self.mapper.BALANCE_MAPPING)
        cash = self._get_field(balance_sheet, 'cash', self.mapper.BALANCE_MAPPING)

        if None in [net_income, debt, equity]:
            logger.warning("Missing required fields for ROIC calculation")
            return None

        # Handle missing interest expense (assume 0)
        # LIMITATION: May understate ROIC for leveraged companies
        if interest_expense is None:
            logger.warning("Interest expense missing, assuming 0 (ROIC may be understated)")
            interest_expense = pd.Series(0, index=net_income.index)

        # Handle missing cash (assume 0)
        if cash is None:
            logger.warning("Cash missing, assuming 0")
            cash = pd.Series(0, index=equity.index)

        # Align series
        net_income = net_income.tail(years)
        interest_expense = interest_expense.tail(years)
        debt = debt.tail(years)
        equity = equity.tail(years)
        cash = cash.tail(years)

        # Calculate NOPAT
        nopat = net_income + interest_expense * (1 - tax_rate)

        # Calculate Invested Capital
        invested_capital = debt + equity - cash

        # ROIC
        roic = nopat / invested_capital
        return float(roic.mean())

    def _get_field(self, statement: pd.DataFrame, field_name: str, mapping_dict: dict) -> Optional[pd.Series]:
        """Get field using mapper or direct access.

        RESEARCH NEEDED: Determine if EdgarTools normalizes tags.
        """
        if self.mapper:
            return self.mapper.get_field(statement, field_name, mapping_dict)
        else:
            # Assume EdgarTools normalizes tags
            # TODO: Test this assumption
            return statement.get(field_name)

    def calculate_all_metrics(self, income_stmt: pd.DataFrame,
                              balance_sheet: pd.DataFrame) -> Dict[str, Optional[float]]:
        """Calculate all screening metrics.

        Returns dict with metrics, may contain None for failed calculations.

        LIMITATIONS:
        - Foreign filers (IFRS): May use different tag names, need fallback
        - REITs: Use FFO instead of net income, need special handling
        - Banks: Different balance sheet structure, need special handling
        - Recent IPOs: <10Y data, CAGR calculation fails
        """
        return {
            'revenue_cagr_10y': self.calculate_revenue_cagr(income_stmt, years=10),
            'operating_margin_3y': self.calculate_avg_margin(income_stmt, 'operating', years=3),
            'net_margin_3y': self.calculate_avg_margin(income_stmt, 'net', years=3),
            'roe_3y': self.calculate_avg_roe(income_stmt, balance_sheet, years=3),
            'roa_3y': self.calculate_avg_roa(income_stmt, balance_sheet, years=3),
            'roic_3y': self.calculate_avg_roic(income_stmt, balance_sheet, years=3),
            'debt_to_equity': self.calculate_debt_to_equity(balance_sheet),
            'current_ratio': self.calculate_current_ratio(balance_sheet)
        }

    # Additional methods (calculate_avg_margin, calculate_avg_roe, etc.) omitted for brevity
    # See original implementation plan for full code
```

#### 3.1.4 Screening Config

**File**: `src/config/screening.py`

```python
"""Configurable screening criteria."""

from dataclasses import dataclass

@dataclass
class ScreeningConfig:
    """Screening criteria configuration.

    Replaces hardcoded thresholds with configurable values.
    """

    # Growth metrics
    MIN_REVENUE_CAGR_10Y: float = 0.08      # 8%
    MIN_REVENUE_CAGR_5Y: float = 0.10       # 10%

    # Profitability
    MIN_OPERATING_MARGIN: float = 0.10      # 10%
    MIN_NET_MARGIN: float = 0.05            # 5%
    MIN_ROE: float = 0.15                   # 15%
    MIN_ROA: float = 0.05                   # 5%
    MIN_ROIC: float = 0.12                  # 12%

    # Financial health
    MAX_DEBT_TO_EQUITY: float = 0.5         # 0.5
    MIN_CURRENT_RATIO: float = 1.0          # 1.0

    # Quality
    MIN_METRICS_REQUIRED: int = 6           # At least 6 of 8 metrics


# Sector-specific configs
SECTOR_CONFIGS = {
    'Technology': ScreeningConfig(
        MIN_REVENUE_CAGR_10Y=0.15,  # Higher growth
        MIN_OPERATING_MARGIN=0.20,   # Higher margins
        MAX_DEBT_TO_EQUITY=0.3       # Lower leverage
    ),
    'Utilities': ScreeningConfig(
        MIN_REVENUE_CAGR_10Y=0.03,  # Lower growth
        MIN_OPERATING_MARGIN=0.10,   # Moderate margins
        MAX_DEBT_TO_EQUITY=1.5       # Higher leverage OK
    )
}
```

#### 3.1.5 Main Screener

**File**: `src/data_collector/screener.py`

```python
"""Main screening orchestrator using EdgarTools (Tier 0)."""

import logging
from typing import List, Dict
from .edgar_screening_client import EdgarScreeningClient
from .metrics_calculator import MetricsCalculator
from .validators import DataValidator
from src.config.screening import ScreeningConfig

logger = logging.getLogger(__name__)

class EdgarToolsScreener:
    """Screen companies using SEC EDGAR data via EdgarTools (Tier 0 only)."""

    def __init__(self, user_email: str, config: ScreeningConfig = None):
        """Initialize screener.

        Args:
            user_email: Email for SEC identity requirement
            config: Screening criteria config (default: ScreeningConfig())
        """
        self.client = EdgarScreeningClient(user_email, rate_limit='NORMAL')
        self.calculator = MetricsCalculator()
        self.validator = DataValidator()
        self.config = config or ScreeningConfig()

    def screen_company(self, ticker: str) -> Dict:
        """Screen a single company (Tier 0 only, 95% quality).

        Returns:
            Dict with ticker, metrics, and pass/fail status

        Note:
            - Uses EdgarTools Tier 0 only (fast, 95% quality)
            - Deep analysis (post-Gate 1) uses multi-tier (98.55%)
        """
        try:
            # Query SEC EDGAR on-demand (Tier 0)
            financials = self.client.get_financials(ticker)

            if not financials:
                return {
                    'ticker': ticker,
                    'status': 'failed',
                    'reason': 'No financials available'
                }

            # Calculate metrics
            metrics = self.calculator.calculate_all_metrics(
                financials['income'],
                financials['balance']
            )

            # Validate data quality
            is_valid, errors = self.validator.validate_quality(metrics)

            if not is_valid:
                return {
                    'ticker': ticker,
                    'status': 'failed',
                    'reason': f"Data quality: {', '.join(errors)}",
                    'metrics': metrics
                }

            # Apply screening criteria (configurable)
            passes_screen = self._apply_criteria(metrics)

            return {
                'ticker': ticker,
                'status': 'passed' if passes_screen else 'filtered',
                'metrics': metrics
            }

        except Exception as e:
            logger.error(f"Error screening {ticker}: {e}")
            return {
                'ticker': ticker,
                'status': 'error',
                'reason': str(e)
            }

    def _apply_criteria(self, metrics: Dict) -> bool:
        """Apply screening criteria using config.

        Args:
            metrics: Calculated metrics dict

        Returns:
            True if meets criteria threshold
        """
        criteria = [
            metrics.get('revenue_cagr_10y', 0) >= self.config.MIN_REVENUE_CAGR_10Y,
            metrics.get('operating_margin_3y', 0) >= self.config.MIN_OPERATING_MARGIN,
            metrics.get('net_margin_3y', 0) >= self.config.MIN_NET_MARGIN,
            metrics.get('roe_3y', 0) >= self.config.MIN_ROE,
            metrics.get('roa_3y', 0) >= self.config.MIN_ROA,
            metrics.get('roic_3y', 0) >= self.config.MIN_ROIC,
            metrics.get('debt_to_equity', 999) <= self.config.MAX_DEBT_TO_EQUITY,
            metrics.get('current_ratio', 0) >= self.config.MIN_CURRENT_RATIO
        ]

        # Pass if meets threshold (configurable)
        return sum(criteria) >= self.config.MIN_METRICS_REQUIRED

    def screen_universe(self, tickers: List[str]) -> Dict:
        """Screen entire universe of companies.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict with 'passed', 'filtered', 'failed', 'errors' lists
        """
        results = {
            'passed': [],
            'filtered': [],
            'failed': [],
            'errors': []
        }

        logger.info(f"Screening {len(tickers)} companies...")

        for i, ticker in enumerate(tickers, 1):
            if i % 50 == 0:
                logger.info(f"Progress: {i}/{len(tickers)} companies")

            result = self.screen_company(ticker)

            if result['status'] == 'passed':
                results['passed'].append(result)
            elif result['status'] == 'filtered':
                results['filtered'].append(result)
            elif result['status'] == 'failed':
                results['failed'].append(result)
            else:  # error
                results['errors'].append(result)

        logger.info(f"Screening complete: {len(results['passed'])} passed, "
                   f"{len(results['filtered'])} filtered, "
                   f"{len(results['failed'])} failed, "
                   f"{len(results['errors'])} errors")

        return results
```

### Phase 2: S&P 500 Integration

#### 3.2.1 S&P 500 Ticker Loader (FIXED: Use SPY API)

**File**: `src/data_collector/sp500_loader.py`

```python
"""Load S&P 500 ticker list from reliable source."""

import pandas as pd
from typing import List
import logging
import httpx

logger = logging.getLogger(__name__)

def get_sp500_tickers(use_spy_api: bool = True,
                     fallback_file: str = 'data/static/sp500_tickers.csv') -> List[str]:
    """Get S&P 500 ticker list from State Street SPY holdings API.

    Args:
        use_spy_api: Fetch from State Street SPDR S&P 500 ETF holdings (reliable)
        fallback_file: Static CSV file as fallback

    Returns:
        List of ticker symbols

    Note:
        - SPY holdings API is more reliable than Wikipedia scraping
        - Wikipedia HTML structure changes break scrapers
        - SPY holdings are official S&P 500 constituents
    """
    if use_spy_api:
        try:
            # State Street SPY holdings endpoint
            url = 'https://www.ssga.com/us/en/intermediary/etfs/library-content/products/fund-data/etfs/us/holdings-daily-us-en-spy.xlsx'

            # Download holdings file
            response = httpx.get(url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()

            # Parse Excel file
            df = pd.read_excel(response.content, sheet_name=0, skiprows=4)
            tickers = df['Ticker'].dropna().tolist()

            logger.info(f"Loaded {len(tickers)} S&P 500 tickers from SPY holdings")

            # Save to fallback file
            pd.DataFrame({'ticker': tickers}).to_csv(fallback_file, index=False)

            return tickers

        except Exception as e:
            logger.warning(f"Failed to load from SPY API: {e}. Using fallback file.")

    # Fallback: Read from static file
    df = pd.read_csv(fallback_file)
    tickers = df['ticker'].tolist()
    logger.info(f"Loaded {len(tickers)} S&P 500 tickers from {fallback_file}")
    return tickers
```

---

## 4. Technical Specifications

### 4.1 Performance Characteristics

**Note**: Time estimates removed per user request. Performance depends on:

- Network latency to SEC servers
- SEC EDGAR API load (varies by time of day)
- Rate limiting (8-9 req/sec)
- Metric calculation complexity
- Database insert performance

**API Calls**:

- ~500 companies × 1 call per company = 500 API calls
- Rate limit: 8-9 req/sec (NORMAL mode)

**Memory Usage**: ~500MB (financial data in pandas DataFrames)

### 4.2 Rate Limiting

**SEC EDGAR Rate Limit**: 10 requests/second (IP-based)

- Enforcement: 10-minute IP block if exceeded
- EdgarTools modes:
  - **NORMAL**: Production use (~8-9 req/sec, safe margin)
  - **CAUTION**: Conservative (~5 req/sec, use if hitting rate limits)
  - **CRAWL**: Bulk processing (~1 req/sec, for large backlogs)

**Setting rate mode**:

```python
from edgar import set_rate_limit

set_rate_limit('NORMAL')  # Production: 8-9 req/sec (safe)
```

**Why 8-9 req/sec instead of 10**:

- Leaves margin for retries
- Avoids IP blocks from slight timing variations
- Safer for production use

### 4.3 Caching Strategy - See Section 6

---

## 5. Checkpoint System

**Integration with DD-011**: The screening process is divided into 4 checkpointed subtasks to enable fast recovery on failure.

### 5.1 Checkpoint Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                  Checkpoint Manager                          │
├─────────────────────────────────────────────────────────────┤
│  Storage: PostgreSQL (durable) + Redis (fast recovery)      │
│  TTL: 7 days                                                 │
└─────────────────────────────────────────────────────────────┘

Checkpointed Subtasks:

1. data_fetch (Deliverable: Raw financial data for 500 companies)
   ├─ Query EdgarTools for each ticker
   ├─ Store raw DataFrames
   └─ Checkpoint: Raw data → PostgreSQL

2. metric_calculation (Deliverable: Calculated metrics for 500 companies)
   ├─ Calculate CAGR, margins, ratios
   ├─ Store calculated metrics
   └─ Checkpoint: Metrics → PostgreSQL

3. screening_filter (Deliverable: Filtered candidate list ~30-50 companies)
   ├─ Apply screening criteria
   ├─ Filter by thresholds
   └─ Checkpoint: Candidate list → PostgreSQL

4. candidate_ranking (Deliverable: Ranked top 10-20 candidates)
   ├─ Query historical context
   ├─ Apply pattern adjustments
   ├─ Rank by composite score
   └─ Checkpoint: Rankings → Neo4j + Message queue
```

### 5.2 Checkpoint Storage Schema

**PostgreSQL Table**: `workflow.screening_checkpoints`

```sql
CREATE TABLE workflow.screening_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL,                     -- Screening run identifier
    subtask_name VARCHAR(50) NOT NULL,         -- data_fetch, metric_calculation, etc.
    status VARCHAR(20) NOT NULL,               -- pending, in_progress, completed, failed
    checkpoint_data JSONB,                     -- Serialized intermediate results
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    UNIQUE(run_id, subtask_name)
);

CREATE INDEX idx_checkpoint_run_id ON workflow.screening_checkpoints(run_id);
CREATE INDEX idx_checkpoint_status ON workflow.screening_checkpoints(status);
```

**Redis Keys** (fast recovery):

```python
# Key: checkpoint:{run_id}:{subtask_name}
# Value: JSON serialized checkpoint data
# TTL: 604800 seconds (7 days)

# Example: checkpoint:abc123:data_fetch → {"status": "completed", "data": {...}}
```

### 5.3 Checkpoint Implementation

**File**: `src/data_collector/checkpoint_manager.py`

```python
"""Checkpoint manager for screening process (DD-011 integration)."""

import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID
import redis.asyncio as redis
from src.storage.postgres_client import PostgresClient

logger = logging.getLogger(__name__)

class CheckpointManager:
    """Manage checkpoints for screening pipeline."""

    def __init__(self, postgres: PostgresClient, redis_client: redis.Redis):
        """Initialize checkpoint manager.

        Args:
            postgres: PostgreSQL client
            redis_client: Redis client for fast recovery
        """
        self.postgres = postgres
        self.redis = redis_client

    async def save_checkpoint(
        self,
        run_id: UUID,
        subtask_name: str,
        status: str,
        checkpoint_data: Dict[str, Any]
    ) -> None:
        """Save checkpoint to PostgreSQL and Redis.

        Args:
            run_id: Screening run identifier
            subtask_name: Name of subtask (data_fetch, metric_calculation, etc.)
            status: Subtask status (in_progress, completed, failed)
            checkpoint_data: Serialized intermediate results
        """
        # Save to PostgreSQL (durable)
        async with self.postgres.session() as session:
            await session.execute(
                """
                INSERT INTO workflow.screening_checkpoints (
                    run_id, subtask_name, status, checkpoint_data, completed_at
                )
                VALUES (:run_id, :subtask_name, :status, :data, NOW())
                ON CONFLICT (run_id, subtask_name) DO UPDATE SET
                    status = EXCLUDED.status,
                    checkpoint_data = EXCLUDED.checkpoint_data,
                    completed_at = NOW()
                """,
                {
                    'run_id': str(run_id),
                    'subtask_name': subtask_name,
                    'status': status,
                    'data': json.dumps(checkpoint_data)
                }
            )

        # Save to Redis (fast recovery)
        redis_key = f"checkpoint:{run_id}:{subtask_name}"
        await self.redis.set(
            redis_key,
            json.dumps({'status': status, 'data': checkpoint_data}),
            ex=604800  # 7 day TTL
        )

        logger.info(f"Checkpoint saved: {run_id} / {subtask_name} ({status})")

    async def load_checkpoint(
        self,
        run_id: UUID,
        subtask_name: str
    ) -> Optional[Dict[str, Any]]:
        """Load checkpoint from Redis (fast) or PostgreSQL (fallback).

        Args:
            run_id: Screening run identifier
            subtask_name: Name of subtask

        Returns:
            Checkpoint data dict or None if not found
        """
        # Try Redis first (fast recovery)
        redis_key = f"checkpoint:{run_id}:{subtask_name}"
        cached = await self.redis.get(redis_key)

        if cached:
            logger.info(f"Checkpoint loaded from Redis: {run_id} / {subtask_name}")
            return json.loads(cached)

        # Fallback to PostgreSQL
        async with self.postgres.session() as session:
            result = await session.execute(
                """
                SELECT status, checkpoint_data
                FROM workflow.screening_checkpoints
                WHERE run_id = :run_id AND subtask_name = :subtask_name
                """,
                {'run_id': str(run_id), 'subtask_name': subtask_name}
            )
            row = result.fetchone()

            if row:
                logger.info(f"Checkpoint loaded from PostgreSQL: {run_id} / {subtask_name}")
                return {'status': row.status, 'data': json.loads(row.checkpoint_data)}

        logger.warning(f"No checkpoint found: {run_id} / {subtask_name}")
        return None

    async def get_run_status(self, run_id: UUID) -> Dict[str, str]:
        """Get status of all subtasks for a screening run.

        Args:
            run_id: Screening run identifier

        Returns:
            Dict mapping subtask_name → status
        """
        async with self.postgres.session() as session:
            result = await session.execute(
                """
                SELECT subtask_name, status
                FROM workflow.screening_checkpoints
                WHERE run_id = :run_id
                ORDER BY created_at
                """,
                {'run_id': str(run_id)}
            )
            return {row.subtask_name: row.status for row in result.fetchall()}
```

### 5.4 Recovery Workflow

**Example Recovery Scenario**:

```text
Screening Run #47:
  ✅ data_fetch (completed, 500 companies fetched)
  ✅ metric_calculation (completed, 500 metrics calculated)
  ❌ screening_filter (failed at 60%, database timeout)

[Checkpoint restore triggered]
  ↳ Load checkpoint from Redis (subtask: metric_calculation)
  ↳ Resume at screening_filter subtask
  ↳ No re-fetch or re-calculation required
  ↳ Fast recovery (vs full restart)
```

---

## 6. Caching Strategy

**Added per user request**: Clarify when to use bulk cache vs HTTP cache.

### 6.1 HTTP Cache (Auto, Default)

**How it works**:

- EdgarTools caches HTTP responses in memory
- TTL: 10 minutes (configurable)
- Automatic (no setup required)
- Cleared on process restart

**When to use**:

- Ad-hoc screening (one-time queries)
- Development/testing
- Exploring different screening criteria
- Low frequency (weekly or less)

**Pros**:

- Zero setup
- No disk space usage
- Fast for repeated queries within 10 min

**Cons**:

- Cache expires quickly (10 min TTL)
- Cleared on restart
- Not shared across processes

### 6.2 Bulk Cache (Optional, Persistent)

**How it works**:

```python
from edgar import download_edgar_data, use_local_storage

# One-time: Download ~2.6GB
download_edgar_data()

# Enable local cache (~/.edgar/)
use_local_storage()
```

**When to use**:

- Daily/weekly screening runs
- High frequency access
- Offline analysis
- Experimenting with different criteria
- Multiple screening runs per day

**Pros**:

- Persistent across restarts
- Shared across processes
- Much faster repeated queries
- Offline capability

**Cons**:

- ~2.6GB disk space
- One-time download overhead
- Requires periodic refresh (filings update)

### 6.3 Decision Matrix

| Use Case                    | Recommended Cache | Rationale                           |
| --------------------------- | ----------------- | ----------------------------------- |
| Daily screening (automated) | Bulk cache        | High reuse, persistent              |
| Weekly screening            | HTTP cache        | Low frequency, minimal setup        |
| Development/testing         | HTTP cache        | Fast iteration, no storage overhead |
| Criteria experimentation    | Bulk cache        | Multiple runs, same data            |
| Ad-hoc analysis             | HTTP cache        | One-time query                      |
| Offline analysis            | Bulk cache        | No network required                 |

### 6.4 Cache Refresh Strategy

**Bulk Cache Refresh**:

- Frequency: Weekly (filings update Mon-Fri)
- Method: Re-run `download_edgar_data()` to get latest filings
- Timing: Weekend (lower SEC load)

**HTTP Cache Management**:

- No manual refresh needed (auto-expires after 10 min)
- Increase TTL if needed: (EdgarTools config option)

---

## 7. Testing Strategy

**Enhanced per user request**: Add comprehensive edge case tests.

### 7.1 Unit Tests

**Coverage Target**: >80%

**Test Files**:

- `tests/data_collector/test_edgar_screening_client.py` - EdgarTools wrapper
- `tests/data_collector/test_field_mapper.py` - XBRL tag mapping (RESEARCH: may be redundant)
- `tests/data_collector/test_metrics_calculator.py` - Ratio calculations
- `tests/data_collector/test_screener.py` - Main screening logic
- `tests/data_collector/test_checkpoint_manager.py` - Checkpoint save/restore
- `tests/config/test_screening_config.py` - Config validation

**Example Test** (`test_metrics_calculator.py`):

```python
import pytest
import pandas as pd
from src.data_collector.metrics_calculator import MetricsCalculator

def test_revenue_cagr():
    """Test revenue CAGR calculation."""
    # Mock income statement
    income = pd.DataFrame({
        'Revenues': [100, 110, 121, 133, 146, 161, 177, 195, 214, 236, 259]
    })

    calc = MetricsCalculator()
    cagr = calc.calculate_revenue_cagr(income, years=10)

    assert abs(cagr - 0.10) < 0.01  # ~10% CAGR

def test_roic_missing_interest_expense():
    """Test ROIC calculation when interest_expense is missing.

    LIMITATION: Should assume 0 and log warning.
    """
    income = pd.DataFrame({
        'NetIncomeLoss': [100, 110, 121]
        # No InterestExpense field
    })
    balance = pd.DataFrame({
        'StockholdersEquity': [500, 550, 605],
        'DebtCurrent': [100, 105, 110],
        'Cash': [50, 55, 60]
    })

    calc = MetricsCalculator()
    roic = calc.calculate_avg_roic(income, balance, years=3)

    assert roic is not None  # Should succeed with warning
    # ROIC will be understated due to missing interest expense
```

### 7.2 Integration Tests

**Test Files**:

- `tests/integration/test_edgar_screening_flow.py` - End-to-end screening
- `tests/integration/test_checkpoint_recovery.py` - Checkpoint save/restore
- `tests/integration/test_foreign_filers.py` - IFRS companies (20-F)
- `tests/integration/test_special_companies.py` - REITs, banks, SPACs

**Example Test** (`test_foreign_filers.py`):

```python
import pytest
from src.data_collector.screener import EdgarToolsScreener

@pytest.mark.integration
@pytest.mark.skip(reason="RESEARCH NEEDED: EdgarTools IFRS support unknown")
def test_foreign_filer_ifrs():
    """Test screening foreign filer with IFRS (20-F).

    Example: ARM Holdings (ARM) - UK company, IFRS accounting

    RESEARCH NEEDED:
    - Does EdgarTools handle 20-F filings?
    - Are IFRS tags normalized to US-GAAP equivalents?
    - If not, need fallback handling
    """
    screener = EdgarToolsScreener(user_email="test@example.com")
    result = screener.screen_company("ARM")

    # Expected: Either succeeds or fails gracefully
    assert result['status'] in ['passed', 'filtered', 'failed']

    if result['status'] == 'failed':
        # Document why it failed
        assert 'IFRS' in result['reason'] or 'foreign filer' in result['reason']
```

**Example Test** (`test_special_companies.py`):

```python
import pytest
from src.data_collector.screener import EdgarToolsScreener

@pytest.mark.integration
@pytest.mark.skip(reason="FALLBACK NEEDED: REITs use FFO instead of net income")
def test_reit_company():
    """Test screening REIT (uses FFO instead of net income).

    Example: American Tower (AMT) - REIT

    FALLBACK NEEDED:
    - REITs report FFO (Funds From Operations) instead of net income
    - Need to use FFO for ROE/ROA/ROIC calculations
    - Currently will fail or produce incorrect metrics
    """
    screener = EdgarToolsScreener(user_email="test@example.com")
    result = screener.screen_company("AMT")

    # Currently may fail or give wrong metrics
    # TODO: Add REIT-specific metric calculations

@pytest.mark.integration
@pytest.mark.skip(reason="FALLBACK NEEDED: Banks have different balance sheet structure")
def test_bank_company():
    """Test screening bank (different balance sheet structure).

    Example: JPMorgan Chase (JPM) - Bank

    FALLBACK NEEDED:
    - Banks use different balance sheet structure
    - Assets = Loans + Securities + Cash (not standard current/non-current)
    - Liabilities = Deposits + Borrowings (not standard structure)
    - May need bank-specific field mapping
    """
    screener = EdgarToolsScreener(user_email="test@example.com")
    result = screener.screen_company("JPM")

    # Currently may fail or give wrong metrics
    # TODO: Add bank-specific field mapping

@pytest.mark.integration
def test_recent_ipo_insufficient_history():
    """Test screening recent IPO (<10Y history).

    LIMITATION: 10Y CAGR calculation will fail.
    Should handle gracefully.
    """
    screener = EdgarToolsScreener(user_email="test@example.com")

    # Example: Company with <10Y public history
    # (Replace with actual recent IPO ticker)
    result = screener.screen_company("RECENT_IPO_TICKER")

    # Expected: revenue_cagr_10y will be None
    if result['status'] in ['passed', 'filtered']:
        assert result['metrics']['revenue_cagr_10y'] is None
        # Should still pass if other metrics meet criteria
```

### 7.3 Performance Tests

```python
@pytest.mark.slow
def test_sp500_screening_performance():
    """Verify S&P 500 screening completes without timeout.

    Note: Time estimates removed per user request.
    Test validates successful completion, not duration.
    """
    screener = EdgarToolsScreener(user_email="test@example.com")
    tickers = get_sp500_tickers()  # ~500 companies

    results = screener.screen_universe(tickers)

    # Validate completion
    total = (len(results['passed']) + len(results['filtered']) +
             len(results['failed']) + len(results['errors']))
    assert total == len(tickers)

    # Validate quality (>90% success rate expected)
    success_rate = (len(results['passed']) + len(results['filtered'])) / len(tickers)
    assert success_rate > 0.90  # At least 90% should succeed

@pytest.mark.slow
def test_checkpoint_recovery():
    """Verify checkpoint recovery works after simulated failure."""
    from uuid import uuid4
    import asyncio

    run_id = uuid4()
    screener = EdgarToolsScreener(user_email="test@example.com")

    # Run first 2 subtasks
    tickers = get_sp500_tickers()[:100]  # Test subset

    # Simulate failure after metric_calculation
    # (implementation details depend on checkpoint manager)

    # Attempt recovery
    # Should resume from screening_filter subtask
    # (test implementation TBD)
```

---

## 8. Open Research Questions

**Document issues requiring further research/testing**:

### 8.1 EdgarTools Field Normalization ~~(HIGH PRIORITY)~~ ✅ **RESOLVED**

**Status**: ✅ **COMPLETE** (2025-11-24)

**Question**: Does EdgarTools normalize US-GAAP XBRL tags to standard field names (`.revenue`, `.net_income`, etc.)?

**Why it matters**: Determines if `FieldMapper` is needed (200+ lines of code)

**Answer**: **YES** - EdgarTools provides built-in getter methods that handle normalization internally!

**Test Results**:

- Tested 10 S&P 500 companies (AAPL, MSFT, JPM, JNJ, XOM, WMT, PG, UNH, HD, V)
- 100% success rate
- Getter methods: `get_revenue()`, `get_net_income()`, `get_total_assets()`, etc.
- Returns latest value as float (perfect for screening)

**Decision**:

- ❌ **Skip FieldMapper for MVP** (saves 200+ lines of code)
- ✅ **Use EdgarTools getter methods** for all basic screening metrics
- 📝 **Optional**: Add lightweight mapper only if advanced metrics needed

**Findings**: See `research/FINDINGS_EdgarTools_Field_Normalization.md`

**Blocking**: ~~No~~ **RESOLVED** - Field mapper not needed

---

### 8.2 EdgarTools Built-in Ratio/Trend Methods (HIGH PRIORITY - NEW)

**Status**: 🔬 **RESEARCH NEEDED**

**Question**: Does EdgarTools provide built-in methods for ratio calculations and trend analysis that we can use instead of building custom metrics calculator?

**Why it matters**: Could eliminate 300+ lines of custom metric calculation code

**Discovered Methods** (from initial testing):

- `financials.get_financial_metrics()` - Returns multiple metrics at once
- `statement.calculate_ratios()` - Built-in ratio calculations
- `statement.analyze_trends()` - Built-in trend analysis

**Research Tasks**:

1. **Test `get_financial_metrics()`**:

   ```python
   financials = company.get_financials()
   metrics = financials.get_financial_metrics()

   # Questions:
   # - What metrics are included? (ROE, ROA, margins, etc.?)
   # - What format is returned? (dict, DataFrame, custom object?)
   # - Are these latest values or time series?
   # - Coverage: Does it include all screening metrics needed?
   ```

2. **Test `calculate_ratios()`**:

   ```python
   income_stmt = financials.income_statement()
   ratios = income_stmt.calculate_ratios()

   # Questions:
   # - What ratios are calculated? (profitability, liquidity, leverage?)
   # - Can we specify which ratios to calculate?
   # - Does it handle missing data gracefully?
   # - Are ratios calculated per period (time series)?
   ```

3. **Test `analyze_trends()`**:

   ```python
   income_stmt = financials.income_statement()
   trends = income_stmt.analyze_trends()

   # Questions:
   # - Does this calculate CAGR automatically?
   # - What periods does it cover? (3Y, 5Y, 10Y?)
   # - What trends are analyzed? (revenue growth, margin trends?)
   # - Can we customize the analysis period?
   ```

4. **Coverage Analysis**:
   - Map screening metrics (from plan) to available methods
   - Identify gaps (metrics not provided by built-in methods)
   - Determine if custom calculator still needed (and for what)

**Screening Metrics Needed** (from plan):

- Revenue CAGR (10Y, 5Y) ← Does `analyze_trends()` provide this?
- Operating/Net Margins (3Y avg) ← Does `calculate_ratios()` provide this?
- ROE/ROA/ROIC (3Y avg) ← Does `get_financial_metrics()` provide this?
- Debt ratios (Debt/Equity, Net Debt/EBITDA)
- Liquidity (Current Ratio, Quick Ratio)

**Impact**:

- If built-in methods cover 80%+ of needs: **Simplify MetricsCalculator dramatically**
- If coverage <50%: **Build custom calculator as planned**
- If coverage 50-80%: **Hybrid approach** (use built-in + custom for gaps)

**Test Plan**:

1. Create test script: `research/test_builtin_metrics.py`
2. Test on 5 companies (different sectors)
3. Document all available metrics/ratios/trends
4. Map to screening requirements
5. Decide implementation approach

**Blocking**: No - can proceed with custom calculator, optimize later if built-in methods sufficient

---

### 8.3 Time Series Data Extraction for CAGR (HIGH PRIORITY - NEW)

**Status**: 🔬 **RESEARCH NEEDED**

**Question**: What's the best approach to extract multi-year time series data for CAGR and average calculations?

**Why it matters**: Critical for screening metrics (10Y revenue CAGR, 3Y average margins)

**Known Approach** (from initial testing):

```python
income_stmt = financials.income_statement()
df = income_stmt.to_dataframe()

# DataFrame structure:
# - Columns: ['concept', 'label', '2025-09-27', '2024-09-28', '2023-09-30', ...]
# - Rows: XBRL line items

# Extract revenue time series (COMPLEX):
revenue_rows = df[df['concept'] == 'us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax']
date_cols = [c for c in df.columns if c not in ['concept', 'label', ...]]
revenue_values = revenue_rows[date_cols].iloc[0]
```

**Research Tasks**:

1. **Identify XBRL Concept Tag Variations**:

   - Test 10 companies (different sectors): Do they all use same revenue tag?
   - Document variations:
     - Revenue: `us-gaap_Revenues` vs `us-gaap_RevenueFromContract...`?
     - Net Income: `us-gaap_NetIncomeLoss` vs variations?
     - Operating Income: Tag consistency?
   - Build mapping if needed (lightweight FieldMapper for concepts only)

2. **Date Column Extraction**:

   - Identify metadata columns to exclude (consistent across companies?)
   - Extract date columns reliably (regex pattern? column type check?)
   - Handle different fiscal year ends (some companies report quarterly)
   - Sort date columns chronologically (string sort may not work)

3. **Historical Data Availability**:

   - How many years of history are available? (10Y needed for CAGR)
   - Recent IPOs: Handle gracefully if <10Y history?
   - Restatements: Do historical values change in latest filing?

4. **Alternative Approaches**:
   - Option A: Use `statement.analyze_trends()` (if it provides CAGR)
   - Option B: Manual DataFrame extraction (current approach)
   - Option C: Query multiple filings (10-K from each year) for historical data
   - Which is most reliable?

**Test Plan**:

1. Create test script: `research/test_time_series_extraction.py`
2. Test on 10 companies:
   - 3 tech companies (AAPL, MSFT, GOOGL)
   - 2 banks (JPM, BAC) - different structure?
   - 2 consumer (WMT, PG)
   - 1 energy (XOM)
   - 1 healthcare (JNJ)
   - 1 recent IPO (<10Y history)
3. Document:
   - XBRL concept tag variations
   - Date column patterns
   - Historical data availability
   - Edge cases (missing data, IPOs, restatements)
4. Recommend best practice approach

**Impact**:

- If `analyze_trends()` works: **No custom time series extraction needed**
- If tags consistent: **Simple concept filtering** (no FieldMapper)
- If tags vary: **Lightweight concept mapper** (50 lines vs 200)

**Blocking**: No - can use fallback approach (query latest filing, may have <10Y history)

---

### 8.4 Foreign Filer / IFRS Support (MEDIUM PRIORITY)

**Question**: Does EdgarTools handle 20-F filings (foreign companies using IFRS) correctly?

**Why it matters**: ~10% of S&P 500 are foreign filers (e.g., ARM, SAP, etc.)

**Known examples**:

- ARM Holdings (ARM) - UK company, IFRS
- SAP SE (SAP) - German company, IFRS
- Linde plc (LIN) - Irish company, IFRS

**Test plan**:

1. Query 5-10 foreign filers via EdgarTools
2. Check if financials are returned
3. Check if IFRS tags map to US-GAAP equivalents
4. Measure success rate

**Fallback options**:

- Skip foreign filers (document as limitation)
- Use alternative parser for 20-F filings
- Manual tag mapping for common IFRS tags

**Impact**:

- If not supported: ~10% of S&P 500 will fail screening
- Acceptable for MVP if documented

**Blocking**: No - can document as limitation, add fallback later

---

### 8.3 Special Company Types (MEDIUM PRIORITY)

**Status**: 🔬 **RESEARCH NEEDED**

**Question**: How to handle REITs, banks, and other special accounting structures?

**Why it matters**: ~10% of S&P 500 have non-standard accounting (may cause incorrect metrics or failures)

**Company Types & Impact**:

| Type        | % of S&P 500 | Accounting Issue                  | Impact on Screening Metrics  |
| ----------- | ------------ | --------------------------------- | ---------------------------- |
| REITs       | ~3%          | Use FFO instead of net income     | ROE/ROA/margins incorrect    |
| Banks       | ~5%          | Different balance sheet structure | Liquidity ratios don't apply |
| SPACs       | <1%          | Zero revenue pre-merger           | Will filter out naturally    |
| Holding cos | ~2%          | Consolidated vs parent-only       | Ambiguous data               |

**Research Tasks**:

1. **REIT Handling**:

   - Test 5 REITs (AMT, PLD, EQIX, DLR, PSA)
   - Check if EdgarTools provides FFO (Funds From Operations)
   - Alternative: Calculate FFO = Net Income + Depreciation - Gains on Sales
   - Do getter methods work? (`get_net_income()` on REITs)
   - Document which metrics are valid for REITs

2. **Bank Handling**:

   - Test 5 banks (JPM, BAC, WFC, C, GS)
   - Check balance sheet structure (different from standard companies)
   - Do standard ratios work? (Current Ratio, Quick Ratio don't apply to banks)
   - Alternative metrics: Tier 1 Capital Ratio, Loan/Deposit ratio
   - Can we detect banks programmatically? (SIC code, industry tag)

3. **Detection Strategy**:

   ```python
   # How to identify special company types?
   company = Company(ticker)

   # Option A: Industry/SIC code
   industry = company.industry  # Does EdgarTools provide this?
   sic_code = company.sic       # Standard Industrial Classification

   # Option B: Balance sheet structure analysis
   # Banks: Large "Loans" asset, no "Inventory"
   # REITs: Large "Real Estate" asset

   # Option C: Filing type (10-K vs specialized forms)
   ```

4. **Fallback Strategies**:
   - **REITs**:
     - Use FFO for profitability (if available in filings)
     - Skip net income-based metrics (ROE, ROA)
     - Focus on FFO yield, occupancy rates
   - **Banks**:
     - Skip liquidity ratios (Current Ratio, Quick Ratio)
     - Use bank-specific metrics (NIM, efficiency ratio)
     - Capital adequacy from regulatory filings
   - **SPACs**:
     - Detect via zero revenue + "Acquisition" in name
     - Skip automatically (won't pass screening anyway)

**Test Plan**:

1. Create test script: `research/test_special_company_types.py`
2. Test companies:
   - REITs: AMT, PLD, EQIX, DLR, PSA
   - Banks: JPM, BAC, WFC, C, GS
   - SPACs: Identify 2-3 current SPACs in S&P 500 (rare)
3. For each:
   - Run standard screening metrics
   - Document failures/incorrect values
   - Test detection methods
   - Design fallback approach
4. Decision:
   - MVP: Document as limitation, skip special handling
   - Production: Implement special handlers for REITs/banks

**Impact**:

- If not handled: ~10% of S&P 500 may have incorrect metrics
- **MVP Decision**: Document as limitation (acceptable for initial version)
- **Production**: Add special handling (improves accuracy from 90% → 100%)

**Blocking**: No - can document as MVP limitation, add special handling in Phase 2

---

### 8.4 ROIC Calculation Accuracy (LOW PRIORITY)

**Question**: When `interest_expense` is missing, should we:

- Option A: Assume 0 (current approach, may understate ROIC)
- Option B: Estimate from industry average
- Option C: Skip ROIC calculation (return None)

**Why it matters**: ROIC is a key screening metric, inaccurate values affect results

**Test plan**:

1. Query 100 companies, measure `interest_expense` availability
2. For companies missing it, calculate ROIC with assumption vs. skipping
3. Compare pass/fail rates
4. Validate assumptions against industry benchmarks

**Recommendation**: Start with Option A (assume 0), add warning log. Revisit if pass rate too low.

**Impact**: Low - most companies report interest expense, affects <5%

**Blocking**: No - current approach is reasonable default

---

### 8.5 S&P 500 Composition Changes (LOW PRIORITY)

**Question**: How frequently to refresh S&P 500 ticker list? How to handle ticker changes (e.g., FB → META)?

**Composition changes**:

- Frequency: ~5-10 companies per quarter
- Ticker changes: ~1-2 per year

**Options**:

- Daily refresh (overkill, API overhead)
- Weekly refresh (reasonable)
- Monthly refresh (may miss recent additions)
- Manual refresh (error-prone)

**Recommendation**: Weekly refresh from SPY holdings API, cache to static file

**Ticker change handling**:

- Track in `metadata.sp500_universe` table (already designed)
- Cache in Redis (7 day TTL)
- Fallback to old ticker if new ticker fails

**Impact**: Low - affects <1% of companies per quarter

**Blocking**: No - can start with monthly refresh, optimize later

---

## 9. Troubleshooting

### 9.1 Common Issues

**Issue**: `HTTPError: 429 Too Many Requests`
**Cause**: Exceeded SEC rate limit (10 req/sec)
**Solution**:

```python
from edgar import set_rate_limit
set_rate_limit('CAUTION')  # Reduce to 5 req/sec
```

**Issue**: `KeyError: 'Revenues'` or similar XBRL tag not found
**Cause**: Company uses different XBRL tag variation
**Solution**: Update `FieldMapper` mappings to include variation (if field mapper is needed - RESEARCH)

**Issue**: `NoFinancialsFoundError`
**Cause**: Company has no XBRL filings (foreign filer, recent IPO, etc.)
**Solution**: Expected, skip company (handle in screener)

**Issue**: Foreign filer (IFRS) returns no data
**Cause**: EdgarTools may not support 20-F filings (RESEARCH NEEDED)
**Solution**: Document as limitation, add fallback later

**Issue**: REIT metrics look incorrect
**Cause**: REITs use FFO instead of net income (FALLBACK NEEDED)
**Solution**: Add REIT-specific metric calculations

**Issue**: Checkpoint recovery fails
**Cause**: Checkpoint data corrupted or Redis cache expired
**Solution**: Fallback to PostgreSQL, or restart from beginning if corrupted

---

## Appendices

### A. Field Mapping Reference

**Complete XBRL tag mappings**: See `src/data_collector/field_mapper.py`

**Common variations**:

- Revenue: `Revenues`, `RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueNet`
- Net Income: `NetIncomeLoss`, `ProfitLoss`, `NetIncomeLossAvailableToCommonStockholdersBasic`
- Total Assets: `Assets`, `AssetsAbstract`

**Note**: May be redundant if EdgarTools normalizes tags (RESEARCH NEEDED)

### B. Screening Criteria Recommendations

Based on fundamental analysis best practices:

| Metric             | Conservative | Moderate | Aggressive |
| ------------------ | ------------ | -------- | ---------- |
| Revenue CAGR (10Y) | 5%           | 8%       | 15%        |
| Operating Margin   | 8%           | 10%      | 15%        |
| ROE                | 12%          | 15%      | 20%        |
| ROIC               | 10%          | 12%      | 15%        |
| Debt/Equity        | <0.3         | <0.5     | <0.8       |

### C. Migration Path from Yahoo Finance

**For existing implementations using Yahoo Finance**:

1. Install EdgarTools: `uv add edgartools`
2. Replace `YahooFinanceClient` with `EdgarScreeningClient`
3. Update field access (Yahoo: `stock.financials` → EdgarTools: `company.get_financials()`)
4. Update metric calculations (may need different field names - RESEARCH)
5. Test on 10 companies, validate metrics match
6. Rollout to full S&P 500

**Rollback plan**: Keep Yahoo Finance client as fallback if EdgarTools has issues

---

## Sign-Off

**Prepared by**: System Architect
**Date**: 2025-11-24
**Status**: Ready for Implementation
**Decision Reference**: DD-033

**Next Steps**:

1. ~~**RESEARCH**: Test EdgarTools field normalization (HIGH PRIORITY)~~ ✅ **COMPLETE** (2025-11-24)
   - **Result**: Field mapper NOT needed - EdgarTools provides getter methods
   - **Findings**: See `research/FINDINGS_EdgarTools_Field_Normalization.md`
   - **Decision**: Use `get_revenue()`, `get_net_income()`, etc. (handles XBRL internally)
2. **RESEARCH**: Test EdgarTools IFRS support on foreign filers (MEDIUM PRIORITY)
3. Implement Phase 1 (core components)
4. Test with 10 companies
5. Implement Phase 2 (S&P 500 integration)
6. Run full screening
7. Analyze results, tune criteria
8. **ADD**: Checkpoint system integration (DD-011)
9. **ADD**: Special company type handling (REITs, banks)
10. **ADD**: Comprehensive edge case testing

**Unresolved Questions** (require research/testing):

1. ~~EdgarTools field normalization behavior?~~ ✅ **RESOLVED** (2025-11-24)
2. **EdgarTools built-in ratio/trend methods** (HIGH PRIORITY - NEW)
   - What does `financials.get_financial_metrics()` return?
   - What ratios does `statement.calculate_ratios()` provide?
   - Does `statement.analyze_trends()` calculate CAGR/growth rates?
   - Can we use these instead of custom metrics calculator?
3. **Time series data extraction for CAGR** (HIGH PRIORITY - NEW)
   - How to extract 10-year revenue history from DataFrame?
   - Are XBRL concept tags consistent across companies?
   - Best practice for multi-year metric calculations?
4. EdgarTools IFRS/20-F support? (MEDIUM PRIORITY)
5. REIT/bank special handling strategy? (MEDIUM PRIORITY)
6. ROIC missing data fallback approach? (LOW PRIORITY)
7. S&P 500 refresh frequency? (LOW PRIORITY)
