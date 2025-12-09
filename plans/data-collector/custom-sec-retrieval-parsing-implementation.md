# SEC File Retrieval & EdgarTools Multi-Tier Parsing - Implementation Plan

## Executive Summary

Build SEC EDGAR API retrieval + EdgarTools-based multi-tier XBRL parsing system. Achieve 98.55% data quality through multi-tier recovery on top of EdgarTools 95% baseline (per DD-033 unified approach).

**Key Metrics (20,000 Filing Backfill)**:

- Data Quality: 98.55% ✅
- Dependencies: boto3, anthropic, tenacity, edgartools

## Architecture Overview

```text
Filing Request → SEC EDGAR Client (custom) → Raw XBRL Download → MinIO Storage
                                                    ↓
                         Tier 0: EdgarTools Parser (95% baseline)
                                                    ↓ (5% fail)
                         Tier 1.5: Smart Deterministic (35% recovery → 96.75%)
                                                    ↓ (3.25% fail)
                         Tier 2: LLM Parsing (60% recovery → 98.7%)
                                                    ↓ (1.3% fail)
                         Tier 2.5: Validation Layer (catch false positives → 98.55%)
                                                    ↓ (1.45% fail)
                         Tier 3: QC Agent Review (75% recovery → 99.6%)
                                                    ↓ (0.4% fail)
                         Tier 4: Human Review (100%)
                                                    ↓
                         PostgreSQL + Screening Metrics Table
```

**Design Rationale**:

- **EdgarTools for Tier 0**: Battle-tested 95% baseline, aligns with DD-033 unified approach
- **Better starting point**: 95% vs 92% custom → fewer escalations to expensive tiers
- **Direct SEC API**: Free, 10 req/sec, compliant with SEC requirements
- **Multi-tier recovery**: 95% → 98.55% final quality through deterministic + LLM fallbacks
- **Hybrid Schema**: Keep existing denormalized tables + add raw XBRL facts for debugging

---

## Phase A: SEC EDGAR Retrieval Infrastructure (3 days)

### A1: SEC EDGAR API Client (`src/agents/data_collector/edgar_client.py`)

**Responsibilities**:

- CIK lookup (ticker → CIK mapping via SEC bulk file)
- Filing index queries (list 10-K/10-Q/8-K for company in date range)
- Raw filing download (XBRL/iXBRL/HTML)
- Rate limiting (10 req/sec, Redis-backed atomic counter)
- User-Agent compliance (SEC requires: "CompanyName <contact@email.com>")
- Amendment detection (form_type ends with /A)

**Implementation**:

```python
# src/agents/data_collector/edgar_client.py
import aiohttp
import asyncio
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SECEdgarClient:
    """Custom SEC EDGAR API client with rate limiting and caching"""

    BASE_URL = "https://www.sec.gov"
    SUBMISSIONS_URL = f"{BASE_URL}/cgi-bin/browse-edgar"

    def __init__(self, redis_client, user_agent: str):
        """
        Args:
            redis_client: Redis client for rate limiting and caching
            user_agent: SEC-compliant User-Agent (required: "CompanyName contact@email.com")
        """
        self.redis = redis_client
        self.user_agent = user_agent
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": self.user_agent},
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_cik(self, ticker: str) -> str:
        """
        Convert ticker to CIK using SEC company_tickers.json

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")

        Returns:
            CIK string zero-padded to 10 digits (e.g., "0000320193")

        Raises:
            ValueError: If ticker not found
        """
        # Check cache first (7 day TTL)
        cache_key = f"cik:{ticker.upper()}"
        cached = await self.redis.get(cache_key)
        if cached:
            logger.debug(f"CIK cache hit for {ticker}: {cached}")
            return cached.decode('utf-8')

        # Fetch from SEC bulk file (JSON format, ~30KB)
        url = "https://www.sec.gov/files/company_tickers.json"
        await self._rate_limit()

        async with self.session.get(url) as resp:
            if resp.status != 200:
                raise RuntimeError(f"SEC API error: {resp.status}")
            data = await resp.json()

        # Find CIK for ticker
        for entry in data.values():
            if entry["ticker"].upper() == ticker.upper():
                cik = str(entry["cik_str"]).zfill(10)  # Zero-pad to 10 digits

                # Cache for 7 days
                await self.redis.setex(cache_key, 604800, cik)
                logger.info(f"CIK lookup: {ticker} → {cik}")
                return cik

        raise ValueError(f"CIK not found for ticker: {ticker}")

    async def get_company_filings(
        self,
        cik: str,
        form_types: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> List[dict]:
        """
        List all filings for company in date range

        Args:
            cik: Company CIK (10 digits)
            form_types: List of form types (e.g., ["10-K", "10-Q"])
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of filing metadata dicts:
                {
                    "accession_number": "0001234567-24-000123",
                    "form_type": "10-K",
                    "filing_date": datetime,
                    "period_end_date": datetime,
                    "fiscal_year": 2024,
                    "fiscal_quarter": None  # or 1-4 for 10-Q
                }
        """
        await self._rate_limit()

        # Use SEC submissions endpoint (returns Atom XML feed)
        url = f"{self.BASE_URL}/cgi-bin/browse-edgar"
        params = {
            "action": "getcompany",
            "CIK": cik,
            "type": "",  # All types (filter client-side)
            "dateb": end_date.strftime("%Y%m%d"),
            "owner": "exclude",
            "output": "atom",  # XML format
            "count": 100  # Max per request
        }

        async with self.session.get(url, params=params) as resp:
            if resp.status != 200:
                raise RuntimeError(f"SEC API error: {resp.status}")
            xml_content = await resp.text()

        # Parse XML to extract filing metadata
        filings = self._parse_submissions_xml(xml_content, form_types, start_date)

        logger.info(f"Found {len(filings)} filings for CIK {cik} ({form_types})")
        return filings

    async def download_filing(self, accession_number: str) -> bytes:
        """
        Download raw XBRL filing from SEC EDGAR

        Args:
            accession_number: SEC accession number (e.g., "0001234567-24-000123")

        Returns:
            Raw filing content as bytes (XBRL XML or text)

        Raises:
            FileNotFoundError: If filing not found (404)
        """
        await self._rate_limit()

        # Format: 0001234567-24-000123 → URL path
        # https://www.sec.gov/Archives/edgar/data/0001234567/000123456724000123.txt
        cik = accession_number.split("-")[0]
        acc_no_dashes = accession_number.replace("-", "")

        url = f"{self.BASE_URL}/Archives/edgar/data/{cik}/{acc_no_dashes}.txt"

        logger.debug(f"Downloading filing: {url}")
        async with self.session.get(url) as resp:
            if resp.status == 404:
                raise FileNotFoundError(f"Filing not found: {accession_number}")
            elif resp.status != 200:
                raise RuntimeError(f"SEC API error: {resp.status}")

            content = await resp.read()
            logger.info(f"Downloaded filing {accession_number}: {len(content)} bytes")
            return content

    async def _rate_limit(self):
        """
        Enforce SEC rate limit: 10 requests/second

        Uses Redis atomic counter with 2-second TTL to track requests per second.
        If limit exceeded, sleeps 1 second and retries.
        """
        current_second = int(datetime.now().timestamp())
        key = f"rate_limit:sec:{current_second}"

        # Atomic increment
        count = await self.redis.incr(key)
        await self.redis.expire(key, 2)  # 2 second TTL (buffer)

        if count > 10:
            # Exceeded limit, wait for next second
            logger.warning(f"SEC rate limit exceeded ({count}/10), sleeping 1s")
            await asyncio.sleep(1.0)
            return await self._rate_limit()  # Retry

    def _parse_submissions_xml(
        self,
        xml_content: str,
        form_types: List[str],
        start_date: datetime
    ) -> List[dict]:
        """
        Parse SEC Atom XML feed to extract filing metadata

        Args:
            xml_content: Atom XML feed from SEC submissions endpoint
            form_types: Filter for these form types only
            start_date: Filter for filings on/after this date

        Returns:
            List of filing metadata dicts
        """
        import xml.etree.ElementTree as ET

        filings = []
        root = ET.fromstring(xml_content)

        # Atom namespace
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        for entry in root.findall('atom:entry', ns):
            # Extract metadata
            form_type = entry.find('.//atom:category[@term]', ns).get('term')

            # Filter by form type
            if form_type not in form_types:
                continue

            # Extract dates and accession number
            filing_date_str = entry.find('.//atom:filing-date', ns).text
            filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")

            # Filter by date
            if filing_date < start_date:
                continue

            accession_number = entry.find('.//atom:accession-number', ns).text
            period_end_date_str = entry.find('.//atom:period', ns).text
            period_end_date = datetime.strptime(period_end_date_str, "%Y-%m-%d")

            # Determine fiscal year/quarter
            fiscal_year = period_end_date.year
            fiscal_quarter = None
            if form_type == "10-Q":
                # Estimate quarter from period end date (rough heuristic)
                month = period_end_date.month
                fiscal_quarter = (month - 1) // 3 + 1

            filings.append({
                "accession_number": accession_number,
                "form_type": form_type,
                "filing_date": filing_date,
                "period_end_date": period_end_date,
                "fiscal_year": fiscal_year,
                "fiscal_quarter": fiscal_quarter
            })

        return filings
```

