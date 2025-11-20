# Parse Failure Recovery - Phase 1 Implementation Plan

**Status**: Ready for Implementation
**Created**: 2025-11-20
**Related**: `data-collector-parse-failure-strategy.md` Section 10
**Dependencies**: Phase B (Filing Parser), Phase C (Data Collector Agent)
**Duration**: 6 development days
**Priority**: CRITICAL - Must implement before deployment

---

## 1. Executive Summary

### Why Phase 1 is Required

Simulation of 10 realistic parse failure scenarios revealed:

- **Current design**: 95% data quality (5% incorrect data entering system)
- **With Phase 1**: 98.55% data quality (0.45% incorrect data)
- **Impact**: 3.55% improvement prevents silent data quality failures

### Critical Issues Being Fixed

1. **False Positives** (20% of LLM-parsed filings) - System accepts wrong data with high confidence
2. **Weak Tier 1** (0% actual recovery vs 60% claimed) - Forces expensive LLM calls
3. **Missing Validation** - No checks between LLM extraction and database storage

### Phase 1 Deliverables

| Improvement | Dev Time | Impact |
|-------------|----------|--------|
| **Tier 1.5: Smart Deterministic** | 3 days | +25% fewer LLM calls, 35% recovery rate |
| **Tier 2: Enhanced LLM Prompt** | 1 day | -25% Tier 3 escalations, fewer false positives |
| **Tier 2.5: Data Validation** | 2 days | Catch 66% of false positives before storage |
| **TOTAL** | **6 days** | **98.55% data quality, $47 saved per 20K filings** |

---

## 2. Implementation Order

### Recommended Sequence

1. **Tier 2.5 (Validation)** - Implement first to catch bad data during testing
2. **Tier 1.5 (Smart Deterministic)** - Reduces load on Tier 2
3. **Tier 2 (Enhanced Prompt)** - Improves quality of LLM extractions

**Rationale**: Build safety net (Tier 2.5) first, then optimize upstream tiers.

---

## 3. Detailed Implementation Steps

### Task 1: Implement Tier 2.5 - Data Validation Layer (2 days)

**Goal**: Prevent false positives from entering database by validating LLM extraction results

#### Step 1.1: Create Validation Module (4 hours)

**File**: `src/data_collector/validation.py`

