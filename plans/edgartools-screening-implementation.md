# EdgarTools Screening Implementation Guide

**Project**: Fundamental Analysis System - Data Collector & Screener
**Version**: 1.0
**Date**: 2025-11-23
**Status**: Ready for Implementation
**Decision**: DD-033 (Screening Data Source: EdgarTools)

---

## Executive Summary

Implementation guide for using EdgarTools to screen S&P 500 companies (Days 1-2 of analysis pipeline). Replaces third-party API approach (SimFin, Finnhub) with unified SEC EDGAR data source for both screening and deep analysis.

**Key Benefits**:

- $0 cost (vs $180/year SimFin)
- 2.5-5 min screening time (500 companies)
- Single source of truth (no data consistency issues)
- On-demand queries (no bulk download required)
- Full control & learning capability

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Architecture Overview](#2-architecture-overview)
3. [Implementation Phases](#3-implementation-phases)
4. [Technical Specifications](#4-technical-specifications)
5. [Code Examples](#5-code-examples)
6. [Testing Strategy](#6-testing-strategy)
7. [Performance Optimization](#7-performance-optimization)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Quick Start

### 1.1 Installation

```bash
# EdgarTools already added per DD-031
uv add edgartools pandas python-dotenv

# Verify installation
python -c "from edgar import Company; print('EdgarTools ready')"
```

### 1.2 Basic Screening Example

```python
from edgar import Company, set_identity

# Required by SEC
set_identity("your.name@example.com")

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
from edgar import Company, set_identity

set_identity("your.email@example.com")

sp500 = ['AAPL', 'MSFT', 'GOOGL', ...]  # Full list from Wikipedia

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

**Time**: ~2.5 minutes for 500 companies

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
│              EdgarTools Query Layer                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │   On-Demand API Queries                              │  │
│  │   - Company.get_financials() → SEC EDGAR API        │  │
│  │   - 10 req/sec rate limit (SEC enforced)            │  │
│  │   - Auto HTTP caching (10 min TTL)                  │  │
│  │   - Optional bulk cache (~/.edgar/)                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                Field Mapper                                 │
│  - Map US-GAAP XBRL concepts → Standard names              │
│  - Handle variations (Revenues vs RevenueFromContract...)   │
│  - Normalize field names across companies                   │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Metrics Calculator                             │
│  - Revenue CAGR (10Y)                                       │
│  - Operating/Net Margins (3Y avg)                           │
│  - ROE/ROA/ROIC (3Y avg)                                    │
│  - Debt ratios (Debt/Equity, Net Debt/EBITDA)             │
│  - Liquidity (Current Ratio, Quick Ratio)                   │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           Screening Logic & Validation                      │
│  - Apply quantitative filters                               │
│  - Completeness check (≥5 of 8 metrics)                    │
│  - Quality validation (95%+ threshold)                      │
│  - Output: Filtered candidates for Human Gate 1            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```text
1. Load S&P 500 tickers (Wikipedia or static file)
2. For each ticker:
   a. Query SEC EDGAR API via EdgarTools
   b. Extract financial statements (income, balance, cash flow)
   c. Map XBRL concepts to standard field names
   d. Calculate screening metrics
   e. Apply filtering criteria
   f. Collect candidates
3. Output candidate list for Human Gate 1
```

### 2.3 Module Structure

```text
src/
├── screening/
│   ├── __init__.py
│   ├── screener.py                # Main screening orchestrator
│   ├── field_mapper.py            # US-GAAP → standard names
│   ├── metrics_calculator.py      # Ratio calculations
│   ├── validators.py              # Data quality checks
│   └── sp500_loader.py            # S&P 500 ticker list
├── data_collector/
│   ├── filing_parser.py           # (Already exists per DD-031)
│   └── validation.py              # (Already exists per DD-031)
└── config/
    ├── __init__.py
    └── screening.py               # Screening criteria config
```

---

## 3. Implementation Phases

### Phase 1: Core Components (Days 1-3)

#### 3.1.1 Field Mapper

**File**: `src/screening/field_mapper.py`

```python
"""Map US-GAAP XBRL concepts to standardized field names."""

from typing import Optional
import pandas as pd

class FieldMapper:
    """Handle XBRL concept name variations."""

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
        """
        Extract field from statement, trying all XBRL tag variations.

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

#### 3.1.2 Metrics Calculator

**File**: `src/screening/metrics_calculator.py`

```python
"""Calculate financial ratios and metrics for screening."""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from .field_mapper import FieldMapper

class MetricsCalculator:
    """Calculate screening metrics from EdgarTools financials."""

    def __init__(self):
        self.mapper = FieldMapper()

    def calculate_revenue_cagr(self, income_stmt: pd.DataFrame,
                               years: int = 10) -> Optional[float]:
        """Calculate N-year revenue CAGR."""
        revenue = self.mapper.get_field(
            income_stmt, 'revenue', self.mapper.INCOME_MAPPING
        )

        if revenue is None or len(revenue) < years:
            return None

        revenue = revenue.tail(years)
        start = revenue.iloc[0]
        end = revenue.iloc[-1]

        if start <= 0 or end <= 0:
            return None

        cagr = (end / start) ** (1 / years) - 1
        return float(cagr)

    def calculate_avg_margin(self, income_stmt: pd.DataFrame,
                            margin_type: str = 'operating',
                            years: int = 3) -> Optional[float]:
        """
        Calculate N-year average margin.

        Args:
            income_stmt: Income statement DataFrame
            margin_type: 'operating' or 'net'
            years: Number of years to average

        Returns:
            Average margin as decimal (e.g., 0.15 = 15%)
        """
        revenue = self.mapper.get_field(
            income_stmt, 'revenue', self.mapper.INCOME_MAPPING
        )

        if margin_type == 'operating':
            numerator = self.mapper.get_field(
                income_stmt, 'operating_income', self.mapper.INCOME_MAPPING
            )
        elif margin_type == 'net':
            numerator = self.mapper.get_field(
                income_stmt, 'net_income', self.mapper.INCOME_MAPPING
            )
        else:
            raise ValueError(f"Unknown margin_type: {margin_type}")

        if revenue is None or numerator is None:
            return None

        revenue = revenue.tail(years)
        numerator = numerator.tail(years)

        margin = numerator / revenue
        return float(margin.mean())

    def calculate_avg_roe(self, income_stmt: pd.DataFrame,
                         balance_sheet: pd.DataFrame,
                         years: int = 3) -> Optional[float]:
        """Calculate N-year average ROE."""
        net_income = self.mapper.get_field(
            income_stmt, 'net_income', self.mapper.INCOME_MAPPING
        )
        equity = self.mapper.get_field(
            balance_sheet, 'stockholders_equity', self.mapper.BALANCE_MAPPING
        )

        if net_income is None or equity is None:
            return None

        net_income = net_income.tail(years)
        equity = equity.tail(years)

        roe = net_income / equity
        return float(roe.mean())

    def calculate_avg_roa(self, income_stmt: pd.DataFrame,
                         balance_sheet: pd.DataFrame,
                         years: int = 3) -> Optional[float]:
        """Calculate N-year average ROA."""
        net_income = self.mapper.get_field(
            income_stmt, 'net_income', self.mapper.INCOME_MAPPING
        )
        assets = self.mapper.get_field(
            balance_sheet, 'total_assets', self.mapper.BALANCE_MAPPING
        )

        if net_income is None or assets is None:
            return None

        net_income = net_income.tail(years)
        assets = assets.tail(years)

        roa = net_income / assets
        return float(roa.mean())

    def calculate_avg_roic(self, income_stmt: pd.DataFrame,
                          balance_sheet: pd.DataFrame,
                          years: int = 3,
                          tax_rate: float = 0.21) -> Optional[float]:
        """
        Calculate N-year average ROIC.

        ROIC = NOPAT / Invested Capital
        NOPAT = Net Income + Interest Expense × (1 - Tax Rate)
        Invested Capital = Total Debt + Stockholders' Equity - Cash
        """
        net_income = self.mapper.get_field(
            income_stmt, 'net_income', self.mapper.INCOME_MAPPING
        )
        interest_expense = self.mapper.get_field(
            income_stmt, 'interest_expense', self.mapper.INCOME_MAPPING
        )
        debt = self.mapper.get_field(
            balance_sheet, 'total_debt', self.mapper.BALANCE_MAPPING
        )
        equity = self.mapper.get_field(
            balance_sheet, 'stockholders_equity', self.mapper.BALANCE_MAPPING
        )
        cash = self.mapper.get_field(
            balance_sheet, 'cash', self.mapper.BALANCE_MAPPING
        )

        if None in [net_income, debt, equity]:
            return None

        # Handle missing interest expense (assume 0)
        if interest_expense is None:
            interest_expense = pd.Series(0, index=net_income.index)

        # Handle missing cash (assume 0)
        if cash is None:
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

    def calculate_debt_to_equity(self, balance_sheet: pd.DataFrame) -> Optional[float]:
        """Calculate latest Debt-to-Equity ratio."""
        debt = self.mapper.get_field(
            balance_sheet, 'total_debt', self.mapper.BALANCE_MAPPING
        )
        equity = self.mapper.get_field(
            balance_sheet, 'stockholders_equity', self.mapper.BALANCE_MAPPING
        )

        if debt is None or equity is None:
            return None

        latest_debt = debt.iloc[-1]
        latest_equity = equity.iloc[-1]

        if latest_equity <= 0:
            return None

        return float(latest_debt / latest_equity)

    def calculate_current_ratio(self, balance_sheet: pd.DataFrame) -> Optional[float]:
        """Calculate latest Current Ratio."""
        current_assets = self.mapper.get_field(
            balance_sheet, 'current_assets', self.mapper.BALANCE_MAPPING
        )
        current_liabilities = self.mapper.get_field(
            balance_sheet, 'current_liabilities', self.mapper.BALANCE_MAPPING
        )

        if current_assets is None or current_liabilities is None:
            return None

        latest_ca = current_assets.iloc[-1]
        latest_cl = current_liabilities.iloc[-1]

        if latest_cl <= 0:
            return None

        return float(latest_ca / latest_cl)

    def calculate_all_metrics(self, income_stmt: pd.DataFrame,
                              balance_sheet: pd.DataFrame) -> Dict[str, Optional[float]]:
        """Calculate all screening metrics."""
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
```

#### 3.1.3 Main Screener

**File**: `src/screening/screener.py`

```python
"""Main screening orchestrator using EdgarTools."""

import logging
from typing import List, Dict
from edgar import Company, set_identity
from .metrics_calculator import MetricsCalculator
from .validators import DataValidator

logger = logging.getLogger(__name__)

class EdgarToolsScreener:
    """Screen companies using SEC EDGAR data via EdgarTools."""

    def __init__(self, user_email: str):
        """
        Initialize screener.

        Args:
            user_email: Email for SEC identity requirement
        """
        set_identity(user_email)
        self.calculator = MetricsCalculator()
        self.validator = DataValidator()

    def screen_company(self, ticker: str) -> Dict:
        """
        Screen a single company.

        Returns:
            Dict with ticker, metrics, and pass/fail status
        """
        try:
            # Query SEC EDGAR on-demand
            company = Company(ticker)
            financials = company.get_financials()

            if not financials:
                return {
                    'ticker': ticker,
                    'status': 'failed',
                    'reason': 'No financials available'
                }

            # Calculate metrics
            metrics = self.calculator.calculate_all_metrics(
                financials.income.get_dataframe(),
                financials.balance.get_dataframe()
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

            # Apply screening criteria
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
        """Apply screening criteria."""
        criteria = [
            metrics.get('revenue_cagr_10y', 0) > 0.08,      # 8%+ 10Y CAGR
            metrics.get('operating_margin_3y', 0) > 0.10,   # 10%+ operating margin
            metrics.get('net_margin_3y', 0) > 0.05,         # 5%+ net margin
            metrics.get('roe_3y', 0) > 0.15,                # 15%+ ROE
            metrics.get('roa_3y', 0) > 0.05,                # 5%+ ROA
            metrics.get('roic_3y', 0) > 0.12,               # 12%+ ROIC
            metrics.get('debt_to_equity', 999) < 0.5,       # <0.5 debt/equity
            metrics.get('current_ratio', 0) > 1.0           # >1.0 current ratio
        ]

        # Pass if meets at least 6 of 8 criteria
        return sum(criteria) >= 6

    def screen_universe(self, tickers: List[str]) -> Dict:
        """
        Screen entire universe of companies.

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

### Phase 2: S&P 500 Integration (Day 4)

#### 3.2.1 S&P 500 Ticker Loader

**File**: `src/screening/sp500_loader.py`

```python
"""Load S&P 500 ticker list."""

import pandas as pd
from typing import List
import logging

logger = logging.getLogger(__name__)

def get_sp500_tickers(use_wikipedia: bool = True,
                     fallback_file: str = 'data/static/sp500_tickers.csv') -> List[str]:
    """
    Get S&P 500 ticker list.

    Args:
        use_wikipedia: Fetch from Wikipedia (requires internet)
        fallback_file: Static CSV file as fallback

    Returns:
        List of ticker symbols
    """
    if use_wikipedia:
        try:
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            sp500 = pd.read_html(url)[0]
            tickers = sp500['Symbol'].tolist()
            logger.info(f"Loaded {len(tickers)} S&P 500 tickers from Wikipedia")

            # Save to fallback file
            pd.DataFrame({'ticker': tickers}).to_csv(fallback_file, index=False)

            return tickers
        except Exception as e:
            logger.warning(f"Failed to load from Wikipedia: {e}. Using fallback file.")

    # Fallback: Read from static file
    df = pd.read_csv(fallback_file)
    tickers = df['ticker'].tolist()
    logger.info(f"Loaded {len(tickers)} S&P 500 tickers from {fallback_file}")
    return tickers
```

#### 3.2.2 Main Execution Script

**File**: `scripts/run_screening.py`

```python
"""Run S&P 500 screening."""

import logging
import json
from datetime import datetime
from pathlib import Path
from src.screening.screener import EdgarToolsScreener
from src.screening.sp500_loader import get_sp500_tickers

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    # Configuration
    USER_EMAIL = "your.email@example.com"  # Required by SEC
    OUTPUT_DIR = Path("data/outputs/screening")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load S&P 500 tickers
    tickers = get_sp500_tickers()

    # Run screening
    screener = EdgarToolsScreener(user_email=USER_EMAIL)
    results = screener.screen_universe(tickers)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"screening_results_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    # Summary report
    print(f"\n{'='*60}")
    print(f"SCREENING RESULTS - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")
    print(f"Total screened:   {len(tickers)}")
    print(f"Passed criteria:  {len(results['passed'])} ({len(results['passed'])/len(tickers)*100:.1f}%)")
    print(f"Filtered out:     {len(results['filtered'])} ({len(results['filtered'])/len(tickers)*100:.1f}%)")
    print(f"Data quality fail: {len(results['failed'])} ({len(results['failed'])/len(tickers)*100:.1f}%)")
    print(f"Errors:           {len(results['errors'])} ({len(results['errors'])/len(tickers)*100:.1f}%)")
    print(f"\nTop candidates:")
    for i, result in enumerate(results['passed'][:10], 1):
        ticker = result['ticker']
        metrics = result['metrics']
        print(f"{i:2d}. {ticker:5s} - "
              f"CAGR: {metrics.get('revenue_cagr_10y', 0)*100:5.1f}%, "
              f"ROE: {metrics.get('roe_3y', 0)*100:5.1f}%, "
              f"ROIC: {metrics.get('roic_3y', 0)*100:5.1f}%")
    print(f"\nResults saved to: {output_file}")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()
```

---

## 4. Technical Specifications

### 4.1 Performance Characteristics

**S&P 500 Screening (500 companies)**:

- API calls: ~1,500 (3 per company: metadata + filing + XBRL)
- Time at 10 req/sec: **150 seconds = 2.5 minutes**
- Time at 5 req/sec (CAUTION mode): **300 seconds = 5 minutes**
- Memory usage: ~500MB (financial data in pandas DataFrames)

**Per-Company Metrics**:

- Single company: 1-3 seconds (3 API calls)
- 100 companies: ~30 seconds
- Cached repeat run: <1 minute

### 4.2 Rate Limiting

**SEC EDGAR Rate Limit**: 10 requests/second (IP-based)

- Enforcement: 10-minute IP block if exceeded
- EdgarTools modes:
  - **NORMAL**: High-performance (default, ~10 req/sec)
  - **CAUTION**: Conservative (~5 req/sec, recommended for production)
  - **CRAWL**: Bulk processing (~1 req/sec)

**Setting rate mode**:

```python
from edgar import set_rate_limit

set_rate_limit('CAUTION')  # Conservative 5 req/sec
```

### 4.3 Caching Strategy

**Auto HTTP Cache** (built-in):

- Location: In-memory HTTP response cache
- TTL: 10 minutes (configurable)
- Automatic (no setup required)

**Optional Bulk Cache**:

```python
from edgar import download_edgar_data, use_local_storage

# One-time: Download ~2.6GB
download_edgar_data()

# Enable local cache
use_local_storage()
```

**When to use bulk cache**:

- Daily/weekly screening runs
- Experimenting with different criteria
- Offline analysis

---

## 5. Code Examples

### 5.1 Complete Screening Script

See `scripts/run_screening.py` in Phase 2.

### 5.2 Custom Screening Criteria

```python
# Custom criteria configuration
class ScreeningConfig:
    # Growth metrics
    MIN_REVENUE_CAGR_10Y = 0.08      # 8%
    MIN_REVENUE_CAGR_5Y = 0.10       # 10%

    # Profitability
    MIN_OPERATING_MARGIN = 0.10      # 10%
    MIN_NET_MARGIN = 0.05            # 5%
    MIN_ROE = 0.15                   # 15%
    MIN_ROA = 0.05                   # 5%
    MIN_ROIC = 0.12                  # 12%

    # Financial health
    MAX_DEBT_TO_EQUITY = 0.5         # 0.5
    MIN_CURRENT_RATIO = 1.0          # 1.0

    # Quality
    MIN_METRICS_REQUIRED = 6         # At least 6 of 8 metrics

# Apply custom criteria
def custom_screen(metrics: Dict, config: ScreeningConfig) -> bool:
    criteria = [
        metrics.get('revenue_cagr_10y', 0) > config.MIN_REVENUE_CAGR_10Y,
        metrics.get('operating_margin_3y', 0) > config.MIN_OPERATING_MARGIN,
        # ... etc
    ]
    return sum(criteria) >= config.MIN_METRICS_REQUIRED
```

### 5.3 Sector-Specific Screening

```python
# Different criteria for different sectors
SECTOR_CRITERIA = {
    'Technology': {
        'min_revenue_cagr_10y': 0.15,  # Higher growth
        'min_operating_margin': 0.20,   # Higher margins
        'max_debt_to_equity': 0.3       # Lower leverage
    },
    'Utilities': {
        'min_revenue_cagr_10y': 0.03,  # Lower growth
        'min_operating_margin': 0.10,   # Moderate margins
        'max_debt_to_equity': 1.5       # Higher leverage OK
    }
}

def screen_by_sector(ticker: str, sector: str) -> bool:
    criteria = SECTOR_CRITERIA.get(sector, DEFAULT_CRITERIA)
    metrics = calculate_metrics(ticker)
    return apply_criteria(metrics, criteria)
```

---

## 6. Testing Strategy

### 6.1 Unit Tests

**File**: `tests/unit/test_metrics_calculator.py`

```python
import pytest
import pandas as pd
from src.screening.metrics_calculator import MetricsCalculator

def test_revenue_cagr():
    # Mock income statement
    income = pd.DataFrame({
        'Revenues': [100, 110, 121, 133, 146, 161, 177, 195, 214, 236, 259]
    })

    calc = MetricsCalculator()
    cagr = calc.calculate_revenue_cagr(income, years=10)

    assert abs(cagr - 0.10) < 0.01  # ~10% CAGR

def test_roe_calculation():
    income = pd.DataFrame({'NetIncomeLoss': [100, 110, 121]})
    balance = pd.DataFrame({'StockholdersEquity': [500, 550, 605]})

    calc = MetricsCalculator()
    roe = calc.calculate_avg_roe(income, balance, years=3)

    assert 0.19 < roe < 0.21  # ~20% ROE
```

### 6.2 Integration Tests

**File**: `tests/integration/test_screening_flow.py`

```python
import pytest
from src.screening.screener import EdgarToolsScreener

@pytest.mark.integration
def test_screen_known_company():
    """Test screening on a known company (AAPL)."""
    screener = EdgarToolsScreener(user_email="test@example.com")
    result = screener.screen_company("AAPL")

    assert result['status'] in ['passed', 'filtered']
    assert 'metrics' in result
    assert result['metrics']['revenue_cagr_10y'] is not None

@pytest.mark.integration
def test_screen_small_universe():
    """Test screening 10 companies."""
    screener = EdgarToolsScreener(user_email="test@example.com")
    test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
                    'TSLA', 'NVDA', 'JPM', 'V', 'WMT']

    results = screener.screen_universe(test_tickers)

    total = (len(results['passed']) + len(results['filtered']) +
             len(results['failed']) + len(results['errors']))

    assert total == 10
    assert len(results['passed']) > 0  # At least some should pass
```

---

## 7. Performance Optimization

### 7.1 Enable Bulk Caching

```python
from edgar import download_edgar_data, use_local_storage
import os

# Set custom cache directory
os.environ['EDGAR_LOCAL_DATA_DIR'] = '/path/to/cache'

# Download bulk data (one-time, ~2.6GB)
download_edgar_data()

# Enable local storage
use_local_storage()
```

### 7.2 Parallel Processing

```python
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

def screen_parallel(tickers: List[str], max_workers: int = 5) -> Dict:
    """Screen companies in parallel (respects rate limits)."""
    screener = EdgarToolsScreener(user_email="your.email@example.com")

    results = {'passed': [], 'filtered': [], 'failed': [], 'errors': []}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(screener.screen_company, t): t
                  for t in tickers}

        for future in futures:
            result = future.result()
            status = result['status']
            results[status].append(result)

    return results
```

**Note**: SEC rate limit (10 req/sec) is per IP, so parallel requests still count toward limit. Use `max_workers=5` to be conservative.

### 7.3 Checkpoint-Based Resume

```python
import json
from pathlib import Path

class CheckpointScreener:
    """Screener with checkpoint/resume capability."""

    def __init__(self, checkpoint_file: str = 'data/checkpoints/screening.json'):
        self.checkpoint_file = Path(checkpoint_file)
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

    def load_checkpoint(self) -> dict:
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {'processed': [], 'results': {'passed': [], 'filtered': [], 'failed': [], 'errors': []}}

    def save_checkpoint(self, processed: list, results: dict):
        with open(self.checkpoint_file, 'w') as f:
            json.dump({'processed': processed, 'results': results}, f)

    def screen_with_resume(self, tickers: list, screener):
        checkpoint = self.load_checkpoint()
        processed = set(checkpoint['processed'])
        results = checkpoint['results']

        remaining = [t for t in tickers if t not in processed]

        print(f"Resuming: {len(processed)} already processed, {len(remaining)} remaining")

        for ticker in remaining:
            result = screener.screen_company(ticker)
            results[result['status']].append(result)
            processed.add(ticker)

            # Save checkpoint every 10 companies
            if len(processed) % 10 == 0:
                self.save_checkpoint(list(processed), results)

        return results
```

---

## 8. Troubleshooting

### 8.1 Common Issues

**Issue**: `HTTPError: 429 Too Many Requests`
**Cause**: Exceeded 10 req/sec rate limit
**Solution**:

```python
from edgar import set_rate_limit
set_rate_limit('CAUTION')  # Reduce to 5 req/sec
```

**Issue**: `KeyError: 'Revenues'` or similar XBRL tag not found
**Cause**: Company uses different XBRL tag variation
**Solution**: Update `FieldMapper` mappings to include variation

**Issue**: `NoFinancialsFoundError`
**Cause**: Company has no XBRL filings (foreign filer, recent IPO, etc.)
**Solution**: Expected, skip company (handle in screener)

**Issue**: Slow performance (>10 min for S&P 500)
**Cause**: Network latency, rate limiting
**Solution**: Enable bulk caching or run during off-peak hours

### 8.2 Debugging Tips

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Inspect company data
from edgar import Company
company = Company("AAPL")
print(company.get_facts())  # See all available XBRL concepts

# Test single company first
screener = EdgarToolsScreener(user_email="your@email.com")
result = screener.screen_company("AAPL")
print(json.dumps(result, indent=2))
```

### 8.3 Performance Monitoring

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(label: str):
    start = time.time()
    yield
    elapsed = time.time() - start
    print(f"{label}: {elapsed:.2f}s")

# Usage
with timer("S&P 500 screening"):
    results = screener.screen_universe(sp500_tickers)
```

---

## Appendices

### A. Field Mapping Reference

**Complete XBRL tag mappings**: See `src/screening/field_mapper.py`

**Common variations**:

- Revenue: `Revenues`, `RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueNet`
- Net Income: `NetIncomeLoss`, `ProfitLoss`, `NetIncomeLossAvailableToCommonStockholdersBasic`
- Total Assets: `Assets`, `AssetsAbstract`

### B. Screening Criteria Recommendations

Based on fundamental analysis best practices:

| Metric             | Conservative | Moderate | Aggressive |
| ------------------ | ------------ | -------- | ---------- |
| Revenue CAGR (10Y) | 5%           | 8%       | 15%        |
| Operating Margin   | 8%           | 10%      | 15%        |
| ROE                | 12%          | 15%      | 20%        |
| ROIC               | 10%          | 12%      | 15%        |
| Debt/Equity        | <0.3         | <0.5     | <0.8       |

### C. Estimated Timelines

**Phase 1** (Core components): 3 days

- Field mapper: 0.5 days
- Metrics calculator: 1.5 days
- Main screener: 1 day

**Phase 2** (Integration): 1 day

- S&P 500 loader: 0.25 days
- Main execution script: 0.25 days
- Testing: 0.5 days

**Phase 3** (Testing & optimization): 1 day

- Unit tests: 0.5 days
- Integration tests: 0.5 days

**Total**: 5 days (50% contingency buffer on DD-031's 10-day estimate)

---

## Sign-Off

**Prepared by**: System Architect
**Date**: 2025-11-23
**Status**: Ready for Implementation
**Decision Reference**: DD-033

**Next Steps**:

1. Implement Phase 1 (core components)
2. Test with 10 companies
3. Implement Phase 2 (S&P 500 integration)
4. Run full screening
5. Analyze results, tune criteria