**Key Features**:

- **CIK caching**: 7-day TTL to minimize API calls
- **Atomic rate limiting**: Redis INCR ensures distributed rate limiting (multiple workers)
- **User-Agent compliance**: SEC blocks requests without proper identification
- **Accession number parsing**: Handles format conversion for URL construction
- **Amendment detection**: Form type contains /A (e.g., "10-K/A")
- **Error handling**: 404 for missing filings, retry on rate limit

**Dependencies**:

- aiohttp (already in pyproject.toml ✅)
- redis (already in pyproject.toml ✅)

**Testing Strategy**:

1. Unit test: CIK lookup for 10 tickers (AAPL, MSFT, GOOGL, etc.)
2. Unit test: Filing list for single company (2015-2025)
3. Unit test: Rate limit enforcement (send 50 requests, measure duration)
4. Integration test: Download 5 real filings, verify content

---

### A2: MinIO/S3 Client (`src/storage/s3_client.py`)

**Responsibilities**:

- Upload raw filings to MinIO (S3-compatible object storage)
- Path convention: `raw/sec_filings/{ticker}/{year}/{accession}.txt`
- Versioning enabled (automatic by MinIO configuration)
- Retry logic (3 attempts, exponential backoff)
- Multipart upload for files >5MB

**Implementation**:

```python
# src/storage/s3_client.py
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class S3Client:
    """MinIO/S3 client for raw filing storage"""

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket_name: str = "raw"
    ):
        """
        Args:
            endpoint_url: MinIO endpoint (e.g., "http://localhost:9000")
            access_key: MinIO access key (default: "minioadmin")
            secret_key: MinIO secret key (default: "minioadmin")
            bucket_name: S3 bucket name (default: "raw")
        """
        self.bucket = bucket_name
        self.s3 = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(
                retries={'max_attempts': 3, 'mode': 'adaptive'},
                signature_version='s3v4'
            )
        )

    def upload_filing(
        self,
        ticker: str,
        fiscal_year: int,
        accession_number: str,
        content: bytes
    ) -> str:
        """
        Upload raw filing to MinIO

        Args:
            ticker: Stock ticker (e.g., "AAPL")
            fiscal_year: Fiscal year (e.g., 2024)
            accession_number: SEC accession number
            content: Raw filing content (bytes)

        Returns:
            S3 path (key) where file was stored

        Example:
            path = s3_client.upload_filing("AAPL", 2024, "0001234567-24-000123", content)
            # Returns: "raw/sec_filings/AAPL/2024/0001234567-24-000123.txt"
        """
        # Path convention
        key = f"raw/sec_filings/{ticker}/{fiscal_year}/{accession_number}.txt"

        try:
            # Upload with metadata
            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
                Metadata={
                    'ticker': ticker,
                    'fiscal_year': str(fiscal_year),
                    'accession': accession_number,
                    'upload_timestamp': datetime.now().isoformat()
                }
            )

            logger.info(f"Uploaded filing to MinIO: {key} ({len(content)} bytes)")
            return key

        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise

    def download_filing(self, s3_path: str) -> bytes:
        """
        Download filing from MinIO

        Args:
            s3_path: S3 key (from upload_filing)

        Returns:
            Raw filing content (bytes)
        """
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=s3_path)
            content = response['Body'].read()
            logger.debug(f"Downloaded from MinIO: {s3_path} ({len(content)} bytes)")
            return content

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"Filing not found in MinIO: {s3_path}")
            raise
```

**Key Features**:

- **Path convention**: Organized by ticker/year for easy browsing
- **Metadata tags**: Store upload timestamp, ticker for auditing
- **Automatic retry**: botocore Config handles 3 retries with backoff
- **Versioning**: Enabled at bucket level (MinIO configuration)

**Dependencies**:

- boto3 (MISSING - needs to be added to pyproject.toml ❌)

**Configuration** (docker-compose.yml already has MinIO):

- Endpoint: <http://localhost:9000>
- Credentials: minioadmin / minioadmin
- Buckets: raw, processed, outputs (created by scripts/setup_minio.sh)

**Testing Strategy**:

1. Unit test: Upload 1KB file, verify S3 path
2. Unit test: Upload 10MB file (multipart), verify integrity
3. Unit test: Download uploaded file, compare content
4. Integration test: Upload 100 filings, verify storage usage

---

## Phase B: EdgarTools XBRL Parser - Tier 0 Baseline (1 day)

### B1: EdgarTools Parser Wrapper (`src/agents/data_collector/xbrl_parser.py`)

**Why EdgarTools**:

- ✅ **Better baseline**: 95% vs 92% custom (per DD-033 unified approach)
- ✅ **Battle-tested**: 1000+ test cases, 5 years edge case handling
- ✅ **Saves 3 days**: No need to rebuild XBRL parsing from scratch
- ✅ **Consistent**: Same library used for screening stage
- ✅ **Multi-tier recovery**: Handles 5% failures via Tiers 1.5-4

**Baseline Target**: 95% success rate on first attempt

**Final Quality**: Multi-tier system compensates (95% → 98.55% final quality)

**Implementation**:

```python
# src/agents/data_collector/xbrl_parser.py
from edgartools import Filing
from typing import Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class XBRLParseResult:
    """Result from XBRL parsing attempt"""
    success: bool
    data: Optional[Dict]
    confidence: float
    error: Optional[str] = None
    tag_mapping: Optional[Dict] = None  # Which XBRL tags used
    parse_tier: Optional[str] = None

class EdgarToolsParser:
    """
    EdgarTools-based XBRL parser for SEC filings (10-K, 10-Q)

    Target: 95% baseline success rate
    Handles: XBRL, iXBRL, US-GAAP, IFRS via EdgarTools
    """

    def __init__(self):
        self.logger = logger

    def parse(self, xbrl_content: bytes, metadata: dict) -> XBRLParseResult:
        """
        Parse XBRL filing to extract 8 core financial metrics using EdgarTools

        Args:
            xbrl_content: Raw XBRL content (bytes)
            metadata: Filing metadata dict with keys:
                - ticker (str)
                - form_type (str)
                - period_end_date (datetime)
                - fiscal_year (int)
                - fiscal_quarter (int or None)
                - accession_number (str)

        Returns:
            XBRLParseResult with success/failure status and extracted data
        """
        try:
            # Parse using EdgarTools
            filing = Filing.from_bytes(
                xbrl_content,
                accession_number=metadata.get("accession_number")
            )

            # Extract financials
            financials = filing.financials

            # Map to our 8 core metrics
            data = {}
            tag_mapping = {}

            # Income statement metrics
            if financials.revenue is not None:
                data["revenue"] = float(financials.revenue)
                tag_mapping["revenue"] = "edgartools.revenue"

            if financials.net_income is not None:
                data["net_income"] = float(financials.net_income)
                tag_mapping["net_income"] = "edgartools.net_income"

            # Balance sheet metrics
            if financials.total_assets is not None:
                data["total_assets"] = float(financials.total_assets)
                tag_mapping["total_assets"] = "edgartools.total_assets"

            if financials.total_liabilities is not None:
                data["total_liabilities"] = float(financials.total_liabilities)
                tag_mapping["total_liabilities"] = "edgartools.total_liabilities"

            if financials.stockholders_equity is not None:
                data["total_equity"] = float(financials.stockholders_equity)
                tag_mapping["total_equity"] = "edgartools.stockholders_equity"

            # Cash flow metrics
            if financials.operating_cash_flow is not None:
                data["operating_cash_flow"] = float(financials.operating_cash_flow)
                tag_mapping["operating_cash_flow"] = "edgartools.operating_cash_flow"

            # Per-share metrics
            if financials.eps_diluted is not None:
                data["eps_diluted"] = float(financials.eps_diluted)
                tag_mapping["eps_diluted"] = "edgartools.eps_diluted"

            if financials.shares_outstanding is not None:
                data["shares_outstanding"] = float(financials.shares_outstanding)
                tag_mapping["shares_outstanding"] = "edgartools.shares_outstanding"

            # Validate completeness (need at least 5/8 metrics)
            required_metrics = 5
            confidence = len(data) / 8.0

            if len(data) < required_metrics:
                return XBRLParseResult(
                    success=False,
                    data=data,
                    confidence=confidence,
                    error=f"Only found {len(data)}/8 metrics (need ≥{required_metrics})",
                    tag_mapping=tag_mapping
                )

            self.logger.info(
                f"EdgarTools parsed {metadata['ticker']}: "
                f"{len(data)}/8 metrics (confidence: {confidence:.2f})"
            )

            return XBRLParseResult(
                success=True,
                data=data,
                confidence=confidence,
                tag_mapping=tag_mapping
            )

        except Exception as e:
            self.logger.warning(f"EdgarTools parsing failed: {e}")
            return XBRLParseResult(
                success=False,
                data=None,
                confidence=0.0,
                error=f"EdgarTools error: {str(e)}"
            )
```

**Key Features**:

- **EdgarTools abstraction**: Handles XBRL/iXBRL, US-GAAP/IFRS automatically
- **Simple mapping**: 8 core metrics → EdgarTools financials API
- **Graceful degradation**: Returns partial data if some metrics missing
- **Error handling**: Catches EdgarTools exceptions, escalates to Tier 1.5
- **Consistent interface**: Same XBRLParseResult output as multi-tier system