```python
"""
Data validation layer for parse results.
Checks extracted financial data for consistency and accuracy.
"""

from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


class ParseValidationError(Exception):
    """Raised when validation fails"""
    pass


class ParseValidator:
    """Validates extracted financial data against filing metadata and consistency rules"""

    def __init__(self):
        self.validation_rules = [
            self._validate_accounting_standard,
            self._validate_balance_sheet,
            self._validate_holding_company,
            self._validate_value_ranges,
            self._validate_completeness,
        ]

    async def validate(
        self,
        extracted_data: Dict[str, Any],
        filing_metadata: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate extracted data against metadata and consistency rules.

        Args:
            extracted_data: LLM extraction result with metrics and confidence
            filing_metadata: Filing context (accounting_standard, company_type, etc.)

        Returns:
            (is_valid, list_of_issues)
        """
        issues = []

        for rule in self.validation_rules:
            try:
                rule_issues = await rule(extracted_data, filing_metadata)
                issues.extend(rule_issues)
            except Exception as e:
                logger.error(f"Validation rule failed: {rule.__name__}: {e}")
                issues.append(f"Validation error in {rule.__name__}: {str(e)}")

        is_valid = len(issues) == 0
        return is_valid, issues

    async def _validate_accounting_standard(
        self,
        extracted_data: Dict[str, Any],
        filing_metadata: Dict[str, Any]
    ) -> List[str]:
        """Check that extracted tags match filing's accounting standard"""
        issues = []
        accounting_standard = filing_metadata.get("accounting_standard")

        if accounting_standard == "IFRS":
            # IFRS filer should only have IFRS tags
            for metric, data in extracted_data.items():
                tag = data.get("tag", "")
                if "us-gaap:" in tag:
                    issues.append(
                        f"IFRS filer has US-GAAP tag for {metric}: {tag}. "
                        "Should use IFRS tags only (likely extracted from reconciliation table)."
                    )

        elif accounting_standard == "US-GAAP":
            # US-GAAP filer should only have US-GAAP tags
            for metric, data in extracted_data.items():
                tag = data.get("tag", "")
                if tag.startswith("ifrs:") or tag.startswith("ifrs-full:"):
                    issues.append(
                        f"US-GAAP filer has IFRS tag for {metric}: {tag}. "
                        "Accounting standard mismatch."
                    )

        return issues

    async def _validate_balance_sheet(
        self,
        extracted_data: Dict[str, Any],
        filing_metadata: Dict[str, Any]
    ) -> List[str]:
        """Check balance sheet equation: Assets = Liabilities + Equity"""
        issues = []

        # Extract values
        assets = extracted_data.get("total_assets", {}).get("value")
        liabilities = extracted_data.get("total_liabilities", {}).get("value")
        equity = extracted_data.get("total_equity", {}).get("value")

        # Only validate if all three present
        if assets is not None and liabilities is not None and equity is not None:
            expected = liabilities + equity
            diff = abs(assets - expected)
            tolerance = assets * 0.01  # 1% tolerance for rounding

            if diff > tolerance:
                issues.append(
                    f"Balance sheet doesn't balance: "
                    f"Assets ${assets:,.0f} != Liabilities ${liabilities:,.0f} + Equity ${equity:,.0f} "
                    f"(difference: ${diff:,.0f}, {diff/assets*100:.2f}%)"
                )

        return issues

    async def _validate_holding_company(
        self,
        extracted_data: Dict[str, Any],
        filing_metadata: Dict[str, Any]
    ) -> List[str]:
        """Check holding companies use consolidated financials"""
        issues = []

        if filing_metadata.get("company_type") == "HOLDING_COMPANY":
            # Check that at least some metrics cite "consolidated" in source
            has_consolidated = any(
                "consolidated" in str(data.get("source", "")).lower()
                for data in extracted_data.values()
            )

            if not has_consolidated:
                issues.append(
                    "Holding company missing 'consolidated' reference in sources. "
                    "May have extracted parent-only financials instead of consolidated."
                )

        return issues

    async def _validate_value_ranges(
        self,
        extracted_data: Dict[str, Any],
        filing_metadata: Dict[str, Any]
    ) -> List[str]:
        """Check that values are within reasonable ranges"""
        issues = []

        # Revenue should never be negative (unless SPAC with zero revenue)
        revenue = extracted_data.get("revenue", {}).get("value")
        if revenue is not None and revenue < 0:
            if filing_metadata.get("company_type") != "SPAC":
                issues.append(f"Revenue is negative: ${revenue:,.0f}")

        # Net income can be negative (losses), but should be reasonable vs revenue
        net_income = extracted_data.get("net_income", {}).get("value")
        if revenue and net_income and abs(net_income) > abs(revenue) * 2:
            issues.append(
                f"Net income ${net_income:,.0f} is >200% of revenue ${revenue:,.0f}. "
                "Likely extraction error."
            )

        # Assets should be positive
        assets = extracted_data.get("total_assets", {}).get("value")
        if assets is not None and assets <= 0:
            issues.append(f"Total assets non-positive: ${assets:,.0f}")

        return issues

    async def _validate_completeness(
        self,
        extracted_data: Dict[str, Any],
        filing_metadata: Dict[str, Any]
    ) -> List[str]:
        """Check that minimum required metrics are present"""
        issues = []

        required_metrics = [
            "revenue", "net_income", "total_assets",
            "total_liabilities", "total_equity"
        ]

        missing = []
        for metric in required_metrics:
            if metric not in extracted_data or extracted_data[metric].get("value") is None:
                # Allow SPACs to have null revenue
                if metric == "revenue" and filing_metadata.get("company_type") == "SPAC":
                    continue
                missing.append(metric)

        if missing:
            issues.append(f"Missing required metrics: {', '.join(missing)}")

        return issues
```

**Testing**:
- Unit tests with mock data for each validation rule
- Test cases: IFRS mismatch, unbalanced balance sheet, missing consolidated, negative revenue

#### Step 1.2: Integrate Validation into Storage Pipeline (2 hours)

**File**: `src/data_collector/storage_pipeline.py` (update existing)