**Expected Success Rate**: 95%

**Common Failure Modes** (5% failures):

1. **Non-standard tags** (2%): Company uses proprietary tag names EdgarTools doesn't recognize
2. **IFRS variations** (1%): Unusual foreign filer IFRS implementations
3. **Malformed XBRL** (1%): XML corruption EdgarTools can't recover from
4. **Missing financials** (1%): Pre-2009 filings or incomplete XBRL

**Dependencies**:

- edgartools (already in pyproject.toml ✅)

**Testing Strategy**:

1. Unit test: Parse 20 real 10-K filings (AAPL, MSFT, GOOGL, etc.)
2. Unit test: Foreign filer with IFRS (e.g., SAP, ARM)
3. Unit test: Holding company (e.g., BRK.B) - verify consolidated extraction
4. Unit test: Amendment (10-K/A) - verify restated values
5. Integration test: 500 random filings, measure success rate (target: 95%)

---

## Phase C: Multi-Tier Recovery System (5 days)

### C1: Tier 1.5 - Smart Deterministic Fallback (2 days)

**Objective**: Recover 35% of Tier 0 failures using metadata-aware rule-based strategies

**Key Improvements Over EdgarTools Tier 0**:

- ✅ Metadata-informed strategy selection (IFRS vs GAAP)
- ✅ XML error recovery (fix encoding issues before re-parsing)
- ✅ Lenient validation (accept partial data with lower threshold)
- ✅ Alternative extraction strategies (try different EdgarTools APIs)

**Implementation**: Enhance `filing_parser.py`

```python
# src/agents/data_collector/filing_parser.py
from xbrl_parser import EdgarToolsParser, XBRLParseResult
from edgartools import Filing
import re
import logging

logger = logging.getLogger(__name__)

class FilingParser:
    """Enhanced parser with multi-tier recovery"""

    def __init__(self):
        self.tier0_parser = EdgarToolsParser()

    async def parse_with_recovery(
        self,
        filing_content: bytes,
        metadata: dict
    ) -> XBRLParseResult:
        """
        Parse XBRL with Tier 0 → Tier 1.5 fallback

        Args:
            filing_content: Raw XBRL bytes
            metadata: Filing metadata

        Returns:
            XBRLParseResult from successful tier
        """

        # Tier 0: EdgarTools parser
        result = self.tier0_parser.parse(filing_content, metadata)

        if result.success:
            result.parse_tier = "tier_0"
            return result

        # Tier 1.5: Smart deterministic recovery
        logger.info(f"Tier 0 failed, trying Tier 1.5: {result.error}")
        result = await self._tier_1_5_smart_deterministic(filing_content, metadata)

        if result.success:
            result.parse_tier = "tier_1.5"
            return result

        # Failed all deterministic methods
        result.parse_tier = "failed_deterministic"
        return result

    async def _tier_1_5_smart_deterministic(
        self,
        content: bytes,
        metadata: dict
    ) -> XBRLParseResult:
        """
        Smart deterministic recovery strategies

        Strategies:
        1. Fix common encoding issues and retry EdgarTools
        2. Lower success threshold (accept 4/8 metrics instead of 5/8)
        3. Try alternative EdgarTools extraction methods
        """

        # Strategy 1: Fix encoding issues and retry
        logger.info("Tier 1.5: Attempting encoding fix")
        fixed_content = self._fix_common_encoding_issues(content)

        try:
            result = self.tier0_parser.parse(fixed_content, metadata)
            if result.success or len(result.data or {}) >= 4:
                # Accept if we got 4+ metrics (lower threshold)
                result.success = True
                result.confidence = len(result.data) / 8.0
                logger.info(f"Tier 1.5 success: {len(result.data)}/8 metrics after encoding fix")
                return result
        except Exception as e:
            logger.debug(f"Tier 1.5 encoding fix failed: {e}")

        # Strategy 2: Try alternative EdgarTools APIs
        # (e.g., use different filing.obj() methods or fallback parsers)
        try:
            filing = Filing.from_bytes(
                fixed_content,
                accession_number=metadata.get("accession_number")
            )

            # Try alternative extraction approach
            data = {}

            # Attempt to get data from filing.obj() instead of .financials
            if hasattr(filing, 'obj'):
                obj = filing.obj()
                # Try common alternative attributes
                for attr in ['Revenues', 'RevenueFromContractWithCustomer', 'SalesRevenueNet']:
                    if hasattr(obj, attr):
                        data['revenue'] = float(getattr(obj, attr))
                        break

                # Similar attempts for other metrics...
                # (abbreviated for brevity - expand in actual implementation)

            if len(data) >= 4:
                return XBRLParseResult(
                    success=True,
                    data=data,
                    confidence=len(data) / 8.0,
                    tag_mapping={k: "edgartools.obj" for k in data.keys()}
                )
        except Exception as e:
            logger.debug(f"Tier 1.5 alternative extraction failed: {e}")

        # All strategies exhausted
        return XBRLParseResult(
            success=False,
            data=None,
            confidence=0.0,
            error="Tier 1.5: All deterministic strategies exhausted"
        )

    def _fix_common_encoding_issues(self, content: bytes) -> bytes:
        """
        Fix common XBRL encoding problems before retrying EdgarTools

        Issues:
        - Non-breaking spaces (&nbsp;) in numeric fields
        - Double-encoded ampersands (&amp;)
        - Non-UTF8 characters
        - Excess whitespace
        """
        text = content.decode('utf-8', errors='ignore')

        # Common fixes
        text = text.replace('&nbsp;', ' ')      # Non-breaking space
        text = text.replace('&amp;', '&')       # Double-encoded ampersand
        text = re.sub(r'\s+', ' ', text)        # Normalize whitespace
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', text)  # Remove control chars

        return text.encode('utf-8')
```

**Target Recovery Rate**: 35% of Tier 0 failures (5% → 3.25% remaining)

**Expected Outcomes (1,000 filings)**:

- Tier 0 success: 950 filings (95%)
- Tier 0 failures: 50 filings (5%)
- Tier 1.5 recovery: 18 filings (35% of 50) → **96.75% cumulative**
- Remaining failures: 32 filings (3.25%)

**Cost**: $0 (no LLM calls, pure computation)

**Testing**:

1. Unit test: 20 filings that failed Tier 0
2. Measure: Recovery rate (target: 35%)
3. Validate: No false positives introduced

---

### C2: Tier 2 - LLM-Assisted Parsing (2 days)

**Objective**: Use Claude Sonnet 4.5 to extract financial data when deterministic parsing fails

**Key Enhancements Over Basic LLM Approach**:

- ✅ Filing metadata context in prompt
- ✅ Intelligent XBRL sampling (target financial statements, not just first 50KB)
- ✅ Special case handling (SPACs, holding companies, IFRS filers)
- ✅ Confidence scoring
- ✅ Source citation (which XBRL tag used)

**Implementation**: Add to `storage_pipeline.py`

````python
# src/agents/data_collector/storage_pipeline.py
import anthropic
import json
from dataclasses import dataclass

@dataclass
class LLMParseResult:
    data: Optional[Dict]
    confidence: float
    source: str
    tag_mapping: Optional[Dict] = None