```python
from .validation import ParseValidator, ParseValidationError

class StoragePipeline:
    def __init__(self):
        # ... existing init ...
        self.validator = ParseValidator()

    async def process_filing(self, cik: str, accession_number: str, form_type: str):
        """Orchestrate filing fetch → parse → validate → store"""

        # Fetch filing metadata
        filing_metadata = await self._get_filing_metadata(cik, accession_number, form_type)

        # Fetch filing content
        filing_content = await edgar_client.download_filing(accession_number)

        # Tier 1: Deterministic parsing (will be Tier 1.5 after Task 2)
        try:
            financial_data = await filing_parser.parse_xbrl_financials(
                filing_content,
                filing_metadata  # Pass metadata for smart parsing
            )
            parse_status = "PARSED"

        except ParseFailureError as e:
            # Tier 2: LLM-assisted parsing
            logger.info(f"Attempting LLM parsing for {accession_number}")
            llm_result = await self._llm_parse(filing_content, filing_metadata)

            if llm_result.confidence >= 0.80:
                # NEW: Tier 2.5 - Validate before accepting
                is_valid, issues = await self.validator.validate(
                    llm_result.data,
                    filing_metadata
                )

                if is_valid:
                    financial_data = llm_result.data
                    parse_status = "LLM_PARSED"
                    logger.info(f"LLM parse validated successfully: {accession_number}")
                else:
                    # Failed validation despite high confidence → Tier 3
                    logger.warning(
                        f"LLM parse failed validation for {accession_number}: {issues}"
                    )
                    await self._escalate_to_qc_agent(
                        filing_content,
                        accession_number,
                        llm_result,
                        validation_issues=issues
                    )
                    parse_status = "PENDING_QC_REVIEW"
                    financial_data = None
            else:
                # Low confidence → Tier 3
                await self._escalate_to_qc_agent(filing_content, accession_number, llm_result)
                parse_status = "PENDING_QC_REVIEW"
                financial_data = None

        # Store results if available
        if financial_data:
            await postgres.insert_financial_data(ticker, financial_data)
            await postgres.update_filing(filing_id, parse_status=parse_status)

    async def _get_filing_metadata(
        self,
        cik: str,
        accession_number: str,
        form_type: str
    ) -> dict:
        """Extract filing metadata for validation and smart parsing"""

        # Query company info from database
        company = await postgres.get_company_by_cik(cik)

        # Determine accounting standard (US-GAAP vs IFRS)
        # Foreign filers (20-F, 6-K) typically use IFRS
        if form_type in ["20-F", "6-K"]:
            accounting_standard = "IFRS"
        else:
            accounting_standard = "US-GAAP"

        # Detect company type
        company_type = self._detect_company_type(company)

        return {
            "ticker": company.ticker,
            "cik": cik,
            "accession_number": accession_number,
            "form_type": form_type,
            "accounting_standard": accounting_standard,
            "company_type": company_type,
            "fiscal_year": self._extract_fiscal_year(accession_number),
        }

    def _detect_company_type(self, company: dict) -> str:
        """Heuristic to detect company type for special handling"""

        name = company.get("name", "").lower()
        sic_code = company.get("sic_code")

        # SPAC detection
        if any(keyword in name for keyword in ["acquisition corp", "acquisition company", "spac"]):
            return "SPAC"

        # Holding company detection (banks, insurance, conglomerates)
        if sic_code in ["6712", "6719"]:  # Holding companies SIC codes
            return "HOLDING_COMPANY"
        if any(keyword in name for keyword in ["holdings", "bancorp", "financial group"]):
            return "HOLDING_COMPANY"

        return "OPERATING_COMPANY"
```

**Testing**:
- Integration test: Feed known false positive scenarios (Scenario #5, #10 from simulation)
- Verify validation catches issues and escalates to Tier 3

#### Step 1.3: Add Monitoring and Metrics (2 hours)

**File**: `src/data_collector/metrics.py` (new)

```python
"""Metrics tracking for parse failure recovery"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class ParseMetrics:
    """Track parse success/failure by tier"""
    tier_0_success: int = 0  # Initial parse
    tier_1_success: int = 0  # Smart deterministic
    tier_2_success: int = 0  # LLM parsed
    tier_2_validation_fail: int = 0  # Tier 2.5 caught false positive
    tier_3_escalated: int = 0  # QC Agent review
    tier_4_human: int = 0  # Human escalation
    total_filings: int = 0

    @property
    def overall_success_rate(self) -> float:
        """Percentage of filings successfully parsed"""
        if self.total_filings == 0:
            return 0.0
        success = self.tier_0_success + self.tier_1_success + self.tier_2_success
        return (success / self.total_filings) * 100

    @property
    def false_positive_catch_rate(self) -> float:
        """Percentage of Tier 2 results caught by validation"""
        tier_2_total = self.tier_2_success + self.tier_2_validation_fail
        if tier_2_total == 0:
            return 0.0
        return (self.tier_2_validation_fail / tier_2_total) * 100
```

**Logging**:
```python
# In storage_pipeline.py, add metrics logging
logger.info(
    f"Parse completed: {parse_status} | "
    f"Overall success: {metrics.overall_success_rate:.1f}% | "
    f"False positive catch rate: {metrics.false_positive_catch_rate:.1f}%"
)
```

---

### Task 2: Implement Tier 1.5 - Smart Deterministic (3 days)

**UPDATED (DD-027)**: This tier is now the **fallback for EdgarTools (Tier 0)**

**Goal**: Handle EdgarTools failures (5% of filings) with 35% recovery rate via metadata-aware parsing

**Context**: Research showed EdgarTools best-in-class for baseline (95% success, 10-30x faster). Tier 1.5 handles edge cases EdgarTools doesn't:
- Context disambiguation (consolidated vs parent, restated vs original)
- Holding companies, SPACs, bankruptcy filings
- Mixed GAAP/IFRS extraction
- Encoding error recovery

#### Step 2.0: Integrate EdgarTools as Tier 0 (0.5 days - NEW)

**File**: `src/data_collector/filing_parser.py` (add Tier 0 wrapper)

```python
"""
Multi-tier XBRL parser with EdgarTools foundation.
Tier 0: EdgarTools (95% baseline) → Tier 1.5: Smart Deterministic → Tier 2: LLM
"""

from edgartools import Filing
import lxml.etree
import re
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ParseFailureError(Exception):
    """Raised when parsing fails"""
    pass


class FilingParser:
    """Parse SEC EDGAR XBRL filings with multi-tier fallback"""

    async def parse_xbrl_financials(
        self,
        filing_content: bytes,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Multi-tier parsing with EdgarTools foundation.

        Tier 0: EdgarTools (95% baseline, fast)
        Tier 1.5: Smart deterministic (metadata-aware fallback)
        Tier 2: LLM-assisted (handled in storage_pipeline.py)
        """

        # Tier 0: Try EdgarTools first
        try:
            return await self._parse_with_edgartools(metadata)
        except Exception as e:
            logger.info(f"Tier 0 (EdgarTools) failed: {e}, trying Tier 1.5")

        # Tier 1.5: Smart deterministic fallback
        return await self._parse_smart_deterministic(filing_content, metadata)

    async def _parse_with_edgartools(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Tier 0: Use EdgarTools for standard filings"""

        filing = Filing(metadata["accession_number"])
        xbrl = filing.xbrl()

        # Extract standardized financial statements
        income = xbrl.statements.income_statement
        balance = xbrl.statements.balance_sheet
        cashflow = xbrl.statements.cash_flow

        financials = {
            "revenue": income.revenue if hasattr(income, "revenue") else None,
            "net_income": income.net_income if hasattr(income, "net_income") else None,
            "total_assets": balance.assets if hasattr(balance, "assets") else None,
            "total_liabilities": balance.liabilities if hasattr(balance, "liabilities") else None,
            "total_equity": balance.equity if hasattr(balance, "equity") else None,
            "operating_cash_flow": cashflow.operating_cf if hasattr(cashflow, "operating_cf") else None,
            # Add other metrics as needed
        }

        # Validate completeness (need at least 5/8 metrics)
        valid_metrics = sum(1 for v in financials.values() if v is not None)
        if valid_metrics < 5:
            raise ParseFailureError(
                f"EdgarTools returned only {valid_metrics}/8 metrics, need ≥5"
            )

        logger.info(f"Tier 0 success: {metadata['accession_number']}, {valid_metrics}/8 metrics")
        return financials
```

**Testing**:
- Integration test: Fetch 10 real filings via EdgarTools
- Verify 95% success rate on random sample
- Measure performance improvement vs custom lxml

**Time**: 0.5 days (4 hours implementation + 4 hours testing)

#### Step 2.1: Enhance FilingParser with Smart Deterministic Fallback (1.5 days)

**File**: `src/data_collector/filing_parser.py` (update existing)

```python
"""
Enhanced filing parser with smart deterministic strategies.
Uses metadata and context awareness for better XBRL extraction.
"""

import lxml.etree
import re
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class ParseFailureError(Exception):
    """Raised when parsing fails"""
    pass


class FilingParser:
    """Parse SEC EDGAR XBRL filings with multi-tier fallback"""

    # Standard US-GAAP tags
    US_GAAP_TAGS = {
        "revenue": "us-gaap:Revenues",
        "net_income": "us-gaap:NetIncomeLoss",
        "total_assets": "us-gaap:Assets",
        "total_liabilities": "us-gaap:Liabilities",
        "total_equity": "us-gaap:StockholdersEquity",
        "total_debt": "us-gaap:LongTermDebt",
        "operating_cash_flow": "us-gaap:NetCashProvidedByUsedInOperatingActivities",
        "eps_diluted": "us-gaap:EarningsPerShareDiluted",
    }

    # IFRS tag equivalents
    IFRS_TAGS = {
        "revenue": "ifrs-full:Revenue",
        "net_income": "ifrs-full:ProfitLoss",
        "total_assets": "ifrs-full:Assets",
        "total_liabilities": "ifrs-full:Liabilities",
        "total_equity": "ifrs-full:Equity",
        "total_debt": "ifrs-full:Borrowings",
        "operating_cash_flow": "ifrs-full:CashFlowsFromUsedInOperatingActivities",
        "eps_diluted": "ifrs-full:BasicAndDilutedEarningsLossPerShare",
    }

    async def parse_xbrl_financials(
        self,
        filing_content: bytes,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse XBRL with Tier 1.5 smart deterministic approach.

        Args:
            filing_content: Raw XBRL filing bytes
            metadata: Filing context (accounting_standard, company_type, etc.)

        Returns:
            Extracted financial metrics

        Raises:
            ParseFailureError: If parsing fails, escalate to Tier 2 LLM
        """
        try:
            return await self._parse_smart_deterministic(filing_content, metadata)
        except ParseFailureError as e:
            logger.info(f"Smart deterministic parse failed: {e}")
            raise

    async def _parse_smart_deterministic(
        self,
        content: bytes,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhanced deterministic parsing with context awareness"""

        # Step 1: Pre-process XBRL (fix common encoding issues)
        content = self._fix_common_encoding_issues(content)

        # Step 2: Lenient XML parsing with error recovery
        try:
            parser = lxml.etree.XMLParser(recover=True)
            tree = lxml.etree.fromstring(content, parser=parser)
        except Exception as e:
            raise ParseFailureError(f"Unrecoverable XML corruption: {e}")

        # Step 3: Metadata-informed strategy selection
        tag_set = self._select_tag_set(metadata)

        # Step 4: Context-aware extraction with disambiguation
        results = {}
        for metric, tag_name in tag_set.items():
            try:
                value = await self._extract_metric_with_disambiguation(
                    tree, metric, tag_name, metadata
                )
                if value is not None:
                    results[metric] = value
            except Exception as e:
                logger.debug(f"Failed to extract {metric}: {e}")

        # Step 5: Validate minimum required metrics
        if len(results) < 5:
            raise ParseFailureError(f"Only found {len(results)}/8 required metrics")

        return results

    def _fix_common_encoding_issues(self, content: bytes) -> bytes:
        """Fix common XBRL encoding problems before parsing"""
        try:
            text = content.decode('utf-8', errors='ignore')
        except:
            text = content.decode('latin-1', errors='ignore')

        # Common fixes
        text = text.replace('&nbsp;', '')  # Non-breaking space in numeric fields
        text = text.replace('&#160;', '')  # Non-breaking space (numeric entity)
        text = re.sub(r'\s+', ' ', text)   # Normalize whitespace

        return text.encode('utf-8')

    def _select_tag_set(self, metadata: Dict[str, Any]) -> Dict[str, str]:
        """Select appropriate tag set based on accounting standard"""

        accounting_standard = metadata.get("accounting_standard", "")

        if accounting_standard == "IFRS":
            logger.info("Using IFRS tags based on filing metadata")
            return self.IFRS_TAGS
        elif accounting_standard == "US-GAAP":
            logger.info("Using US-GAAP tags based on filing metadata")
            return self.US_GAAP_TAGS
        else:
            # Unknown - try both (fallback)
            logger.warning("Unknown accounting standard, trying both GAAP and IFRS")
            return {**self.US_GAAP_TAGS, **self.IFRS_TAGS}

    async def _extract_metric_with_disambiguation(
        self,
        tree: lxml.etree.Element,
        metric: str,
        tag_name: str,
        metadata: Dict[str, Any]
    ) -> Optional[float]:
        """Extract single metric with context disambiguation"""

        # Strategy 1: Direct tag match
        values = self._find_tag_values(tree, tag_name)

        # Strategy 2: Namespace-agnostic fuzzy match
        if not values:
            tag_local = tag_name.split(":")[-1]  # "Revenues" from "us-gaap:Revenues"
            xpath = f"//*[local-name()='{tag_local}']"
            elements = tree.xpath(xpath)
            values = [(elem, self._extract_numeric_value(elem)) for elem in elements]
            values = [(e, v) for e, v in values if v is not None]

        # No values found
        if not values:
            return None

        # Single value - return it
        if len(values) == 1:
            return values[0][1]

        # Multiple values - disambiguate using context
        selected_elem, selected_value = self._disambiguate_contexts(values, metadata)
        return selected_value

    def _find_tag_values(
        self,
        tree: lxml.etree.Element,
        tag_name: str
    ) -> List[tuple]:
        """Find all occurrences of a tag in XBRL tree"""

        # Handle namespace
        if ":" in tag_name:
            namespace, local = tag_name.split(":", 1)
            # Try to find namespace URI
            # (simplified - real implementation should parse xmlns declarations)
            xpath = f"//{tag_name}"
        else:
            xpath = f"//{tag_name}"

        elements = tree.xpath(xpath, namespaces=tree.nsmap)
        result = []

        for elem in elements:
            value = self._extract_numeric_value(elem)
            if value is not None:
                result.append((elem, value))

        return result

    def _extract_numeric_value(self, elem: lxml.etree.Element) -> Optional[float]:
        """Extract numeric value from XBRL element"""
        try:
            text = elem.text.strip() if elem.text else None
            if not text:
                return None

            # Remove commas, convert to float
            text = text.replace(',', '')
            value = float(text)

            # Handle decimals attribute (e.g., decimals="-6" means value in millions)
            decimals = elem.get('decimals')
            if decimals and decimals.startswith('-'):
                scale = 10 ** abs(int(decimals))
                value = value * scale

            return value
        except (ValueError, AttributeError):
            return None

    def _disambiguate_contexts(
        self,
        values: List[tuple],
        metadata: Dict[str, Any]
    ) -> tuple:
        """
        Context-aware value selection when multiple values found.

        Returns: (selected_element, selected_value)
        """

        elements = [elem for elem, val in values]

        # Priority order for disambiguation
        preferences = []

        # 1. Consolidated (for holding companies)
        if metadata.get("company_type") == "HOLDING_COMPANY":
            preferences.append("Consolidated")

        # 2. Restated (for amended filings)
        if "/A" in metadata.get("form_type", ""):
            preferences.extend(["As_Restated", "Amended", "Restated"])

        # 3. Annual periods (not quarterly)
        preferences.extend(["12Months", "Annual", "FY"])

        # Apply preference filters
        for pref in preferences:
            filtered = [
                (elem, val) for elem, val in values
                if pref in elem.get("contextRef", "")
            ]
            if filtered:
                logger.debug(f"Disambiguated using preference: {pref}")
                return filtered[0]

        # Fallback: most recent by period_end_date in contextRef
        # (simplified - real implementation should parse context elements)
        sorted_values = sorted(
            values,
            key=lambda x: x[0].get("contextRef", ""),
            reverse=True
        )

        logger.debug("Disambiguated using contextRef sort")
        return sorted_values[0]
```

**Testing**:
- Unit tests for encoding fixes
- Test metadata-informed tag selection (IFRS vs US-GAAP)
- Test context disambiguation (consolidated, restated, annual)

#### Step 2.2: Test on Simulation Scenarios (1 day)

Run Tier 1.5 on the 10 failure scenarios from simulation:

**Expected outcomes**:
- Scenario #1 (IFRS foreign filer): ✅ Recover (metadata selects IFRS tags)
- Scenario #3 (Amended with restated): ✅ Recover (prefer "As_Restated")
- Scenario #4 (Bankruptcy negative equity): ✅ Recover (remove validation block)
- Scenario #7 (Encoding error): ✅ Recover (fix &nbsp;)
- Scenario #9 (Multiple periods): ✅ Recover (prefer 12Months)

**Target**: 4-5/10 scenarios recovered (40-50% success rate)

#### Step 2.3: Integration and Performance Testing (1 day)

- Integrate with storage_pipeline.py
- Test on 100 random real filings
- Measure recovery rate and performance
- Validate no regressions in standard parsing

---

### Task 3: Implement Tier 2 Enhanced LLM Prompt (1 day)

**Goal**: Improve LLM extraction quality and reduce false positives

#### Step 3.1: Update LLM Prompt with Metadata Context (4 hours)

**File**: `src/data_collector/storage_pipeline.py` (update `_llm_parse` method)

See Section 10, Improvement #2 in `data-collector-parse-failure-strategy.md` for full prompt.

Key additions:
- Filing metadata context (accounting_standard, company_type, form_type)
- Special case handling (IFRS, holding companies, SPACs, restated, GAAP vs non-GAAP)
- Explicit extraction rules (primary statements, not reconciliations)
- Increase sample size from 50KB → 100KB

#### Step 3.2: Implement Intelligent XBRL Sampling (2 hours)

```python
def _sample_xbrl_intelligently(
    self,
    content: bytes,
    target_size: int = 100000
) -> str:
    """
    Smart sampling: prioritize financial statement sections.
    Better than just taking first N bytes.
    """
    try:
        tree = lxml.etree.fromstring(content, recover=True)
    except:
        # Fallback to dumb sampling if parse fails
        return content[:target_size].decode('utf-8', errors='ignore')

    # Priority sections to include
    sections = []

    # 1. Income statement (15KB)
    income = tree.findall(".//*[contains(local-name(), 'IncomeStatement')]")
    if income:
        sections.append(lxml.etree.tostring(income[0])[:15000])

    # 2. Balance sheet (15KB)
    balance = tree.findall(".//*[contains(local-name(), 'BalanceSheet')]")
    if balance:
        sections.append(lxml.etree.tostring(balance[0])[:15000])

    # 3. Cash flow statement (10KB)
    cashflow = tree.findall(".//*[contains(local-name(), 'CashFlow')]")
    if cashflow:
        sections.append(lxml.etree.tostring(cashflow[0])[:10000])

    # 4. Header metadata (5KB) for context
    header = lxml.etree.tostring(tree)[:5000]
    sections.insert(0, header)

    # Combine sections
    sample = b"".join(sections)

    # Pad to target size if needed
    if len(sample) < target_size:
        remaining = target_size - len(sample)
        sample += content[len(header):len(header)+remaining]

    return sample[:target_size].decode('utf-8', errors='ignore')
```

#### Step 3.3: Test Enhanced Prompt on Simulation Failures (2 hours)

Run enhanced Tier 2 on scenarios that failed original Tier 2:

- Scenario #5 (Mixed GAAP/IFRS): Should now correctly identify IFRS primary vs GAAP reconciliation
- Scenario #10 (Holding company): Should extract consolidated, not parent-only

**Expected**: 0/2 false positives (down from 2/2)

---

## 4. Testing Strategy

### Unit Tests (2 hours)

**File**: `tests/unit/test_parse_validator.py`

- Test each validation rule independently
- Mock data for edge cases (IFRS mismatch, unbalanced balance sheet, etc.)
- Coverage target: 90%+

### Integration Tests (4 hours)

**File**: `tests/integration/test_parse_pipeline.py`

- End-to-end test: filing content → Tier 0 (EdgarTools) → Tier 1.5 → Tier 2 → Tier 2.5 → storage
- Use real filing samples (10-K, 20-F, 10-K/A, SPAC)
- Verify metrics tracking
- **NEW**: Validate EdgarTools handles 95% baseline

### Validation Against Simulation Scenarios (4 hours)

**File**: `tests/integration/test_simulation_scenarios.py`

- Recreate the 10 simulation scenarios with real filing samples
- Verify Phase 1 improvements achieve target success rates:
  - Tier 0 (EdgarTools): 9-10/10 recovered (90-95%)
  - Tier 1.5: 4-5/10 of remaining recovered (40-50% of Tier 0 failures)
  - Tier 2 Enhanced: 5-6/10 of remaining recovered (50-60% of Tier 1.5 failures)
  - Tier 2.5 Validation: Catch 2/2 false positives
  - Overall: 99-100% successfully handled

---

## 5. Rollout Plan

### Development Timeline

| Day | Tasks | Owner |
|-----|-------|-------|
| **Day 1** | Task 1.1: Create validation module | Dev |
| | Task 1.2: Integrate into pipeline | Dev |
| | Unit tests for validation | Dev |
| **Day 2** | Task 1.3: Add metrics tracking | Dev |
| | Integration tests | Dev |
| **Day 3** | Task 2.0: **NEW** EdgarTools integration (Tier 0) | Dev |
| | Test EdgarTools on 100 random filings | Dev |
| | Validate 95% baseline success rate | Dev |
| **Day 4** | Task 2.1: Implement Tier 1.5 fallback | Dev |
| | Unit tests for smart deterministic | Dev |
| **Day 5** | Task 2.2: Test on simulation scenarios | Dev |
| | Task 2.3: Integration and performance tests | Dev |
| **Day 6** | Task 3.1: Enhanced LLM prompt | Dev |
| | Task 3.2: Intelligent sampling | Dev |
| | Task 3.3: Test enhanced Tier 2 | Dev |
| | Final validation against all 10 scenarios | Dev |
| | Documentation updates | Dev |

### Deployment Checklist

- [ ] All unit tests pass (90%+ coverage)
- [ ] Integration tests pass
- [ ] Validation against 10 simulation scenarios achieves target rates
- [ ] Performance benchmarks meet requirements (no regression in parse time)
- [ ] Metrics tracking implemented and tested
- [ ] Documentation updated (README, API docs)
- [ ] Code review completed
- [ ] Stakeholder signoff on improved success rates

---

## 6. Success Metrics

### Acceptance Criteria

| Metric | Current | Target (Phase 1) | Measurement |
|--------|---------|------------------|-------------|
| **Data Quality** | 95% | 98.5% | % filings with correct data |
| **Tier 1 Recovery** | 10% | 35% | % failures recovered by Tier 1.5 |
| **Tier 2 False Positives** | 20% | <5% | % LLM results caught by Tier 2.5 |
| **Human Escalations** | 10% | 5% | % filings needing human review |
| **LLM Cost (20K filings)** | $135 | $88 | Total LLM API spend |

### Post-Deployment Monitoring

Monitor these metrics for first 1,000 filings processed:

1. **Parse success rate by tier** (daily dashboard)
2. **False positive detection rate** (Tier 2.5 catch rate)
3. **Validation failure reasons** (most common issues)
4. **Human escalation reasons** (categorize for Phase 2 improvements)

If any metric misses target by >10%, investigate and adjust before scaling.

---

## 7. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Validation too strict** - Rejects valid filings | High | Medium | Adjustable tolerance thresholds, log all rejections for review |
| **Tier 1.5 increases parse time** | Medium | Low | Performance benchmarking, optimize hot paths |
| **Enhanced prompt increases LLM cost** | Low | Medium | 100KB vs 50KB is marginal (~$0.03/call), savings from fewer calls offsets |
| **Real filings differ from simulation** | High | Medium | Test on 500 random real filings before full deployment |

---

## 8. Unresolved Questions

- **Validation threshold tuning**: Should balance sheet tolerance be 1% or 2%?
- **Partial data acceptance**: Accept filings with 6/8 metrics (currently requires 5/8)?
- **Cost vs quality tradeoff**: Use Opus 4 for low-confidence cases (higher accuracy, 3x cost)?

---

## 9. Next Steps After Phase 1

Once Phase 1 complete and validated, proceed to **Phase 2 Optimizations** (9 days):

1. QC Agent strategy library (4 days)
2. Learning loop implementation (3 days)
3. Intelligent LLM sampling v2 (2 days)

**Target**: 99% data quality, 1.5% human escalations

---

**Document Status**: Ready for Implementation
**Last Updated**: 2025-11-20
**Next Review**: After Phase 1 completion, validate actual vs estimated success rates