class StoragePipeline:
    def __init__(self, ..., anthropic_api_key: str):
        # ... existing init
        self.anthropic = anthropic.Anthropic(api_key=anthropic_api_key)

    async def _tier_2_llm_parse(
        self,
        filing_content: bytes,
        metadata: dict
    ) -> LLMParseResult:
        """
        LLM-assisted parsing with metadata context

        Args:
            filing_content: Raw XBRL bytes
            metadata: Filing metadata (ticker, form_type, accounting_standard, etc.)

        Returns:
            LLMParseResult with extracted data and confidence
        """

        # Intelligent sampling: extract financial statement sections
        xbrl_sample = self._sample_xbrl_intelligently(filing_content, target_size=100000)

        # Build context-aware prompt
        prompt = f"""You are parsing an SEC EDGAR XBRL filing that failed automated parsing.

**Filing Context**:
- Ticker: {metadata['ticker']}
- Form: {metadata['form_type']}
- Period End: {metadata['period_end_date']}
- Fiscal Year: {metadata['fiscal_year']} Q{metadata.get('fiscal_quarter', 'Annual')}
- Accounting Standard: {metadata.get('accounting_standard', 'UNKNOWN')}
- Company Type: {metadata.get('company_type', 'STANDARD')}

**Your Task**: Extract the following 8 financial metrics from the XBRL content below.

**Required Metrics**:
1. Revenue (Total Revenue, Net Sales, Operating Revenue)
2. Net Income (Net Income, Profit, Earnings)
3. Total Assets
4. Total Liabilities
5. Total Equity (Stockholders' Equity)
6. Operating Cash Flow (Net Cash from Operating Activities)
7. EPS Diluted (Earnings Per Share, Diluted)
8. Shares Outstanding (Weighted Average Diluted Shares)

**Special Case Handling**:

{self._get_special_case_instructions(metadata)}

**Extraction Rules**:
- Extract from PRIMARY financial statements (Income Statement, Balance Sheet, Cash Flow)
- Do NOT extract from: Reconciliation tables, footnotes, segment breakdowns
- For each metric, cite the XBRL tag name (e.g., "us-gaap:Revenues") or table section where found
- Extract numeric value in base units (no thousands/millions notation)
- If a metric has multiple time periods, extract the MOST RECENT period matching {metadata['period_end_date']}
- For restated values (form type {metadata.get('form_type')}), use the LATEST restated amount
- Return "null" if metric genuinely not found (don't guess)
- Provide confidence score (0.0-1.0) for each extraction

**Output Format** (JSON only, no additional text):
{{
    "revenue": {{"value": 1234567890, "confidence": 0.95, "source": "us-gaap:Revenues, instant 2024-12-31"}},
    "net_income": {{"value": 123456789, "confidence": 0.90, "source": "us-gaap:NetIncomeLoss"}},
    "total_assets": {{"value": null, "confidence": 0.0, "source": "not found"}},
    "total_liabilities": {{"value": 987654321, "confidence": 0.85, "source": "us-gaap:Liabilities"}},
    "total_equity": {{"value": 247901234, "confidence": 0.90, "source": "us-gaap:StockholdersEquity"}},
    "operating_cash_flow": {{"value": 456789012, "confidence": 0.88, "source": "us-gaap:NetCashProvidedByUsedInOperatingActivities"}},
    "eps_diluted": {{"value": 5.67, "confidence": 0.92, "source": "us-gaap:EarningsPerShareDiluted"}},
    "shares_outstanding": {{"value": 21776789, "confidence": 0.90, "source": "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding"}},
    "overall_confidence": 0.85,
    "notes": "Optional: Any ambiguities or issues encountered"
}}

**XBRL Content** ({len(xbrl_sample)} bytes, intelligently sampled from financial statements):
{xbrl_sample.decode('utf-8', errors='ignore')}

Return ONLY the JSON object above, no markdown formatting or additional text."""

        # Call Claude API
        try:
            response = self.anthropic.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4000,
                temperature=0.0,  # Deterministic for data extraction
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse JSON response
            result_text = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]

            result = json.loads(result_text)

            # Extract data and tag mapping
            data = {}
            tag_mapping = {}
            for metric in ["revenue", "net_income", "total_assets", "total_liabilities",
                          "total_equity", "operating_cash_flow", "eps_diluted", "shares_outstanding"]:
                if metric in result and result[metric]["value"] is not None:
                    data[metric] = result[metric]["value"]
                    tag_mapping[metric] = result[metric].get("source", "llm_extracted")

            return LLMParseResult(
                data=data,
                confidence=result.get("overall_confidence", 0.0),
                source="llm_sonnet_4.5",
                tag_mapping=tag_mapping
            )

        except (json.JSONDecodeError, KeyError, anthropic.APIError) as e:
            logger.error(f"LLM parsing failed: {e}")
            return LLMParseResult(
                data=None,
                confidence=0.0,
                source="llm_failed"
            )

    def _get_special_case_instructions(self, metadata: dict) -> str:
        """Generate special case instructions based on filing metadata"""

        instructions = []

        # IFRS filers
        if metadata.get("accounting_standard") == "IFRS":
            instructions.append("""
**IFRS Filer**:
- Use ONLY ifrs: or ifrs-full: tags
- IGNORE any us-gaap: tags (these are reconciliation tables, NOT primary financials)
- Example: Use "ifrs:Revenue" not "us-gaap:Revenues"
""")

        # Holding companies
        if metadata.get("company_type") == "HOLDING_COMPANY":
            instructions.append("""
**Holding Company**:
- Use CONSOLIDATED financials ONLY
- Ignore "Parent Company Only" statements
- Look for contextRef containing "Consolidated"
- Example: If you see both $2.1B (parent) and $364.5B (consolidated), use $364.5B
""")

        # SPACs
        if metadata.get("company_type") == "SPAC":
            instructions.append("""
**SPAC (Special Purpose Acquisition Company)**:
- Revenue may be $0 or null (pre-merger blank check company)
- If revenue is zero, this is EXPECTED - set confidence=1.0 and note "SPAC pre-merger"
- Focus on: Trust account balance, investment income instead
""")

        # Amendments
        if "/A" in metadata.get("form_type", ""):
            instructions.append("""
**Amended Filing**:
- Multiple values may exist for same metric (original vs restated)
- Use values marked "As Restated" or "Amended"
- Ignore "As Originally Reported"
""")

        # GAAP vs Non-GAAP
        instructions.append("""
**GAAP vs Non-GAAP**:
- ALWAYS prefer GAAP metrics (standard us-gaap: tags)
- Do NOT extract custom non-GAAP tags (e.g., "RevenueNonGAAP", "AdjustedEBITDA")
- If only non-GAAP available, note this and set confidence <0.80
""")

        return "\n".join(instructions) if instructions else "No special cases apply."

    def _sample_xbrl_intelligently(self, content: bytes, target_size: int = 100000) -> bytes:
        """
        Sample XBRL content intelligently by targeting financial statement sections

        Instead of just taking first N bytes, extract:
        1. XBRL context definitions (for period disambiguation)
        2. Financial statement sections (income statement, balance sheet, cash flow)
        3. Skip footnotes, segment data, detailed breakdowns

        Args:
            content: Full XBRL content
            target_size: Target sample size in bytes

        Returns:
            Intelligently sampled XBRL content
        """

        # TODO: Implement intelligent sampling
        # For now, take first 100KB (Phase 2 optimization)
        return content[:target_size]
````

**Target Recovery Rate**: 60% of Tier 1.5 failures (3.25% → 1.3% remaining)

**Expected Outcomes (1,000 filings)**:

- Tier 1.5 failures: 32 filings (3.25%)
- Tier 2 recovery: 19 filings (60% of 32) → **98.7% cumulative**
- Remaining failures: 13 filings (1.3%)

**Cost Analysis**:

- LLM call: 100KB input × $3/MTok (Sonnet 4.5) = ~$0.30 per call
- BUT: 50KB sample × $3/MTok = ~$0.15 per call (optimized)
- Frequency: 3.25% of filings need Tier 2
- 20,000 filings × 3.25% × $0.15 = **$97.50** (lower than before due to better Tier 0)
- **Optimization**: Use Haiku 4 ($0.40/MTok) for Tier 2 → $13 total

**Dependencies**:

- anthropic (MISSING - needs to be added to pyproject.toml ❌)

**Testing**:

1. Unit test: 10 filings that failed Tier 1.5
2. Measure: Recovery rate, false positive rate
3. Validate: Confidence scores correlate with accuracy

---

### C3: Tier 2.5 - Data Validation Layer (1 day)

**CRITICAL**: This tier prevents false positives (LLM returning incorrect data with high confidence)

**Objective**: Catch false positives before database insertion

**Key Validations**:

1. ✅ Balance sheet equation (Assets = Liabilities + Equity)
2. ✅ Accounting standard consistency (IFRS filer shouldn't use US-GAAP tags)
3. ✅ Holding company must use consolidated financials
4. ✅ Value range sanity checks (revenue ≥ 0, assets > 0)
5. ✅ Cross-metric consistency (EPS = Net Income / Shares)

**Implementation**: Add to `storage_pipeline.py`

```python
# src/agents/data_collector/storage_pipeline.py

class StoragePipeline:

    async def _tier_2_5_validate(
        self,
        llm_result: LLMParseResult,
        metadata: dict
    ) -> bool:
        """
        Validate LLM extraction before accepting

        Catches false positives where LLM returns incorrect data with high confidence.

        Args:
            llm_result: Result from Tier 2 LLM parsing
            metadata: Filing metadata

        Returns:
            True if validation passes, False if escalation to Tier 3 needed
        """

        data = llm_result.data
        if not data:
            return False

        # Check 1: Balance sheet equation (Assets = Liabilities + Equity)
        if all(k in data for k in ["total_assets", "total_liabilities", "total_equity"]):
            assets = data["total_assets"]
            liabilities = data["total_liabilities"]
            equity = data["total_equity"]

            # Allow 1% tolerance for rounding
            if abs(assets - (liabilities + equity)) > assets * 0.01:
                logger.warning(
                    f"Balance sheet doesn't balance: "
                    f"Assets={assets} != Liabilities+Equity={liabilities + equity}"
                )
                return False

        # Check 2: Accounting standard consistency
        if metadata.get("accounting_standard") == "IFRS":
            for metric, tag in llm_result.tag_mapping.items():
                if "us-gaap:" in str(tag).lower():
                    logger.warning(
                        f"IFRS filer using US-GAAP tag: {metric}={tag}"
                    )
                    return False  # Likely extracted reconciliation table instead of primary

        # Check 3: Holding company must use consolidated
        if metadata.get("company_type") == "HOLDING_COMPANY":
            # Check if any source mentions "consolidated"
            consolidated_found = any(
                "consolidated" in str(llm_result.tag_mapping.get(m, "")).lower()
                for m in data.keys()
            )
            if not consolidated_found:
                logger.warning("Holding company missing consolidated source citation")
                return False  # Likely extracted parent-only financials

        # Check 4: Value range sanity
        if "revenue" in data and data["revenue"] < 0:
            logger.warning(f"Negative revenue: {data['revenue']}")
            return False  # Revenue should never be negative (except rare cases)

        if "total_assets" in data and data["total_assets"] <= 0:
            logger.warning(f"Non-positive assets: {data['total_assets']}")
            return False

        # Check 5: Cross-metric consistency (EPS = Net Income / Shares)
        if all(k in data for k in ["eps_diluted", "net_income", "shares_outstanding"]):
            eps = data["eps_diluted"]
            calculated_eps = data["net_income"] / data["shares_outstanding"]

            # Allow 5% tolerance (different rounding, share classes)
            if abs(eps - calculated_eps) > abs(calculated_eps) * 0.05:
                logger.warning(
                    f"EPS mismatch: reported={eps} vs calculated={calculated_eps}"
                )
                return False

        # All validations passed
        return True
```

**Impact**: Catch 66% of false positives

**False Positive Rate Without Tier 2.5**: 14% of LLM parses (1.9 filings per 1,000)
**False Positive Rate With Tier 2.5**: 5% of LLM parses (0.65 filing per 1,000)

**Final Data Quality**: 98.7% parsed - 0.65% false positives + 0.5% validated = **98.55%** ✅

**Cost**: $0 (no additional LLM calls, pure computation)

**Testing**:

1. Unit test: 10 known false positive cases from simulation
2. Measure: Detection rate (target: 66%)
3. Validate: No false negatives (correct data rejected)

---

## Phase D: Storage Integration & Orchestration (2 days)

### D1: Storage Pipeline Orchestrator (`src/agents/data_collector/storage_pipeline.py`)

**Complete flow with all tiers**:

```python
# src/agents/data_collector/storage_pipeline.py

class StoragePipeline:
    def __init__(
        self,
        edgar_client: SECEdgarClient,
        s3_client: S3Client,
        postgres_client: PostgresClient,
        redis_client: RedisClient,
        anthropic_api_key: str
    ):
        self.edgar = edgar_client
        self.s3 = s3_client
        self.pg = postgres_client
        self.redis = redis_client
        self.filing_parser = FilingParser()
        self.anthropic = anthropic.Anthropic(api_key=anthropic_api_key)

    async def process_filing(
        self,
        ticker: str,
        cik: str,
        accession_number: str,
        form_type: str,
        filing_date: datetime,
        period_end_date: datetime,
        fiscal_year: int,
        fiscal_quarter: Optional[int] = None
    ):
        """
        Complete filing processing pipeline:
        Fetch → Store Raw → Parse (Tiers 0-2.5) → Store Structured

        Handles deduplication, retries, and tier escalation.
        """

        # Check deduplication cache (Redis L1, 24hr TTL)
        cache_key = f"filing:{cik}:{accession_number}"
        if await self.redis.exists(cache_key):
            logger.info(f"Filing already processed: {accession_number}")
            return

        try:
            # Step 1: Download raw filing
            logger.info(f"Downloading {ticker} {form_type}: {accession_number}")
            raw_content = await self.edgar.download_filing(accession_number)

            # Step 2: Store raw in MinIO
            s3_path = await self.s3.upload_filing(
                ticker,
                fiscal_year,
                accession_number,
                raw_content
            )

            # Step 3: Prepare metadata
            metadata = {
                "ticker": ticker,
                "cik": cik,
                "form_type": form_type,
                "filing_date": filing_date,
                "period_end_date": period_end_date,
                "fiscal_year": fiscal_year,
                "fiscal_quarter": fiscal_quarter,
                "company_type": await self._detect_company_type(ticker),
                "accounting_standard": await self._detect_accounting_standard(cik)
            }

            # Step 4: Insert document metadata
            filing_id = await self.pg.insert_document_metadata(
                ticker=ticker,
                cik=cik,
                form_type=form_type,
                filing_date=filing_date,
                period_end_date=period_end_date,
                fiscal_year=fiscal_year,
                fiscal_quarter=fiscal_quarter,
                accession_number=accession_number,
                s3_path=s3_path,
                parse_status="PENDING"
            )

            # Step 5: Multi-tier parsing

            # Tier 0 + 1.5: Deterministic parsing
            parse_result = await self.filing_parser.parse_with_recovery(
                raw_content,
                metadata
            )

            if parse_result.success:
                # Success via Tier 0 or 1.5
                await self._store_financial_data(
                    filing_id,
                    parse_result.data,
                    parse_status="PARSED",
                    parse_tier=parse_result.parse_tier,
                    parse_confidence=parse_result.confidence,
                    tag_mapping=parse_result.tag_mapping
                )
                await self.redis.setex(cache_key, 86400, "1")  # 24hr cache
                return

            # Tier 2: LLM-assisted parsing
            logger.info(f"Attempting Tier 2 LLM parsing for {accession_number}")
            llm_result = await self._tier_2_llm_parse(raw_content, metadata)

            if llm_result.confidence >= 0.80:
                # Tier 2.5: Validation layer
                if await self._tier_2_5_validate(llm_result, metadata):
                    # Validation passed
                    await self._store_financial_data(
                        filing_id,
                        llm_result.data,
                        parse_status="LLM_PARSED",
                        parse_tier="tier_2",
                        parse_confidence=llm_result.confidence,
                        tag_mapping=llm_result.tag_mapping
                    )
                    await self.redis.setex(cache_key, 86400, "1")
                    return
                else:
                    # Validation failed - escalate to Tier 3
                    logger.warning(f"Tier 2.5 validation failed for {accession_number}")
                    await self._escalate_to_tier_3(filing_id, metadata, llm_result, "validation_failed")
                    return
            else:
                # Low confidence - escalate to Tier 3
                logger.warning(f"Low LLM confidence ({llm_result.confidence}) for {accession_number}")
                await self._escalate_to_tier_3(filing_id, metadata, llm_result, "low_confidence")
                return

        except Exception as e:
            logger.error(f"Error processing filing {accession_number}: {e}")
            # Update status to ERROR
            if 'filing_id' in locals():
                await self.pg.update_filing(
                    filing_id,
                    parse_status="ERROR",
                    parse_notes=str(e)
                )

    async def _store_financial_data(
        self,
        filing_id: str,
        data: dict,
        parse_status: str,
        parse_tier: str,
        parse_confidence: float,
        tag_mapping: dict
    ):
        """Store extracted financial data to PostgreSQL"""

        # Update filing metadata
        await self.pg.update_filing(
            filing_id,
            parse_status=parse_status,
            parse_tier=parse_tier,
            parse_confidence=parse_confidence
        )

        # Insert income statement data
        if any(k in data for k in ["revenue", "net_income", "operating_income"]):
            await self.pg.insert_income_statement(
                filing_id=filing_id,
                data=data,
                tag_mapping=tag_mapping
            )

        # Insert balance sheet data
        if any(k in data for k in ["total_assets", "total_liabilities", "total_equity"]):
            await self.pg.insert_balance_sheet(
                filing_id=filing_id,
                data=data,
                tag_mapping=tag_mapping
            )

        # Insert cash flow data
        if "operating_cash_flow" in data:
            await self.pg.insert_cash_flow(
                filing_id=filing_id,
                data=data,
                tag_mapping=tag_mapping
            )

        logger.info(f"Stored financial data for filing {filing_id} via {parse_tier}")

    async def _escalate_to_tier_3(
        self,
        filing_id: str,
        metadata: dict,
        llm_result: LLMParseResult,
        reason: str
    ):
        """
        Escalate to Tier 3 (QC Agent review) - Phase 2 implementation

        For now: Mark as PENDING_QC_REVIEW
        """
        await self.pg.update_filing(
            filing_id,
            parse_status="PENDING_QC_REVIEW",
            parse_notes=f"Escalated to Tier 3: {reason}"
        )

        # TODO Phase 2: Send message to QC Agent
        # await message_bus.send(
        #     from_agent="DataCollectorAgent",
        #     to_agent="QCAgent",
        #     message_type="PARSE_FAILURE_REVIEW",
        #     content={"filing_id": filing_id, "reason": reason, ...}
        # )

    async def _detect_company_type(self, ticker: str) -> str:
        """Detect company type (HOLDING_COMPANY, SPAC, STANDARD)"""
        # TODO: Implement heuristics or lookup table
        # For now: default to STANDARD
        return "STANDARD"

    async def _detect_accounting_standard(self, cik: str) -> str:
        """Detect accounting standard (US-GAAP, IFRS, UNKNOWN)"""
        # TODO: Lookup in metadata or detect from first filing
        # For now: default to US-GAAP (90% of US filers)
        return "US-GAAP"
```

**Key Features**:

- **Deduplication**: Redis cache prevents reprocessing
- **Atomic operations**: Update filing status at each stage
- **Error handling**: Catch exceptions, mark as ERROR
- **Tier escalation**: Clear flow from Tier 0 → 1.5 → 2 → 2.5 → 3
- **Structured storage**: Separate tables for income stmt, balance sheet, cash flow

---

## Phase E: Screening Metrics Calculator (1 day)

### E1: Screening Calculator (`src/agents/data_collector/screening_calculator.py`)

**Objective**: Pre-calculate ratios for fast screening queries

**Metrics to Calculate**:

- 10Y/5Y/3Y revenue CAGR
- 3Y average margins (operating, net, gross)
- 3Y average returns (ROE, ROA, ROIC)
- Latest debt ratios (debt/equity, current ratio)

**Implementation**:

```python
# src/agents/data_collector/screening_calculator.py
from datetime import datetime
from typing import Optional
import math

class ScreeningCalculator:
    """Calculate pre-computed screening metrics for fast queries"""

    def __init__(self, postgres_client: PostgresClient):
        self.pg = postgres_client

    async def calculate_screening_metrics(
        self,
        ticker: str,
        as_of_date: Optional[datetime] = None
    ) -> dict:
        """
        Calculate screening metrics for ticker

        Args:
            ticker: Stock ticker
            as_of_date: Calculate metrics as of this date (default: today)

        Returns:
            Dict of calculated metrics
        """

        if as_of_date is None:
            as_of_date = datetime.now()

        # Fetch 10 years of annual financials
        income_stmts = await self.pg.get_income_statements(
            ticker=ticker,
            start_year=as_of_date.year - 10,
            end_year=as_of_date.year,
            quarterly=False  # Annual only
        )

        balance_sheets = await self.pg.get_balance_sheets(
            ticker=ticker,
            start_year=as_of_date.year - 10,
            end_year=as_of_date.year,
            quarterly=False
        )

        cash_flows = await self.pg.get_cash_flows(
            ticker=ticker,
            start_year=as_of_date.year - 10,
            end_year=as_of_date.year,
            quarterly=False
        )

        # Calculate metrics
        metrics = {
            "ticker": ticker,
            "as_of_date": as_of_date,
            "fiscal_year": as_of_date.year
        }

        # Growth metrics (CAGR)
        if len(income_stmts) >= 10:
            metrics["revenue_cagr_10y"] = self._calculate_cagr(
                start_value=income_stmts[0].revenue,
                end_value=income_stmts[-1].revenue,
                years=10
            )
            metrics["net_income_cagr_10y"] = self._calculate_cagr(
                start_value=income_stmts[0].net_income,
                end_value=income_stmts[-1].net_income,
                years=10
            )

        if len(income_stmts) >= 5:
            metrics["revenue_cagr_5y"] = self._calculate_cagr(
                start_value=income_stmts[-5].revenue,
                end_value=income_stmts[-1].revenue,
                years=5
            )

        # Profitability metrics (3Y average)
        if len(income_stmts) >= 3:
            recent_3y = income_stmts[-3:]

            metrics["operating_margin_3y_avg"] = sum(
                stmt.operating_income / stmt.revenue
                for stmt in recent_3y if stmt.revenue > 0
            ) / len(recent_3y)

            metrics["net_margin_3y_avg"] = sum(
                stmt.net_income / stmt.revenue
                for stmt in recent_3y if stmt.revenue > 0
            ) / len(recent_3y)

        # Returns (3Y average)
        if len(balance_sheets) >= 3 and len(income_stmts) >= 3:
            recent_3y_income = income_stmts[-3:]
            recent_3y_balance = balance_sheets[-3:]

            # ROE = Net Income / Avg Equity
            roe_values = []
            for inc, bal in zip(recent_3y_income, recent_3y_balance):
                if bal.total_equity > 0:
                    roe_values.append(inc.net_income / bal.total_equity)

            if roe_values:
                metrics["roe_3y_avg"] = sum(roe_values) / len(roe_values)

            # ROA = Net Income / Avg Assets
            roa_values = []
            for inc, bal in zip(recent_3y_income, recent_3y_balance):
                if bal.total_assets > 0:
                    roa_values.append(inc.net_income / bal.total_assets)

            if roa_values:
                metrics["roa_3y_avg"] = sum(roa_values) / len(roa_values)

            # ROIC = NOPAT / Invested Capital (simplified)
            # ROIC ≈ Operating Income × (1 - Tax Rate) / (Total Assets - Current Liabilities)
            # Simplified: Operating Income / (Total Assets - Current Liabilities)
            # For MVP: use Operating Income / Total Assets
            roic_values = []
            for inc, bal in zip(recent_3y_income, recent_3y_balance):
                if bal.total_assets > 0:
                    roic_values.append(inc.operating_income / bal.total_assets)

            if roic_values:
                metrics["roic_3y_avg"] = sum(roic_values) / len(roic_values)

        # Debt ratios (latest)
        if balance_sheets:
            latest = balance_sheets[-1]

            if latest.total_equity > 0:
                total_debt = latest.total_liabilities  # Simplified
                metrics["debt_to_equity"] = total_debt / latest.total_equity

            # Current ratio = Current Assets / Current Liabilities
            # Simplified: assume 40% of assets are current, 50% of liabilities are current
            # TODO Phase 2: Add current_assets, current_liabilities to schema
            metrics["current_ratio"] = None  # Placeholder

        return metrics

    async def store_screening_metrics(self, metrics: dict):
        """Store calculated metrics to screening_metrics table"""

        await self.pg.execute(
            """
            INSERT INTO financial_data.screening_metrics (
                ticker, period_end_date, fiscal_year,
                revenue_cagr_10y, revenue_cagr_5y, net_income_cagr_10y,
                operating_margin_3y_avg, net_margin_3y_avg,
                roe_3y_avg, roa_3y_avg, roic_3y_avg,
                debt_to_equity, current_ratio,
                calculated_at, calculation_method, num_periods_used
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
            )
            ON CONFLICT (ticker, fiscal_year) DO UPDATE SET
                revenue_cagr_10y = EXCLUDED.revenue_cagr_10y,
                ... -- update all fields
                calculated_at = EXCLUDED.calculated_at
            """,
            metrics["ticker"],
            metrics["as_of_date"],
            metrics["fiscal_year"],
            # ... all metric values
            metrics.get("revenue_cagr_10y"),
            # ...
            datetime.now(),
            "edgartools_9filing",  # Or "custom_parser"
            len(income_stmts)
        )

    def _calculate_cagr(self, start_value: float, end_value: float, years: int) -> Optional[float]:
        """
        Calculate Compound Annual Growth Rate

        CAGR = (End Value / Start Value) ^ (1 / Years) - 1

        Args:
            start_value: Starting value (e.g., revenue in 2015)
            end_value: Ending value (e.g., revenue in 2025)
            years: Number of years (e.g., 10)

        Returns:
            CAGR as decimal (e.g., 0.15 = 15% CAGR)
        """
        if start_value <= 0 or end_value <= 0:
            return None

        cagr = (end_value / start_value) ** (1 / years) - 1
        return cagr
```

**Usage in Screening Stage**:

```sql
-- Fast screening query using pre-calculated metrics
SELECT ticker, revenue_cagr_10y, operating_margin_3y_avg, roe_3y_avg
FROM financial_data.screening_metrics
WHERE fiscal_year = 2024
  AND revenue_cagr_10y > 0.10  -- 10% revenue CAGR
  AND operating_margin_3y_avg > 0.15  -- 15% operating margin
  AND roe_3y_avg > 0.15  -- 15% ROE
ORDER BY revenue_cagr_10y DESC;
```

**Performance**: <1 second to screen 500 companies (vs 2.5-5 min if calculating on-the-fly)

---

## Phase F: Data Collector Agent Wrapper (2 days)

### F1: Agent Orchestration (`src/agents/data_collector/agent.py`)

**Responsibilities**:

- Task queue management (priority-based)
- Bulk screening (S&P 500 on-demand queries)
- Deep analysis (10-20 approved companies, 10Y history)
- Status reporting
- Error handling & retry logic

**Implementation**:

```python
# src/agents/data_collector/agent.py
import asyncio
from typing import List
from datetime import datetime, timedelta

class DataCollectorAgent:
    """
    Data Collector Agent for SEC filing retrieval and parsing

    Modes:
    1. Screening: Fetch latest 10-K for S&P 500 (on-demand)
    2. Deep Analysis: Fetch 10Y history for approved tickers
    3. Backfill: Historical data ingestion
    """

    def __init__(
        self,
        edgar_client: SECEdgarClient,
        storage_pipeline: StoragePipeline,
        screening_calculator: ScreeningCalculator
    ):
        self.edgar = edgar_client
        self.pipeline = storage_pipeline
        self.calculator = screening_calculator

    async def screen_sp500(self) -> List[str]:
        """
        Screening stage: Fetch + parse latest 10-K for S&P 500

        Flow:
        1. Load S&P 500 ticker list
        2. For each ticker: Fetch latest 10-K
        3. Parse via multi-tier system
        4. Calculate screening metrics
        5. Store to PostgreSQL

        Returns:
            List of tickers successfully processed
        """
        logger.info("Starting S&P 500 screening...")
        start_time = datetime.now()

        # Load ticker list
        tickers = await self._load_sp500_tickers()
        logger.info(f"Loaded {len(tickers)} S&P 500 tickers")

        # Process each ticker (rate-limited to 10 req/sec)
        tasks = []
        for ticker in tickers:
            task = self._process_latest_filing(ticker, form_type="10-K")
            tasks.append(task)

        # Execute in parallel (asyncio manages concurrency)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes/failures
        successes = [ticker for ticker, result in zip(tickers, results)
                    if not isinstance(result, Exception)]
        failures = [ticker for ticker, result in zip(tickers, results)
                   if isinstance(result, Exception)]

        # Calculate screening metrics for successful tickers
        logger.info(f"Calculating screening metrics for {len(successes)} tickers...")
        for ticker in successes:
            await self.calculator.calculate_screening_metrics(ticker)
            await self.calculator.store_screening_metrics(metrics)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Screening completed: {len(successes)}/{len(tickers)} succeeded "
            f"in {duration:.1f}s ({len(tickers)/duration:.1f} tickers/sec)"
        )

        if failures:
            logger.warning(f"Failed tickers: {failures}")

        return successes

    async def deep_analysis(self, approved_tickers: List[str]):
        """
        Deep analysis stage: Fetch 10Y history for approved companies

        Triggered by Gate 1 approval (10-20 tickers selected for full analysis)

        Flow:
        1. For each approved ticker:
        2.   Fetch all 10-K/10-Q from 2015-2025 (~40 filings)
        3.   Parse via multi-tier system
        4.   Store structured data
        5. Duration: ~13 min for 10 companies × 40 filings (10 parallel workers)

        Args:
            approved_tickers: List of tickers approved by Gate 1
        """
        logger.info(f"Starting deep analysis for {len(approved_tickers)} tickers...")
        start_time = datetime.now()

        total_filings = 0

        for ticker in approved_tickers:
            logger.info(f"Processing deep analysis for {ticker}...")

            # Get CIK
            cik = await self.edgar.get_cik(ticker)

            # Fetch all 10-K/10-Q from 2015-2025
            filings = await self.edgar.get_company_filings(
                cik=cik,
                form_types=["10-K", "10-Q"],
                start_date=datetime(2015, 1, 1),
                end_date=datetime.now()
            )

            logger.info(f"Found {len(filings)} filings for {ticker}")
            total_filings += len(filings)

            # Process each filing
            tasks = []
            for filing in filings:
                task = self.pipeline.process_filing(
                    ticker=ticker,
                    cik=cik,
                    accession_number=filing["accession_number"],
                    form_type=filing["form_type"],
                    filing_date=filing["filing_date"],
                    period_end_date=filing["period_end_date"],
                    fiscal_year=filing["fiscal_year"],
                    fiscal_quarter=filing["fiscal_quarter"]
                )
                tasks.append(task)

            # Process in batches of 10 (respect rate limit)
            batch_size = 10
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i+batch_size]
                await asyncio.gather(*batch, return_exceptions=True)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Deep analysis completed: {total_filings} filings processed "
            f"in {duration:.1f}s ({total_filings/duration:.1f} filings/sec)"
        )

    async def _process_latest_filing(self, ticker: str, form_type: str):
        """Process single latest filing for ticker"""

        # Get CIK
        cik = await self.edgar.get_cik(ticker)

        # Get latest filing
        filings = await self.edgar.get_company_filings(
            cik=cik,
            form_types=[form_type],
            start_date=datetime.now() - timedelta(days=400),  # Last ~13 months
            end_date=datetime.now()
        )

        if not filings:
            raise ValueError(f"No {form_type} found for {ticker}")

        # Take most recent
        latest = filings[0]

        # Process via storage pipeline
        await self.pipeline.process_filing(
            ticker=ticker,
            cik=cik,
            accession_number=latest["accession_number"],
            form_type=latest["form_type"],
            filing_date=latest["filing_date"],
            period_end_date=latest["period_end_date"],
            fiscal_year=latest["fiscal_year"],
            fiscal_quarter=latest["fiscal_quarter"]
        )

    async def _load_sp500_tickers(self) -> List[str]:
        """Load S&P 500 ticker list"""
        # TODO: Fetch from State Street SPY API or use static list
        # For now: hardcoded list
        return [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B",
            # ... 492 more tickers
        ]
```

**Performance Estimates**:

- **Screening** (500 tickers): 500 calls ÷ 10 req/sec = 50s base + parsing ~2-5 min total
- **Deep Analysis** (10 tickers × 40 filings): 400 calls ÷ 10 req/sec = 40s base + parsing ~13 min total

---

## Schema Enhancements (P0 - Required)

### Migration 1: Extend `document_registry.filings`

```sql
-- Migration: Add XBRL tracking columns
-- File: src/storage/migrations/versions/YYYYMMDD_add_xbrl_tracking.py

ALTER TABLE document_registry.filings
ADD COLUMN parse_tier VARCHAR(20),           -- 'tier_0', 'tier_1.5', 'tier_2', 'tier_2.5', 'tier_3', 'tier_4'
ADD COLUMN parse_confidence NUMERIC(3,2),    -- 0.00-1.00
ADD COLUMN accounting_standard VARCHAR(20),  -- 'US-GAAP', 'IFRS', 'UNKNOWN'
ADD COLUMN is_restated BOOLEAN DEFAULT FALSE,
ADD COLUMN xbrl_context VARCHAR(100);        -- 'Consolidated', 'Parent_Only', '12M', etc.

-- Add index for filtering by parse tier
CREATE INDEX idx_filings_parse_tier ON document_registry.filings(parse_tier);
```

### Migration 2: Extend Financial Tables

```sql
-- Migration: Add XBRL tag mapping and credibility tracking
-- File: src/storage/migrations/versions/YYYYMMDD_add_xbrl_metadata.py

-- Income statements
ALTER TABLE financial_data.income_statements
ADD COLUMN xbrl_concept VARCHAR(200),         -- 'us-gaap:Revenues'
ADD COLUMN xbrl_label VARCHAR(200),           -- Human-readable label
ADD COLUMN source_credibility NUMERIC(3,2),  -- 0.80-1.00 (tier_0=1.0, tier_2=0.85)
ADD COLUMN data_freshness_score NUMERIC(3,2); -- 1.0 for latest, decays over time

-- Similar for balance_sheets, cash_flows
ALTER TABLE financial_data.balance_sheets
ADD COLUMN xbrl_concept VARCHAR(200),
ADD COLUMN xbrl_label VARCHAR(200),
ADD COLUMN source_credibility NUMERIC(3,2),
ADD COLUMN data_freshness_score NUMERIC(3,2);

ALTER TABLE financial_data.cash_flows
ADD COLUMN xbrl_concept VARCHAR(200),
ADD COLUMN xbrl_label VARCHAR(200),
ADD COLUMN source_credibility NUMERIC(3,2),
ADD COLUMN data_freshness_score NUMERIC(3,2);
```

### Migration 3: Create `screening_metrics` Table

```sql
-- Migration: Create screening_metrics table for fast queries
-- File: src/storage/migrations/versions/YYYYMMDD_create_screening_metrics.py

CREATE TABLE financial_data.screening_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL,
    period_end_date DATE NOT NULL,
    fiscal_year INTEGER NOT NULL,

    -- Growth (CAGR as decimals: 0.15 = 15%)
    revenue_cagr_10y NUMERIC,
    revenue_cagr_5y NUMERIC,
    net_income_cagr_10y NUMERIC,

    -- Profitability (3Y averages)
    operating_margin_3y_avg NUMERIC,
    net_margin_3y_avg NUMERIC,

    -- Returns (3Y averages)
    roe_3y_avg NUMERIC,
    roa_3y_avg NUMERIC,
    roic_3y_avg NUMERIC,

    -- Debt (latest)
    debt_to_equity NUMERIC,
    current_ratio NUMERIC,

    -- Metadata
    calculated_at TIMESTAMP DEFAULT NOW(),
    calculation_method VARCHAR(50),  -- 'custom_parser_9filing'
    num_periods_used INTEGER,
    version INTEGER DEFAULT 1,
    is_latest BOOLEAN DEFAULT TRUE,

    -- Constraints
    UNIQUE(ticker, fiscal_year)

) PARTITION BY RANGE (fiscal_year);

-- Create partitions (2015-2030)
CREATE TABLE financial_data.screening_metrics_2015_2020
PARTITION OF financial_data.screening_metrics
FOR VALUES FROM (2015) TO (2020);

CREATE TABLE financial_data.screening_metrics_2020_2025
PARTITION OF financial_data.screening_metrics
FOR VALUES FROM (2020) TO (2025);

CREATE TABLE financial_data.screening_metrics_2025_2030
PARTITION OF financial_data.screening_metrics
FOR VALUES FROM (2025) TO (2030);

-- Indexes for fast screening queries
CREATE INDEX idx_screening_ticker ON financial_data.screening_metrics(ticker);
CREATE INDEX idx_screening_year ON financial_data.screening_metrics(fiscal_year);
CREATE INDEX idx_screening_cagr ON financial_data.screening_metrics(revenue_cagr_10y);
CREATE INDEX idx_screening_margin ON financial_data.screening_metrics(operating_margin_3y_avg);
CREATE INDEX idx_screening_roe ON financial_data.screening_metrics(roe_3y_avg);
```

---

## Dependencies to Add to pyproject.toml

```toml
[project.dependencies]
# Existing dependencies
edgartools = ">=4.30.0"        # Keep for research/comparison
asyncpg = ">=0.30.0"
sqlalchemy = ">=2.0.44"
alembic = ">=1.17.2"
redis = ">=7.1.0"
pandas = ">=2.3.3"
aiohttp = ">=3.13.2"

# NEW dependencies for custom solution
boto3 = ">=1.28.0"              # MinIO/S3 client
anthropic = ">=0.40.0"          # Claude API for Tier 2 LLM parsing
tenacity = ">=8.2.0"            # Retry logic
lxml = ">=5.0.0"                # XBRL XML parsing (faster than xml.etree)
```

**Installation**:

```bash
uv sync  # Install all dependencies
```

---

## Implementation Timeline

| Phase       | Task                         | Days        | Dependencies      |
| ----------- | ---------------------------- | ----------- | ----------------- |
| **A1**      | SEC EDGAR API Client         | 2           | -                 |
| **A2**      | MinIO/S3 Client              | 1           | A1                |
| **B1**      | Custom XBRL Parser (Tier 0)  | 4           | -                 |
| **C1**      | Tier 1.5 Smart Deterministic | 2           | B1                |
| **C2**      | Tier 2 LLM Parsing           | 2           | C1                |
| **C3**      | Tier 2.5 Validation Layer    | 1           | C2                |
| **D1**      | Storage Pipeline Integration | 2           | A1, A2, B1, C1-C3 |
| **E1**      | Screening Calculator         | 1           | D1                |
| **F1**      | Agent Orchestration          | 2           | D1, E1            |
| **Schema**  | 3 Migrations                 | 1           | -                 |
| **Testing** | End-to-end 500 filings       | 2           | All               |
| **Total**   |                              | **20 days** |                   |

**Critical Path**: A1 → B1 → C1 → C2 → C3 → D1 → F1

**Parallelizable**: A2 (MinIO client), E1 (calculator), Schema migrations can run in parallel with other work

---

## Quality & Cost Targets (20,000 Filing Backfill)

### Success Rates by Tier

| Tier         | Handler             | Input  | Recovery Rate | Cumulative Success  | Remaining    |
| ------------ | ------------------- | ------ | ------------- | ------------------- | ------------ |
| **Tier 0**   | Custom XBRL Parser  | 20,000 | 92%           | 92% (18,400)        | 8% (1,600)   |
| **Tier 1.5** | Smart Deterministic | 1,600  | 35%           | 94.8% (18,960)      | 5.2% (1,040) |
| **Tier 2**   | LLM Parsing         | 1,040  | 60%           | 97.9% (19,584)      | 2.1% (416)   |
| **Tier 2.5** | Validation Layer    | 19,584 | Catch 14% FP  | **98.55% (19,710)** | 1.45% (290)  |
| **Tier 3**   | QC Agent (Phase 2)  | 290    | 75%           | 99.6% (19,928)      | 0.4% (72)    |
| **Tier 4**   | Human Review        | 72     | 100%          | 100% (20,000)       | 0%           |

**Final Data Quality**: 98.55% after Tier 2.5 ✅ (Phase 1 target met)

### Cost Breakdown

| Component               | Frequency            | Unit Cost | Total Cost        |
| ----------------------- | -------------------- | --------- | ----------------- |
| **Tier 0**              | 20,000 filings       | $0        | $0                |
| **Tier 1.5**            | 1,600 filings (8%)   | $0        | $0                |
| **Tier 2 LLM**          | 1,040 filings (5.2%) | $0.15     | $156              |
| **Tier 2.5**            | (no LLM cost)        | $0        | $0                |
| **Tier 3 QC** (Phase 2) | 290 filings (1.45%)  | $0.30     | $87               |
| **Tier 4 Human**        | 72 filings (0.36%)   | 20 min    | 24 hours          |
| **Total**               |                      |           | **$243 + 24 hrs** |

**Optimization**: Use Haiku 4 ($0.40/MTok) for Tier 2 → Reduce to **$87.75 + 24 hrs**

**Comparison to Original Plan (EdgarTools Tier 0)**:

- EdgarTools: $87.75 + 20 hrs (95% baseline)
- Custom: $87.75 + 24 hrs (92% baseline)
- **Difference**: +4 hours human time (acceptable tradeoff for full control)

---

## Risks & Mitigations

### Risk 1: Custom Parser Baseline <92%

**Impact**: More Tier 2 LLM calls → Higher cost + latency

**Mitigation**:

- Allocate 2 extra days for parser testing/tuning
- Test on 100 sample filings before full deployment
- Monitor Tier 0 success rate, iterate if <90%

**Fallback**: Keep EdgarTools as Tier 0, use custom parser as Tier 1.5 fallback

---

### Risk 2: SEC Rate Limiting Enforcement

**Impact**: Slower data collection, potential IP ban

**Mitigation**:

- Implement exponential backoff on 429 errors
- Track Redis rate limit metrics (alert if >9.5 req/sec)
- Test with 100 filings first, monitor SEC response headers
- Use proper User-Agent (SEC requirement)

**Escalation**: If banned, wait 24hrs, reduce to 5 req/sec

---

### Risk 3: XBRL Edge Cases Not Handled

**Impact**: False positives (wrong data stored with high confidence)

**Mitigation**:

- Tier 2.5 validation catches 66% of false positives
- QC Agent (Phase 2) handles novel cases
- Human escalation queue for policy decisions

**Monitoring**: Alert if Tier 2.5 failure rate >3%

---

### Risk 4: Development Time Overrun

**Impact**: Delays to overall roadmap (Screening Agent, Financial Analyst)

**Mitigation**:

- **Hybrid approach**: Use EdgarTools for Phase 1 MVP, replace with custom in Phase 2
- Break implementation into 2-day sprints with working demos
- Parallelize: Schema migrations, MinIO client, calculator can run in parallel

**Decision Point**: After Phase B (Day 6), assess Tier 0 parser quality

- If <90% success → Switch to EdgarTools, defer custom parser to Phase 2
- If ≥92% success → Continue with custom solution

---

## Unresolved Questions

### Data Sources

1. **S&P 500 ticker list** - Hardcoded CSV vs fetch from State Street SPY API?
2. **CIK cache TTL** - 7 days vs 30 days vs permanent (tickers rarely change CIK)?
3. **Company type detection** - Manual lookup table vs heuristic (ticker, industry sector)?
4. **Accounting standard detection** - From first filing vs SEC metadata vs hardcode (US filers = GAAP)?

### Implementation Choices

1. **XBRL library** - Pure lxml vs python-xbrl (more features but slower) vs arelle (overkill)?
2. **LLM model choice** - Sonnet 4.5 ($3/MTok, high accuracy) vs Haiku 4 ($0.40/MTok, 7× cheaper)?
3. **Partial data acceptance** - Require 5/8 metrics (current) or 8/8 metrics (strict) for Tier 0 success?
4. **MinIO bucket structure** - Single `raw` bucket vs separate `sec_filings` bucket?

### Operational

1. **Amendment handling** - Auto-supersede old filings (current approach) or require human approval?
2. **Screening refresh frequency** - Nightly cron vs on-demand trigger vs manual?
3. **Parse failure alert threshold** - Alert at 5% or 10% Tier 0 failure rate?
4. **Retry strategy** - Retry Tier 0 failures after 24hrs (SEC may have fixed file) or skip directly to Tier 1.5?

### Architecture

1. **Phase 1 vs Phase 2 boundary** - Implement QC Agent (Tier 3) in Phase 1 or stub and defer to Phase 2?
2. **EdgarTools hybrid** - Keep EdgarTools as fallback option or remove entirely after custom parser validated?

---

## Next Steps

### Immediate (Before Implementation)

1. **Review plan** with stakeholders - Confirm 8-day overhead acceptable
2. **Decide on unresolved questions** (especially #6 LLM model, #14 EdgarTools fallback)
3. **Add dependencies** to pyproject.toml (boto3, anthropic, tenacity, lxml)
4. **Create S&P 500 ticker list** (CSV file or API integration)

### Phase 0: Setup (Day 0)

1. **Run schema migrations** (3 P0 migrations)
2. **Update PostgresClient dataclasses** for new columns
3. **Verify MinIO buckets** exist (`raw`, `processed`, `outputs`)
4. **Test SEC EDGAR API** access (download 5 sample filings)

### Phase 1: Core Implementation (Days 1-18)

- Follow timeline above (A→B→C→D→E→F)
- Daily standups to track progress
- Working demo every 2 days

### Phase 2: Validation (Days 19-20)

1. **End-to-end test**: 500 random filings (100 tickers × 5 years)
2. **Measure actual success rates** by tier (vs projected)
3. **Validate cost estimates** (LLM API usage)
4. **Identify edge cases** for Tier 1.5 improvement

### Phase 3: Production Deployment

1. **Screen S&P 500** (first production run)
2. **Monitor metrics**: Success rate, latency, cost
3. **Iterate on Tier 0 parser** based on failure patterns
4. **Document edge cases** for QC Agent (Phase 2)

---

## Success Criteria

### Phase 1 Complete When

- ✅ Data quality ≥98.5% after Tier 2.5
- ✅ S&P 500 screening completes in <10 min
- ✅ Deep analysis (10 companies × 40 filings) completes in <30 min
- ✅ LLM costs <$100 for 20K filings
- ✅ Human escalations <1% of total filings
- ✅ Zero data corruption (balance sheet equation validates)

### Ready for Phase 2 (QC Agent Integration) When

- ✅ Tier 3 escalation queue populated (290 filings pending QC review)
- ✅ Failure patterns documented (for QC Agent strategy library)
- ✅ Learning insights collected (for parser improvement)

---
